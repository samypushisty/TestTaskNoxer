from sqlalchemy.orm import Session
from typing import List, Dict
from core.utils.sync.core.database import Repository
from core.database.base import Category
from sqlalchemy.exc import SQLAlchemyError, IntegrityError, DataError
from requests.exceptions import RequestException


def sync_categories(session: Session, categories_data: List[Dict]) -> str:
    """Синхронизация категорий с обработкой ошибок"""
    repo = Repository[Category](session, Category)
    changes = []

    for cat_data in categories_data:
        try:
            cat_id = cat_data["Category_ID"]
            existing = repo.get_by_id(cat_id)

            if existing:
                # Track changes
                updates = []
                if existing.category_name != cat_data["Category_Name"]:
                    updates.append(f"name: '{existing.category_name}' → '{cat_data['Category_Name']}'")
                    existing.category_name = cat_data["Category_Name"]
                if existing.category_image != cat_data["Category_Image"]:
                    updates.append(f"image URL updated")
                    existing.category_image = cat_data["Category_Image"]
                if existing.sort_order != cat_data["sort_order"]:
                    updates.append(f"sort order: {existing.sort_order} → {cat_data['sort_order']}")
                    existing.sort_order = cat_data["sort_order"]
                if updates:
                    changes.append(
                        f"  📌 Category #{cat_id} '{cat_data['Category_Name']}' updated: {', '.join(updates)}")
            else:
                # Create new category
                new_cat = Category(
                    category_id=cat_id,
                    category_name=cat_data["Category_Name"],
                    category_image=cat_data["Category_Image"],
                    sort_order=cat_data["sort_order"]
                )
                repo.add(new_cat)
                changes.append(f"  ➕ New category #{cat_id} '{cat_data['Category_Name']}' added")
        except KeyError as e:
            changes.append(f"  ⚠️ Пропущена категория: отсутствует поле {str(e)}")
        except (DataError, IntegrityError) as e:
            session.rollback()
            changes.append(f"  ❌ Ошибка БД при обработке категории: {str(e)}")
        except Exception as e:
            changes.append(f"  ❓ Неизвестная ошибка при обработке категории: {str(e)}")

    try:
        repo.commit()
        return f"🗂️ Categories sync complete:\n" + ("\n".join(changes) if changes else "  No changes detected")
    except (IntegrityError, DataError) as e:
        repo.rollback()
        return f"🗂️ Categories sync failed: Database error - {str(e)}"
    except SQLAlchemyError as e:
        repo.rollback()
        return f"🗂️ Categories sync failed: Database connection error - {str(e)}"
    except Exception as e:
        repo.rollback()
        return f"🗂️ Categories sync failed: Unexpected error - {str(e)}"