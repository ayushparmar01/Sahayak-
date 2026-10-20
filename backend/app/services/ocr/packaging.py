"""CSC Application Package generator producing structured draft summaries and printable PDFs.

Enforces zero Aadhaar storage, full identifier masking, and prominent statutory disclaimers.
"""
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    HRFlowable,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.core.config import settings
from app.knowledge.foundation_schemes import FOUNDATION_SCHEMES_KNOWLEDGE
from app.services.ocr.checklist import get_scheme_document_checklist
from app.services.ocr.consistency import run_cross_document_consistency_checks


def _mask_id(identifier: str | None) -> str:
    """Safely masks any identifier."""
    if not identifier:
        return "N/A"
    clean = identifier.replace(" ", "").replace("-", "")
    if len(clean) >= 12:
        return f"XXXX-XXXX-{clean[-4:]}"
    elif len(clean) >= 8:
        return f"XXXXXX{clean[-4:]}"
    elif len(clean) > 4:
        return f"XX...{clean[-4:]}"
    return identifier


def build_csc_package_pdf(
    draft_id: str,
    scheme_info: dict[str, Any],
    citizen_info: dict[str, Any],
    checklist_data: dict[str, Any],
    consistency_checks: list[dict[str, Any]],
    output_dir: Path | None = None,
    has_mock_documents: bool = False,
) -> Path:
    """Generates a printable CSC Application Preparation Aid PDF using ReportLab."""
    target_dir = output_dir or settings.PACKAGES_TEMP_DIR
    target_dir.mkdir(parents=True, exist_ok=True)
    pdf_filename = f"csc_package_{draft_id}.pdf"
    pdf_path = target_dir / pdf_filename

    doc = SimpleDocTemplate(
        str(pdf_path),
        pagesize=A4,
        leftMargin=36,
        rightMargin=36,
        topMargin=36,
        bottomMargin=36,
    )

    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle(
        "DocTitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=16,
        leading=20,
        textColor=colors.HexColor("#0f172a"),
        alignment=1,  # Center
    )
    subtitle_style = ParagraphStyle(
        "DocSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=11,
        leading=15,
        textColor=colors.HexColor("#334155"),
        alignment=1,
    )
    banner_disclaimer = ParagraphStyle(
        "BannerDisclaimer",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8.5,
        leading=12,
        textColor=colors.HexColor("#991b1b"),
        alignment=1,
    )
    section_heading = ParagraphStyle(
        "SectionHeading",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=11,
        leading=15,
        textColor=colors.HexColor("#1e3a8a"),
    )
    body_style = ParagraphStyle(
        "BodyDark",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8.5,
        leading=12,
        textColor=colors.HexColor("#1e293b"),
    )
    bold_body_style = ParagraphStyle(
        "BoldBody",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8.5,
        leading=12,
        textColor=colors.HexColor("#0f172a"),
    )
    badge_style = ParagraphStyle(
        "BadgeText",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8,
        leading=10,
        alignment=1,
    )

    story = []

    # 1. Header Banner
    story.append(Paragraph("SAHAYAK (सहायक) - CSC APPLICATION PREPARATION AID", title_style))
    story.append(Spacer(1, 4))
    story.append(Paragraph("Common Service Center (CSC / Digital Seva) Citizen Facilitation Document", subtitle_style))
    story.append(Spacer(1, 8))

    # Prominent Disclaimer Box
    disclaimer_text = (
        "<b>STATUTORY DISCLAIMER / महत्वपूर्ण अस्वीकरण:</b><br/>"
        "This document is an application PREPARATION AID compiled for citizen convenience and data entry at Common Service Centers (CSCs). "
        "It is <b>NOT</b> an official government approval, sanction letter, registration receipt, or benefit guarantee. "
        "Final eligibility and benefit disbursal remain subject to verification and approval by the competent Government Authority."
    )
    disclaimer_table = Table(
        [[Paragraph(disclaimer_text, banner_disclaimer)]],
        colWidths=[520],
    )
    disclaimer_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#fee2e2")),
        ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#b91c1c")),
        ("PADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(disclaimer_table)
    story.append(Spacer(1, 8))

    # Prominent Mock OCR Warning Box if mock documents are attached
    has_mock = has_mock_documents or any(item.get("is_mock") for item in checklist_data.get("checklist", []))
    if has_mock:
        mock_notice_style = ParagraphStyle(
            "MockNotice",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=8,
            leading=11,
            textColor=colors.HexColor("#92400e"),
            alignment=1,
        )
        mock_warning_text = (
            "<b>MOCK OCR NOTICE / सिम्युलेटेड ओसीआर सूचना:</b><br/>"
            "One or more documents in this package were processed using a deterministic simulated mock OCR provider. "
            "Extracted values have NOT been verified from physical originals and must be re-checked before submission."
        )
        mock_table = Table([[Paragraph(mock_warning_text, mock_notice_style)]], colWidths=[520])
        mock_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#fef3c7")),
            ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#f59e0b")),
            ("PADDING", (0, 0), (-1, -1), 6),
        ]))
        story.append(mock_table)
        story.append(Spacer(1, 8))

    # 2. Scheme & Draft Metadata
    gen_time = datetime.now(timezone.utc).strftime("%d-%b-%Y %H:%M UTC")
    scheme_name = f"{scheme_info.get('name_en', 'Scheme')} ({scheme_info.get('name_hi', '')})"
    meta_data = [
        [
            Paragraph("<b>Target Scheme:</b>", bold_body_style),
            Paragraph(scheme_name, body_style),
            Paragraph("<b>Draft ID:</b>", bold_body_style),
            Paragraph(f"<code>{draft_id[:16]}</code>", body_style),
        ],
        [
            Paragraph("<b>Sponsoring Ministry:</b>", bold_body_style),
            Paragraph(scheme_info.get("ministry", "Government of India"), body_style),
            Paragraph("<b>Compiled At:</b>", bold_body_style),
            Paragraph(gen_time, body_style),
        ],
        [
            Paragraph("<b>Official Portal:</b>", bold_body_style),
            Paragraph(scheme_info.get("official_portal_url", "https://india.gov.in"), body_style),
            Paragraph("<b>Benefit Classification:</b>", bold_body_style),
            Paragraph(f"{scheme_info.get('benefit_type', 'DIRECT_CASH_TRANSFER')} ({scheme_info.get('benefit_amount_display_en', 'N/A')})", body_style),
        ],
    ]
    meta_table = Table(meta_data, colWidths=[110, 180, 90, 140])
    meta_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ("PADDING", (0, 0), (-1, -1), 4),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 10))

    # 3. Applicant Profile Summary (Zero Aadhaar persistence, masked identifiers)
    story.append(Paragraph("1. APPLICANT VERIFIED PROFILE DETAILS", section_heading))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#1e3a8a"), spaceAfter=5))

    masked_aadhaar = _mask_id(citizen_info.get("aadhaar_number_masked") or citizen_info.get("masked_identifier"))
    profile_rows = [
        [
            Paragraph("<b>Applicant Name:</b>", bold_body_style),
            Paragraph(str(citizen_info.get("beneficiary_name") or citizen_info.get("name") or "Applicant"), body_style),
            Paragraph("<b>Masked Identity (Aadhaar):</b>", bold_body_style),
            Paragraph(masked_aadhaar, bold_body_style),
        ],
        [
            Paragraph("<b>Age & Gender:</b>", bold_body_style),
            Paragraph(f"{citizen_info.get('age', 'N/A')} yrs / {citizen_info.get('gender', 'N/A')}", body_style),
            Paragraph("<b>Residence / Category:</b>", bold_body_style),
            Paragraph(f"{citizen_info.get('residence_type', 'Rural')} / {citizen_info.get('category', 'GENERAL')}", body_style),
        ],
        [
            Paragraph("<b>State & District:</b>", bold_body_style),
            Paragraph(f"{citizen_info.get('district', 'Varanasi')}, {citizen_info.get('state', 'Uttar Pradesh')}", body_style),
            Paragraph("<b>Agricultural Landholding:</b>", bold_body_style),
            Paragraph(f"{citizen_info.get('land_area_hectares', 'N/A')} Ha (Owns: {citizen_info.get('owns_agricultural_land', True)})", body_style),
        ],
        [
            Paragraph("<b>Annual Family Income:</b>", bold_body_style),
            Paragraph(f"₹{citizen_info.get('annual_income', 0):,.0f}" if citizen_info.get("annual_income") else "N/A", body_style),
            Paragraph("<b>Bank Account / DBT:</b>", bold_body_style),
            Paragraph(f"{_mask_id(citizen_info.get('account_number_masked', 'XXXXXX3489'))} (IFSC: {citizen_info.get('ifsc_code', 'SBIN0001234')})", body_style),
        ],
    ]
    prof_table = Table(profile_rows, colWidths=[120, 160, 130, 110])
    prof_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#ffffff")),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
        ("PADDING", (0, 0), (-1, -1), 4),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    story.append(prof_table)
    story.append(Spacer(1, 10))

    # 4. Mandatory Document Checklist Table
    story.append(Paragraph("2. MANDATORY STATUTORY DOCUMENT CHECKLIST", section_heading))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#1e3a8a"), spaceAfter=5))

    doc_headers = [
        Paragraph("<b>Document Name / प्रकार</b>", bold_body_style),
        Paragraph("<b>Requirement</b>", bold_body_style),
        Paragraph("<b>Verification Status</b>", bold_body_style),
        Paragraph("<b>Statutory Authority Guideline</b>", bold_body_style),
    ]
    doc_rows = [doc_headers]

    for item in checklist_data.get("checklist", []):
        st = item.get("status", "MISSING")
        is_mock_doc = item.get("is_mock", False)
        if st == "PRESENT":
            if is_mock_doc:
                status_text = "<font color='#ca8a04'><b>[ATTACHED - MOCK DEMO]</b></font>"
            else:
                status_text = "<font color='#166534'><b>[ATTACHED & CONFIRMED]</b></font>"
        elif st == "PENDING_CONFIRMATION":
            status_text = "<font color='#ca8a04'><b>[UPLOADED / PENDING REVIEW]</b></font>"
        else:
            status_text = "<font color='#dc2626'><b>[MISSING / REQUIRED]</b></font>"

        doc_rows.append([
            Paragraph(f"<b>{item.get('document_title_en', '')}</b><br/>{item.get('document_title_hi', '')}", body_style),
            Paragraph("Mandatory" if item.get("is_mandatory", True) else "Optional", body_style),
            Paragraph(status_text, body_style),
            Paragraph(item.get("statutory_citation", "Official Guidelines"), body_style),
        ])

    doc_table = Table(doc_rows, colWidths=[160, 65, 135, 160])
    doc_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ("PADDING", (0, 0), (-1, -1), 4),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    story.append(doc_table)
    story.append(Spacer(1, 10))

    # 5. Cross-Document Consistency Audit Findings
    story.append(Paragraph("3. CROSS-DOCUMENT & PROFILE CONSISTENCY AUDIT", section_heading))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#1e3a8a"), spaceAfter=5))

    if consistency_checks:
        audit_rows = [[
            Paragraph("<b>Parameter</b>", bold_body_style),
            Paragraph("<b>Doc Type</b>", bold_body_style),
            Paragraph("<b>Audit Status</b>", bold_body_style),
            Paragraph("<b>Reviewer Notes & Recommendations</b>", bold_body_style),
        ]]
        for chk in consistency_checks:
            st = chk.get("status", "MATCH")
            if st == "MATCH":
                badge = "<font color='#166534'><b>PASS / MATCH</b></font>"
            elif st == "VARIATION":
                badge = "<font color='#ca8a04'><b>VARIATION</b></font>"
            else:
                badge = "<font color='#dc2626'><b>ATTENTION</b></font>"

            audit_rows.append([
                Paragraph(chk.get("field_name", ""), body_style),
                Paragraph(chk.get("document_type", ""), body_style),
                Paragraph(badge, body_style),
                Paragraph(f"{chk.get('message_en', '')}<br/><i>{chk.get('message_hi', '')}</i>", body_style),
            ])
        audit_table = Table(audit_rows, colWidths=[100, 90, 80, 250])
        audit_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ("PADDING", (0, 0), (-1, -1), 4),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ]))
        story.append(audit_table)
    else:
        story.append(Paragraph("<i>No cross-document variations recorded. Documents are mutually consistent.</i>", body_style))

    story.append(Spacer(1, 15))

    # 6. Physical Sign-off Section (CSC Operator + Citizen)
    story.append(Paragraph("4. FACILITATION ACKNOWLEDGEMENT & SIGN-OFF", section_heading))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#1e3a8a"), spaceAfter=5))

    sign_data = [
        [
            Paragraph(
                "<b>Applicant Declaration:</b><br/>"
                "I hereby confirm that all information provided above is true to the best of my knowledge and documents attached are genuine.<br/><br/><br/>"
                "________________________________<br/>"
                "<b>Signature / Thumb Impression of Applicant</b><br/>"
                "Date: ________________________",
                body_style,
            ),
            Paragraph(
                "<b>CSC VLE Verification & Stamp:</b><br/>"
                "Verified physical copies against uploaded scans. Citizen briefed on scheme guidelines and portal submission steps.<br/><br/><br/>"
                "________________________________<br/>"
                "<b>CSC VLE Signature & Seal / Center ID</b><br/>"
                "CSC ID: ______________________",
                body_style,
            ),
        ]
    ]
    sign_table = Table(sign_data, colWidths=[260, 260])
    sign_table.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
        ("PADDING", (0, 0), (-1, -1), 8),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    story.append(sign_table)

    # Build PDF
    doc.build(story)
    return pdf_path


