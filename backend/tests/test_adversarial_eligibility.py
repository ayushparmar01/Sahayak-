"""Adversarial and Edge-Case Test Suite for SAHAYAK Deterministic Eligibility Engine.

Covers:
1. Incomplete profiles (ensuring missing values never silently default to False or 0).
2. Conflicting profile fields (land ownership vs acreage contradictions, negative incomes, invalid ages).
3. Outdated, inactive, and revision-pending scheme safeguards (preventing unjustified ELIGIBLE determination).
4. Boundary condition precision (strict statutory age/income cutoffs across NSAP, SSY, PMUY, PMAY-G).
5. Profile override isolation (ensuring temporary simulated overrides NEVER mutate stored database records).
6. Session ownership, authentication enforcement, and cross-session evaluation isolation.
"""
import pytest
from httpx import AsyncClient
from app.services.eligibility_engine import EligibilityEngine
from app.schemas.eligibility import AssessmentStatus, ConditionOutcome
from app.knowledge.foundation_schemes import FOUNDATION_SCHEMES_KNOWLEDGE

SCHEMES = {s["id"]: s for s in FOUNDATION_SCHEMES_KNOWLEDGE}


class TestIncompleteProfileAdversarial:
    """Verifies that missing profile fields never silently default to False or 0."""

    def test_pm_kisan_empty_profile_flags_all_required_missing_fields(self):
        res = EligibilityEngine.evaluate(SCHEMES["pm-kisan"], {})
        assert res.status == AssessmentStatus.NEEDS_MORE_INFO
        missing = {m.field_name for m in res.missing_information}
        assert "owns_agricultural_land" in missing
        assert "is_income_tax_payer" in missing
        assert len(res.conditions_satisfied) == 0
        assert len(res.conditions_failed) == 0

    def test_pm_jay_missing_ration_and_income_needs_more_info(self):
        res = EligibilityEngine.evaluate(SCHEMES["pm-jay"], {"age": 35})
        assert res.status == AssessmentStatus.NEEDS_MORE_INFO
        missing = {m.field_name for m in res.missing_information}
        assert "ration_card_type" in missing
        assert len(res.conditions_failed) == 0

    def test_pm_ujjwala_missing_gender_needs_more_info(self):
        res = EligibilityEngine.evaluate(SCHEMES["pm-ujjwala"], {"age": 25, "ration_card_type": "BPL"})
        assert res.status == AssessmentStatus.NEEDS_MORE_INFO
        missing = {m.field_name for m in res.missing_information}
        assert "gender" in missing

    def test_nsap_missing_both_age_and_ration_card(self):
        res = EligibilityEngine.evaluate(SCHEMES["nsap-oap"], {})
        assert res.status == AssessmentStatus.NEEDS_MORE_INFO
        missing = {m.field_name for m in res.missing_information}
        assert "age" in missing
        assert "ration_card_type" in missing

    def test_ssy_missing_girl_child_flag(self):
        res = EligibilityEngine.evaluate(SCHEMES["ssy"], {"age": 30})
        assert res.status == AssessmentStatus.NEEDS_MORE_INFO
        missing = {m.field_name for m in res.missing_information}
        assert "has_girl_child_under_10" in missing


