#!/usr/bin/env python3
"""
Pipeline Verification - Check pipeline integrity.

Inspired by Career-Ops verify-pipeline.mjs.
Validates tracking files, data consistency, and pipeline state.
"""

import sys
from pathlib import Path
from typing import List, Dict, Any

sys.path.insert(0, str(Path(__file__).parent.parent))


class PipelineVerifier:
    """Verify trading pipeline integrity."""
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.issues: List[str] = []
        self.warnings: List[str] = []
    
    def verify_all(self) -> bool:
        """Run all verification checks."""
        print("=" * 60)
        print("TradingBot Pipeline Verification")
        print("=" * 60)
        
        checks = [
            ("Data Directory", self._verify_data_dir),
            ("Tracking Files", self._verify_tracking_files),
            ("Trade Records", self._verify_trades),
            ("Position Records", self._verify_positions),
            ("Signal Records", self._verify_signals),
        ]
        
        all_passed = True
        
        for name, check_func in checks:
            try:
                passed, message = check_func()
                status = "OK" if passed else "FAIL"
                symbol = " " if passed else "X"
                print(f"[{symbol}] {name}: {message}")
                
                if not passed:
                    all_passed = False
            except Exception as e:
                print(f"[X] {name}: Error - {e}")
                all_passed = False
        
        print("=" * 60)
        
        if self.warnings:
            print(f"\nWarnings ({len(self.warnings)}):")
            for warning in self.warnings:
                print(f"  ! {warning}")
        
        if self.issues:
            print(f"\nIssues ({len(self.issues)}):")
            for issue in self.issues:
                print(f"  X {issue}")
        
        if all_passed:
            print("\nAll verifications passed!")
        else:
            print(f"\nFAILED: {len(self.issues)} issue(s) found")
        
        print("=" * 60)
        return all_passed
    
    def _verify_data_dir(self) -> tuple[bool, str]:
        """Verify data directory exists."""
        if not self.data_dir.exists():
            return False, "Data directory not found"
        return True, "Data directory exists"
    
    def _verify_tracking_files(self) -> tuple[bool, str]:
        """Verify all tracking files exist and are readable."""
        required_files = ["trades.md", "positions.md", "signals.md"]
        
        missing = []
        for file in required_files:
            filepath = self.data_dir / file
            if not filepath.exists():
                missing.append(file)
            else:
                try:
                    content = filepath.read_text()
                    # Check file is not corrupted
                    if not content.startswith("#"):
                        self.warnings.append(f"{file} may be corrupted (no header)")
                except Exception as e:
                    self.issues.append(f"Cannot read {file}: {e}")
        
        if missing:
            return False, f"Missing files: {', '.join(missing)}"
        
        return True, f"All {len(required_files)} tracking files present"
    
    def _verify_trades(self) -> tuple[bool, str]:
        """Verify trades file format."""
        trades_file = self.data_dir / "trades.md"
        
        if not trades_file.exists():
            return True, "No trades file (new system)"
        
        try:
            lines = trades_file.read_text().split('\n')
            data_lines = [l for l in lines if l.startswith('|') and not l.startswith('|---')]
            
            if len(data_lines) < 1:
                return True, "No trades recorded yet"
            
            # Check header line exists
            if not lines[0].startswith("# Trade History"):
                self.warnings.append("Trades file missing proper header")
            
            # Count data rows (excluding header row)
            trade_count = len(data_lines) - 1
            
            return True, f"{trade_count} trade(s) recorded"
            
        except Exception as e:
            return False, f"Error reading trades: {e}"
    
    def _verify_positions(self) -> tuple[bool, str]:
        """Verify positions file format."""
        positions_file = self.data_dir / "positions.md"
        
        if not positions_file.exists():
            return True, "No positions file (new system)"
        
        try:
            lines = positions_file.read_text().split('\n')
            data_lines = [l for l in lines if l.startswith('|') and not l.startswith('|---')]
            
            if len(data_lines) < 1:
                return True, "No positions recorded yet"
            
            # Count active positions
            active = sum(1 for l in data_lines[1:] if 'OPEN' in l)
            closed = sum(1 for l in data_lines[1:] if 'CLOSED' in l)
            
            return True, f"{active} active, {closed} closed position(s)"
            
        except Exception as e:
            return False, f"Error reading positions: {e}"
    
    def _verify_signals(self) -> tuple[bool, str]:
        """Verify signals file format."""
        signals_file = self.data_dir / "signals.md"
        
        if not signals_file.exists():
            return True, "No signals file (new system)"
        
        try:
            lines = signals_file.read_text().split('\n')
            data_lines = [l for l in lines if l.startswith('|') and not l.startswith('|---')]
            
            if len(data_lines) < 1:
                return True, "No signals recorded yet"
            
            # Count executed signals
            executed = sum(1 for l in data_lines[1:] if 'Yes' in l)
            
            return True, f"{len(data_lines)-1} signal(s), {executed} executed"
            
        except Exception as e:
            return False, f"Error reading signals: {e}"


def main():
    """CLI entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Verify trading pipeline")
    parser.add_argument("--data-dir", default="data", help="Data directory path")
    
    args = parser.parse_args()
    
    verifier = PipelineVerifier(data_dir=args.data_dir)
    success = verifier.verify_all()
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
