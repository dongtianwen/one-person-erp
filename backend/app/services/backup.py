import os
import sqlite3
import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional

from app.config import settings


CORE_TABLES = [
    "customers", "projects", "contracts", "finance_records",
    "reminders", "file_indexes", "quotations", "customer_assets",
]


def get_backup_dir() -> Path:
    return Path("./backups")


def list_backups() -> list[dict]:
    """List all backup files with metadata."""
    backup_dir = get_backup_dir()
    if not backup_dir.exists():
        return []

    backups = []
    for f in sorted(backup_dir.glob("*.db"), reverse=True):
        stat = f.stat()
        meta_path = f.with_suffix(".meta.json")
        meta = {}
        if meta_path.exists():
            try:
                meta = json.loads(meta_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                pass

        backups.append({
            "filename": f.name,
            "path": str(f),
            "size": stat.st_size,
            "created_at": datetime.fromtimestamp(stat.st_ctime).isoformat(),
            "verification": meta.get("verification"),
        })
    return backups


def verify_backup(backup_path: str) -> dict:
    """
    Verify backup integrity by loading it as a temporary database
    and comparing core table record counts.

    Returns verification result dict.
    """
    if not os.path.exists(backup_path):
        return {"valid": False, "error": "备份文件不存在"}

    current_db_path = settings.DATABASE_URL.split("///")[-1]
    current_counts = {}
    backup_counts = {}

    # Get current database counts
    try:
        with sqlite3.connect(current_db_path) as conn:
            for table in CORE_TABLES:
                try:
                    row = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()
                    current_counts[table] = row[0] if row else 0
                except sqlite3.OperationalError:
                    current_counts[table] = -1  # Table doesn't exist yet
    except Exception as e:
        return {"valid": False, "error": f"无法读取当前数据库: {str(e)}"}

    # Get backup database counts using ATTACH
    try:
        with sqlite3.connect(current_db_path) as conn:
            conn.execute(f"ATTACH DATABASE '{backup_path}' AS backup_db")
            for table in CORE_TABLES:
                try:
                    row = conn.execute(f"SELECT COUNT(*) FROM backup_db.{table}").fetchone()
                    backup_counts[table] = row[0] if row else 0
                except sqlite3.OperationalError:
                    backup_counts[table] = -1
            conn.execute("DETACH DATABASE backup_db")
    except Exception as e:
        return {"valid": False, "error": f"无法读取备份数据库: {str(e)}"}

    # Compare
    comparison = {}
    all_match = True
    for table in CORE_TABLES:
        c = current_counts.get(table, -1)
        b = backup_counts.get(table, -1)
        match = c == b
        if not match:
            all_match = False
        comparison[table] = {"current": c, "backup": b, "match": match}

    result = {
        "valid": all_match,
        "backup_path": backup_path,
        "verified_at": datetime.now().isoformat(),
        "tables": comparison,
    }

    # Save verification metadata
    _save_verification_meta(backup_path, result)

    return result


def _save_verification_meta(backup_path: str, result: dict) -> None:
    """Save verification result alongside the backup file."""
    meta_path = Path(backup_path).with_suffix(".meta.json")
    try:
        meta_path.write_text(
            json.dumps({"verification": result}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except OSError:
        pass  # Non-critical - best effort
