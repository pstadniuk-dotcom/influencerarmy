"""Tests for agency influencer management."""

from pathlib import Path

from influencerarmy.agency import Agency
from influencerarmy.models import AccountStatus, Platform


def _make_agency(tmp_path: Path) -> Agency:
    return Agency(data_dir=tmp_path)


def test_add_and_get_influencer(tmp_path):
    agency = _make_agency(tmp_path)
    profile = agency.add_influencer(
        name="Test Influencer",
        handle="test_inf",
        niche="tech",
        character_dna="25yo woman, brown hair, blue eyes",
    )
    retrieved = agency.get_influencer("test_inf")
    assert retrieved.name == "Test Influencer"
    assert retrieved.niche == "tech"
    assert retrieved.identity.character_dna == "25yo woman, brown hair, blue eyes"


def test_auto_creates_social_accounts(tmp_path):
    agency = _make_agency(tmp_path)
    profile = agency.add_influencer(name="A", handle="a", niche="fitness")
    assert "instagram" in profile.accounts
    assert "tiktok" in profile.accounts
    assert profile.accounts["instagram"].status == AccountStatus.NOT_CREATED
    assert profile.accounts["tiktok"].status == AccountStatus.NOT_CREATED


def test_list_influencers(tmp_path):
    agency = _make_agency(tmp_path)
    agency.add_influencer(name="A", handle="a", niche="fitness")
    agency.add_influencer(name="B", handle="b", niche="travel")
    assert len(agency.list_influencers()) == 2


def test_remove_influencer(tmp_path):
    agency = _make_agency(tmp_path)
    agency.add_influencer(name="A", handle="a", niche="fitness")
    agency.remove_influencer("a")
    assert len(agency.list_influencers()) == 0


def test_persistence(tmp_path):
    agency1 = _make_agency(tmp_path)
    agency1.add_influencer(name="A", handle="a", niche="fitness")

    agency2 = _make_agency(tmp_path)
    assert len(agency2.list_influencers()) == 1
    assert agency2.get_influencer("a").name == "A"


def test_connect_instagram(tmp_path):
    agency = _make_agency(tmp_path)
    agency.add_influencer(name="A", handle="a", niche="fitness")

    agency.mark_account_created("a", Platform.INSTAGRAM, "a_fitness")
    account = agency.get_account("a", Platform.INSTAGRAM)
    assert account.status == AccountStatus.CREATED
    assert account.username == "a_fitness"

    agency.connect_instagram(
        "a", ig_user_id="123", access_token="tok", username="a_fitness"
    )
    account = agency.get_account("a", Platform.INSTAGRAM)
    assert account.status == AccountStatus.CONNECTED
    assert account.ig_user_id == "123"


def test_connect_tiktok(tmp_path):
    agency = _make_agency(tmp_path)
    agency.add_influencer(name="A", handle="a", niche="fitness")

    agency.connect_tiktok("a", open_id="oid", access_token="tok", username="a_fit")
    account = agency.get_account("a", Platform.TIKTOK)
    assert account.status == AccountStatus.CONNECTED
    assert account.tiktok_open_id == "oid"


def test_reference_images(tmp_path):
    agency = _make_agency(tmp_path)
    agency.add_influencer(name="A", handle="a", niche="fitness")
    agency.add_reference_image("a", "/path/to/img1.png")
    agency.add_reference_image("a", "/path/to/img2.png")
    profile = agency.get_influencer("a")
    assert len(profile.identity.reference_images) == 2


def test_set_character_dna(tmp_path):
    agency = _make_agency(tmp_path)
    agency.add_influencer(name="A", handle="a", niche="fitness")
    agency.set_character_dna("a", "tall, athletic, dark hair")
    profile = agency.get_influencer("a")
    assert profile.identity.character_dna == "tall, athletic, dark hair"


def test_onboarding_status_not_ready(tmp_path):
    agency = _make_agency(tmp_path)
    agency.add_influencer(name="A", handle="a", niche="fitness")
    status = agency.onboarding_status("a")
    assert status["ready"] is False
    assert status["has_character_dna"] is False


def test_onboarding_status_ready(tmp_path):
    agency = _make_agency(tmp_path)
    agency.add_influencer(
        name="A", handle="a", niche="fitness",
        character_dna="25yo woman",
    )
    agency.add_reference_image("a", "/img.png")
    agency.connect_instagram("a", ig_user_id="1", access_token="t")
    agency.connect_tiktok("a", open_id="o", access_token="t")
    status = agency.onboarding_status("a")
    assert status["ready"] is True
