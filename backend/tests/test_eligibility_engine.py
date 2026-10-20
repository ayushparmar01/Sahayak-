"""Unit tests for the SAHAYAK Deterministic Eligibility Engine.
Tests all 8 foundation schemes, missing vs false/0 distinctions, all 4 assessment statuses,
conflict handling, and unverified/outdated scheme safeguards.
"""
import pytest
from app.services.eligibility_engine import EligibilityEngine
from app.schemas.eligibility import AssessmentStatus, ConditionOutcome
from app.knowledge.foundation_schemes import FOUNDATION_SCHEMES_KNOWLEDGE

# Lookup dictionary for foundation schemes by ID
SCHEMES_BY_ID = {s["id"]: s for s in FOUNDATION_SCHEMES_KNOWLEDGE}


class TestPMKisanEvaluation:
    """Tests for Pradhan Mantri Kisan Samman Nidhi (pm-kisan)."""

    scheme = SCHEMES_BY_ID["pm-kisan"]

    def test_eligible_farmer_confirmed(self):
        profile = {
            "owns_agricultural_land": True,
            "land_acres": 2.5,
            "is_income_tax_payer": False,
            "is_confirmed": True,
        }
        res = EligibilityEngine.evaluate(self.scheme, profile)
        assert res.status == AssessmentStatus.ELIGIBLE
        assert res.status_label_en == "Eligible"
        assert len(res.conditions_satisfied) >= 2
        assert len(res.conditions_failed) == 0
        assert len(res.missing_information) == 0
        assert res.benefit_summary.amount_inr == 6000.0

    def test_potentially_eligible_unconfirmed(self):
        profile = {
            "owns_agricultural_land": True,
            "land_acres": 2.5,
            "is_income_tax_payer": False,
            "is_confirmed": False,
        }
        res = EligibilityEngine.evaluate(self.scheme, profile)
        assert res.status == AssessmentStatus.POTENTIALLY_ELIGIBLE
        assert res.status_label_en == "Potentially Eligible"

    def test_ineligible_income_tax_payer(self):
        profile = {
            "owns_agricultural_land": True,
            "land_acres": 3.0,
            "is_income_tax_payer": True,
            "is_confirmed": True,
        }
        res = EligibilityEngine.evaluate(self.scheme, profile)
        assert res.status == AssessmentStatus.INELIGIBLE
        assert any(e.id == "PMK_EXCLUSION_INCOME_TAX" for e in res.applicable_exclusions)
        assert "आयकर" in res.summary_explanation_hi or "income tax" in res.summary_explanation_en.lower()

    def test_ineligible_no_land(self):
        profile = {
            "owns_agricultural_land": False,
            "is_income_tax_payer": False,
            "is_confirmed": True,
        }
        res = EligibilityEngine.evaluate(self.scheme, profile)
        assert res.status == AssessmentStatus.INELIGIBLE
        assert any(c.id == "PMK_LAND_OWNERSHIP" and c.outcome == ConditionOutcome.FAIL for c in res.conditions_failed)

    def test_missing_info_never_defaults_to_false(self):
        # Empty profile must not assume citizen does NOT own land or IS NOT a taxpayer
        res = EligibilityEngine.evaluate(self.scheme, {})
        assert res.status == AssessmentStatus.NEEDS_MORE_INFO
        missing_keys = [m.field_name for m in res.missing_information]
        assert "owns_agricultural_land" in missing_keys
        assert "is_income_tax_payer" in missing_keys


