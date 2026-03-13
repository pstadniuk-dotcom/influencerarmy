"""Tests for the content queue and QC workflow."""

import pytest
from pathlib import Path

from influencerarmy.models import ContentItem, ContentType, Platform, QCStatus
from influencerarmy.queue import ContentQueue


def _make_queue(tmp_path: Path) -> ContentQueue:
    return ContentQueue(data_dir=tmp_path)


def _sample_item(**kwargs) -> ContentItem:
    defaults = dict(
        influencer_handle="test",
        content_type=ContentType.PHOTO,
        platform=Platform.INSTAGRAM,
        prompt="test photo",
    )
    defaults.update(kwargs)
    return ContentItem(**defaults)


def test_add_and_get(tmp_path):
    q = _make_queue(tmp_path)
    item = q.add(_sample_item())
    assert item.id
    retrieved = q.get(item.id)
    assert retrieved.prompt == "test photo"


def test_mark_pending_review(tmp_path):
    q = _make_queue(tmp_path)
    item = q.add(_sample_item())
    q.mark_pending_review(item.id, image_path="/img.png")
    updated = q.get(item.id)
    assert updated.qc_status == QCStatus.PENDING_REVIEW
    assert updated.image_path == "/img.png"


def test_approve(tmp_path):
    q = _make_queue(tmp_path)
    item = q.add(_sample_item())
    q.mark_pending_review(item.id)
    q.approve(item.id, notes="looks great")
    updated = q.get(item.id)
    assert updated.qc_status == QCStatus.APPROVED
    assert updated.qc_notes == "looks great"


def test_reject(tmp_path):
    q = _make_queue(tmp_path)
    item = q.add(_sample_item())
    q.mark_pending_review(item.id)
    q.reject(item.id, reason="face looks off")
    updated = q.get(item.id)
    assert updated.qc_status == QCStatus.REJECTED
    assert updated.rejection_reason == "face looks off"


def test_cannot_approve_non_pending(tmp_path):
    q = _make_queue(tmp_path)
    item = q.add(_sample_item())
    with pytest.raises(ValueError, match="PENDING_REVIEW"):
        q.approve(item.id)


def test_mark_posted(tmp_path):
    q = _make_queue(tmp_path)
    item = q.add(_sample_item())
    q.mark_pending_review(item.id)
    q.approve(item.id)
    q.mark_posted(item.id, post_id="ig_12345")
    updated = q.get(item.id)
    assert updated.qc_status == QCStatus.POSTED
    assert updated.post_id == "ig_12345"
    assert updated.posted_at


def test_list_by_status(tmp_path):
    q = _make_queue(tmp_path)
    i1 = q.add(_sample_item(prompt="one"))
    i2 = q.add(_sample_item(prompt="two"))
    q.mark_pending_review(i1.id)
    assert len(q.pending_review()) == 1
    assert len(q.list_by_status(QCStatus.GENERATING)) == 1


def test_persistence(tmp_path):
    q1 = _make_queue(tmp_path)
    item = q1.add(_sample_item())
    q1.mark_pending_review(item.id)

    q2 = _make_queue(tmp_path)
    assert len(q2.list_all()) == 1
    assert q2.get(item.id).qc_status == QCStatus.PENDING_REVIEW


def test_stats(tmp_path):
    q = _make_queue(tmp_path)
    q.add(_sample_item(prompt="a"))
    i2 = q.add(_sample_item(prompt="b"))
    q.mark_pending_review(i2.id)
    stats = q.stats()
    assert stats["generating"] == 1
    assert stats["pending_review"] == 1
