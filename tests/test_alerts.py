from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

import market_data.alerts as alerts_mod
from market_data.alerts import (
    Alert,
    AlertCondition,
    AlertStore,
    add_alert,
    evaluate_alerts,
    list_alerts,
    load_alerts,
    remove_alert,
    save_alerts,
)
from market_data.schemas import PriceUpdate


@pytest.fixture(autouse=True)
def isolated_alerts(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(alerts_mod, "ALERTS_PATH", tmp_path / "alerts.json")


def make_price(ticker: str = "AAPL", open: float = 100.0, close: float = 105.0) -> PriceUpdate:
    return PriceUpdate(
        ticker=ticker,
        date="2025-01-01",
        open=open,
        high=110.0,
        low=95.0,
        close=close,
        volume=1000,
    )


class TestLoadEmpty:
    def test_load_empty(self) -> None:
        result = load_alerts()
        assert result.alerts == []


class TestAddAlert:
    def test_add_alert(self) -> None:
        alert = Alert(ticker="AAPL", condition=AlertCondition.above, threshold=200.0)
        add_alert(alert)
        items = list_alerts()
        assert len(items) == 1
        assert items[0].ticker == "AAPL"

    def test_add_normalises_ticker(self) -> None:
        alert = Alert(ticker="aapl", condition=AlertCondition.below, threshold=100.0)
        add_alert(alert)
        items = list_alerts()
        assert items[0].ticker == "AAPL"

    def test_add_multiple(self) -> None:
        add_alert(Alert(ticker="AAPL", condition=AlertCondition.above, threshold=200.0))
        add_alert(Alert(ticker="MSFT", condition=AlertCondition.below, threshold=50.0))
        assert len(list_alerts()) == 2


class TestRemoveAlert:
    def test_remove_alert(self) -> None:
        alert = Alert(ticker="AAPL", condition=AlertCondition.above, threshold=200.0)
        add_alert(alert)
        remove_alert(alert.id)
        assert list_alerts() == []

    def test_remove_nonexistent(self) -> None:
        remove_alert("nonexistent-id")
        assert list_alerts() == []


class TestListByTicker:
    def test_list_by_ticker(self) -> None:
        add_alert(Alert(ticker="AAPL", condition=AlertCondition.above, threshold=200.0))
        add_alert(Alert(ticker="MSFT", condition=AlertCondition.below, threshold=50.0))
        result = list_alerts(ticker="AAPL")
        assert len(result) == 1
        assert result[0].ticker == "AAPL"

    def test_list_by_ticker_empty(self) -> None:
        add_alert(Alert(ticker="AAPL", condition=AlertCondition.above, threshold=200.0))
        result = list_alerts(ticker="GOOG")
        assert result == []

    def test_list_all(self) -> None:
        add_alert(Alert(ticker="AAPL", condition=AlertCondition.above, threshold=200.0))
        add_alert(Alert(ticker="MSFT", condition=AlertCondition.below, threshold=50.0))
        result = list_alerts()
        assert len(result) == 2


class TestEvaluateAlerts:
    def test_above_triggers(self) -> None:
        store = AlertStore(
            alerts=[Alert(ticker="AAPL", condition=AlertCondition.above, threshold=100.0)]
        )
        price = make_price("AAPL", open=95.0, close=110.0)
        triggered = evaluate_alerts([price], store)
        assert len(triggered) == 1
        assert "above" in triggered[0]["message"]

    def test_above_no_trigger(self) -> None:
        store = AlertStore(
            alerts=[Alert(ticker="AAPL", condition=AlertCondition.above, threshold=200.0)]
        )
        price = make_price("AAPL", open=95.0, close=110.0)
        triggered = evaluate_alerts([price], store)
        assert triggered == []

    def test_below_triggers(self) -> None:
        store = AlertStore(
            alerts=[Alert(ticker="AAPL", condition=AlertCondition.below, threshold=150.0)]
        )
        price = make_price("AAPL", open=160.0, close=120.0)
        triggered = evaluate_alerts([price], store)
        assert len(triggered) == 1
        assert "below" in triggered[0]["message"]

    def test_below_no_trigger(self) -> None:
        store = AlertStore(
            alerts=[Alert(ticker="AAPL", condition=AlertCondition.below, threshold=50.0)]
        )
        price = make_price("AAPL", open=95.0, close=110.0)
        triggered = evaluate_alerts([price], store)
        assert triggered == []

    def test_percent_change_above_triggers(self) -> None:
        store = AlertStore(
            alerts=[Alert(ticker="AAPL", condition=AlertCondition.percent_change_above, threshold=5.0)]
        )
        price = make_price("AAPL", open=100.0, close=110.0)
        triggered = evaluate_alerts([price], store)
        assert len(triggered) == 1
        assert "10.00%" in triggered[0]["message"]

    def test_percent_change_above_no_trigger(self) -> None:
        store = AlertStore(
            alerts=[Alert(ticker="AAPL", condition=AlertCondition.percent_change_above, threshold=15.0)]
        )
        price = make_price("AAPL", open=100.0, close=110.0)
        triggered = evaluate_alerts([price], store)
        assert triggered == []

    def test_percent_change_below_triggers(self) -> None:
        store = AlertStore(
            alerts=[Alert(ticker="AAPL", condition=AlertCondition.percent_change_below, threshold=5.0)]
        )
        price = make_price("AAPL", open=100.0, close=90.0)
        triggered = evaluate_alerts([price], store)
        assert len(triggered) == 1
        assert "-10.00%" in triggered[0]["message"]

    def test_percent_change_below_no_trigger(self) -> None:
        store = AlertStore(
            alerts=[Alert(ticker="AAPL", condition=AlertCondition.percent_change_below, threshold=15.0)]
        )
        price = make_price("AAPL", open=100.0, close=90.0)
        triggered = evaluate_alerts([price], store)
        assert triggered == []

    def test_disabled_alert_skipped(self) -> None:
        store = AlertStore(
            alerts=[Alert(ticker="AAPL", condition=AlertCondition.above, threshold=50.0, enabled=False)]
        )
        price = make_price("AAPL", open=95.0, close=110.0)
        triggered = evaluate_alerts([price], store)
        assert triggered == []

    def test_no_price_for_ticker_skipped(self) -> None:
        store = AlertStore(
            alerts=[Alert(ticker="MSFT", condition=AlertCondition.above, threshold=50.0)]
        )
        price = make_price("AAPL", open=95.0, close=110.0)
        triggered = evaluate_alerts([price], store)
        assert triggered == []

    def test_cooldown_prevents_retrigger(self) -> None:
        recent = (datetime.now(timezone.utc) - timedelta(seconds=60)).isoformat()
        store = AlertStore(
            alerts=[
                Alert(
                    ticker="AAPL",
                    condition=AlertCondition.above,
                    threshold=50.0,
                    cooldown_seconds=300,
                    last_triggered=recent,
                )
            ]
        )
        price = make_price("AAPL", open=95.0, close=110.0)
        triggered = evaluate_alerts([price], store)
        assert triggered == []

    def test_cooldown_expired_retriggers(self) -> None:
        old = (datetime.now(timezone.utc) - timedelta(seconds=600)).isoformat()
        store = AlertStore(
            alerts=[
                Alert(
                    ticker="AAPL",
                    condition=AlertCondition.above,
                    threshold=50.0,
                    cooldown_seconds=300,
                    last_triggered=old,
                )
            ]
        )
        price = make_price("AAPL", open=95.0, close=110.0)
        triggered = evaluate_alerts([price], store)
        assert len(triggered) == 1

    def test_last_triggered_updated_on_fire(self) -> None:
        alert = Alert(ticker="AAPL", condition=AlertCondition.above, threshold=50.0)
        assert alert.last_triggered is None
        store = AlertStore(alerts=[alert])
        price = make_price("AAPL", open=95.0, close=110.0)
        evaluate_alerts([price], store)
        assert store.alerts[0].last_triggered is not None


class TestPersistence:
    def test_save_and_load(self) -> None:
        store = AlertStore(
            alerts=[Alert(ticker="AAPL", condition=AlertCondition.above, threshold=200.0)]
        )
        save_alerts(store)
        loaded = load_alerts()
        assert len(loaded.alerts) == 1
        assert loaded.alerts[0].ticker == "AAPL"
        assert loaded.alerts[0].threshold == 200.0

    def test_atomic_write(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        path = tmp_path / "sub" / "alerts.json"
        monkeypatch.setattr(alerts_mod, "ALERTS_PATH", path)
        store = AlertStore(
            alerts=[Alert(ticker="GOOG", condition=AlertCondition.below, threshold=100.0)]
        )
        save_alerts(store)
        assert path.exists()
        data = json.loads(path.read_text())
        assert len(data["alerts"]) == 1
        assert data["alerts"][0]["ticker"] == "GOOG"
