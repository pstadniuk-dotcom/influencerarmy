"""Content queue with quality control approval workflow.

Content flows through these stages:
  GENERATING -> PENDING_REVIEW -> APPROVED -> POSTED
                               -> REJECTED (with reason)
"""

import json
import uuid
from datetime import datetime
from pathlib import Path

from influencerarmy.config import settings
from influencerarmy.models import ContentItem, QCStatus


QUEUE_FILE = "content_queue.json"


class ContentQueue:
    """Manages the content pipeline queue with QC approval gates."""

    def __init__(self, data_dir: Path | None = None):
        self.data_dir = data_dir or settings.ensure_data_dir()
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self._items: dict[str, ContentItem] = {}
        self._load()

    # --- Queue operations ---

    def add(self, item: ContentItem) -> ContentItem:
        """Add a new content item to the queue."""
        if not item.id:
            item.id = uuid.uuid4().hex[:12]
        item.updated_at = datetime.now().isoformat()
        self._items[item.id] = item
        self._save()
        return item

    def get(self, item_id: str) -> ContentItem:
        """Get a content item by ID."""
        if item_id not in self._items:
            raise KeyError(f"Content item {item_id} not found")
        return self._items[item_id]

    def update(self, item: ContentItem) -> ContentItem:
        """Update a content item in the queue."""
        item.updated_at = datetime.now().isoformat()
        self._items[item.id] = item
        self._save()
        return item

    def remove(self, item_id: str) -> None:
        """Remove an item from the queue."""
        if item_id in self._items:
            del self._items[item_id]
            self._save()

    # --- Status transitions ---

    def mark_pending_review(self, item_id: str, image_path: str = "", video_path: str = "") -> ContentItem:
        """Mark content as ready for quality review."""
        item = self.get(item_id)
        item.qc_status = QCStatus.PENDING_REVIEW
        if image_path:
            item.image_path = image_path
        if video_path:
            item.video_path = video_path
        return self.update(item)

    def approve(self, item_id: str, notes: str = "") -> ContentItem:
        """Approve content for posting."""
        item = self.get(item_id)
        if item.qc_status != QCStatus.PENDING_REVIEW:
            raise ValueError(
                f"Can only approve items in PENDING_REVIEW status, got {item.qc_status}"
            )
        item.qc_status = QCStatus.APPROVED
        item.qc_notes = notes
        return self.update(item)

    def reject(self, item_id: str, reason: str) -> ContentItem:
        """Reject content with a reason (will need regeneration)."""
        item = self.get(item_id)
        if item.qc_status != QCStatus.PENDING_REVIEW:
            raise ValueError(
                f"Can only reject items in PENDING_REVIEW status, got {item.qc_status}"
            )
        item.qc_status = QCStatus.REJECTED
        item.rejection_reason = reason
        return self.update(item)

    def mark_posted(self, item_id: str, post_id: str = "", post_url: str = "") -> ContentItem:
        """Mark content as successfully posted."""
        item = self.get(item_id)
        item.qc_status = QCStatus.POSTED
        item.posted_at = datetime.now().isoformat()
        item.post_id = post_id
        item.post_url = post_url
        return self.update(item)

    def mark_failed(self, item_id: str, notes: str = "") -> ContentItem:
        """Mark content as failed to post."""
        item = self.get(item_id)
        item.qc_status = QCStatus.FAILED
        item.qc_notes = notes
        return self.update(item)

    # --- Queries ---

    def list_all(self) -> list[ContentItem]:
        """List all items in the queue."""
        return sorted(self._items.values(), key=lambda x: x.created_at, reverse=True)

    def list_by_status(self, status: QCStatus) -> list[ContentItem]:
        """List items filtered by QC status."""
        return [i for i in self.list_all() if i.qc_status == status]

    def list_by_influencer(self, handle: str) -> list[ContentItem]:
        """List all items for a specific influencer."""
        return [i for i in self.list_all() if i.influencer_handle == handle]

    def pending_review(self) -> list[ContentItem]:
        """Get all items waiting for quality review."""
        return self.list_by_status(QCStatus.PENDING_REVIEW)

    def approved(self) -> list[ContentItem]:
        """Get all approved items ready to post."""
        return self.list_by_status(QCStatus.APPROVED)

    def rejected(self) -> list[ContentItem]:
        """Get all rejected items that need rework."""
        return self.list_by_status(QCStatus.REJECTED)

    # --- Stats ---

    def stats(self) -> dict[str, int]:
        """Get counts by status."""
        counts: dict[str, int] = {}
        for item in self._items.values():
            counts[item.qc_status.value] = counts.get(item.qc_status.value, 0) + 1
        return counts

    # --- Persistence ---

    def _save(self) -> None:
        path = self.data_dir / QUEUE_FILE
        data = {
            item_id: item.model_dump(mode="json")
            for item_id, item in self._items.items()
        }
        path.write_text(json.dumps(data, indent=2))

    def _load(self) -> None:
        path = self.data_dir / QUEUE_FILE
        if path.exists():
            data = json.loads(path.read_text())
            self._items = {
                item_id: ContentItem(**item_data)
                for item_id, item_data in data.items()
            }
