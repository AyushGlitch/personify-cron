# personify-cron

Daily automation to log steps and sleep on Personify Health. Runs locally or via GitHub Actions (free cloud cron).

## Prerequisites

- [pyenv](https://github.com/pyenv/pyenv) with Python 3.12.12 (see `.python-version`)
- GitHub account (for cloud scheduling)

## Local setup

```bash
cd ~/Developer/helper-apps/personify-cron

# pyenv picks up .python-version automatically
pyenv install -s 3.12.12

# Create venv inside this repo only
python -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt
playwright install chromium

cp .env.example .env
# Edit .env with your credentials and selectors
```

## Configure selectors

Personify UI varies by employer. Record selectors once with Playwright:

```bash
source .venv/bin/activate
playwright codegen https://login.personifyhealth.com
```

Log in manually, navigate to steps/sleep entry, and copy the generated selectors into `.env`.

### Smoke test (login only)

```bash
python log_health.py --skip-validation --debug
```

### Full run

```bash
python log_health.py --debug   # visible browser + screenshots/
python log_health.py           # headless production run
```

## GitHub Actions (free cloud cron)

1. Create a GitHub repo and push this project.
2. Add **Settings → Secrets and variables → Actions** secrets:

| Secret | Required | Example |
|--------|----------|---------|
| `PERSONIFY_EMAIL` | yes | `you@company.com` |
| `PERSONIFY_PASSWORD` | yes | `••••••••` |
| `DAILY_STEPS` | yes | `8500` |
| `SLEEP_HOURS` | yes | `7` |
| `SLEEP_MINUTES` | yes | `30` |
| `SELECTOR_STEPS_INPUT` | yes | from codegen |
| `SELECTOR_STEPS_SAVE` | yes | from codegen |
| `SELECTOR_SLEEP_HOURS_INPUT` | if separate fields | from codegen |
| `SELECTOR_SLEEP_MINUTES_INPUT` | if separate fields | from codegen |
| `SELECTOR_SLEEP_SAVE` | yes | from codegen |
| `PERSONIFY_LOGIN_URL` | no | default login URL |
| `STEPS_PAGE_URL` / `SLEEP_PAGE_URL` | no | direct URLs if known |
| `SELECTOR_*` (login/nav) | no | override defaults |

3. Trigger manually: **Actions → Personify Daily Log → Run workflow**.
4. Scheduled run: daily at 8:00 AM IST (edit cron in `.github/workflows/personify-daily.yml`).

### Private repo on free GitHub plan

Scheduled cron does not run on private repos for free accounts. Options:

- Make the repo **public** (secrets stay encrypted), or
- Use [cron-job.org](https://cron-job.org) to POST to the `workflow_dispatch` API daily.

## Notes

- **SSO / 2FA**: If your employer uses Single Sign-On, this script will stop with a clear error. Device sync (Fitbit, Apple Health) is the reliable alternative.
- **Terms of service**: Automating wellness portal entry may violate your program rules. Use at your own discretion.
- Screenshots on failure are saved to `screenshots/` locally and uploaded as CI artifacts on GitHub.
