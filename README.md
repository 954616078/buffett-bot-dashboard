# Trend_OB_AI

A lightweight Trend + Order Book scanner that:
- Uses LongPort OpenAPI for K-line data (with Yahoo fallback for OB when depth is unavailable)
- Dynamically monitors top US market-cap stocks (default: top 100)
- Computes trend and order-book pressure signals
- Calls local OpenClaw for entry/SL/TP style analysis
- Saves every scan result into SQLite
- Sends Telegram alerts only when actionable signals appear
- Runs paper trading automatically with a $20,000 virtual account when rules are hit

## Files
- `config.py`: strategy/runtime config
- `data_fetch.py`: Playwright fetch + HTML parsing
- `trend_analysis.py`: MA trend signal
- `ob_analysis.py`: bid/ask pressure signal
- `ai_reminder.py`: OpenClaw + Telegram integration
- `database.py`: SQLite storage
- `run_system.py`: main runner

## Setup
```bash
pip install -r requirements.txt
playwright install
```

## Run
```bash
python run_system.py
```

## Web Dashboard (Visualization + Operations)
The dashboard provides:
- Equity curve and account KPIs
- Fund-style KPIs: win rate, Sharpe, profit factor, max drawdown, turnover
- Portfolio circuit breaker controls: daily loss limit + max drawdown limit
- Current positions and unrealized PnL
- Latest valid signals and paper orders
- One-click actions: run scan / run daily review
- One-click Telegram summary push
- Runtime strategy settings (saved in DB, editable on web)
- Login authentication for dashboard access

### Start locally
```bash
pip install -r requirements.txt
python run_dashboard.py
```
Open: `http://localhost:8080`

### Dashboard login
By default, login is enabled.
- username: `admin`
- password: `ChangeMe123!`

Please override in production:
- `DASHBOARD_AUTH_ENABLED=1`
- `DASHBOARD_USERNAME=your_user`
- `DASHBOARD_PASSWORD=your_password`
- `DASHBOARD_SECRET_KEY=your_secret`

### Endpoints
- `GET /api/summary`
- `GET /api/equity`
- `GET /api/positions`
- `GET /api/signals`
- `GET /api/orders`
- `POST /api/run/scan`
- `POST /api/run/review`
- `POST /api/run/telegram`
- `GET /api/settings`
- `POST /api/settings`
- `GET /api/fund-metrics`
- `GET /api/daily-comment`

### Deploy online (quick path)
Use any Python web host (Render/Railway/Fly.io/VPS).
- Start command: `python run_dashboard.py`
- Runtime env:
  - `DASHBOARD_HOST=0.0.0.0`
  - `DASHBOARD_PORT=8080` (or provider port)
  - all existing bot env vars (LongPort/OpenClaw/Telegram) if needed
- Persist `trades.db` on a mounted volume (or switch to managed DB later).

For Render Blueprint, this repo also includes: `render.yaml`

## LongPort Credentials
Set these environment variables before running:

```powershell
$env:LONGPORT_APP_KEY="your_app_key"
$env:LONGPORT_APP_SECRET="your_app_secret"
$env:LONGPORT_ACCESS_TOKEN="your_access_token"
$env:USE_LONGPORT="1"
```

## What counts as a signal
- Default policy: aligned signal only
  - `UPTREND + BUY_PRESSURE`
  - `DOWNTREND + SELL_PRESSURE`
- Non-signal symbols are still saved into SQLite but won't trigger Telegram.

## Paper Trading
- Enabled by default (`PAPER_TRADING_ENABLED=1`)
- Initial virtual capital: `$20,000` (`PAPER_INITIAL_CASH`)
- Rule A (`UPTREND+BUY_PRESSURE`): buy candidate
- Rule B (`DOWNTREND+SELL_PRESSURE`): sell/exit candidate
- Auto risk learning: adjusts `risk_pct` based on recent win rate
- SQLite tables:
  - `paper_account`
  - `paper_positions`
  - `paper_orders`

## Telegram Summary (optional)
Set target chat/user before running:

```powershell
$env:TELEGRAM_TARGET="@your_username"
python run_system.py
```

or use chat id:

```powershell
$env:TELEGRAM_TARGET="123456789"
python run_system.py
```

## Notes
- Yahoo quote page typically provides top-level `Bid x Size` and `Ask x Size`, not full L2 depth.
- OpenClaw local analysis requires your local OpenClaw environment to be healthy.
- SQLite DB file is created as `trades.db` in this project directory.
