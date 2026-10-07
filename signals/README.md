# Signals
    pip install -r requirements.txt
    python cli.py backtest          # one-time: history -> signals.db + ema200_breakout_trades.csv
    python cli.py serve             # dashboard at http://127.0.0.1:8000
    python cli.py scan              # daily after 16:00 IST: updates DB + Telegram alerts

Telegram: create a bot with @BotFather, send it a message, then set
TELEGRAM_TOKEN and TELEGRAM_CHAT_ID (from https://api.telegram.org/bot<TOKEN>/getUpdates).
Schedule (Linux cron, Mon-Fri 16:15 IST):  15 16 * * 1-5 cd /path/signals && python cli.py scan
Windows: Task Scheduler running `python cli.py scan`.
New strategy: add app/strategies/<name>.py (subclass Strategy) and register it in __init__.py.

## Telegram setup (free, 2 minutes)
1. In Telegram open @BotFather -> /newbot -> copy the token.
2. Copy `.env.example` to `.env`, paste the token as TELEGRAM_TOKEN.
3. Send any message to your new bot, then run `python cli.py telegram-test` - it prints your chat id.
4. Put it in `.env` as TELEGRAM_CHAT_ID and run `python cli.py telegram-test` again; you should get a test message.

## Free daily deployment (GitHub Actions + GitHub Pages)
1. Put the project in a GitHub repo (public - GitHub Pages is free only for public repos). Never commit `.env`.
2. Copy `deploy/daily.yml` to `<repo root>/.github/workflows/daily.yml` (edit `working-directory` / `path` if `signals/` is not a subfolder).
3. Repo Settings -> Secrets and variables -> Actions: add `TELEGRAM_TOKEN` and `TELEGRAM_CHAT_ID`.
4. Repo Settings -> Pages -> Source: **GitHub Actions**.
5. Actions tab -> daily-scan -> **Run workflow** (first run builds history and sends the first report). After that it runs Mon-Fri at 18:00 IST.
Dashboard: `https://<user>.github.io/<repo>/`.  Local test of the report: `FORCE_REPORT=1 python cli.py scan`.

## BSE stocks
`UNIVERSE=nse,bse` (default) also scans BSE-only stocks (not listed on NSE; duplicates removed by ISIN), shown as `NAME.BO`.
`BSE_GROUPS=A,B` limits to liquid BSE groups. If the BSE list download fails, save BSE's "List of Scrips -> Equity" CSV as `bse_scrips.csv` next to `cli.py`.
