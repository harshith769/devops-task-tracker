# Linux fundamentals – commands practised (Ubuntu)

## Navigation and files
| Command | Purpose |
|---|---|
| `pwd`, `ls -lah`, `cd -` | where am I, list with sizes and hidden files, go back |
| `mkdir -p a/b/c`, `cp -r`, `mv`, `rm -i` | create nested dirs, copy, move/rename, delete with confirmation |
| `find . -name "*.log" -mtime +7` | files ending in .log older than 7 days |
| `grep -rn "ERROR" logs/` | search text recursively with line numbers |
| `less`, `head -n 20`, `tail -f app.log` | read files; follow a growing log |
| `du -sh *`, `df -h` | disk usage per folder; free space per filesystem |
| `tar -czf backup.tar.gz dir/`, `tar -tzf` | create and list a compressed archive |

## Users and permissions
| Command | Purpose |
|---|---|
| `whoami`, `id`, `groups` | current user, UID/GID, group membership |
| `chmod 755 script.sh`, `chmod u+x` | rwx for owner, r-x for group/others; add execute bit |
| `chmod 600 ~/.ssh/id_ed25519` | private key readable only by its owner |
| `chown appuser:appuser /app/data` | change owner and group |
| `sudo useradd -m -u 10001 appuser` | create an unprivileged service user |
| `umask` | default permissions for new files |

## Processes and services
| Command | Purpose |
|---|---|
| `ps aux \| grep gunicorn`, `pgrep -a python` | find running processes |
| `top`, `htop` | live CPU / memory per process |
| `kill -TERM <pid>`, `kill -9 <pid>` | graceful stop; force stop |
| `nohup cmd &`, `jobs`, `fg` | run in background; manage jobs |
| `systemctl status docker`, `journalctl -u docker -f` | service state and its logs |
| `ss -ltnp` | which process listens on which port |
| `crontab -e` | schedule `scripts/backup.sh` and `scripts/rotate_logs.py` |

## Networking
| Command | Purpose |
|---|---|
| `curl -i localhost:8000/health` | HTTP request with response headers |
| `ip a`, `ping`, `dig example.com` | interfaces, reachability, DNS lookup |