class TestPMJAYEvaluation:
    """Tests for Ayushman Bharat PM-JAY (pm-jay)."""

    scheme = SCHEMES_BY_ID["pm-jay"]

    def test_potentially_eligible_bpl_pending_bis(self):
        """BPL card holder without external BIS check is POTENTIALLY_ELIGIBLE, never false ELIGIBLE."""
        profile = {
            "ration_card_type": "BPL",
            "is_income_tax_payer": False,
            "is_confirmed": True,
        }
        res = EligibilityEngine.evaluate(self.scheme, profile)
        assert res.status == AssessmentStatus.POTENTIALLY_ELIGIBLE
        assert res.benefit_summary.amount_inr == 500000.0
        assert any(c.id == "PMJAY_EXT_BIS_MATCH" and c.outcome == ConditionOutcome.PENDING_VERIFICATION for c in res.pending_verifications)

    def test_eligible_with_verified_bis_match(self):
        """When BIS database presence is verified, status promotes to ELIGIBLE."""
        profile = {
            "ration_card_type": "Antyodaya",
            "is_income_tax_payer": False,
            "bis_verified": True,
            "is_confirmed": True,
        }
        res = EligibilityEngine.evaluate(self.scheme, profile)
        assert res.status == AssessmentStatus.ELIGIBLE
        assert res.benefit_summary.amount_inr == 500000.0

    def test_income_alone_cannot_determine_eligibility(self):
        """Providing only annual income without ration card or age 70+ returns NEEDS_MORE_INFO."""
        profile = {
            "annual_income": 120000,
            "is_income_tax_payer": False,
            "is_confirmed": True,
        }
        res = EligibilityEngine.evaluate(self.scheme, profile)
        assert res.status == AssessmentStatus.NEEDS_MORE_INFO
        missing_keys = [m.field_name for m in res.missing_information]
        assert "ration_card_type" in missing_keys

    def test_ineligible_taxpayer_high_income(self):
        profile = {
            "ration_card_type": "APL",
            "annual_income": 800000,
            "is_income_tax_payer": True,
            "is_confirmed": True,
        }
        res = EligibilityEngine.evaluate(self.scheme, profile)
        assert res.status == AssessmentStatus.INELIGIBLE

    def test_missing_economic_criteria(self):
        profile = {"age": 45}
        res = EligibilityEngine.evaluate(self.scheme, profile)
        assert res.status == AssessmentStatus.NEEDS_MORE_INFO
        missing_keys = [m.field_name for m in res.missing_information]
        assert "ration_card_type" in missing_keys


class TestKCCEvaluation:
    """Tests for Kisan Credit Card (kcc)."""

    scheme = SCHEMES_BY_ID["kcc"]

    def test_eligible_farmer_valid_age(self):
        profile = {
            "age": 40,
            "owns_agricultural_land": True,
            "occupation": "FARMER",
            "is_confirmed": True,
        }
        res = EligibilityEngine.evaluate(self.scheme, profile)
        assert res.status == AssessmentStatus.ELIGIBLE
        assert res.benefit_summary.amount_inr == 300000.0

    def test_ineligible_underage(self):
        profile = {
            "age": 16,
            "owns_agricultural_land": True,
            "occupation": "FARMER",
            "is_confirmed": True,
        }
        res = EligibilityEngine.evaluate(self.scheme, profile)
        assert res.status == AssessmentStatus.INELIGIBLE
        assert any(c.id == "KCC_AGE_ELIGIBILITY" for c in res.conditions_failed)

    def test_missing_land_and_age(self):
        res = EligibilityEngine.evaluate(self.scheme, {})
        assert res.status == AssessmentStatus.NEEDS_MORE_INFO
        missing_keys = [m.field_name for m in res.missing_information]
        assert "occupation" in missing_keys


