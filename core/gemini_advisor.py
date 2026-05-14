"""Optional Google Gemini AI integration for signal analysis."""
import json
import logging
import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

try:
    import google.generativeai as genai
    _GEMINI_AVAILABLE = True
except ImportError:
    _GEMINI_AVAILABLE = False
    genai = None


@dataclass
class SignalValidation:
    valid: bool
    confidence: float
    reasoning: str
    concerns: List[str]
    suggestions: List[str]
    market_context: Dict[str, Any]


@dataclass
class PositionSuggestion:
    recommended_qty: int
    confidence: float
    reasoning: str
    risk_assessment: str
    max_loss_estimate: float


class GeminiAdvisor:
    def __init__(self, api_key: Optional[str] = None,
                 model_name: str = "gemini-1.5-flash", enabled: bool = True):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self.model_name = model_name
        self.model = None
        self.enabled = enabled and _GEMINI_AVAILABLE and bool(self.api_key)

        if self.enabled:
            try:
                genai.configure(api_key=self.api_key)
                self.model = genai.GenerativeModel(model_name)
                logger.info("GeminiAdvisor ready: %s", model_name)
            except Exception as e:
                logger.warning("GeminiAdvisor init failed: %s", e)
                self.enabled = False
        else:
            logger.info("GeminiAdvisor disabled (no API key or package not installed)")

    def explain_signal(self, symbol: str, signal_data: Dict[str, Any],
                       market_snapshot: Optional[Dict] = None) -> str:
        if not self.enabled or not self.model:
            return self._fallback_explanation(symbol, signal_data)
        prompt = (
            f"You are an expert technical analyst.\n"
            f"Symbol: {symbol}\nSignal: {signal_data.get('action','HOLD')}\n"
            f"Score: {signal_data.get('score',0):.1f}%\n"
            f"Indicators: {json.dumps(signal_data.get('indicators',{}))}\n"
            f"Explain in 2-3 sentences why this signal was generated and its key risks."
        )
        try:
            return self.model.generate_content(prompt).text.strip()
        except Exception as e:
            logger.error("Gemini explain error: %s", e)
            return self._fallback_explanation(symbol, signal_data)

    def validate_signal(self, signal_data: Dict, market_context: Dict,
                        portfolio_context: Optional[Dict] = None) -> SignalValidation:
        if not self.enabled or not self.model:
            return self._fallback_validation(signal_data)
        prompt = (
            f"Validate this trading signal. Respond in valid JSON only.\n"
            f"Signal: {json.dumps(signal_data)}\nMarket: {json.dumps(market_context)}\n"
            f'Return: {{"valid":bool,"confidence":float,"reasoning":"str","concerns":[],"suggestions":[],"market_alignment":"str"}}'
        )
        try:
            text = self.model.generate_content(prompt).text
            text = text.replace("```json", "").replace("```", "").strip()
            r = json.loads(text)
            return SignalValidation(valid=r.get("valid", False), confidence=r.get("confidence", 0.0),
                                    reasoning=r.get("reasoning", ""), concerns=r.get("concerns", []),
                                    suggestions=r.get("suggestions", []),
                                    market_context={"alignment": r.get("market_alignment", "")})
        except Exception as e:
            logger.error("Gemini validate error: %s", e)
            return self._fallback_validation(signal_data)

    def suggest_position_size(self, signal_data: Dict, portfolio: Dict,
                               risk_per_trade: float = 0.02, max_positions: int = 5) -> PositionSuggestion:
        if not self.enabled:
            return self._fallback_sizing(signal_data, portfolio, risk_per_trade)
        prompt = (
            f"Suggest position size. Respond in valid JSON only.\n"
            f"Signal: {json.dumps(signal_data)}\nPortfolio: {json.dumps(portfolio)}\n"
            f"Risk per trade: {risk_per_trade*100}%\n"
            f'Return: {{"recommended_qty":int,"confidence":float,"reasoning":"str","risk_assessment":"str","max_loss_estimate":float}}'
        )
        try:
            text = self.model.generate_content(prompt).text.replace("```json","").replace("```","").strip()
            r = json.loads(text)
            return PositionSuggestion(recommended_qty=r.get("recommended_qty",1),
                                      confidence=r.get("confidence",0.5),
                                      reasoning=r.get("reasoning",""),
                                      risk_assessment=r.get("risk_assessment",""),
                                      max_loss_estimate=r.get("max_loss_estimate",0.0))
        except Exception as e:
            logger.error("Gemini sizing error: %s", e)
            return self._fallback_sizing(signal_data, portfolio, risk_per_trade)

    def _fallback_explanation(self, symbol: str, signal_data: Dict) -> str:
        action = signal_data.get("action", "HOLD")
        score  = signal_data.get("score", 0)
        rsi    = signal_data.get("indicators", {}).get("rsi", 50)
        msg = f"{action} signal for {symbol} (score: {score:.0f}%)."
        if action == "BUY" and rsi < 30:
            msg += " RSI indicates oversold conditions."
        elif action == "SELL" and rsi > 70:
            msg += " RSI indicates overbought conditions."
        return msg

    def _fallback_validation(self, signal_data: Dict) -> SignalValidation:
        score = signal_data.get("score", 0)
        return SignalValidation(valid=score >= 75, confidence=score / 100,
                                reasoning=f"Score {score:.0f}% {'meets' if score>=75 else 'below'} threshold",
                                concerns=[], suggestions=["Consider market context before trading"],
                                market_context={})

    def _fallback_sizing(self, signal_data: Dict, portfolio: Dict, risk_per_trade: float) -> PositionSuggestion:
        capital = portfolio.get("capital", 100000)
        price   = signal_data.get("price", 100)
        risk    = capital * risk_per_trade
        qty     = max(1, min(int(risk / (price * 0.02)), 100))
        return PositionSuggestion(recommended_qty=qty, confidence=0.5,
                                  reasoning=f"Risk-based: ₹{risk:,.0f} / 2% stop",
                                  risk_assessment="Medium (fallback mode)",
                                  max_loss_estimate=risk)
