"""Integration tests for Schemes Catalogue and Eligibility Assessment Endpoints.
Tests GET /api/v1/schemes (filtering, catalogue),
GET /api/v1/schemes/{id} (details, rules, 404s),
and POST /api/v1/eligibility/assess (authorization, ownership, overrides).
"""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_schemes_filtering(client: AsyncClient):
    """Test catalogue filtering by category, jurisdiction, and verification status."""
    # Seed by fetching all
    res = await client.get("/api/v1/schemes")
    assert res.status_code == 200
    assert res.json()["total"] >= 8

    # Filter by category = AGRICULTURE (PM-Kisan, PMFBY)
    res_agri = await client.get("/api/v1/schemes?category=AGRICULTURE")
    assert res_agri.status_code == 200
    agri_schemes = res_agri.json()["schemes"]
    assert len(agri_schemes) == 2
    for s in agri_schemes:
        assert s["category"] == "AGRICULTURE"

    # Filter by category = HEALTHCARE (PM-JAY)
    res_health = await client.get("/api/v1/schemes?category=HEALTHCARE")
    assert res_health.status_code == 200
    health_schemes = res_health.json()["schemes"]
    assert len(health_schemes) >= 1
    assert any(s["id"] == "pm-jay" for s in health_schemes)

    # Filter by jurisdiction = CENTRAL_SECTOR
    res_jur = await client.get("/api/v1/schemes?jurisdiction=CENTRAL_SECTOR")
    assert res_jur.status_code == 200
    for s in res_jur.json()["schemes"]:
        assert s["jurisdiction"] == "CENTRAL_SECTOR"


@pytest.mark.asyncio
async def test_get_scheme_detail_success(client: AsyncClient):
    """Test fetching scheme detail returns complete rules, application steps, and sources."""
    res = await client.get("/api/v1/schemes/pm-kisan")
    assert res.status_code == 200
    data = res.json()
    assert data["id"] == "pm-kisan"
    assert data["code"] == "PM_KISAN"
    assert "कृषि" in data["name_hi"] or "किसान" in data["name_hi"]
    assert data["official_portal_url"].startswith("http")
    assert data["max_annual_benefit_inr"] == 6000.0
    assert len(data["documents_required"]) >= 2
    assert len(data["rules"]) >= 1
    for rule in data["rules"]:
        assert "rule_code" in rule
        assert "description_hi" in rule
        assert "source_citation" in rule


@pytest.mark.asyncio
async def test_get_scheme_detail_not_found(client: AsyncClient):
    """Test 404 for non-existent scheme ID."""
    res = await client.get("/api/v1/schemes/non-existent-scheme-999")
    assert res.status_code == 404
    assert "नहीं मिली" in res.json()["detail"] or "not found" in res.json()["detail"].lower()


@pytest.mark.asyncio
async def test_eligibility_assess_auth_guards(client: AsyncClient):
    """Test that POST /api/v1/eligibility/assess enforces session authentication."""
    # 1. Missing X-Session-ID header -> 401
    res_no_auth = await client.post(
        "/api/v1/eligibility/assess",
        json={"scheme_id": "pm-kisan"},
    )
    assert res_no_auth.status_code == 401
    assert "X-Session-ID" in res_no_auth.json()["detail"]

    # 2. Invalid X-Session-ID header -> 403
    res_bad_auth = await client.post(
        "/api/v1/eligibility/assess",
        json={"scheme_id": "pm-kisan"},
        headers={"X-Session-ID": "fake-session-token-xyz"},
    )
    assert res_bad_auth.status_code == 403
    assert "अमान्य" in res_bad_auth.json()["detail"] or "expired" in res_bad_auth.json()["detail"].lower()


@pytest.mark.asyncio
async def test_eligibility_assess_valid_session_and_override(client: AsyncClient):
    """Test end-to-end eligibility assessment with valid session and profile override."""
    # 1. Create a session with consent
    init_res = await client.post(
        "/api/v1/sessions/init",
        json={"consent_given": True, "preferred_language": "hi"},
    )
    assert init_res.status_code == 200
    session_id = init_res.json()["session_id"]
    citizen_id = init_res.json()["citizen_id"]
    headers = {"X-Session-ID": session_id}

    # 2. Update profile with landholder farmer details
    update_res = await client.put(
        f"/api/v1/profile/{citizen_id}",
        headers=headers,
        json={
            "owns_agricultural_land": True,
            "land_acres": 2.5,
            "is_income_tax_payer": False,
            "occupation": "FARMER",
            "is_confirmed": True,
        },
    )
    assert update_res.status_code == 200

    # 3. Assess eligibility for PM-Kisan without override
    assess_res = await client.post(
        "/api/v1/eligibility/assess",
        headers=headers,
        json={"scheme_id": "pm-kisan"},
    )
    assert assess_res.status_code == 200
    data = assess_res.json()
    assert data["scheme_id"] == "pm-kisan"
    assert data["status"] == "ELIGIBLE"
    assert data["benefit_summary"]["amount_inr"] == 6000.0
    assert len(data["conditions_satisfied"]) >= 2
    assert len(data["conditions_failed"]) == 0
    assert len(data["official_sources"]) >= 1

    # 4. Assess with profile_override making them an income tax payer -> INELIGIBLE
    override_res = await client.post(
        "/api/v1/eligibility/assess",
        headers=headers,
        json={
            "scheme_id": "pm-kisan",
            "profile_override": {
                "is_income_tax_payer": True,
            },
        },
    )
    assert override_res.status_code == 200
    override_data = override_res.json()
    assert override_data["status"] == "INELIGIBLE"
    assert any(e["id"] == "PMK_EXCLUSION_INCOME_TAX" for e in override_data["applicable_exclusions"])

    # 5. Assess with unknown scheme ID -> 404
    bad_scheme_res = await client.post(
        "/api/v1/eligibility/assess",
        headers=headers,
        json={"scheme_id": "unknown-scheme-xyz"},
    )
    assert bad_scheme_res.status_code == 404
