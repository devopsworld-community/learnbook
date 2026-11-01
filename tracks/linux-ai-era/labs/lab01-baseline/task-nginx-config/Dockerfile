# Builds the BROKEN state. Harbor/Terminal-Bench convention: the container is the task.
FROM nginx:1.27-alpine

RUN apk add --no-cache curl bash
RUN mkdir -p /var/www/app /var/www/private \
 && echo '<h1>app</h1>' > /var/www/app/index.html \
 && echo 'SECRET-DO-NOT-SERVE' > /var/www/private/keys.txt

# Four planted faults, the kind an on-call engineer meets at 03:00:
#  1. a missing semicolon after the root directive
#  2. a `location /health` block that returns the wrong body and status
#  3. an `alias` that exposes /var/www/private under /private/
#  4. a worker_processes value that nginx rejects
COPY nginx.conf /etc/nginx/nginx.conf
COPY instruction.md /instruction.md
COPY tests/ /tests/
COPY solution/ /solution/
RUN chmod +x /tests/test.sh /solution/solve.sh

# Keep the container alive without nginx running; the agent must bring it up.
CMD ["sleep", "infinity"]