class TestConflictingProfileFields:
    """Verifies that contradictory inputs produce explicit conflicts rather than arbitrarily choosing a winner."""

    def test_pm_kisan_conflict_land_false_with_positive_acreage(self):
        profile = {
            "owns_agricultural_land": False,
            "land_acres": 3.5,
            "is_income_tax_payer": False,
        }
        res = EligibilityEngine.evaluate(SCHEMES["pm-kisan"], profile)
        assert res.status == AssessmentStatus.NEEDS_MORE_INFO
        assert res.status_label_en == "Conflicting Information"
        assert "owns_agricultural_land" in [m.field_name for m in res.missing_information]

    def test_pm_kisan_conflict_land_true_with_zero_or_negative_acreage(self):
        profile = {
            "owns_agricultural_land": True,
            "land_acres": 0.0,
            "is_income_tax_payer": False,
        }
        res = EligibilityEngine.evaluate(SCHEMES["pm-kisan"], profile)
        assert res.status == AssessmentStatus.NEEDS_MORE_INFO
        assert res.status_label_en == "Conflicting Information"
        assert "land_acres" in [m.field_name for m in res.missing_information]

    def test_global_negative_annual_income_conflict(self):
        profile = {
            "annual_income": -50000,
            "owns_agricultural_land": True,
            "land_acres": 2.0,
        }
        res = EligibilityEngine.evaluate(SCHEMES["pm-kisan"], profile)
        assert res.status == AssessmentStatus.NEEDS_MORE_INFO
        assert "ऋणात्मक" in res.summary_explanation_hi or "negative" in res.summary_explanation_en.lower()

    def test_global_absurd_age_conflict(self):
        profile = {
            "age": 145,
            "owns_agricultural_land": True,
            "land_acres": 2.0,
        }
        res = EligibilityEngine.evaluate(SCHEMES["pm-kisan"], profile)
        assert res.status == AssessmentStatus.NEEDS_MORE_INFO
        assert "अमान्य" in res.summary_explanation_hi or "invalid" in res.summary_explanation_en.lower()


class TestOutdatedAndRevisionPendingSafeguards:
    """Verifies that outdated, inactive, or revision-pending schemes CANNOT produce an ELIGIBLE status."""

    def test_revision_pending_scheme_never_eligible(self):
        mock_scheme = dict(SCHEMES["pm-kisan"])
        mock_scheme["verification_status"] = "REVISION_PENDING"

        eligible_profile = {
            "owns_agricultural_land": True,
            "land_acres": 5.0,
            "is_income_tax_payer": False,
            "is_confirmed": True,
        }
        res = EligibilityEngine.evaluate(mock_scheme, eligible_profile)
        assert res.status != AssessmentStatus.ELIGIBLE
        assert res.status == AssessmentStatus.NEEDS_MORE_INFO
        assert any(p.id == "SCHEME_VERIF_AUDIT" for p in res.pending_verifications)

    def test_outdated_scheme_never_eligible(self):
        mock_scheme = dict(SCHEMES["pm-jay"])
        mock_scheme["verification_status"] = "OUTDATED"

        profile = {
            "ration_card_type": "BPL",
            "is_income_tax_payer": False,
            "is_confirmed": True,
        }
        res = EligibilityEngine.evaluate(mock_scheme, profile)
        assert res.status != AssessmentStatus.ELIGIBLE
        assert res.status == AssessmentStatus.NEEDS_MORE_INFO

    def test_inactive_scheme_never_eligible(self):
        mock_scheme = dict(SCHEMES["kcc"])
        mock_scheme["is_active"] = False

        profile = {
            "age": 35,
            "occupation": "FARMER",
            "owns_agricultural_land": True,
            "is_confirmed": True,
        }
        res = EligibilityEngine.evaluate(mock_scheme, profile)
        assert res.status != AssessmentStatus.ELIGIBLE
        assert res.status == AssessmentStatus.NEEDS_MORE_INFO


