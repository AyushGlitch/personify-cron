# Personify Cron — Quick Guide

## Setup (once)

```bash
cd ~/Developer/helper-apps/personify-cron
pyenv install -s 3.12.12
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium
cp .env.example .env   # add email, password, steps
```

## Save session (once, with 2FA)

Log in by hand, enter email security code, then save cookies:

```bash
source .venv/bin/activate
python log_health.py --headed --manual-login --save-auth
```

Creates `auth.json` (gitignored). Re-do when session expires.

## Daily run (no 2FA)

Default **home flow**: sleep (7–10h random), steps (7001–21000 random), random mood, daily cards OK if available.

```bash
cd ~/Developer/helper-apps/personify-cron
source .venv/bin/activate
python log_health.py --use-auth --headed
```

Legacy **stats-page flow**:

```bash
python log_health.py --use-auth --headed --flow stats
```

## Common flags

| Flag | Purpose |
|------|---------|
| `--use-auth` | Reuse `auth.json`, skip login |
| `--save-auth` | Save/update `auth.json` after run |
| `--manual-login` | You login + 2FA, press Enter |
| `--headed` | Show browser |
| `--flow home` | Healthy Habits dashboard (default) |
| `--flow stats` | Legacy stats-page flow |
| `--steps-only` | Steps only |
| `--sleep-only` | Sleep only |
| `--skip-mood` | Skip mood (home flow) |
| `--skip-cards` | Skip daily cards (home flow) |

## Reminders

```bash
./scripts/install-reminders.sh   # 11:00, 14:00, 15:30
./scripts/remind.sh              # test now (popup with Run / Later)
./scripts/uninstall-reminders.sh
```

Reminders use **launchd** — Mac must be **awake and logged in** at the scheduled time (missed times are not retried).

### Reminders not showing?

1. Test manually: `./scripts/remind.sh` — you should hear a sound and see a popup.
2. Check if launchd fired: `cat /tmp/personify-reminder.log`
3. Reinstall: `./scripts/uninstall-reminders.sh && ./scripts/install-reminders.sh`
4. Force a run now: `launchctl kickstart -k "gui/$(id -u)/com.personify.reminder"`

## Session expired?

```bash
python log_health.py --headed --manual-login --save-auth
```

## Files

| File | Purpose |
|------|---------|
| `.env` | Credentials + values (never commit) |
| `auth.json` | Saved login session (never commit) |
| `screenshots/` | Debug captures on failure |
