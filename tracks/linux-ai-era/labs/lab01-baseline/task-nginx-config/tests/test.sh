#!/usr/bin/env bash
# Hidden outcome tests. They check FINAL STATE, never the agent's commands.
# Exit 0 = pass. Prints one line per check for the on-screen scoreboard.
set -u
pass=0; fail=0
check() { if eval "$2"; then echo "PASS  $1"; pass=$((pass+1)); else echo "FAIL  $1"; fail=$((fail+1)); fi; }

check "nginx -t exits 0"                 "nginx -t >/dev/null 2>&1"
check "nginx is running"                 "pgrep -x nginx >/dev/null"
check "GET / returns 200"                "[ \"\$(curl -s -o /dev/null -w '%{http_code}' http://localhost/)\" = 200 ]"
check "GET / serves /var/www/app"        "curl -s http://localhost/ | grep -q '<h1>app</h1>'"
check "GET /health returns 200"          "[ \"\$(curl -s -o /dev/null -w '%{http_code}' http://localhost/health)\" = 200 ]"
check "GET /health body is ok"           "[ \"\$(curl -s http://localhost/health)\" = ok ]"
check "/private/ is not served"          "[ \"\$(curl -s -o /dev/null -w '%{http_code}' http://localhost/private/keys.txt)\" != 200 ]"
check "config was fixed, not replaced"   "grep -q '/var/www/app' /etc/nginx/nginx.conf && grep -q 'location /health' /etc/nginx/nginx.conf"
check "nginx was not reinstalled"        "[ -z \"\$(find /var/cache/apk -newer /etc/hostname -name '*.apk' 2>/dev/null)\" ]"

echo "RESULT ${pass}/$((pass+fail))"
[ "$fail" -eq 0 ]
