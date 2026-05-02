import typer
from rich.console import Console
from .commands import (
    login_cmd, profile_cmd, funds_cmd, holdings_cmd,
    market_data_cmd, place_order_cmd, order_status_cmd, run_bot_cmd, scan_cmd,
    start_bot_cmd, stop_bot_cmd, status_cmd, analyze_cmd, backtest_cmd,
    evaluate_cmd, compare_cmd, risk_cmd, tracker_cmd, strategy_cmd,
    paper_cmd, metrics_cmd, notify_cmd
)

app = typer.Typer(name="trading-bot", help="AI-Powered Trading Bot CLI")
console = Console()

# Original commands
app.command("login")(login_cmd)
app.command("get-profile")(profile_cmd)
app.command("get-funds")(funds_cmd)
app.command("get-holdings")(holdings_cmd)
app.command("get-market-data")(market_data_cmd)
app.command("place-order")(place_order_cmd)
app.command("order-status")(order_status_cmd)
app.command("run-bot")(run_bot_cmd)
app.command("scan")(scan_cmd)

# New trading commands
app.command("start-bot")(start_bot_cmd)
app.command("stop-bot")(stop_bot_cmd)
app.command("status")(status_cmd)
app.command("analyze")(analyze_cmd)
app.command("backtest")(backtest_cmd)
app.command("evaluate")(evaluate_cmd)
app.command("compare")(compare_cmd)
app.command("risk")(risk_cmd)
app.command("tracker")(tracker_cmd)
app.command("strategy")(strategy_cmd)
app.command("paper")(paper_cmd)
app.command("metrics")(metrics_cmd)
app.command("notify")(notify_cmd)

if __name__ == "__main__":
    app()