class TestStatutoryBoundaryConditions:
    """Verifies strict boundary adherence across statutory guidelines."""

    # 1. NSAP Old Age Pension (Statutory Age >= 60)
    def test_nsap_age_59_ineligible(self):
        profile = {"age": 59, "ration_card_type": "BPL", "is_confirmed": True}
        res = EligibilityEngine.evaluate(SCHEMES["nsap-oap"], profile)
        assert res.status == AssessmentStatus.INELIGIBLE
        assert any(c.id == "NSAP_AGE_60_CRITERION" and c.outcome == ConditionOutcome.FAIL for c in res.conditions_failed)

    def test_nsap_age_60_eligible(self):
        profile = {"age": 60, "ration_card_type": "BPL", "is_confirmed": True}
        res = EligibilityEngine.evaluate(SCHEMES["nsap-oap"], profile)
        assert res.status == AssessmentStatus.ELIGIBLE
        assert any(c.id == "NSAP_AGE_60_CRITERION" and c.outcome == ConditionOutcome.PASS for c in res.conditions_satisfied)

    # 2. PM Ujjwala (Adult Woman Age >= 18)
    def test_pm_ujjwala_age_17_ineligible(self):
        profile = {
            "gender": "FEMALE",
            "age": 17,
            "has_existing_lpg": False,
            "ration_card_type": "BPL",
            "is_confirmed": True,
        }
        res = EligibilityEngine.evaluate(SCHEMES["pm-ujjwala"], profile)
        assert res.status == AssessmentStatus.INELIGIBLE
        assert any(c.id == "PMUY_MANDATORY_AGE_18" for c in res.conditions_failed)

    def test_pm_ujjwala_age_18_eligible(self):
        profile = {
            "gender": "FEMALE",
            "age": 18,
            "has_existing_lpg": False,
            "ration_card_type": "BPL",
            "is_confirmed": True,
        }
        res = EligibilityEngine.evaluate(SCHEMES["pm-ujjwala"], profile)
        assert res.status == AssessmentStatus.ELIGIBLE

    # 3. PMAY-G Multi-Factor Boundaries & Exclusion Cutoffs
    def test_pmay_g_income_180000_rural_kutcha_potentially_eligible(self):
        """At exactly ₹1,80,000/year (₹15,000/month), rural kutcha household clears exclusion ceiling."""
        profile = {
            "residence_type": "RURAL",
            "has_pucca_house": False,
            "annual_income": 180000,
            "is_income_tax_payer": False,
            "is_confirmed": True,
        }
        res = EligibilityEngine.evaluate(SCHEMES["pmay-g"], profile)
        assert res.status == AssessmentStatus.POTENTIALLY_ELIGIBLE
        assert any(c.id == "PMAY_EXT_AWAAS_PLUS" for c in res.pending_verifications)

    def test_pmay_g_income_180001_ineligible(self):
        """At ₹1,80,001/year (>₹15,000/month), household is disqualified under 13-point exclusion."""
        profile = {
            "residence_type": "RURAL",
            "has_pucca_house": False,
            "annual_income": 180001,
            "is_income_tax_payer": False,
            "is_confirmed": True,
        }
        res = EligibilityEngine.evaluate(SCHEMES["pmay-g"], profile)
        assert res.status == AssessmentStatus.INELIGIBLE
        assert any(e.id == "PMAY_EXCLUSION_INCOME" for e in res.applicable_exclusions)

    def test_pmay_g_urban_residence_ineligible(self):
        """Urban residents are statutorily ineligible for PMAY-Gramin regardless of shelter deficit."""
        profile = {
            "residence_type": "URBAN",
            "has_pucca_house": False,
            "annual_income": 80000,
            "is_income_tax_payer": False,
            "is_confirmed": True,
        }
        res = EligibilityEngine.evaluate(SCHEMES["pmay-g"], profile)
        assert res.status == AssessmentStatus.INELIGIBLE
        assert any(c.id == "PMAY_MANDATORY_RURAL_RESIDENCE" and c.outcome == ConditionOutcome.FAIL for c in res.conditions_failed)

    def test_pmay_g_single_passing_income_alone_cannot_grant_eligibility(self):
        """A single passing low income condition MUST NOT establish overall eligibility if housing/residence is missing."""
        profile = {
            "annual_income": 75000,
            "is_income_tax_payer": False,
            "is_confirmed": True,
        }
        res = EligibilityEngine.evaluate(SCHEMES["pmay-g"], profile)
        assert res.status == AssessmentStatus.NEEDS_MORE_INFO
        missing = {m.field_name for m in res.missing_information}
        assert "has_pucca_house" in missing
        assert "residence_type" in missing

    def test_pmay_g_awaas_plus_verified_produces_eligible(self):
        """When Gram Sabha Awaas+ waitlist ranking and geo-tagging are verified, status promotes to ELIGIBLE."""
        profile = {
            "residence_type": "RURAL",
            "has_pucca_house": False,
            "annual_income": 90000,
            "is_income_tax_payer": False,
            "awaas_plus_verified": True,
            "is_confirmed": True,
        }
        res = EligibilityEngine.evaluate(SCHEMES["pmay-g"], profile)
        assert res.status == AssessmentStatus.ELIGIBLE
        assert any(c.id == "PMAY_EXT_AWAAS_PLUS" and c.outcome == ConditionOutcome.PASS for c in res.conditions_satisfied)

    # 4. PM-JAY Registry Matching & Non-Entitlement via Income Alone
    def test_pm_jay_income_alone_never_grants_eligibility(self):
        """A general income certificate alone (e.g. ₹1,20,000) does NOT confer statutory entitlement to PM-JAY."""
        profile = {
            "annual_income": 120000,
            "is_income_tax_payer": False,
            "is_confirmed": True,
        }
        res = EligibilityEngine.evaluate(SCHEMES["pm-jay"], profile)
        assert res.status == AssessmentStatus.NEEDS_MORE_INFO
        assert any(m.field_name == "ration_card_type" for m in res.missing_information)

    def test_pm_jay_income_250000_with_bpl_potentially_eligible_pending_bis(self):
        """BPL card holders with non-taxpayer income are POTENTIALLY_ELIGIBLE, pending NHA BIS match."""
        profile = {
            "ration_card_type": "BPL",
            "annual_income": 250000,
            "is_income_tax_payer": False,
            "is_confirmed": True,
        }
        res = EligibilityEngine.evaluate(SCHEMES["pm-jay"], profile)
        assert res.status == AssessmentStatus.POTENTIALLY_ELIGIBLE
        assert any(p.id == "PMJAY_EXT_BIS_MATCH" for p in res.pending_verifications)

    def test_pm_jay_income_250001_with_bpl_remains_potentially_eligible(self):
        """PM-JAY has NO statutory ₹2,50,000 cutoff. An income of ₹2,50,001 does NOT disqualify a BPL family."""
        profile = {
            "ration_card_type": "BPL",
            "annual_income": 250001,
            "is_income_tax_payer": False,
            "is_confirmed": True,
        }
        res = EligibilityEngine.evaluate(SCHEMES["pm-jay"], profile)
        assert res.status == AssessmentStatus.POTENTIALLY_ELIGIBLE
        assert not any(c.id == "PMJAY_TAX_EXCLUSION" and c.outcome == ConditionOutcome.FAIL for c in res.conditions_failed)

    def test_pm_jay_bis_verified_produces_eligible(self):
        """When NHA BIS database presence and e-KYC are verified, status promotes to ELIGIBLE."""
        profile = {
            "ration_card_type": "Antyodaya",
            "is_income_tax_payer": False,
            "bis_verified": True,
            "is_confirmed": True,
        }
        res = EligibilityEngine.evaluate(SCHEMES["pm-jay"], profile)
        assert res.status == AssessmentStatus.ELIGIBLE
        assert any(c.id == "PMJAY_EXT_BIS_MATCH" and c.outcome == ConditionOutcome.PASS for c in res.conditions_satisfied)

    def test_pm_jay_apl_ration_card_ineligible(self):
        """APL card holders without SECC deprivation are ineligible under central PM-JAY."""
        profile = {
            "ration_card_type": "APL",
            "is_income_tax_payer": False,
            "is_confirmed": True,
        }
        res = EligibilityEngine.evaluate(SCHEMES["pm-jay"], profile)
        assert res.status == AssessmentStatus.INELIGIBLE
        assert any(c.id == "PMJAY_BENEFICIARY_CATEGORY" and c.outcome == ConditionOutcome.FAIL for c in res.conditions_failed)

    def test_pm_jay_senior_citizen_70plus_potentially_eligible(self):
        """Citizens aged 70+ qualify under universal Ayushman Bharat Senior Citizen (70+) expansion."""
        profile = {
            "age": 73,
            "is_income_tax_payer": False,
            "is_confirmed": True,
        }
        res = EligibilityEngine.evaluate(SCHEMES["pm-jay"], profile)
        assert res.status == AssessmentStatus.POTENTIALLY_ELIGIBLE
        assert any(c.id == "PMJAY_SENIOR_CITIZEN_70PLUS" for c in res.conditions_satisfied)

    def test_pm_jay_senior_citizen_70plus_taxpayer_eligible(self):
        """Citizens aged 70+ qualify under Ayushman Vaya Vandana expansion irrespective of income tax payer status."""
        profile = {
            "age": 75,
            "is_income_tax_payer": True,
            "annual_income": 950000,
            "is_confirmed": True,
        }
        res = EligibilityEngine.evaluate(SCHEMES["pm-jay"], profile)
        # Must be POTENTIALLY_ELIGIBLE, NOT INELIGIBLE
        assert res.status == AssessmentStatus.POTENTIALLY_ELIGIBLE
        assert any(c.id == "PMJAY_SENIOR_CITIZEN_70PLUS" for c in res.conditions_satisfied)
        assert any(c.id == "PMJAY_SENIOR_TAX_EXEMPTION" for c in res.conditions_satisfied)
        assert not any(c.id == "PMJAY_TAX_EXCLUSION" and c.outcome == ConditionOutcome.FAIL for c in res.conditions_failed)


