#!/usr/bin/env python3
"""
System Health Check – verifies all TradingBot components are ready.

FIXES:
- Now detects placeholder credentials (${...}) as failed check
- Added Python version check (requires 3.9+, not just 3.8)
- Added check for data directory writable
- JSON output mode for automation
- Exit code 0 = healthy, 1 = issues found
"""

import importlib
import json
import sys
from pathlib import Path
from typing import List, Tuple

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


class HealthCheck:
    def __init__(self) -> None:
        self.errors: List[str] = []
        self.warnings: List[str] = []

    def run(self, json_output: bool = False) -> bool:
        checks = [
            ("Python version",     self._check_python),
            ("Core dependencies",  self._check_core_deps),
            ("Optional packages",  self._check_optional_deps),
            ("Configuration",      self._check_config),
            ("Credentials",        self._check_credentials),
            ("Data directory",     self._check_data_dir),
            ("Tracking files",     self._check_tracking_files),
            ("Log directory",      self._check_log_dir),
        ]

        results = {}
        all_ok = True

        if not json_output:
            print("=" * 60)
            print("TradingBot Health Check")
            print("=" * 60)

        for name, fn in checks:
            try:
                ok, msg = fn()
                results[name] = {"ok": ok, "message": msg}
                if not ok:
                    all_ok = False
                if not json_output:
                    mark = " " if ok else "X"
                    print(f"[{mark}] {name}: {msg}")
            except Exception as exc:
                results[name] = {"ok": False, "message": str(exc)}
                all_ok = False
                if not json_output:
                    print(f"[X] {name}: Exception – {exc}")

        if json_output:
            status = "healthy" if all_ok else ("warning" if self.warnings else "error")
            print(json.dumps({"status": status, "checks": results,
                               "warnings": self.warnings, "errors": self.errors}, indent=2))
        else:
            print("=" * 60)
            if self.warnings:
                print(f"\nWarnings ({len(self.warnings)}):")
                for w in self.warnings:
                    print(f"  ! {w}")
            if self.errors:
                print(f"\nErrors ({len(self.errors)}):")
                for e in self.errors:
                    print(f"  X {e}")
            print("\n" + ("✓ System healthy." if all_ok else "✗ Issues found – fix before trading."))
            print("=" * 60)

        return all_ok

    # ------------------------------------------------------------------

    def _check_python(self) -> Tuple[bool, str]:
        v = sys.version_info
        if v.major >= 3 and v.minor >= 9:
            return True, f"Python {v.major}.{v.minor}.{v.micro}"
        return False, f"Python {v.major}.{v.minor} found – requires 3.9+"

    def _check_core_deps(self) -> Tuple[bool, str]:
        required = [("pandas", "pandas"), ("numpy", "numpy"),
                    ("fyers_apiv3", "fyers-apiv3"), ("cryptography", "cryptography"),
                    ("yaml", "pyyaml"), ("dateutil", "python-dateutil")]
        missing = []
        for mod, pkg in required:
            try:
                importlib.import_module(mod)
            except ImportError:
                missing.append(pkg)
        if missing:
            self.errors.append(f"Missing: {', '.join(missing)}")
            return False, f"Missing: {', '.join(missing)}"
        return True, "All core packages installed"

    def _check_optional_deps(self) -> Tuple[bool, str]:
        optional = [("jsonlogger", "python-json-logger"), ("selenium", "selenium")]
        missing = [pkg for mod, pkg in optional if not self._module_available(mod)]
        if missing:
            self.warnings.append(f"Optional packages not installed: {', '.join(missing)}")
        return True, f"Optional missing: {missing}" if missing else "All optional packages installed"

    def _check_config(self) -> Tuple[bool, str]:
        yaml_path = Path("config/trading_profile.yml")
        ini_path = Path("config.ini")
        if yaml_path.exists():
            try:
                from utils.config import load_yaml_profile
                load_yaml_profile(str(yaml_path))
                return True, f"YAML profile loaded ({yaml_path})"
            except Exception as e:
                self.errors.append(str(e))
                return False, f"YAML parse error: {e}"
        if ini_path.exists():
            return True, f"INI config found ({ini_path})"
        example = Path("config/trading_profile.example.yml")
        msg = ("No config found. Run: cp config/trading_profile.example.yml "
               "config/trading_profile.yml")
        self.errors.append(msg)
        return False, msg

    def _check_credentials(self) -> Tuple[bool, str]:
        """FIX: detects placeholder strings as invalid credentials."""
        import os
        client_id = os.environ.get("FYERS_CLIENT_ID", "")
        secret_key = os.environ.get("FYERS_SECRET_KEY", "")

        if not client_id or not secret_key:
            # Try reading from YAML
            try:
                from utils.config import load_config
                cfg = load_config()
                client_id = client_id or cfg.get("client_id", "")
                secret_key = secret_key or cfg.get("secret_key", "")
            except Exception:
                pass

        placeholders = ("${", "YOUR_", "XXXX", "")
        bad_id = not client_id or any(client_id.startswith(p) for p in placeholders)
        bad_sk = not secret_key or any(secret_key.startswith(p) for p in placeholders)

        if bad_id or bad_sk:
            msg = ("Credentials missing or placeholder. "
                   "Set FYERS_CLIENT_ID and FYERS_SECRET_KEY env vars.")
            self.warnings.append(msg)
            return False, msg

        masked = client_id[:4] + "****"
        return True, f"Credentials configured (ID prefix: {masked})"

    def _check_data_dir(self) -> Tuple[bool, str]:
        data = Path("data")
        try:
            data.mkdir(parents=True, exist_ok=True)
            test = data / ".write_test"
            test.write_text("ok")
            test.unlink()
            return True, "data/ exists and is writable"
        except Exception as e:
            self.errors.append(str(e))
            return False, f"data/ not writable: {e}"

    def _check_tracking_files(self) -> Tuple[bool, str]:
        required = ["trades.md", "positions.md", "signals.md"]
        missing = [f for f in required if not (Path("data") / f).exists()]
        if missing:
            msg = f"Missing: {missing}. Run: python scripts/init_tracking.py"
            self.warnings.append(msg)
            return False, msg
        return True, "All tracking files present"

    def _check_log_dir(self) -> Tuple[bool, str]:
        logs = Path("logs")
        try:
            logs.mkdir(exist_ok=True)
            return True, "logs/ exists"
        except Exception as e:
            return False, f"Cannot create logs/: {e}"

    @staticmethod
    def _module_available(module: str) -> bool:
        try:
            importlib.import_module(module)
            return True
        except ImportError:
            return False


def main():
    import argparse
    parser = argparse.ArgumentParser(description="TradingBot system health check")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    checker = HealthCheck()
    ok = checker.run(json_output=args.json)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
