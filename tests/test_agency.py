"""Tests for agency influencer management."""

import tempfile
from pathlib import Path

from influencerarmy.agency import Agency
from influencerarmy.models import ContentType, InfluencerProfile, Platform


def _make_agency(tmp_path: Path) -> Agency:
    return Agency(data_dir=tmp_path)


def test_add_and_get_influencer(tmp_path):
    agency = _make_agency(tmp_path)
    profile = InfluencerProfile(
        name="Test Influencer",
        handle="test_inf",
        niche="tech",
    )
    agency.add_influencer(profile)
    retrieved = agency.get_influencer("test_inf")
    assert retrieved.name == "Test Influencer"
    assert retrieved.niche == "tech"


def test_list_influencers(tmp_path):
    agency = _make_agency(tmp_path)
    agency.add_influencer(InfluencerProfile(name="A", handle="a", niche="fitness"))
    agency.add_influencer(InfluencerProfile(name="B", handle="b", niche="travel"))
    assert len(agency.list_influencers()) == 2


def test_remove_influencer(tmp_path):
    agency = _make_agency(tmp_path)
    agency.add_influencer(InfluencerProfile(name="A", handle="a", niche="fitness"))
    agency.remove_influencer("a")
    assert len(agency.list_influencers()) == 0


def test_persistence(tmp_path):
    agency1 = _make_agency(tmp_path)
    agency1.add_influencer(InfluencerProfile(name="A", handle="a", niche="fitness"))

    # Load fresh from disk
    agency2 = _make_agency(tmp_path)
    assert len(agency2.list_influencers()) == 1
    assert agency2.get_influencer("a").name == "A"


def test_create_brief(tmp_path):
    agency = _make_agency(tmp_path)
    agency.add_influencer(
        InfluencerProfile(name="A", handle="a", niche="fitness")
    )
    brief = agency.create_brief(
        handle="a",
        content_type=ContentType.PHOTO,
        prompt="yoga on beach",
        caption="Morning vibes",
        hashtags=["fitness", "yoga"],
    )
    assert brief.influencer.handle == "a"
    assert brief.content_type == ContentType.PHOTO
    assert "yoga" in brief.prompt
