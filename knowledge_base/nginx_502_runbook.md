# Runbook: Nginx 502 Bad Gateway
## Symptoms
`502 Bad Gateway` errors or `connect() failed` messages appear in the load balancer logs.
(111: Connection refused) while connecting to upstream`.
## Reason
Backend service (upstream) has gone down, is restarting, or has exhausted its pool of workers.
## Diagnostics (Read-Only)
1. Check the status of the upstream service: `systemctl status app-backend`
2. Check for open ports on a host: `ss -tulpn | grep 8080`
