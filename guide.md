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

When a reminder fires (11 AM / 2 PM / 3:30 PM):

```bash
cd ~/Developer/helper-apps/personify-cron
source .venv/bin/activate
python log_health.py --use-auth --headed
```

Headless (no browser window):

```bash
python log_health.py --use-auth
```

## Common flags

| Flag | Purpose |
|------|---------|
| `--use-auth` | Reuse `auth.json`, skip login |
| `--save-auth` | Save/update `auth.json` after run |
| `--manual-login` | You login + 2FA, press Enter |
| `--headed` | Show browser |
| `--steps-only` | Steps only |
| `--sleep-only` | Sleep only |

## Reminders

```bash
./scripts/install-reminders.sh   # 11:00, 14:00, 15:30
./scripts/remind.sh              # test notification
./scripts/uninstall-reminders.sh
```

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
