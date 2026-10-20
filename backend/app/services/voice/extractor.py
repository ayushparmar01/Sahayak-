"""Deterministic Indic NLP Extractor for Citizen Profile Attributes and Intent.

Handles natural Hindi (Devanagari) and Hinglish/English phrases, extracting
supported demographic attributes with strict type validation and explicit
negation handling. Never fabricates values.
"""
import re
from typing import Any
from app.services.voice.base import BaseExtractionProvider, ExtractionResult

# Hindi numeral mappings
HINDI_NUM_WORDS: dict[str, float] = {
    "शून्य": 0.0, "एक": 1.0, "दो": 2.0, "ढाई": 2.5, "तीन": 3.0, "साढ़े तीन": 3.5,
    "चार": 4.0, "साढ़े चार": 4.5, "पांच": 5.0, "पाँच": 5.0, "छह": 6.0, "सात": 7.0,
    "आठ": 8.0, "नौ": 9.0, "दस": 10.0, "ग्यारह": 11.0, "बारह": 12.0, "पंद्रह": 15.0,
    "बीस": 20.0, "पच्चीस": 25.0, "तीस": 30.0, "पैंतीस": 35.0, "चालीस": 40.0,
    "पैंतालीस": 45.0, "पचास": 50.0, "पचपन": 55.0, "साठ": 60.0, "पैंसठ": 65.0,
    "सत्तर": 70.0, "पचहत्तर": 75.0, "अस्सी": 80.0,
}


