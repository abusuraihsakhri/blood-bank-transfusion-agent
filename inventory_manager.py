"""Blood Inventory Management: stock tracking, expiry alerts, demand forecasting."""
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
import datetime
import math


@dataclass
class InventoryUnit:
    unit_id: str
    blood_type: str
    collection_date: str
    expiry_date: str
    status: str = "available"
    location: str = "main_bank"


class InventoryManager:
    """Blood bank inventory tracking with expiry management and demand forecasting."""

    SHELF_LIFE_DAYS = 42
    CRITICAL_STOCK_THRESHOLD = 5

    def __init__(self):
        self._inventory: Dict[str, InventoryUnit] = {}
        self._usage_history: List[Dict[str, Any]] = []

    def add_unit(self, unit: InventoryUnit) -> None:
        self._inventory[unit.unit_id] = unit

    def remove_unit(self, unit_id: str, reason: str = "issued") -> bool:
        if unit_id in self._inventory:
            self._inventory[unit_id].status = reason
            return True
        return False

    def get_stock_levels(self) -> Dict[str, Any]:
        """Current stock by blood type."""
        stock: Dict[str, int] = {}
        expiring_soon = []
        today = datetime.date.today()

        for unit in self._inventory.values():
            if unit.status == "available":
                stock[unit.blood_type] = stock.get(unit.blood_type, 0) + 1
                expiry = datetime.date.fromisoformat(unit.expiry_date)
                days_left = (expiry - today).days
                if days_left <= 7:
                    expiring_soon.append({"unit_id": unit.unit_id, "days_left": days_left})

        critical = {bt: count for bt, count in stock.items() if count < self.CRITICAL_STOCK_THRESHOLD}

        return {
            "stock_levels": stock,
            "total_available": sum(stock.values()),
            "expiring_soon": expiring_soon,
            "critical_stock": critical,
            "alerts": [f"Low stock: {bt} ({count} units)" for bt, count in critical.items()],
        }

    def fifo_allocation(self, blood_type: str) -> Optional[str]:
        """Allocate oldest unit first (FIFO)."""
        candidates = [
            u for u in self._inventory.values()
            if u.blood_type == blood_type and u.status == "available"
        ]
        if not candidates:
            return None
        candidates.sort(key=lambda u: u.collection_date)
        return candidates[0].unit_id

    def demand_forecast(self, blood_type: str, historical_usage: List[int], days_ahead: int = 7) -> Dict[str, Any]:
        """Simple exponential smoothing forecast."""
        if not historical_usage:
            return {"forecast": 0, "confidence": "low"}

        alpha = 0.3
        smoothed = historical_usage[0]
        for val in historical_usage[1:]:
            smoothed = alpha * val + (1 - alpha) * smoothed

        variance = sum((x - smoothed) ** 2 for x in historical_usage) / max(len(historical_usage), 1)
        std = math.sqrt(variance)

        return {
            "forecast_daily": round(smoothed, 1),
            "forecast_period": round(smoothed * days_ahead, 1),
            "std_dev": round(std, 2),
            "days_ahead": days_ahead,
            "confidence": "high" if std < smoothed * 0.3 else "medium",
        }

    def expiry_report(self) -> Dict[str, Any]:
        """Report on units approaching expiry."""
        today = datetime.date.today()
        expiring = []
        expired = []

        for unit in self._inventory.values():
            if unit.status != "available":
                continue
            expiry = datetime.date.fromisoformat(unit.expiry_date)
            days_left = (expiry - today).days
            if days_left < 0:
                expired.append({"unit_id": unit.unit_id, "blood_type": unit.blood_type, "days_expired": -days_left})
            elif days_left <= 7:
                expiring.append({"unit_id": unit.unit_id, "blood_type": unit.blood_type, "days_left": days_left})

        expiring.sort(key=lambda x: x["days_left"])
        return {
            "expiring_within_7_days": expiring,
            "expired_units": expired,
            "num_expiring": len(expiring),
            "num_expired": len(expired),
            "recommendation": "Issue expiring units first" if expiring else "No immediate action needed",
        }

    def record_usage(self, blood_type: str, quantity: int, date: str) -> None:
        self._usage_history.append({"blood_type": blood_type, "quantity": quantity, "date": date})
