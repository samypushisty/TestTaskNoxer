from sqlalchemy.orm import Session
from typing import Dict
from sqlalchemy import select
from core.database.base import ProjectParameter
from sqlalchemy.exc import SQLAlchemyError, DataError, IntegrityError


def sync_special_parameters(session: Session, params_data: Dict) -> str:
    """Синхронизация специальных параметров с обработкой ошибок"""
    changes = []
    for key, value in params_data.items():
        try:
            if not key.endswith("_value"):
                continue
            param_key = key[:-6]  # Remove "_value" suffix
            description = params_data.get(f"{param_key}_description", "")

            # Check if parameter exists
            stmt = select(ProjectParameter).where(ProjectParameter.description == param_key)
            existing = session.execute(stmt).scalar_one_or_none()

            if existing:
                if existing.value != value:
                    changes.append(f"  🔧 Parameter '{param_key}' updated: '{existing.value}' → '{value}'")
                    existing.value = value
            else:
                new_param = ProjectParameter(
                    description=param_key,
                    value=value
                )
                session.add(new_param)
                changes.append(f"  ➕ New parameter '{param_key}' added with value: '{value}'")
        except KeyError:
            continue  # Skip if key not found
        except (DataError, IntegrityError) as e:
            session.rollback()
            changes.append(f"  ❌ Ошибка БД при обработке параметра '{key}': {str(e)}")
        except Exception as e:
            changes.append(f"  ❓ Неизвестная ошибка при обработке параметра '{key}': {str(e)}")

    try:
        session.commit()
        return f"⚙️ Special parameters sync complete:\n" + ("\n".join(changes) if changes else "  No changes detected")
    except (IntegrityError, DataError) as e:
        session.rollback()
        return f"⚙️ Special parameters sync failed: Database error - {str(e)}"
    except SQLAlchemyError as e:
        session.rollback()
        return f"⚙️ Special parameters sync failed: Database connection error - {str(e)}"
    except Exception as e:
        session.rollback()
        return f"⚙️ Special parameters sync failed: Unexpected error - {str(e)}"