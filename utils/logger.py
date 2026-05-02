"""
Structured Logging - Enhanced logging with JSON support.

Inspired by Career-Ops automation patterns.
Supports both human-readable and structured JSON formats.
"""

import logging
import sys
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional

try:
    from pythonjsonlogger import jsonlogger
    JSON_LOGGER_AVAILABLE = True
except ImportError:
    JSON_LOGGER_AVAILABLE = False
    jsonlogger = None


class StructuredLogFormatter(logging.Formatter if not JSON_LOGGER_AVAILABLE else jsonlogger.JsonFormatter):
    """Custom JSON formatter for trading logs."""
    
    def add_fields(self, log_record, record, message_dict):
        super().add_fields(log_record, record, message_dict)
        
        # Add timestamp in ISO format
        log_record['timestamp'] = datetime.utcnow().isoformat()
        log_record['level'] = record.levelname
        log_record['logger'] = record.name
        
        # Add trading-specific fields if present
        if hasattr(record, 'symbol'):
            log_record['symbol'] = record.symbol
        if hasattr(record, 'trade_id'):
            log_record['trade_id'] = record.trade_id
        if hasattr(record, 'strategy'):
            log_record['strategy'] = record.strategy


class TradingAdapter(logging.LoggerAdapter):
    """Logger adapter with trading context."""
    
    def __init__(self, logger, extra: Optional[Dict[str, Any]] = None):
        super().__init__(logger, extra or {})
    
    def with_context(self, **kwargs) -> 'TradingAdapter':
        """Create new adapter with additional context."""
        new_extra = {**self.extra, **kwargs}
        return TradingAdapter(self.logger, new_extra)
    
    def process(self, msg, kwargs):
        # Merge extra dict into kwargs
        kwargs.setdefault('extra', {})
        kwargs['extra'].update(self.extra)
        return msg, kwargs
    
    def trade(self, msg, *args, **kwargs):
        """Log trade event."""
        self._log_with_type('trade', msg, *args, **kwargs)
    
    def signal(self, msg, *args, **kwargs):
        """Log signal event."""
        self._log_with_type('signal', msg, *args, **kwargs)
    
    def position(self, msg, *args, **kwargs):
        """Log position event."""
        self._log_with_type('position', msg, *args, **kwargs)
    
    def risk(self, msg, *args, **kwargs):
        """Log risk event."""
        self._log_with_type('risk', msg, *args, **kwargs)
    
    def metric(self, msg, *args, **kwargs):
        """Log metric event."""
        self._log_with_type('metric', msg, *args, **kwargs)
    
    def _log_with_type(self, event_type: str, msg, *args, **kwargs):
        """Log with event type."""
        kwargs.setdefault('extra', {})
        kwargs['extra']['event_type'] = event_type
        self.info(msg, *args, **kwargs)


def setup_logging(
    log_file: str = "trading_bot.log",
    log_level: str = "INFO",
    structured: bool = False,
    log_dir: str = "logs"
) -> TradingAdapter:
    """
    Setup logging with optional structured JSON format.
    
    Args:
        log_file: Log file name
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
        structured: Use JSON format for machine parsing
        log_dir: Directory for log files
        
    Returns:
        TradingAdapter with context support
    """
    log_dir_path = Path(log_dir)
    log_dir_path.mkdir(exist_ok=True)
    
    log_path = log_dir_path / log_file
    
    # Create handlers
    file_handler = logging.FileHandler(log_path)
    console_handler = logging.StreamHandler(sys.stdout)
    
    if structured and JSON_LOGGER_AVAILABLE:
        # JSON format for structured logging
        formatter = StructuredLogFormatter(
            '%(timestamp)s %(level)s %(name)s %(message)s'
        )
        file_handler.setFormatter(formatter)
        
        # Console still gets human-readable format
        console_formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'
        )
        console_handler.setFormatter(console_formatter)
    else:
        # Human-readable format
        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(name)s - %(message)s'
        )
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
    
    # Configure root logger
    logging.basicConfig(
        level=getattr(logging, log_level.upper(), logging.INFO),
        handlers=[file_handler, console_handler]
    )
    
    logger = logging.getLogger("trading_bot")
    adapter = TradingAdapter(logger, {
        'start_time': datetime.utcnow().isoformat()
    })
    
    adapter.info(f"Logging initialized at {datetime.now()} (structured={structured})")
    return adapter


def get_logger(name: str = "trading_bot", extra: Optional[Dict[str, Any]] = None) -> TradingAdapter:
    """
    Get a trading logger adapter.
    
    Args:
        name: Logger name
        extra: Extra context fields
        
    Returns:
        TradingAdapter instance
    """
    logger = logging.getLogger(name)
    return TradingAdapter(logger, extra or {})


def log_trade(
    logger: TradingAdapter,
    symbol: str,
    side: str,
    qty: int,
    price: float,
    order_id: str,
    pnl: Optional[float] = None,
    **kwargs
):
    """
    Log a trade event.
    
    Args:
        logger: TradingAdapter instance
        symbol: Trading symbol
        side: BUY or SELL
        qty: Quantity
        price: Price
        order_id: Order ID
        pnl: Optional P&L
        **kwargs: Additional fields
    """
    ctx_logger = logger.with_context(
        symbol=symbol,
        trade_id=order_id,
        event_type='trade'
    )
    
    msg = f"TRADE {side} {symbol} {qty} @ {price:.2f} (ID: {order_id})"
    if pnl is not None:
        msg += f" P&L: {pnl:.2f}"
    
    ctx_logger.info(msg, extra=kwargs)


def log_signal(
    logger: TradingAdapter,
    symbol: str,
    signal: str,
    score: float,
    price: float,
    **kwargs
):
    """Log a signal event."""
    ctx_logger = logger.with_context(
        symbol=symbol,
        event_type='signal'
    )
    ctx_logger.info(
        f"SIGNAL {signal} {symbol} Score: {score:.1f} Price: {price:.2f}",
        extra={'signal': signal, 'score': score, **kwargs}
    )


def log_position(
    logger: TradingAdapter,
    symbol: str,
    action: str,
    side: str,
    qty: int,
    price: float,
    **kwargs
):
    """Log a position event."""
    ctx_logger = logger.with_context(
        symbol=symbol,
        event_type='position'
    )
    ctx_logger.info(
        f"POSITION {action} {side} {symbol} {qty} @ {price:.2f}",
        extra={'action': action, **kwargs}
    )


def log_metric(
    logger: TradingAdapter,
    metric_name: str,
    value: float,
    **kwargs
):
    """Log a metric."""
    ctx_logger = logger.with_context(
        event_type='metric'
    )
    ctx_logger.info(
        f"METRIC {metric_name}={value:.4f}",
        extra={'metric': metric_name, 'value': value, **kwargs}
    )


def log_risk_event(
    logger: TradingAdapter,
    event_type: str,
    message: str,
    **kwargs
):
    """Log a risk-related event."""
    ctx_logger = logger.with_context(
        event_type='risk'
    )
    ctx_logger.warning(f"RISK {event_type}: {message}", extra=kwargs)


# Backward compatibility
setup_logging = setup_logging
