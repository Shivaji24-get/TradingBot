#!/usr/bin/env python3
"""
Health Check - System verification script.

Inspired by Career-Ops doctor.mjs and verify-pipeline.mjs.
Verifies system health, configuration, and dependencies.
"""

import sys
import os
from pathlib import Path
from typing import List, Dict, Any, Tuple
import importlib

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))


class HealthCheck:
    """System health verification."""
    
    def __init__(self):
        self.checks: List[Dict[str, Any]] = []
        self.warnings: List[str] = []
        self.errors: List[str] = []
    
    def run_all_checks(self) -> bool:
        """Run all health checks and return overall status."""
        print("=" * 60)
        print("TradingBot Health Check")
        print("=" * 60)
        
        checks = [
            ("Python Version", self._check_python_version),
            ("Dependencies", self._check_dependencies),
            ("Configuration", self._check_configuration),
            ("Data Directory", self._check_data_directory),
            ("API Credentials", self._check_api_credentials),
            ("Tracking Files", self._check_tracking_files),
            ("Log Directory", self._check_log_directory),
        ]
        
        all_passed = True
        
        for name, check_func in checks:
            try:
                passed, message = check_func()
                status = "PASS" if passed else "FAIL"
                symbol = " " if passed else "X"
                print(f"[{symbol}] {name}: {message}")
                
                if not passed:
                    all_passed = False
                    self.errors.append(f"{name}: {message}")
            except Exception as e:
                print(f"[X] {name}: Error - {e}")
                all_passed = False
                self.errors.append(f"{name}: Error - {e}")
        
        print("=" * 60)
        
        if all_passed:
            print("All checks passed! System is ready.")
        else:
            print(f"FAILED: {len(self.errors)} error(s) found")
            print("\nIssues to resolve:")
            for error in self.errors:
                print(f"  - {error}")
        
        if self.warnings:
            print(f"\nWARNINGS ({len(self.warnings)}):")
            for warning in self.warnings:
                print(f"  - {warning}")
        
        print("=" * 60)
        return all_passed
    
    def _check_python_version(self) -> Tuple[bool, str]:
        """Check Python version."""
        version = sys.version_info
        if version.major >= 3 and version.minor >= 8:
            return True, f"Python {version.major}.{version.minor}.{version.micro}"
        return False, f"Python {version.major}.{version.minor} (requires 3.8+)"
    
    def _check_dependencies(self) -> Tuple[bool, str]:
        """Check required dependencies."""
        required = [
            ('pandas', 'pandas'),
            ('numpy', 'numpy'),
            ('requests', 'requests'),
            ('fyers_apiv3', 'fyers-apiv3'),
        ]
        
        optional = [
            ('yaml', 'PyYAML'),
            ('jsonlogger', 'python-json-logger'),
        ]
        
        missing_required = []
        missing_optional = []
        
        for module, package in required:
            try:
                importlib.import_module(module)
            except ImportError:
                missing_required.append(package)
        
        for module, package in optional:
            try:
                importlib.import_module(module)
            except ImportError:
                missing_optional.append(package)
        
        if missing_optional:
            self.warnings.append(f"Optional packages not installed: {', '.join(missing_optional)}")
        
        if missing_required:
            return False, f"Missing required: {', '.join(missing_required)}"
        
        return True, f"All required packages installed"
    
    def _check_configuration(self) -> Tuple[bool, str]:
        """Check configuration files."""
        from utils.config import load_config
        
        # Try YAML profile first
        yaml_path = Path("config/trading_profile.yml")
        ini_path = Path("config.ini")
        
        if yaml_path.exists():
            try:
                config = load_config(prefer_yaml=True)
                return True, f"YAML profile loaded ({len(config)} settings)"
            except Exception as e:
                return False, f"YAML profile error: {e}"
        
        elif ini_path.exists():
            try:
                config = load_config(prefer_yaml=False)
                return True, f"INI config loaded ({len(config)} settings)"
            except Exception as e:
                return False, f"INI config error: {e}"
        
        else:
            example_path = Path("config/trading_profile.example.yml")
            if example_path.exists():
                return False, "No config found. Copy trading_profile.example.yml to trading_profile.yml"
            return False, "No configuration file found"
    
    def _check_data_directory(self) -> Tuple[bool, str]:
        """Check data directory exists."""
        data_dir = Path("data")
        
        if not data_dir.exists():
            try:
                data_dir.mkdir()
                return True, "Created data directory"
            except Exception as e:
                return False, f"Cannot create data directory: {e}"
        
        return True, "Data directory exists"
    
    def _check_api_credentials(self) -> Tuple[bool, str]:
        """Check API credentials are configured."""
        try:
            from utils.config import load_config
            config = load_config()
            
            client_id = config.get('client_id', '')
            secret_key = config.get('secret_key', '')
            
            if not client_id:
                return False, "Fyers Client ID not configured"
            
            if not secret_key:
                return False, "Fyers Secret Key not configured"
            
            # Mask credentials for display
            client_masked = client_id[:4] + "****" if len(client_id) > 4 else "****"
            
            return True, f"API credentials configured (Client: {client_masked})"
            
        except Exception as e:
            return False, f"Cannot check credentials: {e}"
    
    def _check_tracking_files(self) -> Tuple[bool, str]:
        """Check tracking files exist."""
        data_dir = Path("data")
        required_files = ["trades.md", "positions.md", "signals.md"]
        
        missing = []
        for file in required_files:
            if not (data_dir / file).exists():
                missing.append(file)
        
        if missing:
            return False, f"Missing tracking files: {', '.join(missing)}. Run: python scripts/init_tracking.py"
        
        return True, "All tracking files present"
    
    def _check_log_directory(self) -> Tuple[bool, str]:
        """Check log directory exists."""
        log_dir = Path("logs")
        
        if not log_dir.exists():
            try:
                log_dir.mkdir()
                return True, "Created logs directory"
            except Exception as e:
                return False, f"Cannot create logs directory: {e}"
        
        return True, "Logs directory exists"


def main():
    """Main entry point."""
    checker = HealthCheck()
    success = checker.run_all_checks()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
