import asyncio

from rich.console import Console

from src.config import ExchangeConfig, StrategyConfig
from src.exchange.client import ExchangeClient
from src.strategy.sma_cross import SMACrossStrategy

console = Console()


async def main() -> None:
    ex = ExchangeClient(ExchangeConfig(name="kraken"))
    combos = [
        ("BTC/USDT", "5m", 5, 15),
        ("BTC/USDT", "15m", 10, 20),
        ("ETH/USDT", "5m", 5, 15),
        ("ETH/USDT", "1h", 10, 30),
        ("SOL/USDT", "15m", 10, 20),
        ("XRP/USDT", "1h", 10, 30),
    ]

    console.print("[bold]Scanning for live signals...[/bold]\n")

    for sym, tf, fast, slow in combos:
        try:
            df = await ex.fetch_ohlcv(sym, tf, 100)
        except Exception:
            continue
        strat = SMACrossStrategy(
            StrategyConfig(fast_period=fast, slow_period=slow)
        )
        signal = strat.evaluate(df)
        price = df["close"].iloc[-1]
        color = "bold cyan" if signal != "hold" else "dim"
        console.print(
            f"  [{color}]{signal.upper():5s}[/{color}] "
            f"{sym:8s} {tf:4s} SMA({fast},{slow}) @ ${price:<8.2f}"
        )

    console.print("\n[bold]Done.[/bold]")
    await ex.close()


asyncio.run(main())
