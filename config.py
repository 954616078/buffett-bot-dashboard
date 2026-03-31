"""Runtime configuration for the Trend + OB scanner."""

from __future__ import annotations

import os

# Fallback list if dynamic top-market-cap universe cannot be fetched.
STOCK_LIST = ["AAPL", "NVDA", "TSLA"]

# Universe selection
USE_TOP_MARKETCAP_UNIVERSE = os.getenv("USE_TOP_MARKETCAP_UNIVERSE", "1") == "1"
TOP_MARKETCAP_COUNT = int(os.getenv("TOP_MARKETCAP_COUNT", "100"))
TOP_MARKETCAP_SOURCE_URL = os.getenv(
    "TOP_MARKETCAP_SOURCE_URL",
    "https://companiesmarketcap.com/usa/largest-companies-in-the-usa-by-market-cap/",
)

# Alert policy
ALERT_ONLY_WHEN_SIGNAL = os.getenv("ALERT_ONLY_WHEN_SIGNAL", "1") == "1"
ALERT_REQUIRE_ALIGNMENT = os.getenv("ALERT_REQUIRE_ALIGNMENT", "1") == "1"  # UPTREND+BUY_PRESSURE or DOWNTREND+SELL_PRESSURE
MAX_ALERTS_PER_RUN = int(os.getenv("MAX_ALERTS_PER_RUN", "30"))
MA_SHORT = 20
MA_LONG = 60
OB_DEPTH = 20
HEADLESS_BROWSER = True
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "trades.db")

# Optional: set this if you want a daily summary pushed to Telegram via OpenClaw.
# Examples: "@your_username" or "123456789" (chat id)
TELEGRAM_TARGET = os.getenv("TELEGRAM_TARGET", "")

# Optional timeout tuning (seconds)
FETCH_TIMEOUT_SECONDS = 30
OPENCLAW_TIMEOUT_SECONDS = 120

# Data source
USE_LONGPORT = os.getenv("USE_LONGPORT", "1") == "1"
LONGPORT_KLINE_COUNT = int(os.getenv("LONGPORT_KLINE_COUNT", "120"))

# Paper trading (simulation only) - OPTIMIZED + EVOLUTION
PAPER_TRADING_ENABLED = os.getenv("PAPER_TRADING_ENABLED", "1") == "1"
PAPER_INITIAL_CASH = float(os.getenv("PAPER_INITIAL_CASH", "20000"))
PAPER_BASE_RISK_PCT = float(os.getenv("PAPER_BASE_RISK_PCT", "0.005"))  # 0.5% equity risk per trade
PAPER_MIN_RISK_PCT = float(os.getenv("PAPER_MIN_RISK_PCT", "0.003"))  # 0.3% min
PAPER_MAX_RISK_PCT = float(os.getenv("PAPER_MAX_RISK_PCT", "0.01"))  # 1% max
PAPER_MAX_POSITION_PCT = float(os.getenv("PAPER_MAX_POSITION_PCT", "0.05"))  # max 5% per symbol
PAPER_MAX_POSITIONS = int(os.getenv("PAPER_MAX_POSITIONS", "5"))  # max 5 open positions
PAPER_STOP_LOSS_PCT = float(os.getenv("PAPER_STOP_LOSS_PCT", "0.015"))  # 1.5% stop loss
PAPER_TAKE_PROFIT_PCT = float(os.getenv("PAPER_TAKE_PROFIT_PCT", "0.06"))  # 6% take profit
PAPER_TRAILING_STOP_PCT = float(os.getenv("PAPER_TRAILING_STOP_PCT", "0.03"))  # 3% trailing stop
PAPER_LEARN_LOOKBACK = int(os.getenv("PAPER_LEARN_LOOKBACK", "20"))

# === 自我进化参数 (Self-Evolution Parameters) ===
# 持仓时间限制 (天)
MAX_HOLD_DAYS = int(os.getenv("MAX_HOLD_DAYS", "5"))

# 技术过滤开关
USE_RSI_FILTER = os.getenv("USE_RSI_FILTER", "1") == "1"
MIN_RSI_BUY = float(os.getenv("MIN_RSI_BUY", "35"))  # RSI低于35超卖时买入
MAX_RSI_SELL = float(os.getenv("MAX_RSI_SELL", "65"))  # RSI高于65超买时卖出

USE_MACD_FILTER = os.getenv("USE_MACD_FILTER", "0") == "1"  # MACD金叉确认(实验性)

# 信号强度过滤
REQUIRE_MULTIPLE_SIGNALS = os.getenv("REQUIRE_MULTIPLE_SIGNALS", "0") == "1"  # 需要多周期确认

# 趋势持续性过滤
MIN_TREND_DAYS = int(os.getenv("MIN_TREND_DAYS", "2"))  # 趋势至少持续2天
