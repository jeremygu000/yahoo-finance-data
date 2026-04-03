import pytest
import pandas as pd
import numpy as np
from datetime import date, timedelta


@pytest.fixture
def sample_ohlcv():
    def _make(days=30, start_date=None):
        if start_date is None:
            start_date = date.today() - timedelta(days=days)
        dates = pd.bdate_range(start=start_date, periods=days)
        rng = np.random.default_rng(42)
        return pd.DataFrame(
            {
                "Open": rng.uniform(100, 200, len(dates)),
                "High": rng.uniform(100, 200, len(dates)),
                "Low": rng.uniform(100, 200, len(dates)),
                "Close": rng.uniform(100, 200, len(dates)),
                "Volume": rng.integers(1_000_000, 10_000_000, len(dates)),
            },
            index=pd.DatetimeIndex(dates, name="Date"),
        )

    return _make
