import typer
from rich.console import Console
from .commands import (
    login_cmd, profile_cmd, funds_cmd, holdings_cmd,
    market_data_cmd, place_order_cmd, order_status_cmd, run_bot_cmd, scan_cmd
)

app = typer.Typer(name="fyers-bot", help="Fyers Trading Bot CLI")
console = Console()

app.command("login")(login_cmd)
app.command("get-profile")(profile_cmd)
app.command("get-funds")(funds_cmd)
app.command("get-holdings")(holdings_cmd)
app.command("get-market-data")(market_data_cmd)
app.command("place-order")(place_order_cmd)
app.command("order-status")(order_status_cmd)
app.command("run-bot")(run_bot_cmd)
app.command("scan")(scan_cmd)

if __name__ == "__main__":
    app()