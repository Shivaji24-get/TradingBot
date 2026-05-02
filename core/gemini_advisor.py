"""
Gemini Advisor - AI-powered trade signal analysis and validation.

Integrates Google Gemini API for intelligent trading insights:
- Signal explanation in natural language
- Signal validation against market context
- Position sizing suggestions
- Trade log analysis

Setup:
    export GEMINI_API_KEY="your_key"
    # or add to trading_profile.yml

Usage:
    advisor = GeminiAdvisor(api_key="...")
    explanation = advisor.explain_signal("NSE:RELIANCE-EQ", signal_data)
    validation = advisor.validate_signal(signal_data, market_context)
"""

import os
import json
import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from datetime import datetime

try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    genai = None

logger = logging.getLogger(__name__)


@dataclass
class SignalValidation:
    """Result of AI signal validation."""
    valid: bool
    confidence: float
    reasoning: str
    concerns: List[str]
    suggestions: List[str]
    market_context: Dict[str, Any]


@dataclass
class PositionSuggestion:
    """AI-suggested position sizing."""
    recommended_qty: int
    confidence: float
    reasoning: str
    risk_assessment: str
    max_loss_estimate: float


class GeminiAdvisor:
    """
    AI-powered trading advisor using Google Gemini.
    
    Features:
    - Natural language signal explanations
    - Multi-factor signal validation
    - Context-aware position sizing
    - Trade log analysis and reporting
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: str = "gemini-1.5-flash",
        enabled: bool = True
    ):
        """
        Initialize Gemini Advisor.
        
        Args:
            api_key: Gemini API key (or from GEMINI_API_KEY env var)
            model_name: Gemini model to use
            enabled: Whether AI features are enabled
        """
        self.enabled = enabled and GEMINI_AVAILABLE
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self.model_name = model_name
        self.model = None
        
        if not self.enabled:
            logger.info("GeminiAdvisor disabled (GEMINI_API_KEY not set or google-generativeai not installed)")
            return
        
        if not self.api_key:
            logger.warning("GeminiAdvisor: No API key provided. Set GEMINI_API_KEY env var.")
            self.enabled = False
            return
        
        try:
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel(model_name)
            logger.info(f"GeminiAdvisor initialized with model: {model_name}")
        except Exception as e:
            logger.error(f"Failed to initialize Gemini: {e}")
            self.enabled = False
    
    def explain_signal(
        self,
        symbol: str,
        signal_data: Dict[str, Any],
        market_snapshot: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Generate natural language explanation of a trading signal.
        
        Args:
            symbol: Trading symbol
            signal_data: Signal details (action, score, indicators, etc.)
            market_snapshot: Optional market context (VIX, sector performance)
            
        Returns:
            Natural language explanation
        """
        if not self.enabled or not self.model:
            return self._fallback_explanation(symbol, signal_data)
        
        prompt = f"""
You are an expert technical analyst explaining a trading signal to a retail trader.

Symbol: {symbol}
Signal: {signal_data.get('action', 'HOLD')}
Confidence Score: {signal_data.get('score', 0):.1f}%

Technical Indicators:
- RSI(14): {signal_data.get('indicators', {}).get('rsi', 'N/A')}
- SMA20: {signal_data.get('indicators', {}).get('sma20', 'N/A')}
- SMA50: {signal_data.get('indicators', {}).get('sma50', 'N/A')}
- Volume Ratio: {signal_data.get('indicators', {}).get('volume_ratio', 'N/A')}
- Current Price: ₹{signal_data.get('price', 'N/A')}

{self._format_market_context(market_snapshot)}

Explain in 2-3 sentences:
1. Why this signal was generated based on the technical indicators
2. What the confidence score means
3. Any caveats or risks the trader should consider

Be concise but informative. Use Indian stock market terminology.
"""
        
        try:
            response = self.model.generate_content(prompt)
            explanation = response.text.strip()
            logger.info(f"Gemini explanation for {symbol}: {explanation[:100]}...")
            return explanation
        except Exception as e:
            logger.error(f"Gemini explanation failed: {e}")
            return self._fallback_explanation(symbol, signal_data)
    
    def validate_signal(
        self,
        signal_data: Dict[str, Any],
        market_context: Dict[str, Any],
        portfolio_context: Optional[Dict[str, Any]] = None
    ) -> SignalValidation:
        """
        AI validation of signal quality with multi-factor analysis.
        
        Args:
            signal_data: Signal details
            market_context: Market conditions (VIX, trend, news sentiment)
            portfolio_context: Current portfolio state (positions, exposure)
            
        Returns:
            SignalValidation with confidence score and reasoning
        """
        if not self.enabled or not self.model:
            return self._fallback_validation(signal_data)
        
        prompt = f"""
You are a risk management AI validating a trading signal. Respond in valid JSON only.

Signal:
{json.dumps(signal_data, indent=2)}

Market Context:
{json.dumps(market_context, indent=2)}

Portfolio Context:
{json.dumps(portfolio_context or {}, indent=2)}

Evaluate the signal and respond with this JSON structure:
{{
    "valid": boolean,
    "confidence": float (0.0 to 1.0),
    "reasoning": "Brief explanation of the validation",
    "concerns": ["List of risk factors or concerns"],
    "suggestions": ["Improvement suggestions"],
    "market_alignment": "How well signal aligns with market context"
}}

Rules:
- Reject signals during high volatility (VIX > 25)
- Reject if portfolio exposure > 50% in same sector
- Reduce confidence if counter-trend signal
- Flag if near major support/resistance without confirmation
"""
        
        try:
            response = self.model.generate_content(prompt)
            result = json.loads(response.text)
            
            validation = SignalValidation(
                valid=result.get("valid", False),
                confidence=result.get("confidence", 0.0),
                reasoning=result.get("reasoning", "No reasoning provided"),
                concerns=result.get("concerns", []),
                suggestions=result.get("suggestions", []),
                market_context={
                    "market_alignment": result.get("market_alignment", "unknown")
                }
            )
            
            logger.info(f"Signal validation: valid={validation.valid}, confidence={validation.confidence:.2f}")
            return validation
            
        except Exception as e:
            logger.error(f"Gemini validation failed: {e}")
            return self._fallback_validation(signal_data)
    
    def suggest_position_size(
        self,
        signal_data: Dict[str, Any],
        portfolio: Dict[str, Any],
        risk_per_trade: float = 0.02,
        max_positions: int = 5
    ) -> PositionSuggestion:
        """
        AI-optimized position sizing based on signal strength and portfolio risk.
        
        Args:
            signal_data: Signal details (score, volatility)
            portfolio: Current portfolio (capital, open_positions, exposure)
            risk_per_trade: Max risk per trade (default 2%)
            max_positions: Max concurrent positions
            
        Returns:
            PositionSuggestion with recommended quantity and reasoning
        """
        if not self.enabled or not self.model:
            return self._fallback_sizing(signal_data, portfolio, risk_per_trade)
        
        prompt = f"""
You are a portfolio management AI suggesting position size. Respond in valid JSON only.

Signal Data:
{json.dumps(signal_data, indent=2)}

Portfolio State:
{json.dumps(portfolio, indent=2)}

Risk Parameters:
- Risk per trade: {risk_per_trade * 100}%
- Max positions: {max_positions}

Suggest position size and respond with this JSON:
{{
    "recommended_qty": integer,
    "confidence": float (0.0 to 1.0),
    "reasoning": "Brief explanation",
    "risk_assessment": "Low/Medium/High with explanation",
    "max_loss_estimate": float (estimated INR loss if stop-loss hit)
}}

Consider:
- Signal confidence score (higher = larger position)
- Current portfolio concentration
- Market volatility
- Available buying power
"""
        
        try:
            response = self.model.generate_content(prompt)
            result = json.loads(response.text)
            
            suggestion = PositionSuggestion(
                recommended_qty=result.get("recommended_qty", 1),
                confidence=result.get("confidence", 0.5),
                reasoning=result.get("reasoning", "No reasoning provided"),
                risk_assessment=result.get("risk_assessment", "Unknown"),
                max_loss_estimate=result.get("max_loss_estimate", 0.0)
            )
            
            logger.info(f"Position suggestion: qty={suggestion.recommended_qty}, risk={suggestion.risk_assessment}")
            return suggestion
            
        except Exception as e:
            logger.error(f"Gemini position sizing failed: {e}")
            return self._fallback_sizing(signal_data, portfolio, risk_per_trade)
    
    def analyze_trade_log(
        self,
        trades: List[Dict[str, Any]],
        days: int = 7
    ) -> str:
        """
        Analyze trade history and provide insights.
        
        Args:
            trades: List of trade records
            days: Analysis period in days
            
        Returns:
            Natural language analysis report
        """
        if not self.enabled or not self.model:
            return "Gemini not available. Install google-generativeai and set GEMINI_API_KEY."
        
        # Calculate basic stats
        total_trades = len(trades)
        winning_trades = sum(1 for t in trades if t.get('pnl', 0) > 0)
        losing_trades = sum(1 for t in trades if t.get('pnl', 0) < 0)
        total_pnl = sum(t.get('pnl', 0) for t in trades)
        
        prompt = f"""
You are a trading performance analyst reviewing a trader's activity.

Period: Last {days} days
Total Trades: {total_trades}
Winning Trades: {winning_trades}
Losing Trades: {losing_trades}
Net P&L: ₹{total_pnl:,.2f}

Trade Details:
{json.dumps(trades[-10:], indent=2)}  # Last 10 trades

Provide a concise analysis covering:
1. Win rate and profitability assessment
2. Risk management observations
3. Patterns in winning vs losing trades
4. 2-3 actionable suggestions for improvement
5. Psychological/behavioral insights (if any)

Be encouraging but honest. Focus on process over outcomes.
"""
        
        try:
            response = self.model.generate_content(prompt)
            analysis = response.text.strip()
            logger.info(f"Trade log analysis generated: {len(analysis)} chars")
            return analysis
        except Exception as e:
            logger.error(f"Gemini analysis failed: {e}")
            return f"Analysis error: {e}"
    
    def _format_market_context(self, context: Optional[Dict[str, Any]]) -> str:
        """Format market context for prompts."""
        if not context:
            return ""
        
        return f"""
Market Context:
- Nifty Trend: {context.get('nifty_trend', 'Unknown')}
- VIX (Volatility): {context.get('vix', 'Unknown')}
- Sector Performance: {context.get('sector', 'Unknown')}
- Recent News Sentiment: {context.get('news_sentiment', 'Neutral')}
"""
    
    def _fallback_explanation(self, symbol: str, signal_data: Dict[str, Any]) -> str:
        """Generate basic explanation without AI."""
        action = signal_data.get('action', 'HOLD')
        score = signal_data.get('score', 0)
        
        indicators = signal_data.get('indicators', {})
        rsi = indicators.get('rsi', 50)
        
        explanations = {
            'BUY': f"BUY signal for {symbol} based on technical indicators (Score: {score:.0f}%). ",
            'SELL': f"SELL signal for {symbol} based on technical indicators (Score: {score:.0f}%). ",
            'HOLD': f"No clear signal for {symbol}. HOLD position (Score: {score:.0f}%)."
        }
        
        base = explanations.get(action, explanations['HOLD'])
        
        if action == 'BUY' and rsi < 30:
            base += "RSI indicates oversold conditions."
        elif action == 'SELL' and rsi > 70:
            base += "RSI indicates overbought conditions."
        
        return base
    
    def _fallback_validation(self, signal_data: Dict[str, Any]) -> SignalValidation:
        """Basic validation without AI."""
        score = signal_data.get('score', 0)
        
        return SignalValidation(
            valid=score >= 75,
            confidence=score / 100,
            reasoning=f"Basic validation: Score {score:.0f}% {'meets' if score >= 75 else 'below'} threshold",
            concerns=["AI validation unavailable"] if not self.enabled else [],
            suggestions=["Consider market context before trading"],
            market_context={}
        )
    
    def _fallback_sizing(
        self,
        signal_data: Dict[str, Any],
        portfolio: Dict[str, Any],
        risk_per_trade: float
    ) -> PositionSuggestion:
        """Basic position sizing without AI."""
        capital = portfolio.get('capital', 100000)
        price = signal_data.get('price', 100)
        score = signal_data.get('score', 50)
        
        # Simple Kelly-like sizing
        risk_amount = capital * risk_per_trade
        stop_loss_pct = 0.02  # 2% stop loss
        
        qty = int(risk_amount / (price * stop_loss_pct))
        qty = max(1, min(qty, 100))  # Cap at 100 shares
        
        return PositionSuggestion(
            recommended_qty=qty,
            confidence=score / 100,
            reasoning=f"Risk-based sizing: ₹{risk_amount:,.0f} risk / {stop_loss_pct*100}% stop",
            risk_assessment="Medium (fallback mode)",
            max_loss_estimate=risk_amount
        )


# Convenience function for quick analysis
def analyze_with_gemini(
    api_key: Optional[str] = None,
    symbol: Optional[str] = None,
    signal_data: Optional[Dict] = None
) -> str:
    """Quick analysis function for CLI usage."""
    advisor = GeminiAdvisor(api_key=api_key)
    
    if symbol and signal_data:
        return advisor.explain_signal(symbol, signal_data)
    
    return "Usage: analyze_with_gemini(symbol='NSE:SBIN-EQ', signal_data={...})"
