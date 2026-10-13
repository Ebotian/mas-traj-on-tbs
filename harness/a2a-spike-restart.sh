#!/bin/bash
# Restart the spike daemon WITHOUT folderTrust (workspace trusted by default when the feature is off),
# then probe that the collaboration surface is mounted again.
pkill -f "[q]wen serve" 2>/dev/null
sleep 1
mkdir -p /root/.qwen
cat > /root/.qwen/settings.json <<'EOF'
{
  "experimental": {"agentCollaboration": true},
  "security": {"auth": {"selectedType": "openai"}},
  "model": {"name": "deepseek-flash"}
}
EOF
export OPENAI_API_KEY="$A_KEY" OPENAI_BASE_URL="$A_BASE" OPENAI_MODEL="deepseek-flash"
cd /root/spike && nohup qwen serve --no-web --workspace /root/spike > /root/serve.log 2>&1 &
sleep 6
echo "-- serve log tail:"; tail -2 /root/serve.log
echo "-- a2a mount probe (expect JSON-RPC refused, NOT html 404):"
curl -s -X POST http://127.0.0.1:4170/a2a/v1 -H "content-type: application/json" -d '{"jsonrpc":"2.0","id":1,"method":"SendMessage","params":{}}' | head -c 300; echo
echo "-- agents route probe via encoded abs path (expect JSON, NOT html):"
curl -s "http://127.0.0.1:4170/workspaces/%2Froot%2Fspike/agent/agents" | head -c 300; echo
