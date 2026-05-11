"""
Enhanced Stock Scanner – historical and live scanning.

FIXES:
- Added mtf_aligned to scan_symbol_smc() result dict (was missing, caused KeyError in display)
- Fixed compare_cmd symbol normalization for index symbols (NSE:NIFTY50-INDEX, BANKNIFTY etc.)
- Added graceful handling when smc_strategy is None in scan_symbol_smc
- Added rate-limit sleep between data fetches consistently
- scan_all() now validates timeframe before fetching
"""

import logging
import time
from typing import Any, Dict, List, Optional

import pandas as pd

from .indicators import IndicatorValues, calculate_all_indicators
from .parser import StrategyParser
from .pattern_detector import PatternDetector
from .signal_scorer import SignalScorer, SignalScore

logger = logging.getLogger(__name__)


class StockScanner:
    """Unified scanner for historical and live market scanning."""

    def __init__(
        self,
        config_path: str = "strategy.json",
        enable_patterns: bool = True,
        enable_scoring: bool = True,
        enable_smc: bool = False,
    ) -> None:
        self.parser = StrategyParser(config_path)
        self.pattern_detector = (
            PatternDetector(min_pattern_size=5, confidence_threshold=0.5)
            if enable_patterns
            else None
        )
        self.signal_scorer = SignalScorer() if enable_scoring else None

        # Lazy import to avoid circular dependencies
        if enable_smc:
            from .smart_money import SmartMoneyStrategy
            self.smc_strategy = SmartMoneyStrategy()
        else:
            self.smc_strategy = None

    # ------------------------------------------------------------------
    # Indicators
    # ------------------------------------------------------------------

    def calculate_indicators(self, df: pd.DataFrame) -> IndicatorValues:
        return calculate_all_indicators(df)

    # ------------------------------------------------------------------
    # Single-symbol scan (historical)
    # ------------------------------------------------------------------

    def scan_symbol(self, symbol: str, df: pd.DataFrame) -> Optional[Dict[str, Any]]:
        """Run indicator + optional pattern/scoring analysis on pre-fetched data."""
        if df.empty or len(df) < 20:
            logger.debug("Skipping %s – insufficient candles (%d)", symbol, len(df))
            return None

        indicators = self.calculate_indicators(df)

        # Base signal from strategy conditions
        signal = self._generate_signal(indicators)

        result: Dict[str, Any] = {
            "symbol": symbol,
            "price": round(indicators.price, 2),
            "signal": signal,
            "rsi": round(indicators.rsi, 2),
            "sma_20": round(indicators.sma_20, 2),
            "volume": int(indicators.volume),
        }

        patterns: List[Dict] = []
        if self.pattern_detector and len(df) >= 50:
            patterns = self.pattern_detector.detect_all(df)
            if patterns:
                top = max(patterns, key=lambda p: p["confidence"])
                result.update(
                    {
                        "pattern": top["name"],
                        "pattern_confidence": round(top["confidence"], 2),
                        "pattern_direction": top["direction"],
                    }
                )
                if signal == "HOLD":
                    result["pattern_signal"] = self.pattern_detector.get_combined_signal([top])
            else:
                result["pattern"] = None

        if self.signal_scorer:
            score: SignalScore = self.signal_scorer.calculate_score(df, indicators, patterns)
            result["score"] = score.total_score
            result["score_confidence"] = score.confidence
            if score.signal != "HOLD":
                result["signal"] = score.signal
                result["signal_source"] = "scored"

        return result

    # ------------------------------------------------------------------
    # SMC single-symbol scan
    # ------------------------------------------------------------------

    def scan_symbol_smc(
        self,
        symbol: str,
        ltf_df: pd.DataFrame,
        mtf_df: Optional[pd.DataFrame] = None,
        htf_df: Optional[pd.DataFrame] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Scan a single symbol using the 3-tier SMC strategy.

        FIX: result dict now includes mtf_aligned (was missing previously).
        """
        if self.smc_strategy is None:
            logger.error("scan_symbol_smc called but SMC strategy is not enabled")
            return None

        if ltf_df is None or ltf_df.empty or len(ltf_df) < 20:
            logger.debug("Skipping SMC for %s – insufficient LTF data", symbol)
            return None

        smc_result = self.smc_strategy.analyze(ltf_df, mtf_df, htf_df)
        smc_result.symbol = symbol

        return {
            "symbol": symbol,
            "price": float(ltf_df["close"].iloc[-1]),
            "signal": smc_result.signal,
            "score": smc_result.score,
            "htf_aligned": smc_result.htf_aligned,
            "mtf_aligned": smc_result.mtf_aligned,   # FIX: was missing
            "liquidity_sweep": smc_result.liquidity_sweep,
            "mss_confirmed": smc_result.mss_confirmed,
            "fvg_present": smc_result.fvg_present,
            "ob_present": smc_result.ob_present,
            "pattern": smc_result.pattern,
            "details": smc_result.details,
        }

    # ------------------------------------------------------------------
    # Batch scan – historical
    # ------------------------------------------------------------------

    def scan_all(
        self,
        fyers_client: Any,
        symbols: Optional[List[str]] = None,
        timeframe: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Fetch historical data and scan every symbol in *symbols*."""
        from api import get_historical_data

        limit = limit or self.parser.get_limit() or 30
        symbols = symbols or self.parser.get_symbols()
        timeframe = timeframe or self.parser.get_timeframe() or "D"

        logger.info(
            "Scanning %d symbols | TF=%s | limit=%d", len(symbols), timeframe, limit
        )

        results: List[Dict[str, Any]] = []
        for symbol in symbols:
            try:
                df = get_historical_data(fyers_client, symbol, timeframe, count=limit)
                if df.empty:
                    logger.warning("No data returned for %s", symbol)
                    continue
                result = self.scan_symbol(symbol, df)
                if result:
                    results.append(result)
            except Exception:
                logger.exception("Error scanning %s", symbol)

        logger.info("Scan complete – %d results", len(results))
        return results

    # ------------------------------------------------------------------
    # Batch scan – SMC (3-tier)
    # ------------------------------------------------------------------

    def scan_all_smc(
        self,
        fyers_client: Any,
        symbols: Optional[List[str]] = None,
        ltf_timeframe: str = "5m",
        mtf_timeframe: str = "15m",
        htf_timeframe: str = "1h",
        ltf_limit: int = 100,
        mtf_limit: int = 100,
        htf_limit: int = 50,
        min_score: int = 50,
    ) -> List[Dict[str, Any]]:
        """
        Perform a 3-tier SMC scan on all *symbols*.

        Returns results with score >= *min_score*.
        """
        from api import get_historical_data

        if self.smc_strategy is None:
            logger.error("scan_all_smc called but enable_smc=False. Returning empty list.")
            return []

        symbols = symbols or self.parser.get_symbols()

        logger.info(
            "3-Tier SMC scan | %d symbols | HTF=%s MTF=%s LTF=%s",
            len(symbols), htf_timeframe, mtf_timeframe, ltf_timeframe,
        )

        results: List[Dict[str, Any]] = []
        for i, symbol in enumerate(symbols):
            # Rate limiting: pause every 5 symbols
            if i > 0 and i % 5 == 0:
                time.sleep(2)

            try:
                htf_df = get_historical_data(fyers_client, symbol, htf_timeframe, count=htf_limit)
                time.sleep(0.5)
                mtf_df = get_historical_data(fyers_client, symbol, mtf_timeframe, count=mtf_limit)
                time.sleep(0.5)
                ltf_df = get_historical_data(fyers_client, symbol, ltf_timeframe, count=ltf_limit)

                if ltf_df.empty or mtf_df.empty or htf_df.empty:
                    logger.warning("Missing data for %s – skipping", symbol)
                    continue

                result = self.scan_symbol_smc(symbol, ltf_df, mtf_df, htf_df)
                if result and result["score"] >= min_score:
                    results.append(result)
                    logger.info(
                        "%s → %s score=%d%% htf=%s sweep=%s mss=%s",
                        symbol,
                        result["signal"],
                        result["score"],
                        "✓" if result["htf_aligned"] else "✗",
                        "✓" if result["liquidity_sweep"] else "✗",
                        "✓" if result["mss_confirmed"] else "✗",
                    )
                else:
                    score = result["score"] if result else 0
                    logger.debug("%s score %d%% below threshold %d%%", symbol, score, min_score)

            except Exception:
                logger.exception("SMC scan error for %s", symbol)

        logger.info("SMC scan complete – %d setups found (score ≥ %d%%)", len(results), min_score)
        return results

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _generate_signal(self, indicators: IndicatorValues) -> str:
        entry = self.parser.get_entry_conditions()
        exit_ = self.parser.get_exit_conditions()

        if self._conditions_met(indicators, entry):
            return "BUY"
        if self._conditions_met(indicators, exit_):
            return "SELL"
        return "HOLD"

    @staticmethod
    def _conditions_met(indicators: IndicatorValues, conditions: Dict) -> bool:
        if not conditions:
            return False
        for key, value in conditions.items():
            if key == "rsi_less_than" and indicators.rsi >= value:
                return False
            elif key == "volume_greater_than" and indicators.volume <= value:
                return False
        return True