@pytest.mark.asyncio
class TestApiSecurityAndOverrideIsolation:
    """Verifies that profile_override never mutates stored citizen data, and session isolation is strict."""

    async def test_profile_override_does_not_mutate_db_profile(self, client: AsyncClient):
        # 1. Initialize session
        init_res = await client.post(
            "/api/v1/sessions/init",
            json={"consent_given": True, "preferred_language": "en"},
        )
        assert init_res.status_code == 200
        session_id = init_res.json()["session_id"]
        citizen_id = init_res.json()["citizen_id"]
        headers = {"X-Session-ID": session_id}

        # 2. Persist legitimate farmer profile
        put_res = await client.put(
            f"/api/v1/profile/{citizen_id}",
            headers=headers,
            json={
                "owns_agricultural_land": True,
                "land_acres": 3.0,
                "is_income_tax_payer": False,
                "is_confirmed": True,
            },
        )
        assert put_res.status_code == 200

        # 3. Assess with temporary override: is_income_tax_payer = True
        assess_res = await client.post(
            "/api/v1/eligibility/assess",
            headers=headers,
            json={
                "scheme_id": "pm-kisan",
                "profile_override": {"is_income_tax_payer": True},
            },
        )
        assert assess_res.status_code == 200
        assert assess_res.json()["status"] == "INELIGIBLE"

        # 4. Genuinely verify the stored profile was NOT modified
        get_res = await client.get(
            f"/api/v1/profile/{citizen_id}",
            headers=headers,
        )
        assert get_res.status_code == 200
        stored = get_res.json()
        assert stored["is_income_tax_payer"] is False
        assert stored["land_acres"] == 3.0
        assert stored["owns_agricultural_land"] is True

    async def test_cross_session_profile_access_is_blocked(self, client: AsyncClient):
        # Create session 1
        s1 = (await client.post("/api/v1/sessions/init", json={"consent_given": True, "preferred_language": "hi"})).json()
        # Create session 2
        s2 = (await client.post("/api/v1/sessions/init", json={"consent_given": True, "preferred_language": "en"})).json()

        # Session 2 tries to modify Session 1's profile
        attack_res = await client.put(
            f"/api/v1/profile/{s1['citizen_id']}",
            headers={"X-Session-ID": s2["session_id"]},
            json={"annual_income": 999999},
        )
        assert attack_res.status_code == 403
        assert "अनधिकृत" in attack_res.json()["detail"] or "unauthorized" in attack_res.json()["detail"].lower()

    async def test_kiosk_terminate_purges_citizen_and_prevents_subsequent_assess(self, client: AsyncClient):
        # 1. Create session
        init = (await client.post("/api/v1/sessions/init", json={"consent_given": True, "preferred_language": "hi"})).json()
        session_id = init["session_id"]
        headers = {"X-Session-ID": session_id}

        # 2. Terminate session (Kiosk wipe)
        term_res = await client.post(
            "/api/v1/sessions/terminate",
            json={"session_id": session_id},
        )
        assert term_res.status_code == 200
        assert term_res.json()["data_purged"] is True

        # 3. Subsequent assess attempt using wiped session must return 403 Forbidden
        post_wipe_assess = await client.post(
            "/api/v1/eligibility/assess",
            headers=headers,
            json={"scheme_id": "pm-kisan"},
        )
        assert post_wipe_assess.status_code == 403
