# Task: nginx will not start

The web server on this host is down. `systemctl status nginx` (or `nginx -t` in the container)
reports a configuration error. Restore service so that:

1. `nginx -t` exits 0.
2. `curl -s -o /dev/null -w '%{http_code}' http://localhost/` returns `200`.
3. `curl -s http://localhost/health` returns the body `ok`.
4. The site must keep serving from `/var/www/app` and must NOT expose `/var/www/private`
   (a request to `/private/` must return 403 or 404).

Do not reinstall nginx. Do not replace the whole config with a default; fix the existing one.
When done, state what you changed and what you did not verify.