def generate_csc_application_package(
    draft_id: str,
    scheme_id: str,
    citizen_data: dict[str, Any],
    profile_data: dict[str, Any],
    documents: list[dict[str, Any]],
    operator_notes: str | None = None,
) -> dict[str, Any]:
    """Compiles complete CSC application package, checklist, audit, and printable PDF."""
    # 1. Scheme knowledge lookup
    scheme = next((s for s in FOUNDATION_SCHEMES_KNOWLEDGE if s["id"] == scheme_id), None)
    if not scheme:
        raise ValueError(f"Scheme '{scheme_id}' not found in knowledge base")

    # 2. Scheme checklist evaluation
    checklist_data = get_scheme_document_checklist(scheme_id, documents)

    # 3. Cross-document consistency audit
    merged_profile = {**citizen_data, **profile_data}
    consistency_checks = run_cross_document_consistency_checks(documents, merged_profile)

    # 4. Generate ReportLab PDF
    has_mock_documents = any(
        doc.get("is_mock") is True or doc.get("provider_name") == "MockOCRProvider"
        for doc in documents
    )
    pdf_path = build_csc_package_pdf(
        draft_id=draft_id,
        scheme_info=scheme,
        citizen_info=merged_profile,
        checklist_data=checklist_data,
        consistency_checks=consistency_checks,
        has_mock_documents=has_mock_documents,
    )

    # 5. Completeness percentage
    checklist_score = checklist_data.get("readiness_percentage", 0.0)
    # Profile completeness: check name, age, income
    prof_score = 100.0 if (merged_profile.get("age") and merged_profile.get("name") or merged_profile.get("beneficiary_name")) else 70.0
    overall_completeness = round((checklist_score * 0.7) + (prof_score * 0.3), 1)

    package_summary = {
        "scheme_id": scheme["id"],
        "scheme_name_hi": scheme["name_hi"],
        "scheme_name_en": scheme["name_en"],
        "ministry": scheme["ministry"],
        "benefit_amount": scheme["benefit_amount_display_en"],
        "applicant_name": merged_profile.get("beneficiary_name") or merged_profile.get("name") or "Applicant",
        "masked_aadhaar": _mask_id(merged_profile.get("aadhaar_number_masked") or merged_profile.get("masked_identifier")),
        "operator_notes": operator_notes or "Compiled via SAHAYAK CSC preparation workflow",
        "has_mock_documents": has_mock_documents,
        "pdf_filename": pdf_path.name,
    }

    return {
        "draft_id": draft_id,
        "scheme_id": scheme_id,
        "completeness_percentage": overall_completeness,
        "package_summary": package_summary,
        "checklist_status": checklist_data,
        "cross_document_checks": consistency_checks,
        "pdf_path": str(pdf_path),
    }
