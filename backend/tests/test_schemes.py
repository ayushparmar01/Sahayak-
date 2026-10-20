"""Test scheme discovery endpoints."""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_get_schemes_foundation_list(client: AsyncClient):
    response = await client.get("/api/v1/schemes")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 8
    
    # Check that each scheme has mandatory governance fields
    for scheme in data["schemes"]:
        assert "id" in scheme
        assert "code" in scheme
        assert "name_hi" in scheme
        assert "name_en" in scheme
        assert "ministry" in scheme
        assert "official_portal_url" in scheme
        assert scheme["official_portal_url"].startswith("http")
        assert "last_verified_date" in scheme
        assert "verification_status" in scheme
        assert scheme["verification_status"] == "VERIFIED"
        assert "jurisdiction" in scheme
        assert scheme["jurisdiction"] in ("CENTRAL_SECTOR", "CENTRALLY_SPONSORED")
        assert "benefit_type" in scheme
        assert scheme["benefit_type"] in (
            "DIRECT_CASH_TRANSFER",
            "HEALTH_INSURANCE_COVER",
            "CONCESSIONAL_CREDIT_LIMIT",
            "ONE_TIME_ASSISTANCE",
            "CROP_INSURANCE_COVER",
            "SOCIAL_PENSION",
            "SMALL_SAVINGS_DEPOSIT_LIMIT",
        )
        assert "benefit_metric_label_hi" in scheme
        assert "benefit_amount_display_hi" in scheme
