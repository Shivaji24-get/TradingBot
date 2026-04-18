from strategies import StockScanner
import sys
import typer
from rich.console import Console
from rich.table import Table
from rich import print as rprint
from pathlib import Path
import configparser

sys.path.insert(0, str(Path(__file__).parent.parent))

from auth import TokenManager, LoginFlow
from api import FyersClient
from api import get_profile, get_funds, get_holdings, get_historical_data, get_quotes
from api import place_order as api_place_order, get_order_status
from strategies import SignalGenerator, RiskManager
from utils import load_config, setup_logging, is_market_open, export_to_csv

console = Console()

def get_client():
    config = load_config()
    tm = TokenManager(config["client_id"], config["secret_key"])
    token = tm.get_access_token()
    if not token:
        console.print("[red]Not logged in. Run 'login' first.[/red]")
        raise typer.Exit(1)
    return FyersClient(config["client_id"], token), config

def login_cmd():
    config = load_config()
    console.print("[cyan]Starting Fyers authentication...[/cyan]")
    tm = TokenManager(config["client_id"], config["secret_key"])
    lf = LoginFlow(
        config["client_id"], 
        config["secret_key"], 
        config["redirect_uri"],
        username=config.get("username"),
        pin=config.get("pin"),
        mobile=config.get("mobile")
    )
    try:
        token = lf.authenticate()
        tm.save_token(token)
        console.print("[green]✓ Authentication successful![/green]")
    except Exception as e:
        console.print(f"[red]✗ Authentication failed: {e}[/red]")
        raise typer.Exit(1)

def profile_cmd():
    client, config = get_client()
    profile = get_profile(client.get_client())
    
    table = Table(title="User Profile")
    table.add_column("Field", style="cyan")
    table.add_column("Value", style="white")
    
    for k, v in profile.items():
        table.add_row(k.replace("_", " ").title(), str(v))
    
    console.print(table)

def funds_cmd():
    client, _ = get_client()
    funds = get_funds(client.get_client())
    
    table = Table(title="Funds")
    table.add_column("Field", style="cyan")
    table.add_column("Value", style="white")
    
    for k, v in funds.items():
        table.add_row(k.replace("_", " ").title(), str(v))
    
    console.print(table)

def holdings_cmd():
    client, _ = get_client()
    holdings = get_holdings(client.get_client())
    
    if not holdings or "error" in holdings[0]:
        console.print("[yellow]No holdings found[/yellow]")
        return
    
    table = Table(title="Holdings")
    for col in ["symbol", "qty", "avg_price", "ltp", "pnl", "pnl_percent"]:
        table.add_column(col.replace("_", " ").title(), style="cyan")
    
    for h in holdings:
        table.add_row(
            str(h.get("symbol", "")),
            str(h.get("qty", 0)),
            str(h.get("avg_price", 0)),
            str(h.get("ltp", 0)),
            str(h.get("pnl", 0)),
            str(h.get("pnl_percent", 0)) + "%"
        )
    
    console.print(table)

def market_data_cmd(symbol: str = typer.Option(..., "--symbol", help="Symbol (e.g., NSE:SBIN-EQ)")):
    client, _ = get_client()
    df = get_historical_data(client.get_client(), symbol, "D", count=30)
    
    if df.empty:
        console.print("[red]No data found[/red]")
        return
    
    table = Table(title=f"Market Data - {symbol}")
    for col in ["timestamp", "open", "high", "low", "close", "volume"]:
        table.add_column(col.title(), style="cyan")
    
    for _, row in df.tail(10).iterrows():
        table.add_row(
            str(row["timestamp"])[:10],
            f"₹{row['open']:.2f}",
            f"₹{row['high']:.2f}",
            f"₹{row['low']:.2f}",
            f"₹{row['close']:.2f}",
            str(int(row["volume"]))
        )
    
    console.print(table)

def place_order_cmd(
    symbol: str = typer.Option(..., "--symbol"),
    qty: int = typer.Option(..., "--qty", min=1),
    side: str = typer.Option(..., "--side", help="buy or sell"),
    order_type: str = typer.Option("MARKET", "--type", help="MARKET or LIMIT"),
    product_type: str = typer.Option("MIS", "--product", help="MIS or CNC"),
    price: float = typer.Option(None, "--price", help="Limit price (required for LIMIT orders)")
):
    client, config = get_client()
    
    result = api_place_order(
        client.get_client(), symbol, qty, side.upper(),
        order_type.upper(), product_type.upper(), price
    )
    
    if "error" in result:
        console.print(f"[red]✗ Order failed: {result['error']}[/red]")
    else:
        console.print(f"[green]✓ Order placed: {result.get('order_id', 'N/A')}[/green]")
        export_to_csv([{"symbol": symbol, "side": side, "qty": qty, "status": "placed", **result}])

