from sqlalchemy.orm import Session
from typing import List, Dict
from core.database.base import ProjectAction
from sqlalchemy.exc import SQLAlchemyError, IntegrityError, DataError


def sync_special_actions(session: Session, actions_data: List[Dict]) -> str:
    """Синхронизация специальных действий с обработкой ошибок"""
    changes = []
    for action_data in actions_data:
        try:
            action_id = action_data["id"]
            existing = session.get(ProjectAction, action_id)

            if existing:
                # Check for changes (simplified for brevity)
                if existing.description != action_data["description"]:
                    changes.append(f"  🎯 Action #{action_id} description updated")
                    existing.description = action_data["description"]
                # ... other fields
            else:
                new_action = ProjectAction(
                    id=action_id,
                    action_type=action_data["action_type"],
                    description=action_data["description"],
                    image_url=action_data["image_url"],
                    url=action_data["url"],
                    sort_order=action_data["sort_order"],
                    extra_field_1=action_data["extra_field_1"],
                    extra_field_2=action_data["extra_field_2"]
                )
                session.add(new_action)
                changes.append(f"  ➕ New action #{action_id} '{action_data['description']}' added")
        except KeyError as e:
            changes.append(f"  ⚠️ Пропущено действие: отсутствует поле {str(e)}")
        except (DataError, IntegrityError) as e:
            session.rollback()
            changes.append(f"  ❌ Ошибка БД при обработке действия: {str(e)}")
        except Exception as e:
            changes.append(f"  ❓ Неизвестная ошибка при обработке действия: {str(e)}")

    try:
        session.commit()
        return f"🎯 Actions sync complete:\n" + ("\n".join(changes) if changes else "  No changes detected")
    except (IntegrityError, DataError) as e:
        session.rollback()
        return f"🎯 Actions sync failed: Database error - {str(e)}"
    except SQLAlchemyError as e:
        session.rollback()
        return f"🎯 Actions sync failed: Database connection error - {str(e)}"
    except Exception as e:
        session.rollback()
        return f"🎯 Actions sync failed: Unexpected error - {str(e)}"