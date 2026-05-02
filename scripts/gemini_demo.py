#!/usr/bin/env python3
"""
Gemini AI Demo - Quick test of GeminiAdvisor functionality.

Usage:
    set GEMINI_API_KEY=your_api_key
    python scripts/gemini_demo.py

Or with explicit key:
    python scripts/gemini_demo.py --api-key AIzaSy...
"""

import sys
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.gemini_advisor import GeminiAdvisor, SignalValidation, PositionSuggestion


def demo_signal_explanation():
    """Demo: Explain a trading signal."""
    print("=" * 60)
    print("Demo 1: Signal Explanation")
    print("=" * 60)
    
    signal_data = {
        "action": "BUY",
        "score": 82.5,
        "price": 2450.75,
        "indicators": {
            "rsi": 28.5,
            "sma20": 2420.0,
            "sma50": 2400.0,
            "volume_ratio": 1.8
        },
        "patterns": ["bullish_flag"]
    }
    
    advisor = GeminiAdvisor()
    
    if not advisor.enabled:
        print("⚠️  Gemini not available. Set GEMINI_API_KEY environment variable.")
        print("\nFallback explanation:")
    
    explanation = advisor.explain_signal("NSE:RELIANCE-EQ", signal_data)
    print(f"\nSymbol: NSE:RELIANCE-EQ")
    print(f"Signal: {explanation}")
    print()


def demo_signal_validation():
    """Demo: Validate a signal with AI."""
    print("=" * 60)
    print("Demo 2: Signal Validation")
    print("=" * 60)
    
    signal_data = {
        "action": "BUY",
        "score": 82.5,
        "confidence": 0.825,
        "indicators": {
            "rsi": 28.5,
            "trend": "bullish",
            "volume": "high"
        }
    }
    
    market_context = {
        "nifty_trend": "bullish",
        "vix": 14.2,
        "sector": "energy",
        "sector_performance": "+1.2%",
        "news_sentiment": "positive"
    }
    
    portfolio_context = {
        "capital": 500000,
        "open_positions": 2,
        "exposure": 0.15,
        "sector_exposure": {"energy": 0.05}
    }
    
    advisor = GeminiAdvisor()
    validation = advisor.validate_signal(signal_data, market_context, portfolio_context)
    
    print(f"\nSignal Validation Result:")
    print(f"  Valid: {validation.valid}")
    print(f"  Confidence: {validation.confidence:.2%}")
    print(f"  Reasoning: {validation.reasoning}")
    print(f"  Concerns: {validation.concerns}")
    print(f"  Suggestions: {validation.suggestions}")
    print()


def demo_position_sizing():
    """Demo: AI position sizing."""
    print("=" * 60)
    print("Demo 3: Position Sizing")
    print("=" * 60)
    
    signal_data = {
        "action": "BUY",
        "score": 82.5,
        "price": 2450.75,
        "volatility": 0.015
    }
    
    portfolio = {
        "capital": 500000,
        "available_cash": 350000,
        "open_positions": 2,
        "exposure": 0.15,
        "daily_pnl": 12500
    }
    
    advisor = GeminiAdvisor()
    suggestion = advisor.suggest_position_size(
        signal_data, portfolio, risk_per_trade=0.02, max_positions=5
    )
    
    print(f"\nPosition Suggestion:")
    print(f"  Recommended Qty: {suggestion.recommended_qty}")
    print(f"  Confidence: {suggestion.confidence:.2%}")
    print(f"  Reasoning: {suggestion.reasoning}")
    print(f"  Risk Assessment: {suggestion.risk_assessment}")
    print(f"  Max Loss Estimate: ₹{suggestion.max_loss_estimate:,.2f}")
    print()


def demo_trade_analysis():
    """Demo: Analyze trade history."""
    print("=" * 60)
    print("Demo 4: Trade History Analysis")
    print("=" * 60)
    
    # Sample trades
    trades = [
        {"symbol": "NSE:RELIANCE-EQ", "side": "BUY", "qty": 10, "entry": 2400, "exit": 2450, "pnl": 5000},
        {"symbol": "NSE:TCS-EQ", "side": "BUY", "qty": 5, "entry": 3500, "exit": 3480, "pnl": -1000},
        {"symbol": "NSE:SBIN-EQ", "side": "SELL", "qty": 20, "entry": 580, "exit": 570, "pnl": 2000},
        {"symbol": "NSE:INFY-EQ", "side": "BUY", "qty": 8, "entry": 1500, "exit": 1520, "pnl": 1600},
        {"symbol": "NSE:HDFC-EQ", "side": "SELL", "qty": 10, "entry": 1600, "exit": 1620, "pnl": -2000},
    ]
    
    advisor = GeminiAdvisor()
    analysis = advisor.analyze_trade_log(trades, days=7)
    
    print(f"\nAI Trade Analysis:\n{analysis}")
    print()


def main():
    parser = argparse.ArgumentParser(description="Gemini AI Demo for TradingBot")
    parser.add_argument("--api-key", help="Gemini API key (or set GEMINI_API_KEY env var)")
    parser.add_argument("--demo", choices=["explain", "validate", "size", "analyze", "all"],
                        default="all", help="Which demo to run")
    
    args = parser.parse_args()
    
    # Set API key if provided
    if args.api_key:
        import os
        os.environ["GEMINI_API_KEY"] = args.api_key
    
    print("\n" + "=" * 60)
    print("TradingBot Gemini AI Integration Demo")
    print("=" * 60)
    
    # Check if Gemini is available
    advisor = GeminiAdvisor()
    if not advisor.enabled:
        print("\n⚠️  WARNING: Gemini AI is not available.")
        print("Please set GEMINI_API_KEY environment variable:")
        print("    set GEMINI_API_KEY=your_api_key_here")
        print("\nContinuing with fallback mode (basic analysis without AI)...\n")
    else:
        print("\n✓ Gemini AI is ready")
        print(f"  Model: {advisor.model_name}")
        print(f"  API Key: {'*' * 20} (masked)")
        print()
    
    # Run demos
    demos = {
        "explain": demo_signal_explanation,
        "validate": demo_signal_validation,
        "size": demo_position_sizing,
        "analyze": demo_trade_analysis,
    }
    
    if args.demo == "all":
        for demo_func in demos.values():
            demo_func()
    else:
        demos[args.demo]()
    
    print("=" * 60)
    print("Demo complete!")
    print("=" * 60)
    
    if not advisor.enabled:
        print("\nTo enable AI features:")
        print("1. Get API key from https://makersuite.google.com/app/apikey")
        print("2. set GEMINI_API_KEY=your_key")
        print("3. Run again with: python scripts/gemini_demo.py")


if __name__ == "__main__":
    main()
