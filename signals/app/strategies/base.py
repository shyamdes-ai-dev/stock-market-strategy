from abc import ABC, abstractmethod
import pandas as pd

class Strategy(ABC):
    """Add a new strategy: subclass this, implement trades(), register in __init__.py."""
    name = "base"
    warmup = 0   # candles needed before signals are possible

    @abstractmethod
    def trades(self, df: pd.DataFrame) -> list[dict]:
        """df: daily OHLC (Open,High,Low,Close) indexed by date.
        Return trades: cross_date, signal_date, entry_price, exit_date, exit_price,
        exit_reason, ret_pct, days_held, status ('open'|'closed')."""

    def forming(self, df):
        """Optional: dict describing a pattern still being confirmed (for the watchlist), else None."""
        return None
