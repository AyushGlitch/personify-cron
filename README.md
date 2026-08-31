# personify-cron

Log steps and sleep on Personify Health locally.

**→ See [guide.md](guide.md) for commands and daily workflow.**

## Quick start

```bash
source .venv/bin/activate
python log_health.py --headed --manual-login --save-auth   # once (2FA)
python log_health.py --use-auth --headed                   # daily runs
```

## Reminders

```bash
./scripts/install-reminders.sh   # 11 AM, 2 PM, 3:30 PM
```
