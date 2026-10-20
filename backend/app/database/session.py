"""Database session management with Async SQLAlchemy and SQLite."""
from collections.abc import AsyncGenerator
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings
from app.database.base import Base

# Engine configuration
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    future=True,
)

# Async session factory
async_session_maker = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def init_db() -> None:
    """Initialize database tables and ensure required columns exist."""
    # Import all models so Base has metadata registered
    import app.models  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

        def _run_migrations(connection):
            cursor = connection.connection.cursor()
            # Ensure schemes table has new Phase 2 columns
            cursor.execute("PRAGMA table_info(schemes)")
            cols_s = [row[1] for row in cursor.fetchall()]
            schemes_migrations = {
                "jurisdiction": "ALTER TABLE schemes ADD COLUMN jurisdiction VARCHAR(50) DEFAULT 'CENTRAL_SECTOR'",
                "category": "ALTER TABLE schemes ADD COLUMN category VARCHAR(50) DEFAULT 'GENERAL'",
                "target_group_hi": "ALTER TABLE schemes ADD COLUMN target_group_hi VARCHAR(200) DEFAULT ''",
                "target_group_en": "ALTER TABLE schemes ADD COLUMN target_group_en VARCHAR(200) DEFAULT ''",
                "application_process_hi": "ALTER TABLE schemes ADD COLUMN application_process_hi TEXT DEFAULT ''",
                "application_process_en": "ALTER TABLE schemes ADD COLUMN application_process_en TEXT DEFAULT ''",
                "documents_required_json": "ALTER TABLE schemes ADD COLUMN documents_required_json JSON DEFAULT '[]'",
                "caveats_hi": "ALTER TABLE schemes ADD COLUMN caveats_hi TEXT DEFAULT ''",
                "caveats_en": "ALTER TABLE schemes ADD COLUMN caveats_en TEXT DEFAULT ''",
                "benefit_type": "ALTER TABLE schemes ADD COLUMN benefit_type VARCHAR(50) DEFAULT 'DIRECT_CASH_TRANSFER'",
                "benefit_metric_label_hi": "ALTER TABLE schemes ADD COLUMN benefit_metric_label_hi VARCHAR(100) DEFAULT 'अधिकतम वार्षिक लाभ'",
                "benefit_metric_label_en": "ALTER TABLE schemes ADD COLUMN benefit_metric_label_en VARCHAR(100) DEFAULT 'Max Annual Benefit'",
                "benefit_amount_display_hi": "ALTER TABLE schemes ADD COLUMN benefit_amount_display_hi VARCHAR(100) DEFAULT '₹6,000'",
                "benefit_amount_display_en": "ALTER TABLE schemes ADD COLUMN benefit_amount_display_en VARCHAR(100) DEFAULT '₹6,000'",
            }
            for col, stmt in schemes_migrations.items():
                if cols_s and col not in cols_s:
                    cursor.execute(stmt)

            # Ensure scheme_rules table has new columns
            cursor.execute("PRAGMA table_info(scheme_rules)")
            cols_sr = [row[1] for row in cursor.fetchall()]
            sr_migrations = {
                "rule_code": "ALTER TABLE scheme_rules ADD COLUMN rule_code VARCHAR(50) DEFAULT 'RULE_DEFAULT'",
                "description_hi": "ALTER TABLE scheme_rules ADD COLUMN description_hi TEXT DEFAULT ''",
                "description_en": "ALTER TABLE scheme_rules ADD COLUMN description_en TEXT DEFAULT ''",
                "source_citation": "ALTER TABLE scheme_rules ADD COLUMN source_citation VARCHAR(255) DEFAULT ''",
            }
            for col, stmt in sr_migrations.items():
                if cols_sr and col not in cols_sr:
                    cursor.execute(stmt)

            # Ensure citizens table has session_id
            cursor.execute("PRAGMA table_info(citizens)")
            cols_c = [row[1] for row in cursor.fetchall()]
            if cols_c and "session_id" not in cols_c:
                cursor.execute(
                    "ALTER TABLE citizens ADD COLUMN session_id VARCHAR(64)"
                )

            # Ensure citizen_profiles table has new fields
            cursor.execute("PRAGMA table_info(citizen_profiles)")
            cols_cp = [row[1] for row in cursor.fetchall()]
            cp_migrations = {
                "gender": "ALTER TABLE citizen_profiles ADD COLUMN gender VARCHAR(20)",
                "is_income_tax_payer": "ALTER TABLE citizen_profiles ADD COLUMN is_income_tax_payer BOOLEAN",
                "has_pucca_house": "ALTER TABLE citizen_profiles ADD COLUMN has_pucca_house BOOLEAN",
                "owns_agricultural_land": "ALTER TABLE citizen_profiles ADD COLUMN owns_agricultural_land BOOLEAN",
                "has_girl_child_under_10": "ALTER TABLE citizen_profiles ADD COLUMN has_girl_child_under_10 BOOLEAN",
                "has_existing_lpg": "ALTER TABLE citizen_profiles ADD COLUMN has_existing_lpg BOOLEAN",
                "enrolled_in_crop_insurance": "ALTER TABLE citizen_profiles ADD COLUMN enrolled_in_crop_insurance BOOLEAN",
                "residence_type": "ALTER TABLE citizen_profiles ADD COLUMN residence_type VARCHAR(20)",
                "bis_verified": "ALTER TABLE citizen_profiles ADD COLUMN bis_verified BOOLEAN",
                "awaas_plus_verified": "ALTER TABLE citizen_profiles ADD COLUMN awaas_plus_verified BOOLEAN",
            }
            for col, stmt in cp_migrations.items():
                if cols_cp and col not in cols_cp:
                    cursor.execute(stmt)

            # Ensure document_records table has Phase 4 columns
            cursor.execute("PRAGMA table_info(document_records)")
            cols_dr = [row[1] for row in cursor.fetchall()]
            dr_migrations = {
                "file_name": "ALTER TABLE document_records ADD COLUMN file_name VARCHAR(255)",
                "mime_type": "ALTER TABLE document_records ADD COLUMN mime_type VARCHAR(100)",
                "file_size_bytes": "ALTER TABLE document_records ADD COLUMN file_size_bytes INTEGER",
                "page_count": "ALTER TABLE document_records ADD COLUMN page_count INTEGER DEFAULT 1",
                "ocr_provider": "ALTER TABLE document_records ADD COLUMN ocr_provider VARCHAR(50) DEFAULT 'mock'",
                "is_mock": "ALTER TABLE document_records ADD COLUMN is_mock BOOLEAN DEFAULT 1",
                "ocr_status": "ALTER TABLE document_records ADD COLUMN ocr_status VARCHAR(50) DEFAULT 'COMPLETED'",
                "review_status": "ALTER TABLE document_records ADD COLUMN review_status VARCHAR(50) DEFAULT 'UNREVIEWED'",
                "page_extractions": "ALTER TABLE document_records ADD COLUMN page_extractions JSON DEFAULT '[]'",
                "user_corrections": "ALTER TABLE document_records ADD COLUMN user_corrections JSON DEFAULT '{}'",
                "error_message": "ALTER TABLE document_records ADD COLUMN error_message VARCHAR(500)",
            }
            for col, stmt in dr_migrations.items():
                if cols_dr and col not in cols_dr:
                    cursor.execute(stmt)

            # Ensure application_drafts table has Phase 4 columns
            cursor.execute("PRAGMA table_info(application_drafts)")
            cols_ad = [row[1] for row in cursor.fetchall()]
            ad_migrations = {
                "checklist_status": "ALTER TABLE application_drafts ADD COLUMN checklist_status JSON DEFAULT '{}'",
                "cross_document_checks": "ALTER TABLE application_drafts ADD COLUMN cross_document_checks JSON DEFAULT '[]'",
                "package_summary": "ALTER TABLE application_drafts ADD COLUMN package_summary JSON DEFAULT '{}'",
                "pdf_export_path": "ALTER TABLE application_drafts ADD COLUMN pdf_export_path VARCHAR(500)",
                "disclaimer_ack": "ALTER TABLE application_drafts ADD COLUMN disclaimer_ack BOOLEAN DEFAULT 1",
            }
            for col, stmt in ad_migrations.items():
                if cols_ad and col not in cols_ad:
                    cursor.execute(stmt)

        await conn.run_sync(_run_migrations)



async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for obtaining an asynchronous database session."""
    async with async_session_maker() as session:
        try:
            yield session
        finally:
            await session.close()
