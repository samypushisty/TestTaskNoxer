from sqlalchemy.orm import Session
from typing import List, Dict
from core.utils.sync.core.database import Repository
from core.database.base import ProductMark
from sqlalchemy.exc import SQLAlchemyError, IntegrityError, DataError


def sync_product_marks(session: Session, marks_data: List[Dict]) -> str:
    """Синхронизация меток продуктов с обработкой ошибок"""
    repo = Repository[ProductMark](session, ProductMark)
    changes = []

    for mark_data in marks_data:
        try:
            mark_id = mark_data["Mark_ID"]
            existing = repo.get_by_id(mark_id)

            if existing:
                if existing.mark_name != mark_data["Mark_Name"]:
                    old_name = existing.mark_name
                    existing.mark_name = mark_data["Mark_Name"]
                    changes.append(f"  🏷️ Mark #{mark_id} '{old_name}' → '{mark_data['Mark_Name']}'")
            else:
                new_mark = ProductMark(
                    mark_id=mark_id,
                    mark_name=mark_data["Mark_Name"]
                )
                repo.add(new_mark)
                changes.append(f"  ➕ New mark #{mark_id} '{mark_data['Mark_Name']}' added")
        except KeyError as e:
            changes.append(f"  ⚠️ Пропущена метка: отсутствует поле {str(e)}")
        except (DataError, IntegrityError) as e:
            session.rollback()
            changes.append(f"  ❌ Ошибка БД при обработке метки: {str(e)}")
        except Exception as e:
            changes.append(f"  ❓ Неизвестная ошибка при обработке метки: {str(e)}")

    try:
        repo.commit()
        return f"🔖 Product marks sync complete:\n" + ("\n".join(changes) if changes else "  No changes detected")
    except (IntegrityError, DataError) as e:
        repo.rollback()
        return f"🔖 Product marks sync failed: Database error - {str(e)}"
    except SQLAlchemyError as e:
        repo.rollback()
        return f"🔖 Product marks sync failed: Database connection error - {str(e)}"
    except Exception as e:
        repo.rollback()
        return f"🔖 Product marks sync failed: Unexpected error - {str(e)}"