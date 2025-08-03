from sqlalchemy.orm import Session
from typing import List, Dict
from core.database.base import ProjectBadge
from sqlalchemy.exc import SQLAlchemyError, DataError, IntegrityError


def sync_special_badges(session: Session, badges_data: List[Dict]) -> str:
    """Синхронизация специальных бейджей с обработкой ошибок"""
    changes = []
    for badge_data in badges_data:
        try:
            badge_id = badge_data["id"]
            existing = session.get(ProjectBadge, badge_id)

            if existing:
                # Check for changes
                if existing.description != badge_data["description"]:
                    changes.append(f"  📌 Badge #{badge_id} description updated")
                    existing.description = badge_data["description"]
                # ... other fields
            else:
                new_badge = ProjectBadge(
                    id=badge_id,
                    description=badge_data["description"],
                    image_url=badge_data["image_url"],
                    meaning_tag=badge_data["meaning_tag"],
                    url=badge_data["url"],
                    sort_order=badge_data["sort_order"]
                )
                session.add(new_badge)
                changes.append(f"  ➕ New badge #{badge_id} '{badge_data['description']}' added")
        except KeyError as e:
            changes.append(f"  ⚠️ Пропущен бейдж: отсутствует поле {str(e)}")
        except (DataError, IntegrityError) as e:
            session.rollback()
            changes.append(f"  ❌ Ошибка БД при обработке бейджа: {str(e)}")
        except Exception as e:
            changes.append(f"  ❓ Неизвестная ошибка при обработке бейджа: {str(e)}")

    try:
        session.commit()
        return f"📌 Badges sync complete:\n" + ("\n".join(changes) if changes else "  No changes detected")
    except (IntegrityError, DataError) as e:
        session.rollback()
        return f"📌 Badges sync failed: Database error - {str(e)}"
    except SQLAlchemyError as e:
        session.rollback()
        return f"📌 Badges sync failed: Database connection error - {str(e)}"
    except Exception as e:
        session.rollback()
        return f"📌 Badges sync failed: Unexpected error - {str(e)}"