"""Structured logging with trading-specific context support."""
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

try:
    from pythonjsonlogger import jsonlogger
    _JSON_AVAILABLE = True
except ImportError:
    _JSON_AVAILABLE = False


class TradingAdapter(logging.LoggerAdapter):
    def with_context(self, **kwargs) -> "TradingAdapter":
        return TradingAdapter(self.logger, {**self.extra, **kwargs})

    def process(self, msg, kwargs):
        kwargs.setdefault("extra", {}).update(self.extra)
        return msg, kwargs

    def trade(self, msg, *args, **kwargs):
        kwargs.setdefault("extra", {})["event_type"] = "trade"
        self.info(msg, *args, **kwargs)

    def signal(self, msg, *args, **kwargs):
        kwargs.setdefault("extra", {})["event_type"] = "signal"
        self.info(msg, *args, **kwargs)

    def position(self, msg, *args, **kwargs):
        kwargs.setdefault("extra", {})["event_type"] = "position"
        self.info(msg, *args, **kwargs)

    def risk(self, msg, *args, **kwargs):
        kwargs.setdefault("extra", {})["event_type"] = "risk"
        self.warning(msg, *args, **kwargs)

    def metric(self, msg, *args, **kwargs):
        kwargs.setdefault("extra", {})["event_type"] = "metric"
        self.info(msg, *args, **kwargs)


def setup_logging(
    log_file: str = "trading_bot.log",
    log_level: str = "INFO",
    structured: bool = False,
    log_dir: str = "logs",
) -> TradingAdapter:
    Path(log_dir).mkdir(exist_ok=True)
    log_path = Path(log_dir) / log_file

    fmt = "%(asctime)s - %(levelname)s - %(name)s - %(message)s"
    file_handler = logging.FileHandler(log_path)
    console_handler = logging.StreamHandler(sys.stdout)

    if structured and _JSON_AVAILABLE:
        file_handler.setFormatter(jsonlogger.JsonFormatter("%(timestamp)s %(level)s %(name)s %(message)s"))
        console_handler.setFormatter(logging.Formatter(fmt))
    else:
        formatter = logging.Formatter(fmt)
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)

    logging.basicConfig(
        level=getattr(logging, log_level.upper(), logging.INFO),
        handlers=[file_handler, console_handler],
    )
    logger = logging.getLogger("trading_bot")
    adapter = TradingAdapter(logger, {"start_time": datetime.utcnow().isoformat()})
    adapter.info("Logging started (structured=%s)", structured)
    return adapter


def get_logger(name: str = "trading_bot", extra: Optional[Dict[str, Any]] = None) -> TradingAdapter:
    return TradingAdapter(logging.getLogger(name), extra or {})


def log_trade(logger: TradingAdapter, symbol: str, side: str, qty: int,
              price: float, order_id: str, pnl: Optional[float] = None, **kwargs):
    ctx = logger.with_context(symbol=symbol, trade_id=order_id, event_type="trade")
    msg = f"TRADE {side} {symbol} {qty} @ {price:.2f} (ID: {order_id})"
    if pnl is not None:
        msg += f" P&L: {pnl:.2f}"
    ctx.info(msg, extra=kwargs)


def log_signal(logger: TradingAdapter, symbol: str, signal: str,
               score: float, price: float, **kwargs):
    ctx = logger.with_context(symbol=symbol, event_type="signal")
    ctx.info("SIGNAL %s %s score=%.1f price=%.2f", signal, symbol, score, price, extra=kwargs)


def log_risk_event(logger: TradingAdapter, event_type: str, message: str, **kwargs):
    ctx = logger.with_context(event_type="risk")
    ctx.warning("RISK %s: %s", event_type, message, extra=kwargs)