def order_status_cmd(order_id: str = typer.Option(..., "--order-id")):
    client, _ = get_client()
    status = get_order_status(client.get_client(), order_id)
    
    if "error" in status:
        console.print(f"[red]Error: {status['error']}[/red]")
        return
    
    table = Table(title=f"Order Status - {order_id}")
    for k, v in status.items():
        table.add_row(k.replace("_", " ").title(), str(v))
    
    console.print(table)

def run_bot_cmd():
    console.print("[cyan]Starting trading bot...[/cyan]")
    setup_logging()
    client, config = get_client()
    
    if not is_market_open():
        console.print("[yellow]Market is closed. Waiting for market open...[/yellow]")
    
    signal_gen = SignalGenerator(
        min_pattern_size=5,
        confidence_threshold=config.get("confidence_threshold", 0.75)
    )
    risk_mgr = RiskManager(config)
    
    funds = get_funds(client.get_client())
    capital = funds.get("available_cash", 100000)
    
    console.print(f"[green]Bot started with capital: ₹{capital}[/green]")
    console.print("[yellow]Press Ctrl+C to stop[/yellow]")
    
    import time
    from datetime import datetime
    
    try:
        while True:
            if is_market_open():
                for symbol in config.get("symbols", ["NSE:NIFTY50-INDEX", "NSE:BANKNIFTY-INDEX"]):
                    try:
                        df = get_historical_data(client.get_client(), symbol, "D", count=50)
                        if not df.empty:
                            signal = signal_gen.analyze(df)
                            console.print(f"[cyan]{symbol}: {signal}[/cyan]")
                            
                            if signal != "HOLD" and risk_mgr.can_trade():
                                price = get_quotes(client.get_client(), symbol).get("last", 0)
                                if price > 0:
                                    qty = risk_mgr.calculate_position_size(capital, price)
                                    result = api_place_order(
                                        client.get_client(), symbol, qty, signal.lower(),
                                        "MARKET", "MIS"
                                    )
                                    if "order_id" in result:
                                        risk_mgr.add_position(symbol, signal, price, qty)
                                        console.print(f"[green]✓ Executed {signal} {symbol}[/green]")
                    except Exception as e:
                        console.print(f"[red]Error with {symbol}: {e}[/red]")
            
            time.sleep(60)            
    except KeyboardInterrupt:
        console.print("[yellow]Bot stopped[/yellow]")

