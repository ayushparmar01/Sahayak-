"""Test session initialization, consent, kiosk termination, and authorization guards."""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_session_init_with_consent(client: AsyncClient):
    payload = {"preferred_language": "hi", "consent_given": True}
    response = await client.post("/api/v1/sessions/init", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "session_id" in data
    assert "citizen_id" in data
    assert data["preferred_language"] == "hi"
    assert data["consent_granted_at"] is not None
    assert data["status"] == "active"


@pytest.mark.asyncio
async def test_profile_session_authorization_guard(client: AsyncClient):
    # 1. Create session A
    res_a = await client.post(
        "/api/v1/sessions/init",
        json={"preferred_language": "hi", "consent_given": True},
    )
    data_a = res_a.json()
    citizen_a_id = data_a["citizen_id"]
    session_a_id = data_a["session_id"]

    # 2. Access with valid session A -> 200 OK
    get_res = await client.get(
        f"/api/v1/profile/{citizen_a_id}",
        headers={"X-Session-ID": session_a_id},
    )
    assert get_res.status_code == 200

    # 3. Access with mismatched session ID -> 403 Forbidden (Anti-ID-guessing)
    bad_res = await client.get(
        f"/api/v1/profile/{citizen_a_id}",
        headers={"X-Session-ID": "sess_attacker_forged_999"},
    )
    assert bad_res.status_code == 403
    assert "बेमेल" in bad_res.json()["detail"] or "Session ID mismatch" in bad_res.json()["detail"]

    # 4. Update with valid session A -> 200 OK
    update_res = await client.put(
        f"/api/v1/profile/{citizen_a_id}",
        headers={"X-Session-ID": session_a_id},
        json={"age": 42, "state": "Uttar Pradesh", "occupation": "farmer"},
    )
    assert update_res.status_code == 200
    assert update_res.json()["profile"]["age"] == 42

    # 5. Update with mismatched session ID -> 403 Forbidden
    bad_update = await client.put(
        f"/api/v1/profile/{citizen_a_id}",
        headers={"X-Session-ID": "sess_attacker_forged_999"},
        json={"age": 99},
    )
    assert bad_update.status_code == 403


@pytest.mark.asyncio
async def test_session_termination_kiosk_wipe_deletes_db_records(client: AsyncClient):
    # 1. Create a session
    init_res = await client.post(
        "/api/v1/sessions/init",
        json={"preferred_language": "hi", "consent_given": True},
    )
    data = init_res.json()
    citizen_id = data["citizen_id"]
    session_id = data["session_id"]

    # 2. Verify profile exists
    check_res = await client.get(
        f"/api/v1/profile/{citizen_id}",
        headers={"X-Session-ID": session_id},
    )
    assert check_res.status_code == 200

    # 3. Terminate session (Kiosk Wipe)
    term_res = await client.post(
        "/api/v1/sessions/terminate",
        json={"session_id": session_id},
    )
    assert term_res.status_code == 200
    assert term_res.json()["data_purged"] is True

    # 4. Verify citizen record is genuinely removed from DB
    after_res = await client.get(
        f"/api/v1/profile/{citizen_id}",
        headers={"X-Session-ID": session_id},
    )
    assert after_res.status_code == 404
