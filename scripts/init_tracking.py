#!/usr/bin/env python3
"""
Initialize tracking data files.

Creates the data directory structure and initial tracking files.
Run this before first use of the new tracking system.
"""

import os
from pathlib import Path


def init_tracking_files(data_dir: str = "data"):
    """Create initial tracking files."""
    data_path = Path(data_dir)
    data_path.mkdir(exist_ok=True)
    
    # Trades tracking file
    trades_file = data_path / "trades.md"
    if not trades_file.exists():
        trades_file.write_text("""# Trade History

Complete history of all executed trades with P&L.

| # | Date | Symbol | Side | Entry | Exit | Qty | P&L | P&L% | Status | Strategy | Paper | Notes |
|---|------|--------|------|-------|------|-----|-----|------|--------|----------|-------|-------|
""")
        print(f"Created {trades_file}")
    
    # Positions tracking file
    positions_file = data_path / "positions.md"
    if not positions_file.exists():
        positions_file.write_text("""# Position History

Active and closed positions.

| # | Date | Symbol | Side | Entry | Current/Exit | Qty | Unrealized/Realized P&L | Status | Strategy | Paper | Notes |
|---|------|--------|------|-------|--------------|-----|------------------------|--------|----------|-------|-------|
""")
        print(f"Created {positions_file}")
    
    # Signals tracking file
    signals_file = data_path / "signals.md"
    if not signals_file.exists():
        signals_file.write_text("""# Signal History

All generated signals with outcomes.

| # | Date | Symbol | Signal | Score | Price | Executed | Outcome | Notes |
|---|------|--------|--------|-------|-------|----------|---------|-------|
""")
        print(f"Created {signals_file}")
    
    # Scan history TSV
    scan_file = data_path / "scan_history.tsv"
    if not scan_file.exists():
        scan_file.write_text("date\tsymbol\tsignal\tscore\tprice\tvolume\tnotes\n")
        print(f"Created {scan_file}")
    
    # Daily P&L file
    pnl_file = data_path / "daily_pnl.md"
    if not pnl_file.exists():
        pnl_file.write_text("""# Daily P&L Summary

Daily trading performance summary.

| Date | Trades | Wins | Losses | Gross P&L | Charges | Net P&L | Cumulative | Drawdown |
|------|--------|------|--------|-----------|---------|---------|------------|----------|
""")
        print(f"Created {pnl_file}")
    
    print(f"\nTracking files initialized in {data_dir}/")
    print("You can now use the TradingTracker for trade/position/signal tracking.")


if __name__ == "__main__":
    init_tracking_files()