def scan_cmd(
    symbol: str = typer.Option(None, "--symbol", help="Scan specific symbol"),
    symbols: str = typer.Option(None, "--symbols", help="Comma-separated symbols (e.g., NSE:SBIN-EQ,NSE:RELIANCE-EQ)"),
    index: str = typer.Option(None, "--index", help="Index group (NIFTY50, BANKNIFTY, SENSEX)"),
    timeframe: str = typer.Option(None, "--timeframe", help="Timeframe (D, 5m, 1h)"),
    htf: str = typer.Option(None, "--htf", help="Higher timeframe for HTF bias (e.g., 15m, 1h). Auto if not specified."),
    limit: int = typer.Option(None, "--limit", help="Number of candles"),
    live: bool = typer.Option(False, "--live", help="Enable live real-time scanning"),
    smc: bool = typer.Option(False, "--smc", help="Use Smart Money Concepts strategy (HTF+LTF alignment, FVG, OB, MSS, Liquidity)"),
    min_score: int = typer.Option(50, "--min-score", help="Minimum SMC score to display (0-100, default: 50)"),
    interval: int = typer.Option(5, "--interval", help="Polling interval in seconds (live mode only, min: 3)"),
    auto_trade: bool = typer.Option(False, "--auto-trade", help="Auto-place orders for high-confidence signals (live mode only)"),
    threshold: int = typer.Option(75, "--threshold", help="Minimum score threshold for auto-trading (0-100)"),
    top: int = typer.Option(5, "--top", help="Show top N results by score")
):
    client, _ = get_client()

    # Build symbol list from various options
    scan_symbols = None
    if symbol:
        scan_symbols = [symbol]
    elif symbols:
        # Parse comma-separated symbols
        scan_symbols = [s.strip() for s in symbols.split(",")]
    elif index:
        # Use predefined index group
        index_upper = index.upper()
        INDEX_GROUPS = {
            "NIFTY50": [
                "NSE:RELIANCE-EQ", "NSE:TCS-EQ", "NSE:HDFCBANK-EQ", "NSE:ICICIBANK-EQ",
                "NSE:INFY-EQ", "NSE:SBIN-EQ", "NSE:ITC-EQ", "NSE:HINDUNILVR-EQ",
                "NSE:HDFC-EQ", "NSE:BAJFINANCE-EQ", "NSE:KOTAKBANK-EQ", "NSE:LT-EQ",
                "NSE:AXISBANK-EQ", "NSE:ASIANPAINT-EQ", "NSE:MARUTI-EQ", "NSE:TITAN-EQ",
                "NSE:ONGC-EQ", "NSE:NTPC-EQ", "NSE:WIPRO-EQ", "NSE:ULTRACEMCO-EQ"
            ],
            "BANKNIFTY": [
                "NSE:HDFCBANK-EQ", "NSE:ICICIBANK-EQ", "NSE:SBIN-EQ", "NSE:KOTAKBANK-EQ",
                "NSE:AXISBANK-EQ", "NSE:INDUSINDBK-EQ", "NSE:BANKBARODA-EQ", "NSE:AUBANK-EQ",
                "NSE:PNB-EQ", "NSE:CANBK-EQ", "NSE:UNIONBANK-EQ", "NSE:BANDHANBNK-EQ"
            ],
            "SENSEX": [
                "BSE:RELIANCE", "BSE:TCS", "BSE:HDFCBANK", "BSE:INFY", "BSE:ICICIBANK"
            ]
        }
        if index_upper in INDEX_GROUPS:
            scan_symbols = INDEX_GROUPS[index_upper]
            console.print(f"[cyan]Scanning {len(scan_symbols)} stocks from {index} index...[/cyan]")
        else:
            console.print(f"[red]Error: Unknown index '{index}'. Available: {', '.join(INDEX_GROUPS.keys())}[/red]")
            raise typer.Exit(1)

    if live:
        # Live mode: Continuous real-time scanning
        if not scan_symbols:
            console.print("[red]Error: --symbol, --symbols, or --index required for live mode[/red]")
            raise typer.Exit(1)
        
        if smc:
            # Live SMC Mode - Smart Money Concepts with real-time updates
            from strategies import LiveSMCEngine
            
            ltf_timeframe = timeframe or "5m"
            htf_timeframe = htf
            
            scanner = StockScanner(enable_smc=True)
            engine = LiveSMCEngine(
                client.get_client(),
                scanner,
                interval=interval,
                auto_trade=auto_trade,
                threshold=threshold,
                ltf_timeframe=ltf_timeframe,
                htf_timeframe=htf_timeframe
            )
            engine.start(scan_symbols)
        else:
            # Standard Live Mode
            from strategies import LiveEngine
            
            scanner = StockScanner(enable_patterns=True)
            engine = LiveEngine(client.get_client(), scanner, interval=interval, auto_trade=auto_trade, threshold=threshold)
            engine.start(scan_symbols)
        return  # Exit after live mode - results table not needed for live
    else:
        # Historical mode: One-time scan
        if smc:
            # Smart Money Concepts scan
            ltf_timeframe = timeframe or "5m"
            htf_timeframe = htf
            
            scanner = StockScanner(enable_smc=True)
            results = scanner.scan_all_smc(
                client.get_client(), 
                scan_symbols, 
                ltf_timeframe=ltf_timeframe,
                htf_timeframe=htf_timeframe,
                ltf_limit=limit or 100,
                htf_limit=50,
                min_score=min_score  # Use CLI parameter (default: 50)
            )
            
            # Display SMC results
            _display_smc_results(results, top)
        else:
            # Standard scan
            scanner = StockScanner(enable_patterns=True, enable_scoring=True)
            results = scanner.scan_all(client.get_client(), scan_symbols, timeframe, limit)

            # Sort by score (descending) and take top N
            results = sorted(results, key=lambda x: x.get("score", 0), reverse=True)
            if top and len(results) > top:
                results = results[:top]

            if not results:
                console.print("[yellow]No signals found[/yellow]")
                return
            
            # Display standard results
            _display_standard_results(results, top)