class TestPMAYGEvaluation:
    """Tests for Pradhan Mantri Awas Yojana - Gramin (pmay-g)."""

    scheme = SCHEMES_BY_ID["pmay-g"]

    def test_potentially_eligible_kutcha_house_rural(self):
        """Rural kutcha shelter with unverified Awaas+ list returns POTENTIALLY_ELIGIBLE, not false ELIGIBLE."""
        profile = {
            "residence_type": "RURAL",
            "has_pucca_house": False,
            "is_income_tax_payer": False,
            "annual_income": 95000,
            "is_confirmed": True,
        }
        res = EligibilityEngine.evaluate(self.scheme, profile)
        assert res.status == AssessmentStatus.POTENTIALLY_ELIGIBLE
        assert res.benefit_summary.amount_inr == 130000.0
        assert any(c.id == "PMAY_EXT_AWAAS_PLUS" and c.outcome == ConditionOutcome.PENDING_VERIFICATION for c in res.pending_verifications)

    def test_eligible_kutcha_house_rural_awaas_plus_verified(self):
        """When Awaas+ waitlist priority and geo-tagging are verified, status promotes to ELIGIBLE."""
        profile = {
            "residence_type": "RURAL",
            "has_pucca_house": False,
            "is_income_tax_payer": False,
            "annual_income": 95000,
            "awaas_plus_verified": True,
            "is_confirmed": True,
        }
        res = EligibilityEngine.evaluate(self.scheme, profile)
        assert res.status == AssessmentStatus.ELIGIBLE
        assert res.benefit_summary.amount_inr == 130000.0

    def test_ineligible_already_has_pucca_house(self):
        profile = {
            "residence_type": "RURAL",
            "has_pucca_house": True,
            "is_income_tax_payer": False,
            "annual_income": 90000,
            "is_confirmed": True,
        }
        res = EligibilityEngine.evaluate(self.scheme, profile)
        assert res.status == AssessmentStatus.INELIGIBLE
        assert any(e.id == "PMAY_EXCLUSION_PUCCA" for e in res.applicable_exclusions)

    def test_ineligible_urban_residence(self):
        """Urban resident is ineligible for PMAY-G even with shelter deficit and low income."""
        profile = {
            "residence_type": "URBAN",
            "has_pucca_house": False,
            "is_income_tax_payer": False,
            "annual_income": 90000,
            "is_confirmed": True,
        }
        res = EligibilityEngine.evaluate(self.scheme, profile)
        assert res.status == AssessmentStatus.INELIGIBLE
        assert any(c.id == "PMAY_MANDATORY_RURAL_RESIDENCE" and c.outcome == ConditionOutcome.FAIL for c in res.conditions_failed)

    def test_single_passing_income_without_housing_returns_needs_more_info(self):
        """A low income condition alone must NOT establish eligibility without housing & residence verification."""
        profile = {
            "annual_income": 95000,
            "is_income_tax_payer": False,
            "is_confirmed": True,
        }
        res = EligibilityEngine.evaluate(self.scheme, profile)
        assert res.status == AssessmentStatus.NEEDS_MORE_INFO
        missing = {m.field_name for m in res.missing_information}
        assert "has_pucca_house" in missing
        assert "residence_type" in missing


class TestPMUjjwalaEvaluation:
    """Tests for Pradhan Mantri Ujjwala Yojana (pm-ujjwala)."""

    scheme = SCHEMES_BY_ID["pm-ujjwala"]

    def test_eligible_adult_woman_no_lpg(self):
        profile = {
            "gender": "FEMALE",
            "age": 28,
            "has_existing_lpg": False,
            "ration_card_type": "BPL",
            "is_confirmed": True,
        }
        res = EligibilityEngine.evaluate(self.scheme, profile)
        assert res.status == AssessmentStatus.ELIGIBLE
        assert res.benefit_summary.amount_inr == 1600.0
        assert res.benefit_summary.benefit_type == "ONE_TIME_ASSISTANCE"

    def test_ineligible_male_applicant(self):
        profile = {
            "gender": "MALE",
            "age": 30,
            "has_existing_lpg": False,
            "is_confirmed": True,
        }
        res = EligibilityEngine.evaluate(self.scheme, profile)
        assert res.status == AssessmentStatus.INELIGIBLE
        assert any(c.id == "PMUY_MANDATORY_FEMALE" for c in res.conditions_failed)

    def test_ineligible_already_has_lpg(self):
        profile = {
            "gender": "FEMALE",
            "age": 30,
            "has_existing_lpg": True,
            "is_confirmed": True,
        }
        res = EligibilityEngine.evaluate(self.scheme, profile)
        assert res.status == AssessmentStatus.INELIGIBLE
        assert any(e.id == "PMUY_EXCLUSION_EXISTING_LPG" for e in res.applicable_exclusions)


class TestPMFBYEvaluation:
    """Tests for Pradhan Mantri Fasal Bima Yojana (pmfby)."""

    scheme = SCHEMES_BY_ID["pmfby"]

    def test_eligible_farmer_landholder(self):
        profile = {
            "owns_agricultural_land": True,
            "occupation": "FARMER",
            "enrolled_in_crop_insurance": False,
            "is_confirmed": True,
        }
        res = EligibilityEngine.evaluate(self.scheme, profile)
        assert res.status == AssessmentStatus.ELIGIBLE
        assert res.benefit_summary.amount_inr == 0.0
        assert res.benefit_summary.benefit_type == "CROP_INSURANCE_COVER"

    def test_ineligible_already_enrolled(self):
        profile = {
            "owns_agricultural_land": True,
            "occupation": "FARMER",
            "enrolled_in_crop_insurance": True,
            "is_confirmed": True,
        }
        res = EligibilityEngine.evaluate(self.scheme, profile)
        assert res.status == AssessmentStatus.INELIGIBLE
        assert any(e.id == "PMFBY_EXCL_DUPLICATE_INSURANCE" for e in res.applicable_exclusions)


