from sqlalchemy.orm import Session
from typing import Dict
from sqlalchemy import select
from core.database.base import ProjectJsonConfig
from sqlalchemy.exc import SQLAlchemyError, IntegrityError, DataError


def sync_special_json_configs(session: Session, json_data: Dict) -> str:
    """Синхронизация JSON конфигураций с обработкой ошибок"""
    changes = []
    for config_type, config_value in json_data.items():
        try:
            # Check if config exists
            stmt = select(ProjectJsonConfig).where(ProjectJsonConfig.config_type == config_type)
            existing = session.execute(stmt).scalar_one_or_none()

            if existing:
                if existing.config_data != config_value:
                    changes.append(f"  📦 JSON config '{config_type}' updated")
                    existing.config_data = config_value
            else:
                new_config = ProjectJsonConfig(
                    config_type=config_type,
                    config_data=config_value
                )
                session.add(new_config)
                changes.append(f"  ➕ New JSON config '{config_type}' added")
        except (DataError, IntegrityError) as e:
            session.rollback()
            changes.append(f"  ❌ Ошибка БД при обработке JSON конфига '{config_type}': {str(e)}")
        except Exception as e:
            changes.append(f"  ❓ Неизвестная ошибка при обработке JSON конфига '{config_type}': {str(e)}")

    try:
        session.commit()
        return f"📦 JSON configs sync complete:\n" + ("\n".join(changes) if changes else "  No changes detected")
    except (IntegrityError, DataError) as e:
        session.rollback()
        return f"📦 JSON configs sync failed: Database error - {str(e)}"
    except SQLAlchemyError as e:
        session.rollback()
        return f"📦 JSON configs sync failed: Database connection error - {str(e)}"
    except Exception as e:
        session.rollback()
        return f"📦 JSON configs sync failed: Unexpected error - {str(e)}"