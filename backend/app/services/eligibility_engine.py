"""SAHAYAK Deterministic Eligibility Engine.
Pure Python, rule-based, fully explainable and traceable assessment service.
Does NOT use LLMs for decisions; strictly executes verified official scheme rules.
"""
from datetime import datetime, timezone
from typing import Any

from app.schemas.eligibility import (
    AssessmentStatus,
    ConditionOutcome,
    ConditionEvaluation,
    MissingFieldRequirement,
    BenefitAssessmentSummary,
    OfficialSourceReference,
    EligibilityAssessResponse,
)


class EligibilityEngine:
    """Deterministic rules engine for evaluating citizen eligibility against official government schemes."""

    @classmethod
    def evaluate(
        cls,
        scheme: Any,
        profile: Any,
    ) -> EligibilityAssessResponse:
        """Evaluates a citizen profile against a specific scheme's verified rules.

        Accepts either Pydantic models, SQLAlchemy models, or dicts.
        Returns a structured, explainable EligibilityAssessResponse.
        """
        # Normalize profile into a clean dictionary
        p = cls._normalize_profile(profile)

        def _get_val(obj: Any, key: str, default: Any = None) -> Any:
            if isinstance(obj, dict):
                return obj.get(key, default)
            return getattr(obj, key, default)

        scheme_id = _get_val(scheme, "id") or str(scheme)
        scheme_code = _get_val(scheme, "code", "")
        scheme_name_hi = _get_val(scheme, "name_hi", "")
        scheme_name_en = _get_val(scheme, "name_en", "")
        rule_version = _get_val(scheme, "rule_version", 1)
        verification_status = _get_val(scheme, "verification_status", "VERIFIED")
        is_active = _get_val(scheme, "is_active", True)
        benefit_amount = _get_val(scheme, "max_annual_benefit_inr", 0.0)
        benefit_hi = _get_val(scheme, "benefit_summary_hi", "")
        benefit_en = _get_val(scheme, "benefit_summary_en", "")
        caveats_hi = _get_val(scheme, "caveats_hi", "")
        caveats_en = _get_val(scheme, "caveats_en", "")
        docs = _get_val(scheme, "documents_required_json", [])
        portal_url = _get_val(scheme, "official_portal_url", "https://myscheme.gov.in")

        # Route evaluation to scheme-specific rule evaluator
        eval_method = cls._RULE_EVALUATORS.get(scheme_id)

        if not eval_method:
            return cls._fallback_unsupported_scheme(
                scheme_id=scheme_id,
                scheme_name_hi=scheme_name_hi,
                scheme_name_en=scheme_name_en,
                rule_version=rule_version,
            )

        # Check for inactive or outdated rule status
        if not is_active or verification_status not in ("VERIFIED",):
            return cls._handle_outdated_or_unverified_scheme(
                scheme_id=scheme_id,
                scheme_name_hi=scheme_name_hi,
                scheme_name_en=scheme_name_en,
                rule_version=rule_version,
                verification_status=verification_status,
                portal_url=portal_url,
            )

        # Check global sanity conflicts
        if p.get("age") is not None and (p["age"] < 0 or p["age"] > 125):
            result = cls._build_conflict_result(
                f"दर्ज आयु ({p['age']} वर्ष) अमान्य है। कृपया 0 से 125 वर्ष के मध्य वैध आयु दर्ज करें।",
                f"Entered age ({p['age']} years) is invalid. Please enter a valid age between 0 and 125.",
                "age",
            )
        elif p.get("annual_income") is not None and p["annual_income"] < 0:
            result = cls._build_conflict_result(
                "वार्षिक आय ऋणात्मक नहीं हो सकती। कृपया वैध आय दर्ज करें।",
                "Annual income cannot be negative. Please enter a valid annual income.",
                "annual_income",
            )
        else:
            # Run scheme evaluator
            result = eval_method(cls, p)

        # Build official source reference
        sources = [
            OfficialSourceReference(
                title=getattr(scheme, "verification_source", "Official Scheme Guidelines") or (scheme.get("verification_source", "Official Scheme Guidelines") if isinstance(scheme, dict) else "Official Scheme Guidelines"),
                url=portal_url,
            )
        ]

        benefit_summary = BenefitAssessmentSummary(
            amount_inr=benefit_amount,
            benefit_type=_get_val(scheme, "benefit_type", "DIRECT_CASH_TRANSFER"),
            benefit_metric_label_hi=_get_val(scheme, "benefit_metric_label_hi", "अधिकतम वार्षिक लाभ"),
            benefit_metric_label_en=_get_val(scheme, "benefit_metric_label_en", "Max Annual Benefit"),
            benefit_amount_display_hi=_get_val(scheme, "benefit_amount_display_hi", f"₹{benefit_amount:,.0f}"),
            benefit_amount_display_en=_get_val(scheme, "benefit_amount_display_en", f"₹{benefit_amount:,.0f}"),
            description_hi=benefit_hi,
            description_en=benefit_en,
            caveats_hi=caveats_hi,
            caveats_en=caveats_en,
        )

        return EligibilityAssessResponse(
            scheme_id=scheme_id,
            scheme_name_hi=scheme_name_hi,
            scheme_name_en=scheme_name_en,
            rule_version=rule_version,
            evaluated_at=datetime.now(timezone.utc),
            status=result["status"],
            status_label_hi=result["status_label_hi"],
            status_label_en=result["status_label_en"],
            summary_explanation_hi=result["summary_explanation_hi"],
            summary_explanation_en=result["summary_explanation_en"],
            conditions_satisfied=result["conditions_satisfied"],
            conditions_failed=result["conditions_failed"],
            missing_information=result["missing_information"],
            applicable_exclusions=result["applicable_exclusions"],
            pending_verifications=result["pending_verifications"],
            benefit_summary=benefit_summary,
            required_documents=docs,
            official_sources=sources,
            next_recommended_action_hi=result["next_recommended_action_hi"],
            next_recommended_action_en=result["next_recommended_action_en"],
        )

    # -------------------------------------------------------------------------
    # SCHEME EVALUATORS
    # -------------------------------------------------------------------------

    def _eval_pm_kisan(cls, p: dict[str, Any]) -> dict[str, Any]:
        """Rules for PM Kisan Samman Nidhi (pm-kisan)."""
        satisfied: list[ConditionEvaluation] = []
        failed: list[ConditionEvaluation] = []
        missing: list[MissingFieldRequirement] = []
        exclusions: list[ConditionEvaluation] = []
        pending: list[ConditionEvaluation] = []

        # Check conflicting inputs: land_acres > 0 but owns_agricultural_land == False
        if p.get("owns_agricultural_land") is False and p.get("land_acres", 0) and p["land_acres"] > 0:
            return cls._build_conflict_result(
                "कृषि भूमि स्वामित्व और भूमि क्षेत्र में परस्पर विरोध है। कृपया अपनी प्रोफ़ाइल में पुष्टि करें कि आप भूमि के पंजीकृत स्वामी हैं अथवा नहीं।",
                "Conflict detected between land ownership flag and acreage. Please clarify whether you own the land.",
                "owns_agricultural_land",
            )
        if p.get("owns_agricultural_land") is True and p.get("land_acres") is not None and p["land_acres"] <= 0:
            return cls._build_conflict_result(
                "कृषि भूमि स्वामित्व दर्ज है किंतु भूमि क्षेत्र शून्य अथवा अमान्य है। कृपया अपनी प्रोफ़ाइल में भूमि क्षेत्र स्पष्ट करें।",
                "Conflict detected: Agricultural land ownership is declared as True, but acreage is zero or negative. Please clarify acreage.",
                "land_acres",
            )

        # 1. Mandatory Criterion: Agricultural land ownership
        owns_land = p.get("owns_agricultural_land")
        acres = p.get("land_acres")

        if owns_land is None and acres is None:
            missing.append(
                MissingFieldRequirement(
                    field_name="owns_agricultural_land",
                    label_hi="कृषि भूमि स्वामित्व",
                    label_en="Agricultural Land Ownership",
                    reason_hi="पीएम-किसान केवल पंजीकृत कृषि भूमि धारक परिवारों हेतु लागू है।",
                    reason_en="PM-Kisan is restricted to registered cultivable landholding farmer families.",
                )
            )
        elif owns_land is False or (acres is not None and acres <= 0):
            failed.append(
                ConditionEvaluation(
                    id="PMK_LAND_OWNERSHIP",
                    title_hi="कृषि भूमि का मालिकाना हक",
                    title_en="Agricultural Land Ownership",
                    outcome=ConditionOutcome.FAIL,
                    outcome_detail_hi="आपके नाम पर कृषि भूमि दर्ज नहीं है। योजना केवल भू-स्वामी किसान परिवारों के लिए है।",
                    outcome_detail_en="No cultivable land ownership recorded. The scheme only covers landholding farmer families.",
                    source_citation="PM-KISAN Guidelines para 2.1",
                )
            )
        else:
            satisfied.append(
                ConditionEvaluation(
                    id="PMK_LAND_OWNERSHIP",
                    title_hi="कृषि भूमि का मालिकाना हक",
                    title_en="Agricultural Land Ownership",
                    outcome=ConditionOutcome.PASS,
                    outcome_detail_hi=f"कृषि भूमि दर्ज है ({acres or 'स्वामित्व घोषित'} एकड़)।",
                    outcome_detail_en=f"Cultivable agricultural land recorded ({acres or 'ownership declared'} acres).",
                    source_citation="PM-KISAN Guidelines para 2.1",
                )
            )

        # 2. Exclusion: Income Tax Payer
        is_tax_payer = p.get("is_income_tax_payer")
        if is_tax_payer is None:
            missing.append(
                MissingFieldRequirement(
                    field_name="is_income_tax_payer",
                    label_hi="आयकर दाता स्थिति (Income Tax Payer)",
                    label_en="Income Tax Payer Status",
                    reason_hi="यदि परिवार का कोई सदस्य आयकर देता है, तो पीएम-किसान के नियमों के तहत अपवर्जन लागू होता है।",
                    reason_en="PM-Kisan strictly excludes any family where a member paid income tax in the last assessment year.",
                )
            )
        elif is_tax_payer is True:
            failed.append(
                ConditionEvaluation(
                    id="PMK_EXCLUSION_INCOME_TAX",
                    title_hi="आयकर दाता अपवर्जन नियम",
                    title_en="Income Tax Exclusion Rule",
                    outcome=ConditionOutcome.FAIL,
                    outcome_detail_hi="परिवार में आयकर दाता होने के कारण योजना के अपवर्जन नियम के तहत अपात्र हैं।",
                    outcome_detail_en="Ineligible under statutory exclusion criteria: income tax paid in previous assessment year.",
                    source_citation="PM-KISAN Guidelines Section 3(d)",
                )
            )
            exclusions.append(failed[-1])
        else:
            satisfied.append(
                ConditionEvaluation(
                    id="PMK_EXCLUSION_INCOME_TAX",
                    title_hi="आयकर दाता अपवर्जन नियम",
                    title_en="Income Tax Exclusion Rule",
                    outcome=ConditionOutcome.PASS,
                    outcome_detail_hi="परिवार गैर-आयकर दाता है (अपवर्जन से मुक्त)।",
                    outcome_detail_en="Non-income tax paying household (clear of exclusion).",
                    source_citation="PM-KISAN Guidelines Section 3(d)",
                )
            )

        # 3. External Verification: Land Revenue Records (Khatauni mutation)
        pending.append(
            ConditionEvaluation(
                id="PMK_EXT_KHATAUNI_MUTATION",
                title_hi="राज्य भू-अभिलेख (खतौनी) में नाम दर्ज होने की आधिकारिक पुष्टि",
                title_en="Official State Land Records (Khatauni) Mutation Verification",
                outcome=ConditionOutcome.PENDING_VERIFICATION,
                outcome_detail_hi="राज्य के भूलेख पोर्टल पर खतौनी में आपका नाम और आधार-लिंक्ड बैंक खाता सक्रिय होना अनिवार्य है।",
                outcome_detail_en="Name in State Bhulekh portal and Aadhaar-seeded NPCI bank account must be verified by District Agriculture Dept.",
                source_citation="PM-KISAN Guidelines Section 4",
            )
        )

        # Result Classification
        if failed:
            return {
                "status": AssessmentStatus.INELIGIBLE,
                "status_label_hi": "अपात्र (Ineligible)",
                "status_label_en": "Ineligible",
                "summary_explanation_hi": "आप पीएम-किसान सम्मान निधि के लिए वर्तमान में पात्र नहीं हैं। कारण: " + failed[0].outcome_detail_hi,
                "summary_explanation_en": "You are currently ineligible for PM-Kisan. Reason: " + failed[0].outcome_detail_en,
                "conditions_satisfied": satisfied,
                "conditions_failed": failed,
                "missing_information": missing,
                "applicable_exclusions": exclusions,
                "pending_verifications": pending,
                "next_recommended_action_hi": "यदि आपके पास वैध भूमि है और आयकर नहीं देते हैं, तो अपनी प्रोफ़ाइल में सही विवरण अपडेट करें।",
                "next_recommended_action_en": "If you own land and do not pay income tax, update your profile with correct verified details.",
            }

        if missing:
            return {
                "status": AssessmentStatus.NEEDS_MORE_INFO,
                "status_label_hi": "अधिक जानकारी आवश्यक (Needs More Info)",
                "status_label_en": "Needs More Info",
                "summary_explanation_hi": "पात्रता निर्धारण हेतु कुछ आवश्यक विवरण छूटे हुए हैं। कृपया भूमि स्वामित्व और आयकर स्थिति दर्ज करें।",
                "summary_explanation_en": "Incomplete profile. Please provide land ownership and income tax status to evaluate eligibility.",
                "conditions_satisfied": satisfied,
                "conditions_failed": failed,
                "missing_information": missing,
                "applicable_exclusions": exclusions,
                "pending_verifications": pending,
                "next_recommended_action_hi": "प्रोफ़ाइल में जाकर भूमि स्वामित्व और आयकर दाता स्थिति की पुष्टि करें।",
                "next_recommended_action_en": "Visit your profile and confirm your land ownership and tax status.",
            }

        is_confirmed = p.get("is_confirmed", False)
        status = AssessmentStatus.ELIGIBLE if is_confirmed else AssessmentStatus.POTENTIALLY_ELIGIBLE
        status_label_hi = "पात्र (Eligible)" if is_confirmed else "संभावित पात्र (Potentially Eligible)"
        status_label_en = "Eligible" if is_confirmed else "Potentially Eligible"

        return {
            "status": status,
            "status_label_hi": status_label_hi,
            "status_label_en": status_label_en,
            "summary_explanation_hi": "आपकी स्व-सत्यापित प्रोफ़ाइल के अनुसार आप पीएम-किसान के पात्रता मानदंडों को पूरा करते हैं। आधिकारिक पोर्टल पर भू-अभिलेख खतौनी एवं ई-केवाईसी सत्यापन के उपरांत ही किस्तें जारी होंगी।" if is_confirmed else "आपकी दी गई जानकारी के अनुसार आप पीएम-किसान के लिए संभावित रूप से पात्र हैं। आधिकारिक पोर्टल पर खतौनी व ई-केवाईसी सत्यापन के बाद किस्तें शुरू होंगी।",
            "summary_explanation_en": "Based on self-confirmed profile details, you meet PM-Kisan eligibility criteria. Official DBT disbursement commences only after state revenue (Khatauni) mutation & biometric/OTP e-KYC verification on pmkisan.gov.in." if is_confirmed else "Based on provided details, you are potentially eligible for PM-Kisan. Final sanction requires state land mutation & e-KYC verification.",
            "conditions_satisfied": satisfied,
            "conditions_failed": failed,
            "missing_information": missing,
            "applicable_exclusions": exclusions,
            "pending_verifications": pending,
            "next_recommended_action_hi": "खतौनी की प्रति और आधार कार्ड के साथ pmkisan.gov.in या नजदीकी सीएससी केंद्र पर नया किसान पंजीकरण (New Farmer Registration) करें।",
            "next_recommended_action_en": "Apply via 'New Farmer Registration' at pmkisan.gov.in or nearest CSC with Khatauni and Aadhaar.",
        }

    def _eval_pm_jay(cls, p: dict[str, Any]) -> dict[str, Any]:
        """Rules for Ayushman Bharat PM-JAY (pm-jay).
        
        Official Source: National Health Authority (NHA) PM-JAY Operational Guidelines 2024.
        Key Statutory Principles:
        1. Entitlement is based strictly on inclusion in pre-identified beneficiary registries:
           - SECC 2011 deprivation categories (Rural D1-D5, D7; Urban 11 occupational categories).
           - National Food Security Act (NFSA) Antyodaya Anna Yojana (AAY) / BPL ration cards.
           - Senior Citizens aged 70 and above (universal coverage regardless of income - Sept 2024 expansion).
           - State health convergence schemes (e.g., Mukhyamantri Jan Arogya Yojana in UP).
        2. There is NO universal central annual income cutoff (e.g. ₹2,50,000). A general income certificate
           alone does NOT confer statutory entitlement to PM-JAY.
        3. Automatic Exclusions (NHA Clause 4): Households with motorized 4-wheelers, mechanized agricultural
           machinery, paying income tax, or government employees are excluded.
        4. Beneficiary Verification: Without direct NHA Beneficiary Identification System (BIS) integration,
           a self-confirmed profile can only achieve POTENTIALLY_ELIGIBLE pending official registry check.
        """
        satisfied: list[ConditionEvaluation] = []
        failed: list[ConditionEvaluation] = []
        missing: list[MissingFieldRequirement] = []
        exclusions: list[ConditionEvaluation] = []
        pending: list[ConditionEvaluation] = []

        ration = p.get("ration_card_type")
        income = p.get("annual_income")
        age = p.get("age")
        is_tax = p.get("is_income_tax_payer")
        bis_verified = p.get("bis_verified") or p.get("in_beneficiary_list")

        is_senior_70plus = (age is not None and age >= 70)

        # 1. Automatic Exclusion Check: Income Tax Payer
        # Note: Under Union Cabinet Decision (Sept 2024), coverage for senior citizens aged 70+
        # is universal and distinct, exempt from ordinary socio-economic tax exclusions.
        if is_senior_70plus:
            satisfied.append(
                ConditionEvaluation(
                    id="PMJAY_SENIOR_TAX_EXEMPTION",
                    title_hi="वरिष्ठ नागरिक (70+) सार्वभौमिक पात्रता (आयकर अपवर्जन मुक्त)",
                    title_en="Senior Citizen (70+) Universal Exemption (No Tax Exclusion)",
                    outcome=ConditionOutcome.PASS,
                    outcome_detail_hi="70 वर्ष और उससे अधिक आयु के वरिष्ठ नागरिकों हेतु आयुष्मान भारत सार्वभौमिक है; आयकर दाता होना अपवर्जित नहीं करता।",
                    outcome_detail_en="PM-JAY health coverage for senior citizens aged 70+ is universal irrespective of income or income tax status.",
                    source_citation="Union Cabinet PM-JAY 70+ Universal Expansion Notification (Sept 2024)",
                )
            )
        elif is_tax is True:
            failed.append(
                ConditionEvaluation(
                    id="PMJAY_TAX_EXCLUSION",
                    title_hi="आयकर अपवर्जन नियम",
                    title_en="Income Tax Exclusion Rule",
                    outcome=ConditionOutcome.FAIL,
                    outcome_detail_hi="परिवार में आयकर दाता होने के कारण एनएचए 14-सूत्रीय स्वतः अपवर्जन नियमों (Clause 4) के तहत आयुष्मान भारत से अपवर्जित।",
                    outcome_detail_en="Income tax paying households are automatically excluded from PM-JAY under NHA Exclusion Clause 4.",
                    source_citation="NHA Automatic Exclusion Framework Clause 4",
                )
            )
            exclusions.append(failed[-1])
        elif is_tax is False:
            satisfied.append(
                ConditionEvaluation(
                    id="PMJAY_TAX_EXCLUSION",
                    title_hi="आयकर अपवर्जन नियम",
                    title_en="Income Tax Exclusion Rule",
                    outcome=ConditionOutcome.PASS,
                    outcome_detail_hi="गैर-आयकर दाता परिवार (अपवर्जन से मुक्त)।",
                    outcome_detail_en="Non-income tax payer household (clear of statutory exclusion).",
                    source_citation="NHA Automatic Exclusion Framework Clause 4",
                )
            )
        else:
            missing.append(
                MissingFieldRequirement(
                    field_name="is_income_tax_payer",
                    label_hi="आयकर दाता स्थिति (Income Tax Payer)",
                    label_en="Income Tax Payer Status",
                    reason_hi="आयुष्मान भारत में आयकर दाता परिवार स्वतः अपवर्जित (Ineligible) होते हैं।",
                    reason_en="PM-JAY strictly excludes any household with an income tax payer under NHA Clause 4.",
                )
            )


        # 2. Beneficiary Registry / Target Category Evaluation
        # Senior Citizen (70+) expansion: Universal coverage regardless of income
        if age is not None and age >= 70:
            satisfied.append(
                ConditionEvaluation(
                    id="PMJAY_SENIOR_CITIZEN_70PLUS",
                    title_hi="वरिष्ठ नागरिक (70+) सार्वभौमिक स्वास्थ्य सुरक्षा",
                    title_en="Universal Senior Citizen (70+) Health Coverage",
                    outcome=ConditionOutcome.PASS,
                    outcome_detail_hi=f"आयु ({age} वर्ष) वरिष्ठ नागरिक (70+) विस्तार के अंतर्गत ₹5 लाख पृथक आयुष्मान कवर हेतु पात्र श्रेणी में है।",
                    outcome_detail_en=f"Age ({age} years) satisfies universal PM-JAY Senior Citizen (70+) expansion criterion.",
                    source_citation="Union Cabinet PM-JAY 70+ Expansion Notification (Sept 2024)",
                )
            )
        elif ration in ("BPL", "Antyodaya"):
            satisfied.append(
                ConditionEvaluation(
                    id="PMJAY_BENEFICIARY_CATEGORY",
                    title_hi="राष्ट्रीय खाद्य सुरक्षा (NFSA) / बीपीएल राशन कार्ड श्रेणी",
                    title_en="NFSA / BPL Ration Card Category",
                    outcome=ConditionOutcome.PASS,
                    outcome_detail_hi=f"राशन कार्ड श्रेणी ({ration}) एनएचए/एसईसीसी वंचन पात्रता के अनुरूप है।",
                    outcome_detail_en=f"Ration card category ({ration}) matches eligible target group under NFSA/SECC entitlement framework.",
                    source_citation="NHA PM-JAY Operational Guidelines 2024 & NFSA Alignment",
                )
            )
        elif ration == "APL":
            failed.append(
                ConditionEvaluation(
                    id="PMJAY_BENEFICIARY_CATEGORY",
                    title_hi="केंद्रीय एसईसीसी / एनएफएसए वंचन पात्रता",
                    title_en="Central SECC / NFSA Deprivation Entitlement",
                    outcome=ConditionOutcome.FAIL,
                    outcome_detail_hi="एपीएल राशन कार्ड धारक केंद्रीय आयुष्मान भारत सूची में स्वतः शामिल नहीं हैं। कृपया राज्य विशिष्ट स्वास्थ्य योजनाओं (जैसे मुख्यमंत्री जन आरोग्य) की जांच करें।",
                    outcome_detail_en="APL ration card holders are not entitled under central PM-JAY registry guidelines. Check state-specific health convergence schemes.",
                    source_citation="NHA Beneficiary Eligibility Criteria 2024",
                )
            )
        else:
            # Ration card type is missing or None
            missing.append(
                MissingFieldRequirement(
                    field_name="ration_card_type",
                    label_hi="राशन कार्ड प्रकार (Ration Card Type)",
                    label_en="Ration Card Type",
                    reason_hi="आयुष्मान भारत में पात्रता आय प्रमाण पत्र के बजाय राष्ट्रीय खाद्य सुरक्षा (NFSA) राशन कार्ड (बीपीएल/अंत्योदय) अथवा एसईसीसी डेटाबेस पर आधारित है। केवल आय से पात्रता तय नहीं हो सकती।",
                    reason_en="PM-JAY entitlement cannot be established by income alone; it statutorily requires an NFSA ration card (BPL/Antyodaya), SECC 2011 deprivation listing, or 70+ age.",
                )
            )
            # If user entered income alone without ration card, explicitly flag that income alone does not qualify
            if income is not None:
                pending.append(
                    ConditionEvaluation(
                        id="PMJAY_INCOME_ALONE_NON_ENTITLEMENT",
                        title_hi="आय प्रमाणपत्र बनाम रजिस्ट्री पात्रता",
                        title_en="Income Certificate vs Registry Entitlement",
                        outcome=ConditionOutcome.PENDING_VERIFICATION,
                        outcome_detail_hi=f"दर्ज वार्षिक आय ₹{income:,.0f} है। केंद्रीय आयुष्मान भारत में सामान्य आय सीमा लागू नहीं होती; नाम एसईसीसी 2011 या अंत्योदय सूची में होना अनिवार्य है।",
                        outcome_detail_en=f"Entered annual income is ₹{income:,.0f}. PM-JAY has no general income cutoff; entitlement requires SECC 2011 or NFSA registry listing.",
                        source_citation="NHA PM-JAY Operational Guidelines Section 3",
                    )
                )

        # 3. External check: NHA Beneficiary Identification System (BIS) Match
        if bis_verified:
            satisfied.append(
                ConditionEvaluation(
                    id="PMJAY_EXT_BIS_MATCH",
                    title_hi="एनएचए के बीआईएस डेटाबेस (BIS) में नाम की उपस्थिति",
                    title_en="Presence of Household in NHA Beneficiary Identification System (BIS)",
                    outcome=ConditionOutcome.PASS,
                    outcome_detail_hi="एनएचए के बीआईएस पोर्टल पर परिवार का नाम व ई-केवाईसी आधिकारिक रूप से सत्यापित है।",
                    outcome_detail_en="Household record and e-KYC verified in NHA Beneficiary Identification System (BIS).",
                    source_citation="NHA BIS 2.0 Directives",
                )
            )
        else:
            pending.append(
                ConditionEvaluation(
                    id="PMJAY_EXT_BIS_MATCH",
                    title_hi="एनएचए के बीआईएस डेटाबेस (BIS) में नाम की उपस्थिति",
                    title_en="Presence of Household in NHA Beneficiary Identification System (BIS)",
                    outcome=ConditionOutcome.PENDING_VERIFICATION,
                    outcome_detail_hi="mera.pmjay.gov.in या नजदीकी सूचीबद्ध अस्पताल में राशन कार्ड/आधार द्वारा नाम मिलान एवं बायोमेट्रिक ई-केवाईसी आवश्यक है।",
                    outcome_detail_en="Name match required in SECC/NFSA records via mera.pmjay.gov.in or Ayushman Mitra at empaneled hospital.",
                    source_citation="NHA BIS 2.0 Directives",
                )
            )

        # Decision Resolution
        if failed:
            return {
                "status": AssessmentStatus.INELIGIBLE,
                "status_label_hi": "अपात्र (Ineligible)",
                "status_label_en": "Ineligible",
                "summary_explanation_hi": "आयुष्मान भारत योजना के मानदंडों के अनुसार आप अपात्र हैं। कारण: " + failed[0].outcome_detail_hi,
                "summary_explanation_en": "Ineligible for Ayushman Bharat PM-JAY. Reason: " + failed[0].outcome_detail_en,
                "conditions_satisfied": satisfied,
                "conditions_failed": failed,
                "missing_information": missing,
                "applicable_exclusions": exclusions,
                "pending_verifications": pending,
                "next_recommended_action_hi": "यदि आपके पास बीपीएल/अंत्योदय राशन कार्ड है या परिवार में 70+ वरिष्ठ नागरिक हैं, तो प्रोफ़ाइल अपडेट करें या राज्य की अन्य स्वास्थ्य योजनाओं की जांच करें।",
                "next_recommended_action_en": "If you hold a BPL/Antyodaya ration card or have family members aged 70+, update your profile or check state health welfare schemes.",
            }

        if missing:
            return {
                "status": AssessmentStatus.NEEDS_MORE_INFO,
                "status_label_hi": "अधिक जानकारी आवश्यक (Needs More Info)",
                "status_label_en": "Needs More Info",
                "summary_explanation_hi": "आयुष्मान भारत पात्रता निर्धारण हेतु राशन कार्ड श्रेणी (बीपीएल/अंत्योदय) या 70+ वरिष्ठ नागरिक विवरण आवश्यक है। केवल आय के आधार पर पात्रता तय नहीं हो सकती।",
                "summary_explanation_en": "Ration card category (BPL/Antyodaya) or age (70+ senior citizen) is required to evaluate PM-JAY eligibility. Entitlement cannot be determined by income alone.",
                "conditions_satisfied": satisfied,
                "conditions_failed": failed,
                "missing_information": missing,
                "applicable_exclusions": exclusions,
                "pending_verifications": pending,
                "next_recommended_action_hi": "प्रोफ़ाइल में जाकर राशन कार्ड प्रकार और आयकर दाता स्थिति दर्ज करें।",
                "next_recommended_action_en": "Record your ration card type and income tax status in your profile.",
            }

        if bis_verified:
            status = AssessmentStatus.ELIGIBLE
            status_label_hi = "पात्र (Eligible)"
            status_label_en = "Eligible"
            summary_hi = "सत्यापित बीआईएस डेटाबेस रिकॉर्ड एवं पात्रता मानदंडों के आधार पर आप आयुष्मान भारत ₹5 लाख वार्षिक कैशलेस स्वास्थ्य कवर के पात्र हैं।"
            summary_en = "Based on verified BIS database listing and eligibility criteria, you are eligible for ₹5 Lakh annual cashless health coverage under PM-JAY."
            action_hi = "अपने नजदीकी सूचीबद्ध अस्पताल या सीएससी केंद्र पर जाकर बायोमेट्रिक ई-केवाईसी से प्लास्टिक आयुष्मान कार्ड प्राप्त करें।"
            action_en = "Visit your nearest empaneled hospital or CSC to collect your physical Ayushman Card via biometric e-KYC."
        else:
            status = AssessmentStatus.POTENTIALLY_ELIGIBLE
            status_label_hi = "संभावित पात्र (Potentially Eligible)"
            status_label_en = "Potentially Eligible"
            if is_senior_70plus:
                summary_hi = f"आयु ({age} वर्ष) के आधार पर आप आयुष्मान भारत ₹5 लाख वरिष्ठ नागरिक सार्वभौमिक स्वास्थ्य सुरक्षा के संभावित पात्र हैं। आधिकारिक एनएचए पोर्टल पर ई-केवाईसी (आयुष्मान वय वंदना कार्ड) सत्यापन के बाद कार्ड जारी होगा।"
                summary_en = f"Based on universal senior citizen (70+) expansion (age {age}), you are potentially eligible for ₹5 Lakh health cover under PM-JAY. Official entitlement requires verification on the NHA BIS database."
                action_hi = "beneficiary.nha.gov.in या नजदीकी सीएससी केंद्र पर जाकर वरिष्ठ नागरिक (आयुष्मान वय वंदना कार्ड) हेतु आधार ई-केवाईसी कराएं।"
                action_en = "Visit beneficiary.nha.gov.in or nearest CSC for Senior Citizen (Ayushman Vaya Vandana Card) Aadhaar e-KYC."
            else:
                summary_hi = "बीपीएल/अंत्योदय श्रेणी के आधार पर आप आयुष्मान भारत ₹5 लाख स्वास्थ्य कवर के संभावित पात्र हैं। आधिकारिक एनएचए बीआईएस डेटाबेस में नाम मिलान के उपरांत ही आयुष्मान कार्ड जारी होगा।"
                summary_en = "Based on BPL/Antyodaya category, you are potentially eligible for ₹5 Lakh health cover under PM-JAY. Official entitlement requires verification on the NHA BIS database."
                action_hi = "mera.pmjay.gov.in पर या नजदीकी सरकारी अस्पताल में आयुष्मान मित्र के पास जाकर परिवार के नाम का सत्यापन कराएं और आयुष्मान कार्ड बनवाएं।"
                action_en = "Verify your family record on mera.pmjay.gov.in or visit an empaneled hospital Ayushman Mitra to confirm BIS registry listing."


        return {
            "status": status,
            "status_label_hi": status_label_hi,
            "status_label_en": status_label_en,
            "summary_explanation_hi": summary_hi,
            "summary_explanation_en": summary_en,
            "conditions_satisfied": satisfied,
            "conditions_failed": failed,
            "missing_information": missing,
            "applicable_exclusions": exclusions,
            "pending_verifications": pending,
            "next_recommended_action_hi": action_hi,
            "next_recommended_action_en": action_en,
        }

    def _eval_kcc(cls, p: dict[str, Any]) -> dict[str, Any]:
        """Rules for Kisan Credit Card (kcc)."""
        satisfied: list[ConditionEvaluation] = []
        failed: list[ConditionEvaluation] = []
        missing: list[MissingFieldRequirement] = []
        exclusions: list[ConditionEvaluation] = []
        pending: list[ConditionEvaluation] = []

        occ = (p.get("occupation") or "").lower()
        owns_land = p.get("owns_agricultural_land")

        if not occ and owns_land is None:
            missing.append(
                MissingFieldRequirement(
                    field_name="occupation",
                    label_hi="व्यवसाय (Occupation)",
                    label_en="Occupation",
                    reason_hi="केसीसी ऋण केवल किसानों व पशुपालन/डेयरी/मत्स्यपालन से जुड़े नागरिकों हेतु उपलब्ध है।",
                    reason_en="KCC credit is available strictly to farmers and allied animal husbandry/fishery workers.",
                )
            )
        elif "farmer" in occ or "kisan" in occ or "krishi" in occ or owns_land is True or "dairy" in occ or "animal" in occ:
            satisfied.append(
                ConditionEvaluation(
                    id="KCC_FARMER_OCCUPATION",
                    title_hi="कृषि / संबद्ध गतिविधि में संलग्नता",
                    title_en="Engagement in Agriculture / Allied Activity",
                    outcome=ConditionOutcome.PASS,
                    outcome_detail_hi="आवेदक किसान या संबद्ध कृषि गतिविधियों में संलग्न है।",
                    outcome_detail_en="Applicant is engaged in farming or allied agricultural/animal husbandry activity.",
                    source_citation="RBI Master Circular on KCC Section 2",
                )
            )
        else:
            failed.append(
                ConditionEvaluation(
                    id="KCC_FARMER_OCCUPATION",
                    title_hi="कृषि / संबद्ध गतिविधि में संलग्नता",
                    title_en="Engagement in Agriculture / Allied Activity",
                    outcome=ConditionOutcome.FAIL,
                    outcome_detail_hi="गैर-कृषक व्यवसाय होने के कारण केसीसी सुविधा लागू नहीं होती।",
                    outcome_detail_en="Ineligible: KCC facility is limited to agricultural and allied farming operations.",
                    source_citation="RBI Master Circular on KCC Section 2",
                )
            )

        # Age criterion: minimum 18 years
        age = p.get("age")
        if age is not None:
            if age < 18:
                failed.append(
                    ConditionEvaluation(
                        id="KCC_AGE_ELIGIBILITY",
                        title_hi="न्यूनतम आयु पात्रता (18 वर्ष)",
                        title_en="Minimum Age Eligibility (18 years)",
                        outcome=ConditionOutcome.FAIL,
                        outcome_detail_hi=f"आपकी आयु {age} वर्ष है। केसीसी खाताधारक की न्यूनतम आयु 18 वर्ष होना अनिवार्य है।",
                        outcome_detail_en=f"Age is {age} years. Minimum age for KCC account holder is 18 years.",
                        source_citation="RBI KCC Operational Guidelines Clause 3.1",
                    )
                )
            else:
                satisfied.append(
                    ConditionEvaluation(
                        id="KCC_AGE_ELIGIBILITY",
                        title_hi="न्यूनतम आयु पात्रता (18 वर्ष)",
                        title_en="Minimum Age Eligibility (18 years)",
                        outcome=ConditionOutcome.PASS,
                        outcome_detail_hi=f"आयु ({age} वर्ष) केसीसी पात्रता मानदंडों (18-75 वर्ष) के अनुरूप है।",
                        outcome_detail_en=f"Age ({age} years) satisfies KCC operational guidelines (18-75 years).",
                        source_citation="RBI KCC Operational Guidelines Clause 3.1",
                    )
                )

        pending.append(
            ConditionEvaluation(
                id="KCC_EXT_BANK_SANCTION",
                title_hi="बैंक साख निर्धारण एवं नो-ड्यूज (No-Dues) सत्यापन",
                title_en="Bank Credit Appraisal & No-Dues Sanction",
                outcome=ConditionOutcome.PENDING_VERIFICATION,
                outcome_detail_hi="ऋण सीमा (अधिकतम ₹3 लाख पर 4% प्रभावी ब्याज) बैंक द्वारा भूमि व फसल पैमाने के अनुसार तय की जाएगी।",
                outcome_detail_en="Credit limit (up to ₹3 Lakh at 4% effective interest) will be appraised by bank based on crop scale of finance.",
                source_citation="NABARD KCC Guidelines Chapter 4",
            )
        )

        if failed:
            return {
                "status": AssessmentStatus.INELIGIBLE,
                "status_label_hi": "अपात्र (Ineligible)",
                "status_label_en": "Ineligible",
                "summary_explanation_hi": "केसीसी ऋण योजना केवल किसानों व संबद्ध पशुपालकों हेतु है।",
                "summary_explanation_en": "KCC credit facility is restricted to farmers and allied agricultural producers.",
                "conditions_satisfied": satisfied,
                "conditions_failed": failed,
                "missing_information": missing,
                "applicable_exclusions": exclusions,
                "pending_verifications": pending,
                "next_recommended_action_hi": "यदि आप काश्तकार अथवा पशुपालक हैं, तो प्रोफ़ाइल में व्यवसाय अपडेट करें।",
                "next_recommended_action_en": "If you undertake agricultural or allied livestock operations, update your profile.",
            }

        if missing:
            return {
                "status": AssessmentStatus.NEEDS_MORE_INFO,
                "status_label_hi": "अधिक जानकारी आवश्यक (Needs More Info)",
                "status_label_en": "Needs More Info",
                "summary_explanation_hi": "केसीसी पात्रता निर्धारण के लिए व्यवसाय (किसान/पशुपालन) का विवरण आवश्यक है।",
                "summary_explanation_en": "Occupation details (farming/allied activity) required to assess KCC credit eligibility.",
                "conditions_satisfied": satisfied,
                "conditions_failed": failed,
                "missing_information": missing,
                "applicable_exclusions": exclusions,
                "pending_verifications": pending,
                "next_recommended_action_hi": "प्रोफ़ाइल में जाकर अपना व्यवसाय दर्ज करें।",
                "next_recommended_action_en": "Record your occupation in your profile.",
            }

        is_confirmed = p.get("is_confirmed", False)
        status = AssessmentStatus.ELIGIBLE if is_confirmed else AssessmentStatus.POTENTIALLY_ELIGIBLE
        status_label_hi = "पात्र (Eligible)" if is_confirmed else "संभावित पात्र (Potentially Eligible)"
        status_label_en = "Eligible" if is_confirmed else "Potentially Eligible"

        return {
            "status": status,
            "status_label_hi": status_label_hi,
            "status_label_en": status_label_en,
            "summary_explanation_hi": "कृषि संलग्नता के आधार पर आप रियायती दर (प्रभावी 4%) पर ₹3 लाख तक केसीसी साख हेतु बैंक आवेदन करने के पात्र हैं।" if is_confirmed else "कृषि संलग्नता के आधार पर आप रियायती दर (प्रभावी 4%) पर ₹3 लाख तक केसीसी साख हेतु बैंक आवेदन करने के संभावित पात्र हैं।",
            "summary_explanation_en": "Based on verified agricultural occupation, you are eligible to apply for up to ₹3 Lakh concessional KCC credit." if is_confirmed else "Based on agricultural occupation, you are potentially eligible to apply for up to ₹3 Lakh concessional KCC credit.",
            "conditions_satisfied": satisfied,
            "conditions_failed": failed,
            "missing_information": missing,
            "applicable_exclusions": exclusions,
            "pending_verifications": pending,
            "next_recommended_action_hi": "भूमि खतौनी और बोआई विवरण के साथ अपनी स्थानीय बैंक शाखा या सीएससी में 1-पेज केसीसी फॉर्म जमा करें।",
            "next_recommended_action_en": "Submit 1-page KCC application form with land records and crop details at your bank branch.",
        }

    def _eval_pmay_g(cls, p: dict[str, Any]) -> dict[str, Any]:
        """Rules for Pradhan Mantri Awas Yojana - Gramin (pmay-g).
        
        Official Source: Ministry of Rural Development (MoRD) PMAY-G Implementation Framework.
        Key Statutory Principles:
        1. Mandatory Rural Residence: Scheme strictly applies to rural areas (Gram Panchayats).
           Urban residents are covered under PMAY-Urban (PMAY-U) and are disqualified from PMAY-G.
        2. Mandatory Housing Deficit: Beneficiary must be houseless or living in kutcha/dilapidated
           shelter (0, 1, or 2 rooms). Ownership of a pucca house is an automatic 13-point exclusion.
        3. 13-Point Exclusion Criteria (Clause 7 & 8): Monthly household income > ₹15,000 (annual > ₹1,80,000),
           motorized 2/3/4-wheelers, mechanized farm equipment, or paying income tax disqualifies the household.
        4. Multi-Factor Gating: Low income alone does NOT establish eligibility. All mandatory criteria
           (rural residence + kutcha shelter + exclusion clearance) must be satisfied.
        5. Permanent Wait List (PWL) / Awaas+ Selection: Entitlement requires Gram Sabha approved prioritization
           in the Awaas+ survey and site geo-tagging on AwaasSoft. Prototype returns POTENTIALLY_ELIGIBLE
           unless official Awaas+ verification is established.
        """
        satisfied: list[ConditionEvaluation] = []
        failed: list[ConditionEvaluation] = []
        missing: list[MissingFieldRequirement] = []
        exclusions: list[ConditionEvaluation] = []
        pending: list[ConditionEvaluation] = []

        residence = p.get("residence_type")
        is_rural = p.get("is_rural")
        pucca = p.get("has_pucca_house")
        is_tax = p.get("is_income_tax_payer")
        income = p.get("annual_income")
        awaas_verified = p.get("awaas_plus_verified") or p.get("in_awaas_waitlist")

        # 1. Mandatory Criterion: Rural Residence (Gram Panchayat)
        if residence == "URBAN" or is_rural is False:
            failed.append(
                ConditionEvaluation(
                    id="PMAY_MANDATORY_RURAL_RESIDENCE",
                    title_hi="ग्रामीण क्षेत्र निवास अनिवार्यता",
                    title_en="Mandatory Rural Area Residence",
                    outcome=ConditionOutcome.FAIL,
                    outcome_detail_hi="शहरी क्षेत्र के निवासी पीएम आवास (ग्रामीण) के तहत अपात्र हैं। कृपया पीएम आवास (शहरी - PMAY-U) के दिशानिर्देश देखें।",
                    outcome_detail_en="Urban residents are ineligible for PMAY-Gramin. Please apply under PMAY-Urban (PMAY-U).",
                    source_citation="MoRD PMAY-G Implementation Framework Section 1.2",
                )
            )
        elif residence == "RURAL" or is_rural is True:
            satisfied.append(
                ConditionEvaluation(
                    id="PMAY_MANDATORY_RURAL_RESIDENCE",
                    title_hi="ग्रामीण क्षेत्र निवास अनिवार्यता",
                    title_en="Mandatory Rural Area Residence",
                    outcome=ConditionOutcome.PASS,
                    outcome_detail_hi="ग्रामीण क्षेत्र निवास (ग्राम पंचायत अधिकार क्षेत्र)।",
                    outcome_detail_en="Rural residence confirmed within Gram Panchayat jurisdiction.",
                    source_citation="MoRD PMAY-G Implementation Framework Section 1.2",
                )
            )
        else:
            missing.append(
                MissingFieldRequirement(
                    field_name="residence_type",
                    label_hi="निवास क्षेत्र (ग्रामीण/शहरी)",
                    label_en="Residence Type (Rural/Urban)",
                    reason_hi="पीएम आवास (ग्रामीण) केवल ग्राम पंचायत क्षेत्र के निवासियों हेतु है। निवास क्षेत्र (ग्रामीण/शहरी) की पुष्टि आवश्यक है।",
                    reason_en="PMAY-G is strictly for rural residents. Please confirm whether you reside in a rural or urban area.",
                )
            )

        # 2. Mandatory Criterion: Housing Deficit (Kutcha / Houseless)
        if pucca is True:
            failed.append(
                ConditionEvaluation(
                    id="PMAY_EXCLUSION_PUCCA",
                    title_hi="पक्का मकान अपवर्जन नियम",
                    title_en="Pucca House Exclusion Rule",
                    outcome=ConditionOutcome.FAIL,
                    outcome_detail_hi="परिवार के पास पहले से पक्का मकान उपलब्ध होने के कारण 13-सूत्रीय अपवर्जन के तहत अपात्र।",
                    outcome_detail_en="Ineligible under PMAY-G 13-point exclusion: household already possesses a pucca house.",
                    source_citation="PMAY-G Implementation Framework Chapter 2",
                )
            )
            exclusions.append(failed[-1])
        elif pucca is False:
            satisfied.append(
                ConditionEvaluation(
                    id="PMAY_HOUSING_DEFICIT",
                    title_hi="आवास विहीन अथवा कच्चा मकान",
                    title_en="Houseless or Kutcha Shelter",
                    outcome=ConditionOutcome.PASS,
                    outcome_detail_hi="पक्का मकान उपलब्ध नहीं है (कच्चा/बेघर परिवार - आवास अभाव शर्त पूरी)।",
                    outcome_detail_en="No pucca house owned (satisfies mandatory shelter deficit criterion).",
                    source_citation="PMAY-G Framework Section 2.1",
                )
            )
        else:
            missing.append(
                MissingFieldRequirement(
                    field_name="has_pucca_house",
                    label_hi="पक्के मकान का स्वामित्व (Owns Pucca House)",
                    label_en="Owns Pucca House",
                    reason_hi="पीएम आवास (ग्रामीण) केवल बेघर या कच्चे मकान में रहने वाले परिवारों के लिए है। पक्के मकान की स्थिति स्पष्ट करें।",
                    reason_en="PMAY-G is strictly for houseless families or households living in kutcha shelters. Pucca house ownership status is required.",
                )
            )

        # 3. 13-Point Economic Exclusion Criteria: Income Tax & Monthly Income Ceiling
        if is_tax is True:
            failed.append(
                ConditionEvaluation(
                    id="PMAY_EXCLUSION_TAX",
                    title_hi="आयकर दाता अपवर्जन",
                    title_en="Income Tax Payer Exclusion",
                    outcome=ConditionOutcome.FAIL,
                    outcome_detail_hi="परिवार में आयकर दाता होने के कारण 13-सूत्रीय अपवर्जन के तहत अपात्र।",
                    outcome_detail_en="Ineligible under 13-point exclusion: household pays income tax.",
                    source_citation="PMAY-G 13-Point Exclusion Criteria Clause 8",
                )
            )
            exclusions.append(failed[-1])
        elif is_tax is False:
            pass  # Tax exclusion cleared; income threshold evaluated next
        else:
            missing.append(
                MissingFieldRequirement(
                    field_name="is_income_tax_payer",
                    label_hi="आयकर दाता स्थिति (Income Tax Payer)",
                    label_en="Income Tax Payer Status",
                    reason_hi="पीएम आवास में आयकर दाता परिवार 13-सूत्रीय अपवर्जन के तहत अपात्र होते हैं।",
                    reason_en="Households paying income tax are disqualified under PMAY-G 13-point exclusion rules.",
                )
            )

        if income is not None and income > 180000:
            failed.append(
                ConditionEvaluation(
                    id="PMAY_EXCLUSION_INCOME",
                    title_hi="आय अपवर्जन सीमा",
                    title_en="Income Exclusion Threshold",
                    outcome=ConditionOutcome.FAIL,
                    outcome_detail_hi=f"पारिवारिक आय सीमा (अधिकतम ₹15,000/माह अर्थात ₹1.80 लाख/वर्ष) से अधिक (₹{income:,.0f}) होने के कारण अपात्र।",
                    outcome_detail_en=f"Ineligible under 13-point exclusion: monthly household income exceeds ₹15,000 limit (annual ₹{income:,.0f} > ₹1,80,000).",
                    source_citation="PMAY-G 13-Point Exclusion Criteria Clause 7",
                )
            )
            exclusions.append(failed[-1])
        elif income is not None and income <= 180000 and is_tax is False:
            satisfied.append(
                ConditionEvaluation(
                    id="PMAY_INCOME_CRITERION",
                    title_hi="पारिवारिक आय सीमा एवं गैर-आयकर दाता",
                    title_en="Household Income Ceiling & Non-Taxpayer",
                    outcome=ConditionOutcome.PASS,
                    outcome_detail_hi=f"पारिवारिक आय सीमा (अधिकतम ₹15,000/माह) के अनुरूप (₹{income:,.0f}) एवं गैर-आयकर दाता।",
                    outcome_detail_en=f"Household income (₹{income:,.0f}/year) is within ₹15,000/month statutory ceiling and non-taxpayer.",
                    source_citation="PMAY-G 13-Point Exclusion Clause 7",
                )
            )

        # 4. External Verification: Gram Sabha Awaas+ Waitlist Verification
        if awaas_verified:
            satisfied.append(
                ConditionEvaluation(
                    id="PMAY_EXT_AWAAS_PLUS",
                    title_hi="आवास+ (Awaas+) स्थायी वरीयता प्रतीक्षा सूची में नाम की पुष्टि",
                    title_en="Awaas+ Permanent Wait List Priority Verification",
                    outcome=ConditionOutcome.PASS,
                    outcome_detail_hi="ग्राम सभा द्वारा आवास+ सूची में नाम और भू-टैगिंग सत्यापन की आधिकारिक पुष्टि हो चुकी है।",
                    outcome_detail_en="Gram Sabha approved Awaas+ waitlist ranking and geo-tagging officially verified.",
                    source_citation="PMAY-G Selection Directives 2024",
                )
            )
        else:
            pending.append(
                ConditionEvaluation(
                    id="PMAY_EXT_AWAAS_PLUS",
                    title_hi="आवास+ (Awaas+) स्थायी वरीयता प्रतीक्षा सूची में नाम की पुष्टि",
                    title_en="Awaas+ Permanent Wait List Priority Verification",
                    outcome=ConditionOutcome.PENDING_VERIFICATION,
                    outcome_detail_hi="ग्राम सभा द्वारा अनुमोदित आवास+ सूची में वरीयता एवं निर्माण स्थल की जियो-टैगिंग सत्यापन आवश्यक है।",
                    outcome_detail_en="Gram Sabha approved Awaas+ list ranking and site geo-tagging required before financial sanction.",
                    source_citation="PMAY-G Selection Directives 2024",
                )
            )

        # Decision Resolution
        if failed:
            return {
                "status": AssessmentStatus.INELIGIBLE,
                "status_label_hi": "अपात्र (Ineligible)",
                "status_label_en": "Ineligible",
                "summary_explanation_hi": "पीएम आवास योजना (ग्रामीण) के नियमों के अनुसार आप अपात्र हैं। कारण: " + failed[0].outcome_detail_hi,
                "summary_explanation_en": "Ineligible for PMAY-G. Reason: " + failed[0].outcome_detail_en,
                "conditions_satisfied": satisfied,
                "conditions_failed": failed,
                "missing_information": missing,
                "applicable_exclusions": exclusions,
                "pending_verifications": pending,
                "next_recommended_action_hi": "यदि आप ग्रामीण क्षेत्र में रहते हैं और पक्का मकान नहीं है, तो कृपया प्रोफ़ाइल में जानकारी सही करें अथवा पीएम आवास (शहरी) देखें।",
                "next_recommended_action_en": "If you reside in a rural area without a pucca house, update your profile or check PMAY-Urban if residing in a municipality.",
            }

        if missing:
            return {
                "status": AssessmentStatus.NEEDS_MORE_INFO,
                "status_label_hi": "अधिक जानकारी आवश्यक (Needs More Info)",
                "status_label_en": "Needs More Info",
                "summary_explanation_hi": "पीएम आवास (ग्रामीण) पात्रता जांचने के लिए ग्रामीण निवास और पक्के मकान के स्वामित्व की जानकारी अनिवार्य है। केवल आय से पात्रता तय नहीं होती।",
                "summary_explanation_en": "Rural residence status and pucca house ownership are required to evaluate PMAY-G. A low income condition alone cannot determine eligibility.",
                "conditions_satisfied": satisfied,
                "conditions_failed": failed,
                "missing_information": missing,
                "applicable_exclusions": exclusions,
                "pending_verifications": pending,
                "next_recommended_action_hi": "प्रोफ़ाइल में जाकर ग्रामीण/शहरी निवास और पक्के मकान की स्थिति दर्ज करें।",
                "next_recommended_action_en": "Update your residence type (Rural/Urban) and pucca house status in your profile.",
            }

        if awaas_verified:
            status = AssessmentStatus.ELIGIBLE
            status_label_hi = "पात्र (Eligible)"
            status_label_en = "Eligible"
            summary_hi = "ग्रामीण निवास, कच्चा मकान एवं आवास+ सूची सत्यापन के आधार पर आप ₹1.20 लाख मकान निर्माण अनुदान हेतु पात्र हैं।"
            summary_en = "Based on verified rural residence, shelter deficit, and Awaas+ listing, you are eligible for ₹1.20 Lakh unit construction assistance under PMAY-G."
            action_hi = "ग्राम पंचायत सचिव या बीडीओ कार्यालय से संपर्क कर प्रथम किस्त (फाउंडेशन कार्य) हेतु बैंक खाते की जानकारी जमा करें।"
            action_en = "Contact your Panchayat Secretary or BDO office to submit bank details for 1st installment disbursement."
        else:
            status = AssessmentStatus.POTENTIALLY_ELIGIBLE
            status_label_hi = "संभावित पात्र (Potentially Eligible)"
            status_label_en = "Potentially Eligible"
            summary_hi = "ग्रामीण निवास एवं कच्चा मकान/आवास विहीन स्थिति के आधार पर आप ₹1.20 लाख सहायता हेतु पीएम आवास (ग्रामीण) के संभावित पात्र हैं। अंतिम स्वीकृति ग्राम सभा आवास+ प्रतीक्षा सूची व जियो-टैगिंग पर निर्भर है।"
            summary_en = "Based on rural residence and shelter deficit, you are potentially eligible for ₹1.20 Lakh assistance under PMAY-G, subject to Gram Sabha Awaas+ waitlist priority and geo-tagging."
            action_hi = "ग्राम पंचायत सचिव या खंड विकास अधिकारी (BDO) कार्यालय से संपर्क कर आवास+ प्रतीक्षा सूची में अपना क्रमांक जांचें।"
            action_en = "Contact your Village Panchayat Secretary or BDO office to check your priority ranking in the Awaas+ waitlist."

        return {
            "status": status,
            "status_label_hi": status_label_hi,
            "status_label_en": status_label_en,
            "summary_explanation_hi": summary_hi,
            "summary_explanation_en": summary_en,
            "conditions_satisfied": satisfied,
            "conditions_failed": failed,
            "missing_information": missing,
            "applicable_exclusions": exclusions,
            "pending_verifications": pending,
            "next_recommended_action_hi": action_hi,
            "next_recommended_action_en": action_en,
        }

    def _eval_pm_ujjwala(cls, p: dict[str, Any]) -> dict[str, Any]:
        """Rules for PM Ujjwala Yojana 2.0 (pm-ujjwala)."""
        satisfied: list[ConditionEvaluation] = []
        failed: list[ConditionEvaluation] = []
        missing: list[MissingFieldRequirement] = []
        exclusions: list[ConditionEvaluation] = []
        pending: list[ConditionEvaluation] = []

        gender = (p.get("gender") or "").lower()
        age = p.get("age")

        if not gender:
            missing.append(
                MissingFieldRequirement(
                    field_name="gender",
                    label_hi="लिंग (Gender)",
                    label_en="Gender",
                    reason_hi="उज्ज्वला योजना केवल परिवार की वयस्क महिला सदस्य के नाम पर जारी की जाती है।",
                    reason_en="PM Ujjwala connections are issued strictly in the name of an adult woman of the household.",
                )
            )
        elif gender not in ("female", "महिला"):
            failed.append(
                ConditionEvaluation(
                    id="PMUY_MANDATORY_FEMALE",
                    title_hi="वयस्क महिला आवेदक नियम",
                    title_en="Adult Woman Applicant Rule",
                    outcome=ConditionOutcome.FAIL,
                    outcome_detail_hi="उज्ज्वला गैस कनेक्शन केवल परिवार की वयस्क महिला (18+ वर्ष) के नाम ही जारी होता है। पुरुष आवेदक अपात्र हैं।",
                    outcome_detail_en="Ineligible: PMUY connections are granted strictly to adult female applicants (males are ineligible).",
                    source_citation="MoPNG PMUY 2.0 Guidelines Clause 3.1",
                )
            )
        else:
            if age is not None and age < 18:
                failed.append(
                    ConditionEvaluation(
                        id="PMUY_MANDATORY_AGE_18",
                        title_hi="न्यूनतम आयु 18 वर्ष",
                        title_en="Minimum Age 18 Years",
                        outcome=ConditionOutcome.FAIL,
                        outcome_detail_hi=f"आवेदक की आयु 18 वर्ष से कम ({age} वर्ष) है।",
                        outcome_detail_en=f"Applicant age is under 18 years ({age} years).",
                        source_citation="MoPNG PMUY 2.0 Guidelines Clause 3.1",
                    )
                )
            else:
                satisfied.append(
                    ConditionEvaluation(
                        id="PMUY_MANDATORY_FEMALE",
                        title_hi="वयस्क महिला आवेदक नियम",
                        title_en="Adult Woman Applicant Rule",
                        outcome=ConditionOutcome.PASS,
                        outcome_detail_hi="आवेदक वयस्क महिला (18+ वर्ष) है।",
                        outcome_detail_en="Applicant is an adult woman (18+ years).",
                        source_citation="MoPNG PMUY 2.0 Guidelines Clause 3.1",
                    )
                )

        # Existing LPG check
        has_lpg = p.get("has_existing_lpg")
        if has_lpg is True:
            failed.append(
                ConditionEvaluation(
                    id="PMUY_EXCLUSION_EXISTING_LPG",
                    title_hi="पूर्व एलपीजी कनेक्शन अपवर्जन नियम",
                    title_en="Pre-existing LPG Exclusion Rule",
                    outcome=ConditionOutcome.FAIL,
                    outcome_detail_hi="परिवार में पहले से एलपीजी गैस कनेक्शन सक्रिय होने के कारण अपात्र।",
                    outcome_detail_en="Ineligible: Household already possesses an active LPG connection across any OMC.",
                    source_citation="MoPNG PMUY 2.0 Guidelines Clause 3.2",
                )
            )
            exclusions.append(failed[-1])
        elif has_lpg is False:
            satisfied.append(
                ConditionEvaluation(
                    id="PMUY_EXCLUSION_EXISTING_LPG",
                    title_hi="पूर्व एलपीजी कनेक्शन अपवर्जन नियम",
                    title_en="Pre-existing LPG Exclusion Rule",
                    outcome=ConditionOutcome.PASS,
                    outcome_detail_hi="परिवार में पहले से कोई एलपीजी कनेक्शन नहीं है।",
                    outcome_detail_en="No pre-existing active LPG connection in household.",
                    source_citation="MoPNG PMUY 2.0 Guidelines Clause 3.2",
                )
            )

        # Economic eligibility (BPL / Antyodaya / SC / ST)
        ration = p.get("ration_card_type")
        cat = (p.get("social_category") or "").upper()
        if ration in ("BPL", "Antyodaya") or cat in ("SC", "ST"):
            satisfied.append(
                ConditionEvaluation(
                    id="PMUY_ECONOMIC_CATEGORY",
                    title_hi="निर्धन / वंचित सामाजिक श्रेणी",
                    title_en="Deprived / Poor Social Category",
                    outcome=ConditionOutcome.PASS,
                    outcome_detail_hi=f"वंचित श्रेणी मान्य ({ration or cat})।",
                    outcome_detail_en=f"Deprived category satisfied ({ration or cat}).",
                    source_citation="MoPNG PMUY 2.0 Target Categories",
                )
            )

        pending.append(
            ConditionEvaluation(
                id="PMUY_EXT_OMC_DEDUP",
                title_hi="तेल कंपनियों (IOCL/BPCL/HPCL) के केंद्रीय पोर्टल पर डी-डुप्लीकेशन जांच",
                title_en="OMC Centralized De-duplication Verification",
                outcome=ConditionOutcome.PENDING_VERIFICATION,
                outcome_detail_hi="राशन कार्ड में दर्ज सभी वयस्क सदस्यों का आधार आधारित डी-डुप्लीकेशन जांच वितरक द्वारा की जाएगी।",
                outcome_detail_en="LPG distributor will run biometric deduplication across all 3 OMCs for all adult family members.",
                source_citation="Inter-OMC Deduplication Directives",
            )
        )

        if failed:
            return {
                "status": AssessmentStatus.INELIGIBLE,
                "status_label_hi": "अपात्र (Ineligible)",
                "status_label_en": "Ineligible",
                "summary_explanation_hi": "उज्ज्वला 2.0 के नियमों के अनुसार आप अपात्र हैं। कारण: " + failed[0].outcome_detail_hi,
                "summary_explanation_en": "Ineligible for PM Ujjwala 2.0. Reason: " + failed[0].outcome_detail_en,
                "conditions_satisfied": satisfied,
                "conditions_failed": failed,
                "missing_information": missing,
                "applicable_exclusions": exclusions,
                "pending_verifications": pending,
                "next_recommended_action_hi": "उज्ज्वला कनेक्शन केवल परिवार की वयस्क महिला के नाम पर ही आवेदन किया जा सकता है।",
                "next_recommended_action_en": "PMUY applications must be made strictly by an adult female family member.",
            }

        if missing:
            return {
                "status": AssessmentStatus.NEEDS_MORE_INFO,
                "status_label_hi": "अधिक जानकारी आवश्यक (Needs More Info)",
                "status_label_en": "Needs More Info",
                "summary_explanation_hi": "उज्ज्वला योजना हेतु आवेदक का लिंग (महिला) व आयु सत्यापित करना आवश्यक है।",
                "summary_explanation_en": "Gender (female) and age verification required to evaluate PM Ujjwala eligibility.",
                "conditions_satisfied": satisfied,
                "conditions_failed": failed,
                "missing_information": missing,
                "applicable_exclusions": exclusions,
                "pending_verifications": pending,
                "next_recommended_action_hi": "प्रोफ़ाइल में जाकर लिंग और आयु का विवरण दर्ज करें।",
                "next_recommended_action_en": "Record your gender and age in your profile.",
            }

        is_confirmed = p.get("is_confirmed", False)
        status = AssessmentStatus.ELIGIBLE if is_confirmed else AssessmentStatus.POTENTIALLY_ELIGIBLE
        status_label_hi = "पात्र (Eligible)" if is_confirmed else "संभावित पात्र (Potentially Eligible)"
        status_label_en = "Eligible" if is_confirmed else "Potentially Eligible"

        return {
            "status": status,
            "status_label_hi": status_label_hi,
            "status_label_en": status_label_en,
            "summary_explanation_hi": "वयस्क महिला व बीपीएल/वंचित श्रेणी के आधार पर आप निःशुल्क एलपीजी कनेक्शन (उज्ज्वला 2.0) के पात्र हैं।" if is_confirmed else "वयस्क महिला व बीपीएल/वंचित श्रेणी के आधार पर आप निःशुल्क एलपीजी कनेक्शन (उज्ज्वला 2.0) के संभावित पात्र हैं।",
            "summary_explanation_en": "Based on adult female status and verified category, you are eligible for deposit-free LPG under PMUY 2.0." if is_confirmed else "Based on adult female status and BPL/deprived category, you are potentially eligible for deposit-free LPG under PMUY 2.0.",
            "conditions_satisfied": satisfied,
            "conditions_failed": failed,
            "missing_information": missing,
            "applicable_exclusions": exclusions,
            "pending_verifications": pending,
            "next_recommended_action_hi": "राशन कार्ड, बैंक पासबुक व 14-सूत्रीय घोषणा पत्र के साथ नजदीकी गैस एजेंसी (Indane/BharatGas/HP) में आवेदन करें।",
            "next_recommended_action_en": "Apply at nearest LPG distributor (Indane/BharatGas/HP) with ration card, bank passbook, and declaration.",
        }

    def _eval_pmfby(cls, p: dict[str, Any]) -> dict[str, Any]:
        """Rules for Pradhan Mantri Fasal Bima Yojana (pmfby)."""
        satisfied: list[ConditionEvaluation] = []
        failed: list[ConditionEvaluation] = []
        missing: list[MissingFieldRequirement] = []
        exclusions: list[ConditionEvaluation] = []
        pending: list[ConditionEvaluation] = []

        occ = (p.get("occupation") or "").lower()
        owns_land = p.get("owns_agricultural_land")

        if not occ and owns_land is None:
            missing.append(
                MissingFieldRequirement(
                    field_name="occupation",
                    label_hi="व्यवसाय (Occupation)",
                    label_en="Occupation",
                    reason_hi="फसल बीमा केवल अधिसूचित फसलों की खेती करने वाले किसानों हेतु लागू है।",
                    reason_en="Crop insurance applies strictly to farmers cultivating notified agricultural crops.",
                )
            )
        elif "farmer" in occ or "kisan" in occ or "krishi" in occ or owns_land is True:
            satisfied.append(
                ConditionEvaluation(
                    id="PMFBY_FARMER_STATUS",
                    title_hi="फसल कृषक / काश्तकार स्थिति",
                    title_en="Crop Cultivator / Farmer Status",
                    outcome=ConditionOutcome.PASS,
                    outcome_detail_hi="आवेदक कृषि कार्य में संलग्न है (बीमा योग्य हित उपलब्ध)।",
                    outcome_detail_en="Applicant is engaged in farming with insurable crop interest.",
                    source_citation="Revised Operational Guidelines PMFBY Section 2",
                )
            )
        else:
            failed.append(
                ConditionEvaluation(
                    id="PMFBY_FARMER_STATUS",
                    title_hi="फसल कृषक / काश्तकार स्थिति",
                    title_en="Crop Cultivator / Farmer Status",
                    outcome=ConditionOutcome.FAIL,
                    outcome_detail_hi="गैर-कृषक होने के कारण फसल बीमा योजना लागू नहीं होती।",
                    outcome_detail_en="Ineligible: PMFBY applies strictly to farmers growing notified crops.",
                    source_citation="Revised Operational Guidelines PMFBY Section 2",
                )
            )

        # Duplicate insurance exclusion
        enrolled = p.get("enrolled_in_crop_insurance")
        if enrolled is True:
            failed.append(
                ConditionEvaluation(
                    id="PMFBY_EXCL_DUPLICATE_INSURANCE",
                    title_hi="दोहरा फसल बीमा अपवर्जन",
                    title_en="Duplicate Crop Insurance Exclusion",
                    outcome=ConditionOutcome.FAIL,
                    outcome_detail_hi="समान फसल व मौसम हेतु पहले से बीमा धारक होने के कारण दोहरा बीमा अनुमन्य नहीं है।",
                    outcome_detail_en="Ineligible: Duplicate crop insurance on the same cultivable land for the same season is prohibited.",
                    source_citation="PMFBY Operational Guidelines Clause 7.2",
                )
            )
            exclusions.append(failed[-1])
        elif enrolled is False:
            satisfied.append(
                ConditionEvaluation(
                    id="PMFBY_EXCL_DUPLICATE_INSURANCE",
                    title_hi="दोहरा फसल बीमा अपवर्जन",
                    title_en="Duplicate Crop Insurance Exclusion",
                    outcome=ConditionOutcome.PASS,
                    outcome_detail_hi="वर्तमान मौसम में पूर्व-बीमा नहीं है (दोहरे बीमा से मुक्त)।",
                    outcome_detail_en="No existing duplicate crop insurance recorded for this season.",
                    source_citation="PMFBY Operational Guidelines Clause 7.2",
                )
            )

        pending.append(
            ConditionEvaluation(
                id="PMFBY_EXT_NOTIFIED_WINDOW",
                title_hi="राज्य सरकार की मौसमी अधिसूचना एवं कट-ऑफ तिथि की आधिकारिक पुष्टि",
                title_en="Official State Seasonal Notification & Enrollment Cutoff Window Check",
                outcome=ConditionOutcome.PENDING_VERIFICATION,
                outcome_detail_hi="संबंधित जिले में चालू मौसम (खरीफ/रबी) हेतु फसल अधिसूचित होने व अंतिम तिथि शेष होने की पुष्टि आवश्यक है।",
                outcome_detail_en="Confirmation required that the specific crop in your district is notified for current season within enrollment deadline.",
                source_citation="PMFBY State Notification Framework",
            )
        )

        if failed:
            return {
                "status": AssessmentStatus.INELIGIBLE,
                "status_label_hi": "अपात्र (Ineligible)",
                "status_label_en": "Ineligible",
                "summary_explanation_hi": "फसल बीमा योजना केवल फसलों की खेती करने वाले किसानों हेतु उपलब्ध है।",
                "summary_explanation_en": "Ineligible: PMFBY crop insurance is restricted to crop-cultivating farmers.",
                "conditions_satisfied": satisfied,
                "conditions_failed": failed,
                "missing_information": missing,
                "applicable_exclusions": exclusions,
                "pending_verifications": pending,
                "next_recommended_action_hi": "यदि आप फसलों की खेती करते हैं, तो प्रोफ़ाइल में व्यवसाय 'किसान' चुनें।",
                "next_recommended_action_en": "If you cultivate crops, update your occupation to 'Farmer' in your profile.",
            }

        if missing:
            return {
                "status": AssessmentStatus.NEEDS_MORE_INFO,
                "status_label_hi": "अधिक जानकारी आवश्यक (Needs More Info)",
                "status_label_en": "Needs More Info",
                "summary_explanation_hi": "फसल बीमा पात्रता जांचने के लिए व्यवसाय (किसान) की जानकारी आवश्यक है।",
                "summary_explanation_en": "Occupation details required to assess PMFBY crop insurance eligibility.",
                "conditions_satisfied": satisfied,
                "conditions_failed": failed,
                "missing_information": missing,
                "applicable_exclusions": exclusions,
                "pending_verifications": pending,
                "next_recommended_action_hi": "प्रोफ़ाइल में जाकर अपना व्यवसाय दर्ज करें।",
                "next_recommended_action_en": "Record your occupation in your profile.",
            }

        is_confirmed = p.get("is_confirmed", False)
        status = AssessmentStatus.ELIGIBLE if is_confirmed else AssessmentStatus.POTENTIALLY_ELIGIBLE
        status_label_hi = "पात्र (Eligible)" if is_confirmed else "संभावित पात्र (Potentially Eligible)"
        status_label_en = "Eligible" if is_confirmed else "Potentially Eligible"

        return {
            "status": status,
            "status_label_hi": status_label_hi,
            "status_label_en": status_label_en,
            "summary_explanation_hi": "किसान स्थिति के आधार पर आप 1.5% से 2% रियायती प्रीमियम पर व्यापक फसल बीमा हेतु आवेदन के पात्र हैं।" if is_confirmed else "किसान स्थिति के आधार पर आप 1.5% से 2% रियायती प्रीमियम पर व्यापक फसल बीमा हेतु आवेदन के संभावित पात्र हैं।",
            "summary_explanation_en": "Based on verified farmer status, you are eligible for comprehensive crop insurance at 1.5%-2% subsidized premium." if is_confirmed else "Based on farmer status, you are potentially eligible for comprehensive crop insurance at 1.5%-2% subsidized premium.",
            "conditions_satisfied": satisfied,
            "conditions_failed": failed,
            "missing_information": missing,
            "applicable_exclusions": exclusions,
            "pending_verifications": pending,
            "next_recommended_action_hi": "फसल बोआई प्रमाण पत्र व खतौनी के साथ pmfby.gov.in या अपनी बैंक शाखा में मौसमी अंतिम तिथि से पहले बीमा कराएं।",
            "next_recommended_action_en": "Enroll at pmfby.gov.in or your bank branch before the seasonal cutoff deadline with sowing certificate.",
        }

    def _eval_nsap_oap(cls, p: dict[str, Any]) -> dict[str, Any]:
        """Rules for NSAP Old Age Pension (nsap-oap)."""
        satisfied: list[ConditionEvaluation] = []
        failed: list[ConditionEvaluation] = []
        missing: list[MissingFieldRequirement] = []
        exclusions: list[ConditionEvaluation] = []
        pending: list[ConditionEvaluation] = []

        age = p.get("age")
        ration = p.get("ration_card_type")

        # 1. Mandatory Criterion: Age >= 60
        if age is None:
            missing.append(
                MissingFieldRequirement(
                    field_name="age",
                    label_hi="आयु (Age)",
                    label_en="Age",
                    reason_hi="वृद्धावस्था पेंशन हेतु न्यूनतम आयु 60 वर्ष होना वैधानिक शर्त है।",
                    reason_en="Minimum age of 60 years is a mandatory statutory requirement for Old Age Pension.",
                )
            )
        elif age < 60:
            failed.append(
                ConditionEvaluation(
                    id="NSAP_AGE_60_CRITERION",
                    title_hi="न्यूनतम आयु 60 वर्ष",
                    title_en="Minimum Age 60 Years",
                    outcome=ConditionOutcome.FAIL,
                    outcome_detail_hi=f"आवेदक की आयु {age} वर्ष है (न्यूनतम आवश्यक आयु 60 वर्ष है)।",
                    outcome_detail_en=f"Ineligible: Current age is {age} years (minimum required age is 60).",
                    source_citation="NSAP Guidelines Clause 2.1 (IGNOAPS)",
                )
            )
        else:
            satisfied.append(
                ConditionEvaluation(
                    id="NSAP_AGE_60_CRITERION",
                    title_hi="न्यूनतम आयु 60 वर्ष",
                    title_en="Minimum Age 60 Years",
                    outcome=ConditionOutcome.PASS,
                    outcome_detail_hi=f"आयु {age} वर्ष (60 वर्ष या अधिक की शर्त पूरी)।",
                    outcome_detail_en=f"Age is {age} years (meets requirement of >= 60 years).",
                    source_citation="NSAP Guidelines Clause 2.1 (IGNOAPS)",
                )
            )

        # 2. Mandatory Criterion: BPL household status
        if ration is None:
            missing.append(
                MissingFieldRequirement(
                    field_name="ration_card_type",
                    label_hi="राशन कार्ड प्रकार (बीपीएल स्थिति)",
                    label_en="Ration Card Type (BPL Status)",
                    reason_hi="इंदिरा गांधी राष्ट्रीय वृद्धावस्था पेंशन केवल बीपीएल परिवारों के वृद्धजनों हेतु है।",
                    reason_en="IGNOAPS is strictly meant for elderly persons belonging to Below Poverty Line (BPL) households.",
                )
            )
        elif ration in ("BPL", "Antyodaya"):
            satisfied.append(
                ConditionEvaluation(
                    id="NSAP_BPL_CRITERION",
                    title_hi="बीपीएल / अंत्योदय परिवार स्थिति",
                    title_en="BPL / Antyodaya Household Status",
                    outcome=ConditionOutcome.PASS,
                    outcome_detail_hi=f"बीपीएल स्थिति मान्य ({ration})।",
                    outcome_detail_en=f"BPL household status satisfied ({ration}).",
                    source_citation="NSAP Guidelines Clause 2.2",
                )
            )
        else:
            failed.append(
                ConditionEvaluation(
                    id="NSAP_BPL_CRITERION",
                    title_hi="बीपीएल / अंत्योदय परिवार स्थिति",
                    title_en="BPL / Antyodaya Household Status",
                    outcome=ConditionOutcome.FAIL,
                    outcome_detail_hi="एपीएल (APL) राशन कार्ड होने के कारण बीपीएल शर्त पूरी नहीं होती।",
                    outcome_detail_en="Ineligible: Non-BPL / APL ration card does not qualify under NSAP poverty criteria.",
                    source_citation="NSAP Guidelines Clause 2.2",
                )
            )

        pending.append(
            ConditionEvaluation(
                id="NSAP_EXT_TEHSILDAR_SANCTION",
                title_hi="समाज कल्याण विभाग / तहसीलदार द्वारा आयु व बीपीएल सत्यापन",
                title_en="Social Welfare Department / Tehsildar Verification",
                outcome=ConditionOutcome.PENDING_VERIFICATION,
                outcome_detail_hi="प्रखंड विकास अधिकारी (BDO) एवं समाज कल्याण विभाग द्वारा बीपीएल क्रमांक व भौतिक सत्यापन आवश्यक है।",
                outcome_detail_en="BDO and District Social Welfare Officer must verify BPL serial number and physical residency.",
                source_citation="NSAP State Sanction Directives",
            )
        )

        if failed:
            return {
                "status": AssessmentStatus.INELIGIBLE,
                "status_label_hi": "अपात्र (Ineligible)",
                "status_label_en": "Ineligible",
                "summary_explanation_hi": "वृद्धावस्था पेंशन योजना के नियमों के अनुसार आप अपात्र हैं। कारण: " + failed[0].outcome_detail_hi,
                "summary_explanation_en": "Ineligible for Old Age Pension (IGNOAPS). Reason: " + failed[0].outcome_detail_en,
                "conditions_satisfied": satisfied,
                "conditions_failed": failed,
                "missing_information": missing,
                "applicable_exclusions": exclusions,
                "pending_verifications": pending,
                "next_recommended_action_hi": "वृद्धावस्था पेंशन हेतु न्यूनतम 60 वर्ष आयु और बीपीएल श्रेणी अनिवार्य है।",
                "next_recommended_action_en": "Eligibility strictly requires age 60+ and BPL household qualification.",
            }

        if missing:
            return {
                "status": AssessmentStatus.NEEDS_MORE_INFO,
                "status_label_hi": "अधिक जानकारी आवश्यक (Needs More Info)",
                "status_label_en": "Needs More Info",
                "summary_explanation_hi": "वृद्धावस्था पेंशन पात्रता जांचने के लिए आयु और राशन कार्ड (बीपीएल) का विवरण आवश्यक है।",
                "summary_explanation_en": "Age and BPL ration card details are required to evaluate Old Age Pension eligibility.",
                "conditions_satisfied": satisfied,
                "conditions_failed": failed,
                "missing_information": missing,
                "applicable_exclusions": exclusions,
                "pending_verifications": pending,
                "next_recommended_action_hi": "प्रोफ़ाइल में जाकर आयु और राशन कार्ड प्रकार दर्ज करें।",
                "next_recommended_action_en": "Update your age and ration card type in your profile.",
            }

        is_confirmed = p.get("is_confirmed", False)
        status = AssessmentStatus.ELIGIBLE if is_confirmed else AssessmentStatus.POTENTIALLY_ELIGIBLE
        status_label_hi = "पात्र (Eligible)" if is_confirmed else "संभावित पात्र (Potentially Eligible)"
        status_label_en = "Eligible" if is_confirmed else "Potentially Eligible"

        return {
            "status": status,
            "status_label_hi": status_label_hi,
            "status_label_en": status_label_en,
            "summary_explanation_hi": f"आयु ({age} वर्ष) और बीपीएल श्रेणी के आधार पर आप मासिक वृद्धावस्था पेंशन (केंद्रीय सहायता ₹200-500 + राज्य टॉप-अप) के पात्र हैं।" if is_confirmed else f"आयु ({age} वर्ष) और बीपीएल श्रेणी के आधार पर आप मासिक वृद्धावस्था पेंशन (केंद्रीय सहायता ₹200-500 + राज्य टॉप-अप) के संभावित पात्र हैं।",
            "summary_explanation_en": f"Based on age ({age} yrs) and verified BPL category, you are eligible for monthly pension." if is_confirmed else f"Based on age ({age} yrs) and BPL category, you are potentially eligible for monthly pension (Central ₹200-500 + State top-up).",
            "conditions_satisfied": satisfied,
            "conditions_failed": failed,
            "missing_information": missing,
            "applicable_exclusions": exclusions,
            "pending_verifications": pending,
            "next_recommended_action_hi": "आयु प्रमाण, बीपीएल राशन कार्ड व बैंक पासबुक के साथ अपने राज्य के समाज कल्याण पोर्टल या सीएससी पर आवेदन करें।",
            "next_recommended_action_en": "Apply on State Social Welfare portal (e.g. sspy-up.gov.in) with age proof, BPL card, and bank passbook.",
        }

    def _eval_ssy(cls, p: dict[str, Any]) -> dict[str, Any]:
        """Rules for Sukanya Samriddhi Account (ssy)."""
        satisfied: list[ConditionEvaluation] = []
        failed: list[ConditionEvaluation] = []
        missing: list[MissingFieldRequirement] = []
        exclusions: list[ConditionEvaluation] = []
        pending: list[ConditionEvaluation] = []

        has_girl_child = p.get("has_girl_child_under_10")

        if has_girl_child is None:
            missing.append(
                MissingFieldRequirement(
                    field_name="has_girl_child_under_10",
                    label_hi="10 वर्ष तक की बालिका (Girl Child <= 10 yrs)",
                    label_en="Girl Child <= 10 Years",
                    reason_hi="सुकन्या समृद्धि खाता केवल 10 वर्ष या उससे कम आयु की बालिका के नाम पर ही खोला जा सकता है।",
                    reason_en="Sukanya Samriddhi Account can be opened strictly for a girl child aged 10 years or younger.",
                )
            )
        elif has_girl_child is False:
            failed.append(
                ConditionEvaluation(
                    id="SSY_GIRL_CHILD_CRITERION",
                    title_hi="10 वर्ष तक की बालिका नियम",
                    title_en="Girl Child Aged <= 10 Years Rule",
                    outcome=ConditionOutcome.FAIL,
                    outcome_detail_hi="परिवार में 10 वर्ष तक की बालिका न होने के कारण सुकन्या समृद्धि खाता नहीं खोला जा सकता।",
                    outcome_detail_en="Ineligible: SSY account requires a girl child aged up to 10 years.",
                    source_citation="Sukanya Samriddhi Account Rules 2019 Rule 3",
                )
            )
        else:
            satisfied.append(
                ConditionEvaluation(
                    id="SSY_GIRL_CHILD_CRITERION",
                    title_hi="10 वर्ष तक की बालिका नियम",
                    title_en="Girl Child Aged <= 10 Years Rule",
                    outcome=ConditionOutcome.PASS,
                    outcome_detail_hi="परिवार में 10 वर्ष तक की बालिका उपलब्ध है।",
                    outcome_detail_en="Household has an eligible girl child aged up to 10 years.",
                    source_citation="Sukanya Samriddhi Account Rules 2019 Rule 3",
                )
            )

        pending.append(
            ConditionEvaluation(
                id="SSY_EXT_POST_OFFICE_VERIF",
                title_hi="डाकघर अथवा अधिकृत बैंक में बालिका के जन्म प्रमाण पत्र का सत्यापन",
                title_en="Birth Certificate Verification at Post Office / Authorized Bank",
                outcome=ConditionOutcome.PENDING_VERIFICATION,
                outcome_detail_hi="खाता खुलवाने हेतु सक्षम प्राधिकारी द्वारा जारी बालिका का जन्म प्रमाण पत्र एवं अभिभावक का केवाईसी आवश्यक है।",
                outcome_detail_en="Original birth certificate of girl child and guardian KYC required at the time of account opening.",
                source_citation="India Post Small Savings Operational Rules",
            )
        )

        if failed:
            return {
                "status": AssessmentStatus.INELIGIBLE,
                "status_label_hi": "अपात्र (Ineligible)",
                "status_label_en": "Ineligible",
                "summary_explanation_hi": "सुकन्या समृद्धि योजना केवल 10 वर्ष तक की बालिकाओं के नाम पर बचत खाता खोलने हेतु है।",
                "summary_explanation_en": "Ineligible: SSY is strictly meant for girl children aged 10 years or younger.",
                "conditions_satisfied": satisfied,
                "conditions_failed": failed,
                "missing_information": missing,
                "applicable_exclusions": exclusions,
                "pending_verifications": pending,
                "next_recommended_action_hi": "यदि आपके परिवार में 10 वर्ष तक की बालिका है, तो प्रोफ़ाइल में पुष्टि करें।",
                "next_recommended_action_en": "If you have a girl child aged up to 10 years, update your profile.",
            }

        if missing:
            return {
                "status": AssessmentStatus.NEEDS_MORE_INFO,
                "status_label_hi": "अधिक जानकारी आवश्यक (Needs More Info)",
                "status_label_en": "Needs More Info",
                "summary_explanation_hi": "सुकन्या समृद्धि पात्रता जांचने के लिए 10 वर्ष तक की बालिका होने की पुष्टि आवश्यक है।",
                "summary_explanation_en": "Confirmation of having a girl child aged <= 10 years is required to assess SSY eligibility.",
                "conditions_satisfied": satisfied,
                "conditions_failed": failed,
                "missing_information": missing,
                "applicable_exclusions": exclusions,
                "pending_verifications": pending,
                "next_recommended_action_hi": "प्रोफ़ाइल में जाकर 10 वर्ष तक की बालिका की स्थिति दर्ज करें।",
                "next_recommended_action_en": "Record girl child status in your profile.",
            }

        is_confirmed = p.get("is_confirmed", False)
        status = AssessmentStatus.ELIGIBLE if is_confirmed else AssessmentStatus.POTENTIALLY_ELIGIBLE
        status_label_hi = "पात्र (Eligible)" if is_confirmed else "संभावित पात्र (Potentially Eligible)"
        status_label_en = "Eligible" if is_confirmed else "Potentially Eligible"

        return {
            "status": status,
            "status_label_hi": status_label_hi,
            "status_label_en": status_label_en,
            "summary_explanation_hi": "आप अपनी बालिका के नाम पर डाकघर अथवा बैंक में 8.2% वार्षिक ब्याज दर व 80C कर-मुक्त सुकन्या समृद्धि खाता खोलने हेतु पूर्णतः पात्र हैं।" if is_confirmed else "आप अपनी बालिका के नाम पर डाकघर अथवा बैंक में 8.2% वार्षिक ब्याज दर व 80C कर-मुक्त सुकन्या समृद्धि खाता खोलने हेतु संभावित पात्र हैं।",
            "summary_explanation_en": "You are eligible to open an 8.2% tax-free Sukanya Samriddhi Account for your girl child at any Post Office or commercial bank." if is_confirmed else "You are potentially eligible to open a Sukanya Samriddhi Account for your girl child.",
            "conditions_satisfied": satisfied,
            "conditions_failed": failed,
            "missing_information": missing,
            "applicable_exclusions": exclusions,
            "pending_verifications": pending,
            "next_recommended_action_hi": "बालिका का जन्म प्रमाण पत्र, अभिभावक का आधार व फोटो लेकर नजदीकी डाकघर या अधिकृत बैंक शाखा में खाता खुलवाएं।",
            "next_recommended_action_en": "Visit your nearest Post Office or bank branch with child's birth certificate and guardian KYC.",
        }

    # -------------------------------------------------------------------------
    # UTILITY HELPERS
    # -------------------------------------------------------------------------

    @classmethod
    def _normalize_profile(cls, p: Any) -> dict[str, Any]:
        """Normalizes input profile from Pydantic model, ORM entity, or dict into a clean dict."""
        if isinstance(p, dict):
            raw = p
        elif hasattr(p, "model_dump"):
            raw = p.model_dump()
        elif hasattr(p, "__dict__"):
            raw = p.__dict__
        else:
            raw = {}

        return {
            "age": raw.get("age"),
            "state": raw.get("state"),
            "district": raw.get("district"),
            "land_acres": raw.get("land_acres"),
            "land_type": raw.get("land_type"),
            "annual_income": raw.get("annual_income"),
            "ration_card_type": raw.get("ration_card_type"),
            "occupation": raw.get("occupation"),
            "social_category": raw.get("social_category"),
            "gender": raw.get("gender"),
            "is_income_tax_payer": raw.get("is_income_tax_payer"),
            "has_pucca_house": raw.get("has_pucca_house"),
            "owns_agricultural_land": raw.get("owns_agricultural_land"),
            "has_girl_child_under_10": raw.get("has_girl_child_under_10"),
            "has_existing_lpg": raw.get("has_existing_lpg"),
            "enrolled_in_crop_insurance": raw.get("enrolled_in_crop_insurance"),
            "residence_type": (raw.get("residence_type") or ("RURAL" if raw.get("is_rural") is True else ("URBAN" if raw.get("is_rural") is False else None))),
            "is_rural": raw.get("is_rural") if raw.get("is_rural") is not None else (True if str(raw.get("residence_type", "")).upper() == "RURAL" else (False if str(raw.get("residence_type", "")).upper() == "URBAN" else None)),
            "bis_verified": bool(raw.get("bis_verified") or raw.get("in_beneficiary_list")),
            "in_beneficiary_list": bool(raw.get("bis_verified") or raw.get("in_beneficiary_list")),
            "awaas_plus_verified": bool(raw.get("awaas_plus_verified") or raw.get("in_awaas_waitlist")),
            "in_awaas_waitlist": bool(raw.get("awaas_plus_verified") or raw.get("in_awaas_waitlist")),
            "is_confirmed": raw.get("is_confirmed", False),
        }

    @classmethod
    def _build_conflict_result(cls, detail_hi: str, detail_en: str, field: str) -> dict[str, Any]:
        """Builds a response when conflicting profile information is detected."""
        return {
            "status": AssessmentStatus.NEEDS_MORE_INFO,
            "status_label_hi": "विवरण में विरोधाभास (Conflicting Info)",
            "status_label_en": "Conflicting Information",
            "summary_explanation_hi": detail_hi,
            "summary_explanation_en": detail_en,
            "conditions_satisfied": [],
            "conditions_failed": [],
            "missing_information": [
                MissingFieldRequirement(
                    field_name=field,
                    label_hi="पुष्टि आवश्यक",
                    label_en="Confirmation Required",
                    reason_hi=detail_hi,
                    reason_en=detail_en,
                )
            ],
            "applicable_exclusions": [],
            "pending_verifications": [],
            "next_recommended_action_hi": "कृपया अपनी प्रोफ़ाइल में दर्ज विवरण को सही करें।",
            "next_recommended_action_en": "Please correct the conflicting fields in your profile.",
        }

    @classmethod
    def _handle_outdated_or_unverified_scheme(
        cls,
        scheme_id: str,
        scheme_name_hi: str,
        scheme_name_en: str,
        rule_version: int,
        verification_status: str,
        portal_url: str,
    ) -> EligibilityAssessResponse:
        """Handles schemes that are not in VERIFIED status, preventing unjustified definitive determinations."""
        return EligibilityAssessResponse(
            scheme_id=scheme_id,
            scheme_name_hi=scheme_name_hi,
            scheme_name_en=scheme_name_en,
            rule_version=rule_version,
            evaluated_at=datetime.now(timezone.utc),
            status=AssessmentStatus.NEEDS_MORE_INFO,
            status_label_hi="समीक्षाधीन (Pending Verification)",
            status_label_en="Pending Verification",
            summary_explanation_hi=f"इस योजना के नियम वर्तमान में आधिकारिक समीक्षाधीन ({verification_status}) हैं। स्वचालित अंतिम निर्णय उपलब्ध नहीं है।",
            summary_explanation_en=f"Scheme rules are currently under review/unverified ({verification_status}). Automated definitive assessment is disabled.",
            conditions_satisfied=[],
            conditions_failed=[],
            missing_information=[],
            applicable_exclusions=[],
            pending_verifications=[
                ConditionEvaluation(
                    id="SCHEME_VERIF_AUDIT",
                    title_hi="आधिकारिक सरकारी नियमों का अद्यतन सत्यापन",
                    title_en="Official Government Scheme Rules Update Verification",
                    outcome=ConditionOutcome.PENDING_VERIFICATION,
                    outcome_detail_hi="सरकारी पोर्टल से नियमों की आधिकारिक पुष्टि लंबित है।",
                    outcome_detail_en="Official confirmation pending from government portal.",
                    source_citation="SAHAYAK Quality Governance Policy",
                )
            ],
            benefit_summary=BenefitAssessmentSummary(
                amount_inr=0.0,
                benefit_type="UNKNOWN",
                benefit_metric_label_hi="समीक्षाधीन",
                benefit_metric_label_en="Pending Verification",
                benefit_amount_display_hi="समीक्षाधीन",
                benefit_amount_display_en="Pending Verification",
                description_hi="समीक्षाधीन",
                description_en="Under Review",
                caveats_hi="नियम सत्यापन लंबित होने के कारण लाभ विवरण अनिश्चित हो सकता है।",
                caveats_en="Benefit details may vary while rules are pending review.",
            ),
            required_documents=[],
            official_sources=[OfficialSourceReference(title="Official Portal", url=portal_url)],
            next_recommended_action_hi="कृपया आधिकारिक पोर्टल पर जाकर सीधे वर्तमान अधिसूचना जांचें।",
            next_recommended_action_en="Please visit the official government portal to check the latest notification.",
        )

    @classmethod
    def _fallback_unsupported_scheme(
        cls,
        scheme_id: str,
        scheme_name_hi: str,
        scheme_name_en: str,
        rule_version: int,
    ) -> EligibilityAssessResponse:
        """Fallback for an unknown or unsupported scheme."""
        return EligibilityAssessResponse(
            scheme_id=scheme_id,
            scheme_name_hi=scheme_name_hi or scheme_id,
            scheme_name_en=scheme_name_en or scheme_id,
            rule_version=rule_version,
            evaluated_at=datetime.now(timezone.utc),
            status=AssessmentStatus.NEEDS_MORE_INFO,
            status_label_hi="नियम अनुपलब्ध (Rules Unavailable)",
            status_label_en="Rules Unavailable",
            summary_explanation_hi="इस योजना के लिए स्वचालित नियम वर्तमान चरण में उपलब्ध नहीं हैं।",
            summary_explanation_en="Deterministic rules for this scheme are not implemented in the current phase.",
            conditions_satisfied=[],
            conditions_failed=[],
            missing_information=[],
            applicable_exclusions=[],
            pending_verifications=[],
            benefit_summary=BenefitAssessmentSummary(
                amount_inr=0.0,
                benefit_type="UNKNOWN",
                benefit_metric_label_hi="अनुपलब्ध",
                benefit_metric_label_en="Unavailable",
                benefit_amount_display_hi="अनुपलब्ध",
                benefit_amount_display_en="Unavailable",
                description_hi="अनुपलब्ध",
                description_en="Unavailable",
                caveats_hi="",
                caveats_en="",
            ),
            required_documents=[],
            official_sources=[],
            next_recommended_action_hi="कृपया MyScheme पोर्टल पर योजना विवरण देखें।",
            next_recommended_action_en="Please consult the MyScheme portal for details.",
        )

    # Dispatch dictionary mapping scheme IDs to evaluator functions
    _RULE_EVALUATORS = {
        "pm-kisan": _eval_pm_kisan,
        "pm-jay": _eval_pm_jay,
        "kcc": _eval_kcc,
        "pmay-g": _eval_pmay_g,
        "pm-ujjwala": _eval_pm_ujjwala,
        "pmfby": _eval_pmfby,
        "nsap-oap": _eval_nsap_oap,
        "ssy": _eval_ssy,
    }