class TestNSAPOAPEvaluation:
    """Tests for National Social Assistance Programme - Old Age Pension (nsap-oap)."""

    scheme = SCHEMES_BY_ID["nsap-oap"]

    def test_eligible_senior_citizen_bpl(self):
        profile = {
            "age": 65,
            "ration_card_type": "BPL",
            "is_income_tax_payer": False,
            "is_confirmed": True,
        }
        res = EligibilityEngine.evaluate(self.scheme, profile)
        assert res.status == AssessmentStatus.ELIGIBLE
        assert res.benefit_summary.amount_inr == 12000.0

    def test_ineligible_under_60(self):
        profile = {
            "age": 52,
            "ration_card_type": "BPL",
            "is_income_tax_payer": False,
            "is_confirmed": True,
        }
        res = EligibilityEngine.evaluate(self.scheme, profile)
        assert res.status == AssessmentStatus.INELIGIBLE
        assert any(c.id == "NSAP_AGE_60_CRITERION" for c in res.conditions_failed)


class TestSSYEvaluation:
    """Tests for Sukanya Samriddhi Yojana (ssy)."""

    scheme = SCHEMES_BY_ID["ssy"]

    def test_eligible_has_girl_child_under_10(self):
        profile = {
            "has_girl_child_under_10": True,
            "is_confirmed": True,
        }
        res = EligibilityEngine.evaluate(self.scheme, profile)
        assert res.status == AssessmentStatus.ELIGIBLE
        assert res.benefit_summary.amount_inr == 150000.0

    def test_ineligible_no_eligible_girl_child(self):
        profile = {
            "has_girl_child_under_10": False,
            "is_confirmed": True,
        }
        res = EligibilityEngine.evaluate(self.scheme, profile)
        assert res.status == AssessmentStatus.INELIGIBLE
        assert any(c.id == "SSY_GIRL_CHILD_CRITERION" for c in res.conditions_failed)


class TestSafeguardsAndConflicts:
    """Tests for conflicting inputs, unverified schemes, and unknown scheme fallbacks."""

    def test_conflicting_inputs_detected(self):
        # land_acres > 0 but owns_agricultural_land == False
        profile = {
            "owns_agricultural_land": False,
            "land_acres": 4.0,
            "is_confirmed": True,
        }
        res = EligibilityEngine.evaluate(SCHEMES_BY_ID["pm-kisan"], profile)
        assert res.status == AssessmentStatus.NEEDS_MORE_INFO
        assert "परस्पर विरोध" in res.summary_explanation_hi or "Conflict" in res.summary_explanation_en

    def test_unverified_scheme_returns_needs_more_info_with_safeguard(self):
        unverified_scheme = {
            "id": "pm-kisan",
            "name_hi": "परीक्षण योजना",
            "name_en": "Test Scheme",
            "rule_version": 1,
            "verification_status": "REVISION_PENDING",
            "is_active": True,
            "official_portal_url": "https://myscheme.gov.in",
        }
        res = EligibilityEngine.evaluate(unverified_scheme, {"owns_agricultural_land": True})
        assert res.status == AssessmentStatus.NEEDS_MORE_INFO
        assert "समीक्षाधीन" in res.status_label_hi or "Pending Verification" in res.status_label_en

    def test_inactive_scheme_returns_needs_more_info(self):
        inactive_scheme = {
            "id": "pm-kisan",
            "name_hi": "निष्क्रिय योजना",
            "name_en": "Inactive Scheme",
            "rule_version": 1,
            "verification_status": "VERIFIED",
            "is_active": False,
            "official_portal_url": "https://myscheme.gov.in",
        }
        res = EligibilityEngine.evaluate(inactive_scheme, {"owns_agricultural_land": True})
        assert res.status == AssessmentStatus.NEEDS_MORE_INFO

    def test_unknown_scheme_id_fallback(self):
        res = EligibilityEngine.evaluate({"id": "unknown-scheme-xyz"}, {})
        assert res.status == AssessmentStatus.NEEDS_MORE_INFO
        assert "Rules Unavailable" in res.status_label_en
