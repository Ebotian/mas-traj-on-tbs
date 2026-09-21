#!/usr/bin/env bash
# =============================================================================
# probe_loreley_services.sh -- requirement 4.
#
# Loreley runs a worker plus separate Postgres and Redis containers. The worker
# must reach them. This probe answers: can they simply join the internal network
# and be addressed by container name, and does that change the closure claim?
#
# It starts throwaway services named a0pc-pg / a0pc-redis (postgres:16, redis:8
# are already present locally; nothing is pulled or installed) and exercises:
#   1. reachability by container name from the internal side
#   2. the host's own reachability INTO the internal network
#   3. whether the internal client's egress is still blocked with the services up
#   4. whether DUAL-HOMING a service onto the bridge hands the worker an uplink
#   5. whether a service's own reachability follows its interfaces
# =============================================================================
set -uo pipefail

NET="${NET:-a0pc-internal}"
CLI_CTR="${CLI_CTR:-a0pc-cli}"
PG="${PG:-a0pc-pg}"
REDIS="${REDIS:-a0pc-redis}"

banner() { echo; echo "===== $* ====="; }

banner "0. start throwaway services on $NET (internal-only)"
docker rm -f "$PG" "$REDIS" >/dev/null 2>&1 || true
docker run -d --name "$PG" --network "$NET" -e POSTGRES_PASSWORD=a0pc -e POSTGRES_DB=a0pc postgres:16 >/dev/null
docker run -d --name "$REDIS" --network "$NET" redis:8 redis-server --save '' --appendonly no >/dev/null
for _ in $(seq 1 40); do docker exec "$PG" pg_isready -U postgres >/dev/null 2>&1 && break; sleep 1; done
docker network inspect "$NET" --format '  peers: {{range .Containers}}{{.Name}}({{.IPv4Address}}) {{end}}'

banner "1. from the internal side: reach the services BY CONTAINER NAME"
docker exec "$CLI_CTR" python3 -c '
import socket
for h,p in [("a0pc-pg",5432),("a0pc-redis",6379),("a0pc-proxy",8787)]:
    s=socket.socket(); s.settimeout(6)
    try: s.connect((h,p)); print("  %-14s:%-5d -> CONNECTED  (dns %s)" % (h,p,socket.gethostbyname(h)))
    except Exception as e: print("  %-14s:%-5d -> %s" % (h,p,e))
    s.close()
'

banner "2. from the HOST: is an internal-only container reachable?"
PGIP=$(docker inspect "$PG" --format "{{(index .NetworkSettings.Networks \"$NET\").IPAddress}}")
echo "  $PG = $PGIP"
python3 -c "
import socket
s=socket.socket(); s.settimeout(6)
try: s.connect(('$PGIP',5432)); print('  host -> $PGIP:5432 CONNECTED -- the internal net is one-way: no egress out, but ingress from the host owner')
except Exception as e: print('  host -> $PGIP:5432 ->',type(e).__name__,e)
"

banner "3. with the services up, is the internal client's OWN egress still blocked?"
docker exec "$CLI_CTR" python3 -c '
import socket
for t in [("123.148.116.184",443),("1.1.1.1",443),("8.8.8.8",53)]:
    s=socket.socket(); s.settimeout(6)
    try: s.connect(t); print("  DIRECT %-24s -> CONNECTED (LEAK)" % (t,))
    except Exception as e: print("  DIRECT %-24s -> %s" % (t,e))
    s.close()
'

banner "4. dual-home $REDIS and $PG onto the default bridge -- does the worker gain an uplink?"
docker network connect bridge "$REDIS" >/dev/null 2>&1
docker network connect bridge "$PG" >/dev/null 2>&1
for c in "$PG" "$REDIS"; do echo -n "  $c:"; docker inspect "$c" --format '{{range $k,$v := .NetworkSettings.Networks}} {{$k}}({{$v.IPAddress}}){{end}}'; done
docker exec "$CLI_CTR" python3 -c '
import socket
print("  client -> a0pc-pg:5432        :", end=" ")
s=socket.socket(); s.settimeout(5)
try: s.connect(("a0pc-pg",5432)); print("CONNECTED (still reachable by name)")
except Exception as e: print(e)
print("  client -> 1.1.1.1:443          :", end=" ")
s=socket.socket(); s.settimeout(5)
try: s.connect(("1.1.1.1",443)); print("CONNECTED  <-- LEAK")
except Exception as e: print(e)
print("  client -> bridge-side redis IP :", end=" ")
s=socket.socket(); s.settimeout(5)
try: s.connect((socket.gethostbyname("a0pc-redis") if True else "",0))
except Exception: pass
'

banner "5. the service's OWN reachability follows its interfaces, not its callers"
docker exec "$REDIS" bash -c 'timeout 6 bash -c "cat < /dev/null > /dev/tcp/123.148.116.184/443" 2>/dev/null && echo "  redis (dual-homed) -> model endpoint: REACHABLE" || echo "  redis -> model endpoint: NOT reachable"'
docker network disconnect bridge "$REDIS" >/dev/null 2>&1
docker network disconnect bridge "$PG" >/dev/null 2>&1
docker exec "$REDIS" bash -c 'timeout 6 bash -c "cat < /dev/null > /dev/tcp/123.148.116.184/443" 2>/dev/null && echo "  redis (internal-only) -> model endpoint: REACHABLE" || echo "  redis (internal-only) -> model endpoint: NOT reachable"'

echo
echo "probe_loreley_services.sh: done $(date -Is)"
echo "left running (see teardown.sh): $PG, $REDIS"