def _display_standard_results(results: list, top: int):
    """Display standard scan results."""
    table = Table(title=f"Stock Scan Results (Top {len(results)} by Score)")
    table.add_column("Rank", style="white")
    table.add_column("Symbol", style="cyan")
    table.add_column("Price", style="white")
    table.add_column("Score", style="bright_green")
    table.add_column("Signal", style="green")
    table.add_column("RSI", style="yellow")
    table.add_column("SMA20", style="magenta")
    table.add_column("Pattern", style="bright_blue")

    for rank, r in enumerate(results, 1):
        signal_color = "green" if r["signal"] == "BUY" else ("red" if r["signal"] == "SELL" else "white")

        # Score display with color coding
        score = r.get("score", 0)
        score_color = "green" if score >= 75 else ("yellow" if score >= 50 else "red")
        score_display = f"[{score_color}]{score}%[/{score_color}]" if score > 0 else "-"

        pattern_info = ""
        if r.get("pattern"):
            pattern_icon = "📈" if r.get("pattern_direction") == "bullish" else "📉"
            confidence = r.get("pattern_confidence", 0)
            pattern_info = f"{pattern_icon} {r['pattern']} ({confidence:.0%})"

        table.add_row(
            str(rank),
            r["symbol"],
            f"₹{r['price']:.2f}",
            score_display,
            f"[{signal_color}]{r['signal']}[/{signal_color}]",
            str(r["rsi"]),
            f"₹{r['sma_20']:.2f}",
            pattern_info
        )
    
    console.print(table)


def _display_smc_results(results: list, top: int, min_score: int = 50):
    """Display Smart Money Concepts scan results."""
    if not results:
        console.print(f"[yellow]No SMC setups found (score < {min_score}%)[/yellow]")
        return
    
    # Sort by score and take top N
    results = sorted(results, key=lambda x: x.get("score", 0), reverse=True)
    if top and len(results) > top:
        results = results[:top]
    
    table = Table(title=f"Smart Money Concepts Scan (Top {len(results)} Setups)")
    table.add_column("Symbol", style="cyan", no_wrap=True)
    table.add_column("Signal", style="green")
    table.add_column("Score", style="bright_green")
    table.add_column("Strength", style="white")
    table.add_column("HTF", style="yellow")
    table.add_column("Sweep", style="yellow")
    table.add_column("MSS", style="yellow")
    table.add_column("FVG", style="yellow")
    table.add_column("Pattern", style="bright_blue")
    table.add_column("Price", style="white")

    for r in results:
        signal_color = "green" if r["signal"] == "BUY" else ("red" if r["signal"] == "SELL" else "white")
        
        # Score with color
        score = r.get("score", 0)
        if score >= 75:
            score_color = "green"
            strength = "STRONG"
        elif score >= 60:
            score_color = "yellow"
            strength = "MODERATE"
        else:
            score_color = "red"
            strength = "WEAK"
        score_display = f"[{score_color}]{score}%[/{score_color}]"
        
        # Check marks for conditions
        htf_mark = "✅" if r.get("htf_aligned") else "❌"
        sweep_mark = "✅" if r.get("liquidity_sweep") else "❌"
        mss_mark = "✅" if r.get("mss_confirmed") else "❌"
        fvg_mark = "✅" if r.get("fvg_present") else "❌"
        
        # Pattern info
        pattern = r.get("pattern", "NONE")
        
        # Shorten symbol for display
        symbol_short = r["symbol"].replace("NSE:", "").replace("-EQ", "")[:12]
        
        table.add_row(
            symbol_short,
            f"[{signal_color}]{r['signal']}[/{signal_color}]",
            score_display,
            strength,
            htf_mark,
            sweep_mark,
            mss_mark,
            fvg_mark,
            pattern,
            f"₹{r['price']:.2f}"
        )
    
    console.print(table)
    
    # Print summary
    strong_count = sum(1 for r in results if r.get("score", 0) >= 75)
    console.print(f"\n[dim]Found {len(results)} setups: {strong_count} Strong (≥75%), {len(results) - strong_count} Below 75%[/dim]")
    console.print("[dim]Legend: HTF=Higher Timeframe | Sweep=Liquidity Sweep | MSS=Market Structure Shift | FVG=Fair Value Gap[/dim]")