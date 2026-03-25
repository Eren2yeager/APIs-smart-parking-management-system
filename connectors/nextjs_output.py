"""
Forward processed AI backend results to Next.js via HTTP webhooks (sync httpx).
"""

from __future__ import annotations

import httpx
from typing import Any, Dict

from config.settings import settings
from utils.logger import logger


class NextJSOutputConnector:
    """Async HTTP client for optional async callers (tests or future use)."""

    def __init__(self) -> None:
        timeout = httpx.Timeout(settings.nextjs_webhook_timeout_seconds)
        headers: dict[str, str] = {}
        if settings.ai_webhook_secret:
            headers["X-AI-Secret"] = settings.ai_webhook_secret
        self.client = httpx.AsyncClient(timeout=timeout, headers=headers)
        self.nextjs_base_url = settings.nextjs_api_url.rstrip("/")

    async def send_vehicle_entry(self, data: Dict[str, Any]) -> bool:
        url = f"{self.nextjs_base_url}{settings.nextjs_webhook_entry}"
        return await self._send(url, data, "vehicle_entry")

    async def send_vehicle_exit(self, data: Dict[str, Any]) -> bool:
        url = f"{self.nextjs_base_url}{settings.nextjs_webhook_exit}"
        return await self._send(url, data, "vehicle_exit")

    async def send_capacity_update(self, data: Dict[str, Any]) -> bool:
        url = f"{self.nextjs_base_url}{settings.nextjs_webhook_capacity}"
        return await self._send(url, data, "capacity_update")

    async def _send(self, url: str, data: Dict[str, Any], event_type: str) -> bool:
        try:
            response = await self.client.post(url, json=data)
            if response.status_code in (200, 201):
                logger.info(f"[NextJSOutput] {event_type} sent successfully to {url}")
                return True
            logger.warning(
                f"[NextJSOutput] {event_type} failed: {response.status_code} — {response.text[:200]}"
            )
            return False
        except httpx.ConnectTimeout:
            logger.error(f"[NextJSOutput] Connection timeout sending {event_type} to {url}")
            return False
        except httpx.ConnectError:
            logger.error(f"[NextJSOutput] Connection error sending {event_type} to {url} — is Next.js running?")
            return False
        except Exception as e:
            logger.error(f"[NextJSOutput] Unexpected error sending {event_type}: {e}")
            return False

    async def close(self) -> None:
        await self.client.aclose()


_sync_client: httpx.Client | None = None

_capacity_slot_store: dict[str, dict] = {}


def get_capacity_slot_store_snapshot(parking_lot_id: str) -> dict:
    """Latest slot_id -> {slot_id, status, confidence} for a lot."""
    raw = _capacity_slot_store.get(parking_lot_id, {})
    return dict(raw) if isinstance(raw, dict) else {}


def set_slot_store_data(parking_lot_id: str, slot_id: int, status: str, confidence: float) -> None:
    if parking_lot_id not in _capacity_slot_store:
        _capacity_slot_store[parking_lot_id] = {}
    _capacity_slot_store[parking_lot_id][slot_id] = {
        "slot_id": slot_id,
        "status": status,
        "confidence": confidence,
    }


def set_slot_store_batch(parking_lot_id: str, slots: list) -> None:
    _capacity_slot_store[parking_lot_id] = {
        s.get("slot_id", s.get("slotId", i)): {
            "slot_id": s.get("slot_id", s.get("slotId", i)),
            "status": s.get("status", "empty"),
            "confidence": s.get("confidence", 0.0),
        }
        for i, s in enumerate(slots)
    }


def _get_sync_client() -> httpx.Client:
    global _sync_client
    if _sync_client is None:
        timeout = httpx.Timeout(settings.nextjs_webhook_timeout_seconds)
        headers: dict[str, str] = {}
        if settings.ai_webhook_secret:
            headers["X-AI-Secret"] = settings.ai_webhook_secret
        _sync_client = httpx.Client(timeout=timeout, headers=headers)
    return _sync_client


def _sync_send(url: str, data: dict, event_type: str) -> bool:
    try:
        client = _get_sync_client()
        response = client.post(url, json=data)
        if response.status_code in (200, 201):
            logger.info(f"[NextJSOutput] {event_type} sent successfully to {url}")
            return True
        logger.warning(f"[NextJSOutput] {event_type} failed: {response.status_code}")
        return False
    except Exception as e:
        logger.error(f"[NextJSOutput] Error sending {event_type}: {e}")
        return False


def send_vehicle_webhook_sync(event_type: str, data: Dict[str, Any]) -> None:
    base_url = settings.nextjs_api_url.rstrip("/")
    path = settings.nextjs_webhook_exit if event_type == "exit" else settings.nextjs_webhook_entry
    url = f"{base_url}{path}"
    label = f"vehicle_{event_type}"
    logger.info(
        f"[NextJSOutput] {label}: plate={data.get('plate_number')}, lot={data.get('parking_lot_id')}"
    )
    _sync_send(url, data, label)


def send_capacity_webhook_sync(row: Dict[str, Any]) -> None:
    base_url = settings.nextjs_api_url.rstrip("/")
    url = f"{base_url}{settings.nextjs_webhook_capacity}"
    parking_lot_id = row.get("parking_lot_id", "")
    slot_dict = _capacity_slot_store.get(parking_lot_id, {})
    slots_array = list(slot_dict.values()) if isinstance(slot_dict, dict) else []

    data = {
        "parking_lot_id": parking_lot_id,
        "total_slots": row.get("total_slots", 0),
        "occupied": row.get("occupied", 0),
        "empty": row.get("empty", row.get("empty_slots", 0)),
        "occupancy_rate": row.get("occupancy_rate", 0.0),
        "slots": slots_array,
        "timestamp": row.get("last_updated", row.get("timestamp", 0)),
    }

    logger.info(
        f"[NextJSOutput] capacity_update: lot={parking_lot_id}, "
        f"occupied={data['occupied']}/{data['total_slots']}, slots={len(slots_array)}"
    )
    _sync_send(url, data, "capacity_update")
