"""Queue manager: ONLY module allowed to mutate item state."""
from __future__ import annotations

from typing import Iterable, Optional

from . import database as db
from .logging_config import get_logger
from .models import MediaItem
from .state_machine import assert_transition, can_transition

_log = get_logger("teledrive.queue")


class QueueManager:
    def enqueue(self, item: MediaItem) -> MediaItem:
        existing = db.find_by_source_key(item.source_key) if item.source_key else None
        if existing:
            return existing
        db.upsert_item(item)
        db.add_event(item.id, "enqueued", f"{item.safe_name}")
        return item

    def bulk_enqueue(self, items: Iterable[MediaItem]) -> list[MediaItem]:
        return [self.enqueue(i) for i in items]

    def transition(self, item_id: str, to_state: str, reason: str = "", **fields) -> MediaItem:
        item = db.get_item(item_id)
        if not item:
            raise KeyError(item_id)
        assert_transition(item.state, to_state)
        prev = item.state
        item.state = to_state
        if to_state in ("Downloading", "Uploading"):
            item.attempts += 1
        for k, v in fields.items():
            if hasattr(item, k):
                setattr(item, k, v)
        db.upsert_item(item)
        db.add_event(item.id, "state", f"{prev}->{to_state} {reason}".strip(),
                     {"from": prev, "to": to_state, "reason": reason, "attempts": item.attempts})
        return item

    def try_transition(self, item_id: str, to_state: str, **fields) -> Optional[MediaItem]:
        item = db.get_item(item_id)
        if not item or not can_transition(item.state, to_state):
            return None
        return self.transition(item_id, to_state, **fields)

    def set_priority(self, item_id: str, priority: int) -> None:
        item = db.get_item(item_id)
        if not item:
            return
        item.priority = priority
        db.upsert_item(item)

    def next_pending(self) -> Optional[MediaItem]:
        items = db.list_items(state="Pending", limit=1)
        return items[0] if items else None

    def pending(self) -> list[MediaItem]:
        return db.items_in_states(["Pending", "NeedsRetry", "Downloaded"])

    def active(self) -> list[MediaItem]:
        return db.items_in_states(["Downloading", "Uploading"])

    def snapshot_counts(self) -> dict[str, int]:
        return db.counts_by_state()


QUEUE = QueueManager()
