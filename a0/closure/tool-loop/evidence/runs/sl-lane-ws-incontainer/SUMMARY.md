# Network-closure solver-lane summary

Probe JSON: `/work/runs/sl-lane-ws-incontainer/wd/inlane_probe.json` (written, exit 0).

## a. DNS

Command:
```
getent hosts example.com
```

Raw output:
```
(no stdout, no stderr)
```
Exit code: `2`

Result: FAILED — name resolution for `example.com` returns nothing.

## b. HTTP direct

Command:
```
python3 -c "import urllib.request;print(urllib.request.urlopen('http://example.com/',timeout=10).status)"
```

Raw output:
```
Traceback (most recent call last):
  File "/usr/local/lib/python3.12/urllib/request.py", line 1344, in do_open
    h.request(req.get_method(), req.selector, req.data, headers,
  File "/usr/local/lib/python3.12/http/client.py", line 1386, in request
    self._send_request(method, url, body, headers, encode_chunked)
  File "/usr/local/lib/python3.12/http/client.py", line 1432, in _send_request
    self.endheaders(body, encode_chunked=encode_chunked)
  File "/usr/local/lib/python3.12/http/client.py", line 1381, in endheaders
    self._send_output(message_body, encode_chunked=encode_chunked)
  File "/usr/local/lib/python3.12/http/client.py", line 1141, in _send_output
    self.send(msg)
  File "/usr/local/lib/python3.12/http/client.py", line 1085, in send
    self.connect()
  File "/usr/local/lib/python3.12/http/client.py", line 1051, in connect
    self.sock = self._create_connection(
                ^^^^^^^^^^^^^^^^^^^^^^^^
  File "/usr/local/lib/python3.12/socket.py", line 841, in create_connection
    for res in getaddrinfo(host, port, 0, SOCK_STREAM):
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/usr/local/lib/python3.12/socket.py", line 978, in getaddrinfo
    for res in _socket.getaddrinfo(host, port, family, type, proto, flags):
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
socket.gaierror: [Errno -3] Temporary failure in name resolution

During handling of the above exception, another exception occurred:

Traceback (most recent call last):
  File "<string>", line 1, in <module>
  File "/usr/local/lib/python3.12/urllib/request.py", line 215, in urlopen
    return opener.open(url, data, timeout)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/usr/local/lib/python3.12/urllib/request.py", line 515, in open
    response = self._open(req, data)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/usr/local/lib/python3.12/urllib/request.py", line 532, in _open
    result = self._call_chain(self.handle_open, protocol, protocol +
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/usr/local/lib/python3.12/urllib/request.py", line 492, in _call_chain
    result = func(*args)
             ^^^^^^^^^^^
  File "/usr/local/lib/python3.12/urllib/request.py", line 1373, in http_open
    return self.do_open(http.client.HTTPConnection, req)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/usr/local/lib/python3.12/urllib/request.py", line 1347, in do_open
    raise URLError(err)
urllib.error.URLError: <urlopen error [Errno -3] Temporary failure in name resolution>
```
Exit code: `1`

Result: FAILED — direct HTTP blocked at DNS resolution.

## c. HTTP proxied

Command:
```
python3 -c "import urllib.request as u;op=u.build_opener(u.ProxyHandler({'https':'http://a0tl-proxy:8787'}));print(op.open('https://example.com/',timeout=10).status)"
```

Raw output:
```
Traceback (most recent call last):
  File "/usr/local/lib/python3.12/urllib/request.py", line 1344, in do_open
    h.request(req.get_method(), req.selector, req.data, headers,
  File "/usr/local/lib/python3.12/http/client.py", line 1386, in request
    self._send_request(method, url, body, headers, encode_chunked)
  File "/usr/local/lib/python3.12/http/client.py", line 1432, in _send_request
    self.endheaders(body, encode_chunked=encode_chunked)
  File "/usr/local/lib/python3.12/http/client.py", line 1381, in endheaders
    self._send_output(message_body, encode_chunked=encode_chunked)
  File "/usr/local/lib/python3.12/http/client.py", line 1141, in _send_output
    self.send(msg)
  File "/usr/local/lib/python3.12/http/client.py", line 1085, in send
    self.connect()
  File "/usr/local/lib/python3.12/http/client.py", line 1520, in connect
    super().connect()
  File "/usr/local/lib/python3.12/http/client.py", line 1051, in connect
    self.sock = self._create_connection(
                ^^^^^^^^^^^^^^^^^^^^^^^^
  File "/usr/local/lib/python3.12/socket.py", line 841, in create_connection
    for res in getaddrinfo(host, port, 0, SOCK_STREAM):
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/usr/local/lib/python3.12/socket.py", line 978, in getaddrinfo
    for res in _socket.getaddrinfo(host, port, family, type, proto, flags):
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
socket.gaierror: [Errno -3] Temporary failure in name resolution

During handling of the above exception, another exception occurred:

Traceback (most recent call last):
  File "<string>", line 1, in <module>
  File "/usr/local/lib/python3.12/urllib/request.py", line 515, in open
    response = self._open(req, data)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/usr/local/lib/python3.12/urllib/request.py", line 532, in _open
    result = self._call_chain(self.handle_open, protocol, protocol +
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/usr/local/lib/python3.12/urllib/request.py", line 492, in _call_chain
    result = func(*args)
             ^^^^^^^^^^^
  File "/usr/local/lib/python3.12/urllib/request.py", line 1392, in https_open
    return self.do_open(http.client.HTTPSConnection, req,
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/usr/local/lib/python3.12/urllib/request.py", line 1347, in do_open
    raise URLError(err)
urllib.error.URLError: <urlopen error [Errno -3] Temporary failure in name resolution>
```
Exit code: `1`

Result: FAILED — the proxy name `a0tl-proxy` itself does not resolve.

## d. Candidate subprocess

Command:
```
mkdir -p /work/runs/sl-lane-ws-incontainer/wd/cand && cp /home/ebt/rsi-dev/a0/tasks/circle-packing/C_STAR/c01_good_hex/solution.py /work/runs/sl-lane-ws-incontainer/wd/cand/solution.py
/home/ebt/rsi-dev/a0/tasks/circle-packing/.venv/bin/python -c "import sys;sys.path.insert(0,'/work/runs/sl-lane-ws-incontainer/wd/cand');import solution;print('sum_radii',sum(r for _,_,r in solution.pack_circles(26)))"
```

Raw output:
```
sum_radii 2.4519205208433132
```
Exit code: `0`

Result: SUCCEEDED — local candidate import and evaluation work with no network.

## Overall

- a (DNS): FAILED  - b (direct HTTP): FAILED  - c (proxied HTTP): FAILED  - d (candidate subprocess): SUCCEEDED
- Network egress is closed (DNS blackholed, proxy name unresolvable); the solver lane's local compute path is unaffected.
