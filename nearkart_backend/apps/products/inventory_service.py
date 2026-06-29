"""
Backward-compatible re-export.
InventoryService has moved to apps.inventory.services.
"""
from apps.inventory.services import InventoryService, LOW_STOCK_THRESHOLD  # noqa: F401
