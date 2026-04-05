"""Database migration helpers for v1.1 schema changes."""
import logging
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

logger = logging.getLogger(__name__)


async def migrate_v11(conn: AsyncConnection) -> None:
    """Add v1.1 columns to existing tables if they don't exist."""
    # Check and add finance_records columns
    result = await conn.execute(text("PRAGMA table_info(finance_records)"))
    existing_cols = {row[1] for row in result.fetchall()}

    new_cols = [
        ("funding_source", "VARCHAR(30)"),
        ("business_note", "TEXT"),
        ("related_record_id", "INTEGER"),
        ("related_note", "VARCHAR(200)"),
    ]
    for col_name, col_type in new_cols:
        if col_name not in existing_cols:
            await conn.execute(
                text(f"ALTER TABLE finance_records ADD COLUMN {col_name} {col_type}")
            )
            logger.info("Added column %s to finance_records", col_name)

    # Set default funding_source for existing expense records
    await conn.execute(
        text(
            "UPDATE finance_records SET funding_source = 'company_account' "
            "WHERE funding_source IS NULL AND type = 'expense'"
        )
    )

    # Ensure reminders table exists
    result = await conn.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='reminders'"))
    if not result.fetchone():
        await conn.execute(text("""
            CREATE TABLE reminders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title VARCHAR(200) NOT NULL,
                reminder_type VARCHAR(30) NOT NULL,
                is_critical BOOLEAN NOT NULL DEFAULT 0,
                reminder_date DATE NOT NULL,
                status VARCHAR(20) NOT NULL DEFAULT 'pending',
                entity_type VARCHAR(30),
                entity_id INTEGER,
                note TEXT,
                completed_at DATETIME,
                source VARCHAR(20) NOT NULL DEFAULT 'manual',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                is_deleted BOOLEAN NOT NULL DEFAULT 0
            )
        """))
        logger.info("Created reminders table")

    # Ensure reminder_settings table exists
    result = await conn.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='reminder_settings'"))
    if not result.fetchone():
        await conn.execute(text("""
            CREATE TABLE reminder_settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                reminder_type VARCHAR(30) NOT NULL,
                config TEXT NOT NULL,
                is_active BOOLEAN NOT NULL DEFAULT 1,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                is_deleted BOOLEAN NOT NULL DEFAULT 0
            )
        """))
        logger.info("Created reminder_settings table")

    # Ensure file_indexes table exists
    result = await conn.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='file_indexes'"))
    if not result.fetchone():
        await conn.execute(text("""
            CREATE TABLE file_indexes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_name VARCHAR(200) NOT NULL,
                file_type VARCHAR(30) NOT NULL,
                version VARCHAR(50),
                is_current BOOLEAN NOT NULL DEFAULT 1,
                issue_date DATE,
                expiry_date DATE,
                storage_location VARCHAR(500),
                entity_type VARCHAR(30),
                entity_id INTEGER,
                issuing_authority VARCHAR(200),
                note TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                is_deleted BOOLEAN NOT NULL DEFAULT 0
            )
        """))
        logger.info("Created file_indexes table")

    await conn.commit()
    logger.info("v1.1 migration complete")
