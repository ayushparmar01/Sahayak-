"""Scheme catalogue and detailed knowledge base endpoints."""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.database.session import get_db
from app.models.scheme import Scheme, SchemeRule
from app.schemas.scheme import SchemeListResponse, SchemeSummaryDTO, SchemeDetailDTO, SchemeRuleDTO
from app.knowledge.foundation_schemes import FOUNDATION_SCHEMES_KNOWLEDGE

router = APIRouter(prefix="/schemes", tags=["Schemes"])


async def ensure_schemes_seeded(db: AsyncSession) -> None:
    """Idempotently seeds or updates foundation schemes and their rules."""
    for s_data in FOUNDATION_SCHEMES_KNOWLEDGE:
        rules_data = s_data.get("rules", [])
        scheme_fields = {k: v for k, v in s_data.items() if k != "rules"}

        existing_scheme = await db.get(Scheme, s_data["id"])
        if not existing_scheme:
            scheme_obj = Scheme(**scheme_fields)
            db.add(scheme_obj)
            await db.flush()
            for r in rules_data:
                db.add(
                    SchemeRule(
                        scheme_id=s_data["id"],
                        rule_code=r.get("rule_code", "RULE_DEFAULT"),
                        rule_type=r.get("rule_type", "MANDATORY_CRITERION"),
                        description_hi=r.get("description_hi", ""),
                        description_en=r.get("description_en", ""),
                        source_citation=r.get("source_citation", ""),
                        failure_message_hi=r.get("failure_message_hi", ""),
                        failure_message_en=r.get("failure_message_en", ""),
                        rule_criteria_json={},
                    )
                )
        else:
            for k, v in scheme_fields.items():
                setattr(existing_scheme, k, v)
            
            # Check if rules exist for this scheme
            res = await db.execute(select(SchemeRule).where(SchemeRule.scheme_id == s_data["id"]))
            existing_rules = list(res.scalars().all())
            if not existing_rules and rules_data:
                for r in rules_data:
                    db.add(
                        SchemeRule(
                            scheme_id=s_data["id"],
                            rule_code=r.get("rule_code", "RULE_DEFAULT"),
                            rule_type=r.get("rule_type", "MANDATORY_CRITERION"),
                            description_hi=r.get("description_hi", ""),
                            description_en=r.get("description_en", ""),
                            source_citation=r.get("source_citation", ""),
                            failure_message_hi=r.get("failure_message_hi", ""),
                            failure_message_en=r.get("failure_message_en", ""),
                            rule_criteria_json={},
                        )
                    )

    await db.commit()


@router.get("", response_model=SchemeListResponse)
async def list_schemes(
    category: str | None = Query(default=None, description="Filter by scheme category"),
    jurisdiction: str | None = Query(default=None, description="Filter by CENTRAL_SECTOR or CENTRALLY_SPONSORED"),
    verification_status: str | None = Query(default=None, description="Filter by VERIFIED, REVISION_PENDING, etc."),
    is_active: bool | None = Query(default=None, description="Filter by active status"),
    db: AsyncSession = Depends(get_db),
) -> SchemeListResponse:
    """Retrieve verified government schemes catalogue with safe filtering."""
    await ensure_schemes_seeded(db)

    query = select(Scheme)
    if category:
        query = query.where(Scheme.category == category)
    if jurisdiction:
        query = query.where(Scheme.jurisdiction == jurisdiction)
    if verification_status:
        query = query.where(Scheme.verification_status == verification_status)
    if is_active is not None:
        query = query.where(Scheme.is_active == is_active)

    result = await db.execute(query)
    schemes = list(result.scalars().all())

    summary_list = [
        SchemeSummaryDTO(
            id=s.id,
            code=s.code,
            name_hi=s.name_hi,
            name_en=s.name_en,
            ministry=s.ministry,
            category=s.category,
            target_group_hi=s.target_group_hi,
            target_group_en=s.target_group_en,
            official_portal_url=s.official_portal_url,
            benefit_summary_hi=s.benefit_summary_hi,
            benefit_summary_en=s.benefit_summary_en,
            max_annual_benefit_inr=s.max_annual_benefit_inr,
            benefit_type=getattr(s, "benefit_type", "DIRECT_CASH_TRANSFER"),
            benefit_metric_label_hi=getattr(s, "benefit_metric_label_hi", "अधिकतम वार्षिक लाभ"),
            benefit_metric_label_en=getattr(s, "benefit_metric_label_en", "Max Annual Benefit"),
            benefit_amount_display_hi=getattr(s, "benefit_amount_display_hi", "₹6,000"),
            benefit_amount_display_en=getattr(s, "benefit_amount_display_en", "₹6,000"),
            jurisdiction=s.jurisdiction,
            last_verified_date=s.last_verified_date,
            verification_source=s.verification_source,
            verification_status=s.verification_status,
            is_active=s.is_active,
            rule_version=s.rule_version,
        )
        for s in schemes
    ]

    return SchemeListResponse(total=len(summary_list), schemes=summary_list)


@router.get("/{scheme_id}", response_model=SchemeDetailDTO)
async def get_scheme_detail(
    scheme_id: str,
    db: AsyncSession = Depends(get_db),
) -> SchemeDetailDTO:
    """Retrieve complete, verified scheme details, structured criteria, exclusions, and primary sources."""
    await ensure_schemes_seeded(db)

    query = select(Scheme).where(Scheme.id == scheme_id).options(selectinload(Scheme.rules))
    result = await db.execute(query)
    scheme = result.scalar_one_or_none()

    if not scheme:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"योजना आईडी '{scheme_id}' नहीं मिली (Scheme not found)",
        )

    rule_dtos = [
        SchemeRuleDTO(
            id=r.id,
            rule_code=r.rule_code,
            rule_type=r.rule_type,
            description_hi=r.description_hi,
            description_en=r.description_en,
            source_citation=r.source_citation,
            failure_message_hi=r.failure_message_hi,
            failure_message_en=r.failure_message_en,
        )
        for r in scheme.rules
    ]

    return SchemeDetailDTO(
        id=scheme.id,
        code=scheme.code,
        name_hi=scheme.name_hi,
        name_en=scheme.name_en,
        ministry=scheme.ministry,
        category=scheme.category,
        target_group_hi=scheme.target_group_hi,
        target_group_en=scheme.target_group_en,
        official_portal_url=scheme.official_portal_url,
        benefit_summary_hi=scheme.benefit_summary_hi,
        benefit_summary_en=scheme.benefit_summary_en,
        max_annual_benefit_inr=scheme.max_annual_benefit_inr,
        benefit_type=getattr(scheme, "benefit_type", "DIRECT_CASH_TRANSFER"),
        benefit_metric_label_hi=getattr(scheme, "benefit_metric_label_hi", "अधिकतम वार्षिक लाभ"),
        benefit_metric_label_en=getattr(scheme, "benefit_metric_label_en", "Max Annual Benefit"),
        benefit_amount_display_hi=getattr(scheme, "benefit_amount_display_hi", "₹6,000"),
        benefit_amount_display_en=getattr(scheme, "benefit_amount_display_en", "₹6,000"),
        jurisdiction=scheme.jurisdiction,
        application_process_hi=scheme.application_process_hi,
        application_process_en=scheme.application_process_en,
        documents_required=scheme.documents_required_json or [],
        caveats_hi=scheme.caveats_hi,
        caveats_en=scheme.caveats_en,
        last_verified_date=scheme.last_verified_date,
        verification_source=scheme.verification_source,
        verification_status=scheme.verification_status,
        is_active=scheme.is_active,
        rule_version=scheme.rule_version,
        rules=rule_dtos,
    )
