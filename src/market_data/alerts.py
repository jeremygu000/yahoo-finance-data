from __future__ import annotations

import json
import os
import threading
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, field_validator

from market_data.config import DATA_DIR
from market_data.schemas import PriceUpdate

ALERTS_PATH = DATA_DIR.parent / "alerts.json"

_alerts_lock = threading.Lock()


class AlertCondition(str, Enum):
    above = "above"
    below = "below"
    percent_change_above = "percent_change_above"
    percent_change_below = "percent_change_below"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class Alert(BaseModel):
    id: str = ""
    ticker: str
    condition: AlertCondition
    threshold: float
    enabled: bool = True
    last_triggered: str | None = None
    cooldown_seconds: int = 300
    created_at: str = ""

    def model_post_init(self, __context: Any) -> None:
        if not self.id:
            object.__setattr__(self, "id", str(uuid.uuid4()))
        if not self.created_at:
            object.__setattr__(self, "created_at", _now_iso())

    @field_validator("ticker", mode="before")
    @classmethod
    def normalise_ticker(cls, v: str) -> str:
        return v.upper()


class AlertStore(BaseModel):
    alerts: list[Alert] = []


def load_alerts() -> AlertStore:
    with _alerts_lock:
        path = ALERTS_PATH
        if not path.exists():
            return AlertStore()
        try:
            data = json.loads(path.read_text())
            return AlertStore.model_validate(data)
        except Exception:
            return AlertStore()


def save_alerts(store: AlertStore) -> None:
    with _alerts_lock:
        path = ALERTS_PATH
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".json.tmp")
        tmp.write_text(store.model_dump_json())
        os.replace(tmp, path)


def add_alert(alert: Alert) -> AlertStore:
    with _alerts_lock:
        path = ALERTS_PATH
        if path.exists():
            try:
                data = json.loads(path.read_text())
                store = AlertStore.model_validate(data)
            except Exception:
                store = AlertStore()
        else:
            store = AlertStore()
        store.alerts.append(alert)
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".json.tmp")
        tmp.write_text(store.model_dump_json())
        os.replace(tmp, path)
        return store


def remove_alert(alert_id: str) -> AlertStore:
    with _alerts_lock:
        path = ALERTS_PATH
        if path.exists():
            try:
                data = json.loads(path.read_text())
                store = AlertStore.model_validate(data)
            except Exception:
                store = AlertStore()
        else:
            store = AlertStore()
        store.alerts = [a for a in store.alerts if a.id != alert_id]
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".json.tmp")
        tmp.write_text(store.model_dump_json())
        os.replace(tmp, path)
        return store


def list_alerts(ticker: str | None = None) -> list[Alert]:
    with _alerts_lock:
        path = ALERTS_PATH
        if not path.exists():
            return []
        try:
            data = json.loads(path.read_text())
            store = AlertStore.model_validate(data)
        except Exception:
            return []
        if ticker is not None:
            return [a for a in store.alerts if a.ticker == ticker.upper()]
        return store.alerts


def _is_in_cooldown(alert: Alert, now: datetime) -> bool:
    if alert.last_triggered is None:
        return False
    try:
        last = datetime.fromisoformat(alert.last_triggered)
        elapsed = (now - last).total_seconds()
        return elapsed < alert.cooldown_seconds
    except Exception:
        return False


def evaluate_alerts(
    price_updates: list[PriceUpdate],
    store: AlertStore,
) -> list[dict[str, Any]]:
    """Evaluate all enabled alerts against the given price updates.

    Returns a list of triggered dicts: {"alert": Alert, "price": PriceUpdate, "message": str}.
    Updates last_triggered on triggered alerts and persists the store.
    """
    now = datetime.now(timezone.utc)
    triggered: list[dict[str, Any]] = []

    update_map: dict[str, PriceUpdate] = {u.ticker: u for u in price_updates}

    for alert in store.alerts:
        if not alert.enabled:
            continue
        price = update_map.get(alert.ticker)
        if price is None:
            continue
        if _is_in_cooldown(alert, now):
            continue

        fired = False
        message = ""

        if alert.condition == AlertCondition.above:
            if price.close > alert.threshold:
                fired = True
                message = f"{alert.ticker} close {price.close:.4f} crossed above threshold {alert.threshold}"
        elif alert.condition == AlertCondition.below:
            if price.close < alert.threshold:
                fired = True
                message = f"{alert.ticker} close {price.close:.4f} crossed below threshold {alert.threshold}"
        elif alert.condition == AlertCondition.percent_change_above:
            if price.open != 0:
                pct = (price.close - price.open) / price.open * 100
                if pct > alert.threshold:
                    fired = True
                    message = f"{alert.ticker} daily change {pct:.2f}% exceeded +{alert.threshold}%"
        elif alert.condition == AlertCondition.percent_change_below:
            if price.open != 0:
                pct = (price.close - price.open) / price.open * 100
                if pct < -alert.threshold:
                    fired = True
                    message = f"{alert.ticker} daily change {pct:.2f}% fell below -{alert.threshold}%"

        if fired:
            alert.last_triggered = now.isoformat()
            triggered.append({"alert": alert, "price": price, "message": message})

    if triggered:
        save_alerts(store)

    return triggered