class DeterministicIndicExtractor(BaseExtractionProvider):
    """Deterministic, rule-based extraction for Hindi/English citizen statements."""

    async def extract_intent_and_fields(
        self,
        text: str,
        current_profile: dict[str, Any] | None = None,
        language: str = "hi",
    ) -> ExtractionResult:
        """Extract intent and validated profile fields without LLM hallucinations."""
        t = (text or "").strip()
        t_lower = t.lower()
        extracted: dict[str, Any] = {}

        if not t:
            return ExtractionResult(
                intent="general_query",
                extracted_fields={},
                confidence=0.0,
                is_mock=True,
            )

        # ---------------------------------------------------------------------
        # 1. Intent Detection
        # ---------------------------------------------------------------------
        is_confirmed = False
        is_cancelled = False
        intent = "general_query"

        # Check Don't Know / Uncertainty
        dont_know_patterns = [
            r"^(पता नहीं|मालूम नहीं|याद नहीं|जानकारी नहीं|नहीं पता|नहीं मालूम|don'?t know|not sure|no idea)[\s\.,!|]*$",
            r"(मुझे नहीं पता|मुझे नहीं मालूम|याद नहीं है|पता नहीं है|जानकारी नहीं है)",
        ]
        if any(re.search(p, t_lower) for p in dont_know_patterns):
            intent = "dont_know"

        # Check Confirmation
        confirm_patterns = [
            r"^(हाँ|हां|जी हाँ|जी हां|सही है|पुष्टि करें|ठीक है|कर दो|yes|correct|confirm|save)[\s\.,!|]*$",
            r"(सब सही है|जानकारी सही है|बिल्कुल सही है|यह सही है|पुष्टि करता हूँ|पुष्टि करती हूँ|सही जानकारी है)",
            r"^(हाँ|हां|जी हाँ|yes)[\s,]+(यह|सब|जानकारी|बिल्कुल|सही)",
        ]
        if intent != "dont_know" and any(re.search(p, t_lower) for p in confirm_patterns) and not re.search(r"(नहीं|गलत|नही)", t_lower):
            is_confirmed = True
            intent = "confirm_changes"

        # Check Cancellation
        cancel_patterns = [
            r"^(नहीं|ना|रद्द करें|गलत है|रोकें|no|cancel|stop|wrong)[\s\.,!|]*$",
            r"(जानकारी गलत है|रद्द करो|रद्द करें|कैंसिल|गलत है|सही नहीं है)",
        ]
        if intent != "dont_know" and not is_confirmed and any(re.search(p, t_lower) for p in cancel_patterns):
            is_cancelled = True
            intent = "cancel"

        # Check Greeting
        greeting_patterns = [
            r"^(नमस्ते|नमस्कार|प्रणाम|हेलो|हैलो|सुप्रभात|शुभ संध्या|राम राम|जय श्री राम|hello|hi|hey|good morning|good evening)[\s\.,!|]*$",
            r"^(नमस्ते|नमस्कार|हेलो|hello|hi)\s+(सहायक|sahayak|जी|sir|madam)",
        ]
        if intent == "general_query" and not is_confirmed and not is_cancelled:
            if any(re.search(p, t_lower) for p in greeting_patterns):
                intent = "greeting"

        # Check Out of Scope Queries
        out_of_scope_patterns = [
            r"(मौसम कैसा है|तापमान क्या है|बारिश होगी|weather|cricket|score|joke|चुटकुला|गाना सुनाओ|गाना बजाओ|movie|फिल्म|राजनीति|election)",
        ]
        if intent == "general_query" and not is_confirmed and not is_cancelled:
            if any(re.search(p, t_lower) for p in out_of_scope_patterns):
                intent = "out_of_scope"

        # Check Scheme Assessment Intent
        assess_patterns = [
            r"(पात्रता|योजना|योजनाएं|कौन सी योजना|किस योजना|लाभ|सहायता|स्कीम|eligib|scheme|benefit)",
            r"(चेक करो|जांच करो|बताओ|बताइए|दिखाओ|दिखाइए)",
        ]
        if intent == "general_query" and not is_confirmed and not is_cancelled:
            if any(re.search(p, t_lower) for p in assess_patterns):
                intent = "check_eligibility"

        # ---------------------------------------------------------------------
        # 2. Demographic Attribute Extraction (Bypassed for conversational intents)
        # ---------------------------------------------------------------------
        if intent in ("greeting", "out_of_scope", "dont_know"):
            return ExtractionResult(
                intent=intent,
                extracted_fields={},
                confidence=0.95,
                is_confirmed=is_confirmed,
                is_cancelled=is_cancelled,
                is_mock=True,
            )

        # Age extraction: "उम्र 45 साल", "45 वर्ष", "age 35", "आयु 62 वर्ष"
        age_match = re.search(r"(?:उम्र|आयु|age)\s*(?:है)?\s*(\d{1,3})", t_lower)
        if not age_match:
            age_match = re.search(r"(\d{1,3})\s*(?:साल|वर्ष|years|yr)", t_lower)
        if age_match:
            age_val = int(age_match.group(1))
            if 0 <= age_val <= 120:
                extracted["age"] = age_val
                if intent == "general_query":
                    intent = "update_profile"

        # Land Ownership & Acreage
        # Negation first: "जमीन नहीं है", "भूमिहीन", "खेत नहीं है", "no land"
        if re.search(r"(जमीन\s*नहीं|खेत\s*नहीं|भूमि\s*नहीं|भूमिहीन|landless|no\s*land)", t_lower):
            extracted["owns_agricultural_land"] = False
            extracted["land_acres"] = 0.0
            if intent == "general_query":
                intent = "update_profile"
        else:
            land_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:एकड़|एकड|acre|acres|बीघा|bigha)", t_lower)
            if land_match:
                acres = float(land_match.group(1))
                # Normalize bigha roughly (approx 0.4 acre in West UP / Mathura context if bigha stated)
                if "बीघा" in t_lower or "bigha" in t_lower:
                    acres = round(acres * 0.4, 2)
                extracted["owns_agricultural_land"] = True
                extracted["land_acres"] = acres
                if intent == "general_query":
                    intent = "update_profile"
            elif re.search(r"(जमीन\s*है|खेत\s*है|अपनी\s*भूमि|own\s*land)", t_lower):
                extracted["owns_agricultural_land"] = True
                if intent == "general_query":
                    intent = "update_profile"

        # Pucca House (Housing Deficit)
        # Negation / Kutcha: "पक्का मकान नहीं", "कच्चा मकान", "बेघर", "झोपड़ी", "no pucca house", "kutcha"
        if re.search(r"(पक्का\s*मकान\s*नहीं|कच्चा\s*मकान|झोपड़ी|बेघर|no\s*pucca|kutcha)", t_lower):
            extracted["has_pucca_house"] = False
            if intent == "general_query":
                intent = "update_profile"
        elif re.search(r"(पक्का\s*मकान\s*है|खुद\s*का\s*पक्का|own\s*pucca|pucca\s*house)", t_lower):
            extracted["has_pucca_house"] = True
            if intent == "general_query":
                intent = "update_profile"

        # Residence Type (Rural / Urban)
        if re.search(r"(ग्रामीण|गांव|गाँव|ग्राम\s*पंचायत|देहात|village|rural)", t_lower):
            extracted["residence_type"] = "RURAL"
            if intent == "general_query":
                intent = "update_profile"
        elif re.search(r"(शहरी|शहर|नगर\s*निगम|नगर\s*पालिका|कस्बा|city|urban|town)", t_lower):
            extracted["residence_type"] = "URBAN"
            if intent == "general_query":
                intent = "update_profile"

        # Income Tax Payer
        if re.search(r"(आयकर\s*नहीं|टैक्स\s*नहीं|tax\s*नहीं|गैर-आयकर|non-tax|no\s*tax)", t_lower):
            extracted["is_income_tax_payer"] = False
            if intent == "general_query":
                intent = "update_profile"
        elif re.search(r"(आयकर\s*दाता|टैक्स\s*भरता|टैक्स\s*देता|pay\s*tax|tax\s*payer)", t_lower):
            extracted["is_income_tax_payer"] = True
            if intent == "general_query":
                intent = "update_profile"

        # Annual Income (e.g. "आय 80000", "85 हजार", "1.2 लाख")
        income_match = re.search(r"(?:आय|कमाई|income)\s*(?:लगभग|करीब)?\s*(\d+(?:,\d+)*)\s*(?:रुपये|रु|rs|inr)?", t_lower)
        if income_match:
            inc_val = float(income_match.group(1).replace(",", ""))
            extracted["annual_income"] = inc_val
            if intent == "general_query":
                intent = "update_profile"
        elif re.search(r"(\d+(?:\.\d+)?)\s*(?:लाख|lakh)", t_lower):
            lakh_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:लाख|lakh)", t_lower)
            if lakh_match:
                extracted["annual_income"] = float(lakh_match.group(1)) * 100000.0
                if intent == "general_query":
                    intent = "update_profile"
        elif re.search(r"(\d+)\s*(?:हजार|हज़ार|thousand)", t_lower):
            hazaar_match = re.search(r"(\d+)\s*(?:हजार|हज़ार|thousand)", t_lower)
            if hazaar_match:
                extracted["annual_income"] = float(hazaar_match.group(1)) * 1000.0
                if intent == "general_query":
                    intent = "update_profile"

        # Ration Card Category
        if re.search(r"(अंत्योदय|aay|antyodaya)", t_lower):
            extracted["ration_card_type"] = "Antyodaya"
            if intent == "general_query":
                intent = "update_profile"
        elif re.search(r"(बीपीएल|bpl)", t_lower):
            extracted["ration_card_type"] = "BPL"
            if intent == "general_query":
                intent = "update_profile"
        elif re.search(r"(एपीएल|apl)", t_lower):
            extracted["ration_card_type"] = "APL"
            if intent == "general_query":
                intent = "update_profile"
        elif re.search(r"(राशन\s*कार्ड\s*नहीं|no\s*ration)", t_lower):
            extracted["ration_card_type"] = "None"
            if intent == "general_query":
                intent = "update_profile"

        # Occupation
        if re.search(r"(किसान|खेती|काश्तकार|farmer|agriculture)", t_lower):
            extracted["occupation"] = "farmer"
            if intent == "general_query":
                intent = "update_profile"
        elif re.search(r"(मजदूर|मजदूरी|श्रमिक|laborer|labour|worker)", t_lower):
            extracted["occupation"] = "laborer"
            if intent == "general_query":
                intent = "update_profile"
        elif re.search(r"(कारीगर|शिल्पकार|artisan)", t_lower):
            extracted["occupation"] = "artisan"
            if intent == "general_query":
                intent = "update_profile"
        elif re.search(r"(दुकानदार|व्यापारी|स्वरोजगार|self[- ]employed|business)", t_lower):
            extracted["occupation"] = "self_employed"
            if intent == "general_query":
                intent = "update_profile"
        elif re.search(r"(छात्र|छात्रा|विद्यार्थी|student)", t_lower):
            extracted["occupation"] = "student"
            if intent == "general_query":
                intent = "update_profile"

        # Gender
        if re.search(r"(महिला|औरत|स्त्री|female|woman)", t_lower):
            extracted["gender"] = "female"
            if intent == "general_query":
                intent = "update_profile"
        elif re.search(r"(पुरुष|आदमी|male|man)", t_lower):
            extracted["gender"] = "male"
            if intent == "general_query":
                intent = "update_profile"

        # Girl Child <= 10
        if re.search(r"(बेटी\s*है|बच्ची\s*है|लड़की\s*है|girl\s*child|daughter)", t_lower):
            # Check age if mentioned: "5 साल की बेटी"
            extracted["has_girl_child_under_10"] = True
            if intent == "general_query":
                intent = "update_profile"
        elif re.search(r"(बेटी\s*नहीं|लड़की\s*नहीं|no\s*girl\s*child)", t_lower):
            extracted["has_girl_child_under_10"] = False
            if intent == "general_query":
                intent = "update_profile"

        # Existing LPG Connection (PM Ujjwala)
        if re.search(r"(गैस\s*नहीं|सिलेंडर\s*नहीं|कनेक्शन\s*नहीं|no\s*lpg|no\s*gas)", t_lower):
            extracted["has_existing_lpg"] = False
            if intent == "general_query":
                intent = "update_profile"
        elif re.search(r"(गैस\s*है|सिलेंडर\s*है|कनेक्शन\s*है|have\s*lpg|have\s*gas)", t_lower):
            extracted["has_existing_lpg"] = True
            if intent == "general_query":
                intent = "update_profile"

        # State and District (Default context Mathura, Uttar Pradesh)
        if re.search(r"(उत्तर\s*प्रदेश|यूपी|uttar\s*pradesh|u\.p\.)", t_lower):
            extracted["state"] = "Uttar Pradesh"
        if re.search(r"(मथुरा|mathura)", t_lower):
            extracted["district"] = "Mathura"

        return ExtractionResult(
            intent=intent,
            extracted_fields=extracted,
            confidence=0.95 if extracted or is_confirmed or is_cancelled else 0.70,
            is_confirmed=is_confirmed,
            is_cancelled=is_cancelled,
            is_mock=True,
        )
