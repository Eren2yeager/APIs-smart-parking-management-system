"""
AI event pipeline — in-process dedupe, capacity aggregation, and Next.js webhooks.

Vehicle: confidence filter → temporal dedupe by (parking_lot_id, plate_number) → webhooks.
Capacity: per-slot state → aggregate per lot → debounced capacity webhooks.
"""

from __future__ import annotations

import queue
import threading
import time
from typing import Any, Optional

from config.settings import settings
from utils.logger import logger

from connectors.nextjs_output import (
    get_capacity_slot_store_snapshot,
    send_capacity_webhook_sync,
    send_vehicle_webhook_sync,
    set_slot_store_batch,
    set_slot_store_data,
)

CAPACITY_DEBOUNCE_MS = 500


class AIEventPipeline:
    """In-process event routing: dedupe, aggregate, forward to Next.js webhooks."""

    def __init__(self) -> None:
        self._running = False
        self._lock = threading.Lock()
        self._vehicle_last_emit_ms: dict[tuple[str, str], int] = {}
        self._capacity_timers: dict[str, threading.Timer] = {}
        self._webhook_queue: queue.Queue = queue.Queue(maxsize=100)
        self._worker: Optional[threading.Thread] = None

    def start(self) -> None:
        if self._running:
            logger.warning("[AIEventPipeline] Already running")
            return
        self._running = True
        self._worker = threading.Thread(target=self._webhook_worker, name="ai-webhook-worker", daemon=True)
        self._worker.start()
        logger.info("[AIEventPipeline] Started (webhook worker thread)")

    def stop(self) -> None:
        if not self._running:
            return
        self._running = False
        with self._lock:
            for t in list(self._capacity_timers.values()):
                try:
                    t.cancel()
                except Exception:
                    pass
            self._capacity_timers.clear()
        try:
            self._webhook_queue.put_nowait(None)
        except queue.Full:
            pass
        if self._worker and self._worker.is_alive():
            self._worker.join(timeout=3.0)
        logger.info("[AIEventPipeline] Stopped")

    def _webhook_worker(self) -> None:
        while self._running:
            try:
                item = self._webhook_queue.get(timeout=0.5)
            except queue.Empty:
                continue
            if item is None:
                break
            kind, payload = item
            try:
                if kind == "vehicle":
                    send_vehicle_webhook_sync(
                        payload["event_type"],
                        payload["data"],
                    )
                elif kind == "capacity":
                    send_capacity_webhook_sync(payload)
            except Exception as e:
                logger.error(f"[AIEventPipeline] Webhook worker error: {e}")

    def _enqueue_webhook(self, kind: str, payload: Any) -> None:
        try:
            self._webhook_queue.put_nowait((kind, payload))
        except queue.Full:
            logger.warning("[AIEventPipeline] Webhook queue full; dropping event")

    def add_vehicle_detection(
        self,
        plate_number: str,
        parking_lot_id: str,
        camera_id: str = "unknown",
        event_type: str = "entry",
        confidence: float = 0.0,
        timestamp: Optional[int] = None,
    ) -> None:
        if not self._running:
            logger.warning("[AIEventPipeline] Not running; ignoring vehicle detection")
            return

        min_conf = settings.plate_detection_confidence / 100.0
        if confidence < min_conf:
            return

        ts = timestamp if timestamp is not None else int(time.time() * 1000)
        window_ms = settings.duplicate_detection_window * 1000
        key = (parking_lot_id, plate_number)

        with self._lock:
            last = self._vehicle_last_emit_ms.get(key)
            if last is not None and abs(ts - last) < window_ms:
                return
            self._vehicle_last_emit_ms[key] = ts

        data = {
            "plate_number": plate_number,
            "parking_lot_id": parking_lot_id,
            "camera_id": camera_id,
            "confidence": confidence,
            "timestamp": ts,
        }
        self._enqueue_webhook(
            "vehicle",
            {"event_type": "exit" if event_type == "exit" else "entry", "data": data},
        )

    def add_capacity_update(
        self,
        parking_lot_id: str,
        camera_id: str = "unknown",
        slot_id: int = 0,
        status: str = "empty",
        confidence: float = 0.0,
        bbox: dict = None,
        timestamp: Optional[int] = None,
    ) -> None:
        if not self._running:
            logger.warning("[AIEventPipeline] Not running; ignoring capacity update")
            return

        min_conf = settings.parking_slot_confidence / 100.0
        if confidence < min_conf:
            return

        ts = timestamp if timestamp is not None else int(time.time() * 1000)
        set_slot_store_data(parking_lot_id, slot_id, status, confidence, bbox)
        self._schedule_capacity_flush(parking_lot_id, camera_id, ts)

    def add_capacity_batch(
        self,
        parking_lot_id: str,
        camera_id: str,
        slots: list,
        timestamp: Optional[int] = None,
    ) -> None:
        if not self._running:
            logger.warning("[AIEventPipeline] Not running; ignoring capacity batch")
            return

        ts = timestamp if timestamp is not None else int(time.time() * 1000)
        set_slot_store_batch(parking_lot_id, slots)
        self._schedule_capacity_flush(parking_lot_id, camera_id, ts)

    def _schedule_capacity_flush(self, parking_lot_id: str, camera_id: str, ts: int) -> None:
        def flush() -> None:
            with self._lock:
                self._capacity_timers.pop(parking_lot_id, None)
            payload = self._build_capacity_payload(parking_lot_id, camera_id, ts)
            if payload:
                self._enqueue_webhook("capacity", payload)

        with self._lock:
            old = self._capacity_timers.pop(parking_lot_id, None)
            if old:
                old.cancel()
            timer = threading.Timer(CAPACITY_DEBOUNCE_MS / 1000.0, flush)
            self._capacity_timers[parking_lot_id] = timer
            timer.daemon = True
            timer.start()

    def _build_capacity_payload(
        self, parking_lot_id: str, camera_id: str, ts: int
    ) -> Optional[dict[str, Any]]:
        slots_map = get_capacity_slot_store_snapshot(parking_lot_id)
        if not slots_map:
            return None

        slots_array = list(slots_map.values())
        occupied = sum(1 for s in slots_array if s.get("status") == "occupied")
        empty_n = sum(1 for s in slots_array if s.get("status") == "empty")
        total_slots = len(slots_array)
        if total_slots == 0:
            return None

        confidences = [float(s.get("confidence", 0.0)) for s in slots_array]
        avg_conf = sum(confidences) / len(confidences) if confidences else 0.0
        occ_rate = float(occupied) / float(total_slots) if total_slots else 0.0

        return {
            "parking_lot_id": parking_lot_id,
            "total_slots": total_slots,
            "occupied": occupied,
            "empty": empty_n,
            "empty_slots": empty_n,
            "occupancy_rate": occ_rate,
            "slots": slots_array,
            "timestamp": ts,
            "last_updated": ts,
            "camera_id": camera_id,
            "avg_confidence": avg_conf,
        }


_pipeline_instance: Optional[AIEventPipeline] = None


def get_ai_event_pipeline() -> AIEventPipeline:
    global _pipeline_instance
    if _pipeline_instance is None:
        _pipeline_instance = AIEventPipeline()
    return _pipeline_instance
