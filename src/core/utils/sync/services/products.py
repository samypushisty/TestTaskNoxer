from sqlalchemy.orm import Session
from typing import List, Dict
from datetime import datetime
from core.database.base import Product
from .product_relations import sync_product_relations
from sqlalchemy.exc import SQLAlchemyError, IntegrityError, DataError


def sync_products(session: Session, products_data: List[Dict]) -> str:
    """Синхронизация продуктов с обработкой ошибок"""
    changes = []

    for prod_data in products_data:
        try:
            prod_id = prod_data["Product_ID"]
            existing = session.get(Product, prod_id)

            # Parse dates with error handling
            created_at = None
            updated_at = None

            try:
                if prod_data["Created_At"]:
                    created_at = datetime.strptime(prod_data["Created_At"], "%a, %d %b %Y %H:%M:%S GMT")
                else:
                    created_at = datetime.utcnow()
            except (KeyError, ValueError, TypeError):
                created_at = datetime.utcnow()
                changes.append(
                    f"  ⚠️ Неверный формат даты создания для продукта #{prod_id}, используется текущее время")

            try:
                if prod_data["Updated_At"]:
                    updated_at = datetime.strptime(prod_data["Updated_At"], "%a, %d %b %Y %H:%M:%S GMT")
                else:
                    updated_at = datetime.utcnow()
            except (KeyError, ValueError, TypeError):
                updated_at = datetime.utcnow()
                changes.append(
                    f"  ⚠️ Неверный формат даты обновления для продукта #{prod_id}, используется текущее время")

            if existing:
                # Check main product changes
                updates = []
                if existing.product_name != prod_data["Product_Name"]:
                    updates.append(f"name: '{existing.product_name}' → '{prod_data['Product_Name']}'")
                    existing.product_name = prod_data["Product_Name"]
                if existing.on_main != prod_data["OnMain"]:
                    updates.append(f"on_main: {existing.on_main} → {prod_data['OnMain']}")
                    existing.on_main = prod_data["OnMain"]
                if existing.updated_at != updated_at:
                    updates.append(f"updated_at: {existing.updated_at} → {updated_at}")
                    existing.updated_at = updated_at
                if existing.tags != prod_data["tags"]:
                    updates.append("tags updated")
                    existing.tags = prod_data["tags"]
                if updates:
                    changes.append(f"📦 Product #{prod_id} updated: {', '.join(updates)}")

                # Sync related entities
                try:
                    product_changes = sync_product_relations(session, existing, prod_data)
                    if product_changes:
                        changes.extend(product_changes)
                except Exception as e:
                    changes.append(
                        f"  ❌ Ошибка при синхронизации связанных сущностей для продукта #{prod_id}: {str(e)}")
            else:
                # Create new product
                new_product = Product(
                    product_id=prod_id,
                    product_name=prod_data["Product_Name"],
                    on_main=prod_data["OnMain"],
                    created_at=created_at,
                    updated_at=updated_at,
                    moysklad_connector_products_data=prod_data.get("moysklad_connector_products_data", {}),
                    tags=prod_data.get("tags", "")
                )
                session.add(new_product)

                # Sync related entities for new product
                try:
                    product_changes = sync_product_relations(session, new_product, prod_data)
                    if product_changes:
                        changes.extend(product_changes)
                except Exception as e:
                    changes.append(
                        f"  ❌ Ошибка при синхронизации связанных сущностей для нового продукта #{prod_id}: {str(e)}")

                changes.append(f"📦 New product #{prod_id} '{prod_data['Product_Name']}' added")
        except KeyError as e:
            changes.append(f"  ⚠️ Пропущен продукт: отсутствует поле {str(e)}")
        except (DataError, IntegrityError) as e:
            session.rollback()
            changes.append(f"  ❌ Ошибка БД при обработке продукта: {str(e)}")
        except Exception as e:
            changes.append(f"  ❓ Неизвестная ошибка при обработке продукта: {str(e)}")

    try:
        session.commit()
        return f"🛍️ Products sync complete:\n" + ("\n".join(changes) if changes else "  No changes detected")
    except (IntegrityError, DataError) as e:
        session.rollback()
        return f"🛍️ Products sync failed: Database error - {str(e)}"
    except SQLAlchemyError as e:
        session.rollback()
        return f"🛍️ Products sync failed: Database connection error - {str(e)}"
    except Exception as e:
        session.rollback()
        return f"🛍️ Products sync failed: Unexpected error - {str(e)}"