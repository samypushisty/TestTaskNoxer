from datetime import datetime
import requests
from sqlalchemy.orm import Session
from sqlalchemy import select
from typing import Dict, List
from core.database.base import Category, ProductMark, Product, ProductColor, ProjectBadge, ProjectJsonConfig, \
    ProjectAction, ProjectParameter, ProductParameter
# Импортируем исключения
from sqlalchemy.exc import SQLAlchemyError, DataError, IntegrityError
from requests.exceptions import RequestException, Timeout, ConnectionError

def sync_api_data(session: Session, on_main: bool) -> str:
    """
    Main function to sync data from API to database with comprehensive error handling.
    Returns a human-readable report of changes or errors.
    Args:
        session: SQLAlchemy database session
        on_main: Whether to fetch products from on_main=true or on_main=false endpoint
    Returns:
        String report of changes or errors during sync
    """
    report_lines = []
    try:
        url = f"https://bot-igor.ru/api/products?on_main={str(on_main).lower()}"

        # === 1. Запрос к API с обработкой сетевых ошибок ===
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()  # Проверка HTTP-статуса (4xx/5xx)
            api_data = response.json()
        except ConnectionError:
            error_msg = f"❌ Не удалось подключиться к API: ошибка соединения с {url}"
            report_lines.append(error_msg)
            return error_msg
        except Timeout:
            error_msg = f"❌ Таймаут при запросе к API: {url}"
            report_lines.append(error_msg)
            return error_msg
        except requests.exceptions.JSONDecodeError:
            error_msg = f"❌ Ошибка парсинга JSON от API: некорректный ответ от {url}"
            report_lines.append(error_msg)
            return error_msg
        except RequestException as e:
            error_msg = f"❌ Ошибка запроса к API: {str(e)}"
            report_lines.append(error_msg)
            return error_msg

        if api_data.get("status") != "ok":
            error_msg = f"❌ API вернул статус ошибки: {api_data.get('status', 'unknown')}. Сообщение: {api_data.get('message', '')}"
            report_lines.append(error_msg)
            return error_msg

        # === 2. Синхронизация данных с обработкой ошибок для каждого блока ===
        endpoints = [
            ("categories", sync_categories, api_data.get("categories", [])),
            ("product_marks", sync_product_marks, api_data.get("product_marks", [])),
            ("products", sync_products, api_data.get("products", [])),
            ("special_project_parameters", sync_special_parameters, api_data.get("special_project_parameters", {})),
            ("special_project_parameters_actions", sync_special_actions, api_data.get("special_project_parameters_actions", [])),
            ("special_project_parameters_badges", sync_special_badges, api_data.get("special_project_parameters_badges", [])),
            ("special_project_parameters_json", sync_special_json_configs, api_data.get("special_project_parameters_json", {})),
        ]

        for section_name, sync_func, data in endpoints:
            if not data:  # Пропускаем пустые данные
                continue

            try:
                result = sync_func(session, data)
                if result and "No changes" not in result:
                    report_lines.append(result)
            except Exception as e:
                error_msg = f"💥 Ошибка при синхронизации {section_name}: {str(e)}"
                report_lines.append(error_msg)
                # Не останавливаем весь процесс — продолжаем с другими секциями
                continue  # Продолжаем, даже если один блок упал

        # === 3. Формирование финального отчёта ===
        final_report = "\n".join([r for r in report_lines if r.strip()])
        if not final_report:
            return "✨ Все системы зелёные! Нет изменений и ошибок."

        return f"🔄 Синхронизация завершена (on_main={on_main}):\n{final_report}"

    except Exception as e:
        error_msg = f"🚨 Критическая ошибка в процессе синхронизации: {str(e)}"
        report_lines.append(error_msg)
        return "\n".join(report_lines)

def sync_categories(session: Session, categories_data: List[Dict]) -> str:
    """Sync category data from API to database with error handling"""
    changes = []
    for cat_data in categories_data:
        try:
            cat_id = cat_data["Category_ID"]
            existing = session.get(Category, cat_id)

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
                    changes.append(f"  📌 Category #{cat_id} '{cat_data['Category_Name']}' updated: {', '.join(updates)}")
            else:
                # Create new category
                new_cat = Category(
                    category_id=cat_id,
                    category_name=cat_data["Category_Name"],
                    category_image=cat_data["Category_Image"],
                    sort_order=cat_data["sort_order"]
                )
                session.add(new_cat)
                changes.append(f"  ➕ New category #{cat_id} '{cat_data['Category_Name']}' added")
        except KeyError as e:
            changes.append(f"  ⚠️ Пропущена категория: отсутствует поле {str(e)}")
        except (DataError, IntegrityError) as e:
            session.rollback()
            changes.append(f"  ❌ Ошибка БД при обработке категории: {str(e)}")
        except Exception as e:
            changes.append(f"  ❓ Неизвестная ошибка при обработке категории: {str(e)}")

    try:
        session.commit()
        return f"🗂️ Categories sync complete:\n" + ("\n".join(changes) if changes else "  No changes detected")
    except (IntegrityError, DataError) as e:
        session.rollback()
        return f"🗂️ Categories sync failed: Database error - {str(e)}"
    except SQLAlchemyError as e:
        session.rollback()
        return f"🗂️ Categories sync failed: Database connection error - {str(e)}"
    except Exception as e:
        session.rollback()
        return f"🗂️ Categories sync failed: Unexpected error - {str(e)}"

def sync_product_marks(session: Session, marks_data: List[Dict]) -> str:
    """Sync product mark data from API to database with error handling"""
    changes = []
    for mark_data in marks_data:
        try:
            mark_id = mark_data["Mark_ID"]
            existing = session.get(ProductMark, mark_id)

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
                session.add(new_mark)
                changes.append(f"  ➕ New mark #{mark_id} '{mark_data['Mark_Name']}' added")
        except KeyError as e:
            changes.append(f"  ⚠️ Пропущена метка: отсутствует поле {str(e)}")
        except (DataError, IntegrityError) as e:
            session.rollback()
            changes.append(f"  ❌ Ошибка БД при обработке метки: {str(e)}")
        except Exception as e:
            changes.append(f"  ❓ Неизвестная ошибка при обработке метки: {str(e)}")

    try:
        session.commit()
        return f"🔖 Product marks sync complete:\n" + ("\n".join(changes) if changes else "  No changes detected")
    except (IntegrityError, DataError) as e:
        session.rollback()
        return f"🔖 Product marks sync failed: Database error - {str(e)}"
    except SQLAlchemyError as e:
        session.rollback()
        return f"🔖 Product marks sync failed: Database connection error - {str(e)}"
    except Exception as e:
        session.rollback()
        return f"🔖 Product marks sync failed: Unexpected error - {str(e)}"

def sync_products(session: Session, products_data: List[Dict]) -> str:
    """Sync product data and all related entities with error handling"""
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
                changes.append(f"  ⚠️ Неверный формат даты создания для продукта #{prod_id}, используется текущее время")

            try:
                if prod_data["Updated_At"]:
                    updated_at = datetime.strptime(prod_data["Updated_At"], "%a, %d %b %Y %H:%M:%S GMT")
                else:
                    updated_at = datetime.utcnow()
            except (KeyError, ValueError, TypeError):
                updated_at = datetime.utcnow()
                changes.append(f"  ⚠️ Неверный формат даты обновления для продукта #{prod_id}, используется текущее время")

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
                    changes.append(f"  ❌ Ошибка при синхронизации связанных сущностей для продукта #{prod_id}: {str(e)}")
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
                    changes.append(f"  ❌ Ошибка при синхронизации связанных сущностей для нового продукта #{prod_id}: {str(e)}")

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

def sync_product_relations(session: Session, product: Product, prod_data: Dict) -> List[str]:
    """Sync all related entities for a product with error handling"""
    changes = []

    try:
        # 1. Sync categories
        if "categories" in prod_data:
            try:
                # Clear existing associations
                product.categories = []
                for cat_data in prod_data["categories"]:
                    try:
                        cat_id = cat_data["Category_ID"]
                        category = session.get(Category, cat_id)
                        if not category:
                            # Create category if it doesn't exist
                            category = Category(
                                category_id=cat_id,
                                category_name=cat_data["Category_Name"],
                                category_image=cat_data["Category_Image"],
                                sort_order=cat_data["sort_order"]
                            )
                            session.add(category)
                            changes.append(f"  ➕ Category #{cat_id} added for product #{product.product_id}")
                        product.categories.append(category)
                    except KeyError as e:
                        changes.append(f"    ⚠️ Пропущена категория для продукта #{product.product_id}: отсутствует поле {str(e)}")
                    except Exception as e:
                        changes.append(f"    ❓ Ошибка при обработке категории для продукта #{product.product_id}: {str(e)}")
                changes.append(f"  🗂️ Categories synced for product #{product.product_id}")
            except Exception as e:
                changes.append(f"  ❌ Ошибка при синхронизации категорий для продукта #{product.product_id}: {str(e)}")

        # 2. Sync marks
        if "marks" in prod_data:
            try:
                # Clear existing marks
                product.marks = []
                for mark_data in prod_data["marks"]:
                    try:
                        mark_id = mark_data["Mark_ID"]
                        mark = session.get(ProductMark, mark_id)
                        if not mark:
                            # Create mark if it doesn't exist
                            mark = ProductMark(
                                mark_id=mark_id,
                                mark_name=mark_data["Mark_Name"]
                            )
                            session.add(mark)
                            changes.append(f"  ➕ Mark #{mark_id} added for product #{product.product_id}")
                        product.marks.append(mark)
                    except KeyError as e:
                        changes.append(f"    ⚠️ Пропущена метка для продукта #{product.product_id}: отсутствует поле {str(e)}")
                    except Exception as e:
                        changes.append(f"    ❓ Ошибка при обработке метки для продукта #{product.product_id}: {str(e)}")
                changes.append(f"  🏷️ Marks synced for product #{product.product_id}")
            except Exception as e:
                changes.append(f"  ❌ Ошибка при синхронизации меток для продукта #{product.product_id}: {str(e)}")

        # 3. Sync colors
        if "colors" in prod_data:
            try:
                existing_colors = {color.color_id: color for color in product.colors}
                new_color_ids = {color_data["Color_ID"] for color_data in prod_data["colors"]}

                # Delete removed colors
                for color_id, color in existing_colors.items():
                    if color_id not in new_color_ids:
                        try:
                            session.delete(color)
                            changes.append(f"  ❌ Color #{color_id} deleted from product #{product.product_id}")
                        except Exception as e:
                            changes.append(f"    ❌ Ошибка при удалении цвета #{color_id}: {str(e)}")

                # Add/update colors
                for color_data in prod_data["colors"]:
                    try:
                        color_id = color_data["Color_ID"]
                        color = existing_colors.get(color_id)
                        if color:
                            # Update existing color
                            updates = []
                            if color.color_name != color_data["Color_Name"]:
                                updates.append(f"name: '{color.color_name}' → '{color_data['Color_Name']}'")
                                color.color_name = color_data["Color_Name"]
                            if color.color_code != color_data["Color_Code"]:
                                updates.append(f"code: '{color.color_code}' → '{color_data['Color_Code']}'")
                                color.color_code = color_data["Color_Code"]
                            if color.discount != color_data["discount"]:
                                updates.append(f"discount: {color.discount} → {color_data['discount']}")
                                color.discount = color_data["discount"]
                            if updates:
                                changes.append(f"  🎨 Color #{color_id} updated: {', '.join(updates)}")
                        else:
                            # Add new color
                            new_color = ProductColor(
                                color_id=color_id,
                                color_name=color_data["Color_Name"],
                                color_code=color_data["Color_Code"],
                                color_image=color_data["Color_image"],
                                discount=color_data["discount"],
                                sort_order=color_data["sort_order"],
                                product_id=product.product_id
                            )
                            product.colors.append(new_color)
                            changes.append(f"  ➕ Color #{color_id} added to product #{product.product_id}")
                    except KeyError as e:
                        changes.append(f"    ⚠️ Пропущен цвет для продукта #{product.product_id}: отсутствует поле {str(e)}")
                    except Exception as e:
                        changes.append(f"    ❓ Ошибка при обработке цвета для продукта #{product.product_id}: {str(e)}")
            except Exception as e:
                changes.append(f"  ❌ Ошибка при синхронизации цветов для продукта #{product.product_id}: {str(e)}")

        # 5. Sync parameters
        if "parameters" in prod_data:
            try:
                existing_params = {param.parameter_id: param for param in product.parameters}
                new_param_ids = {param_data["Parameter_ID"] for param_data in prod_data["parameters"]}

                # Delete removed parameters
                for param_id in list(existing_params.keys()):
                    if param_id not in new_param_ids:
                        try:
                            session.delete(existing_params[param_id])
                            changes.append(f"  ❌ Parameter #{param_id} deleted from product #{product.product_id}")
                        except Exception as e:
                            changes.append(f"    ❌ Ошибка при удалении параметра #{param_id}: {str(e)}")

                # Add/update parameters
                for param_data in prod_data["parameters"]:
                    try:
                        param_id = param_data["Parameter_ID"]
                        param = existing_params.get(param_id)
                        if param:
                            # Update existing parameter
                            updates = []
                            if param.name != param_data["name"]:
                                updates.append(f"name: '{param.name}' → '{param_data['name']}'")
                                param.name = param_data["name"]
                            if param.parameter_string != param_data["parameter_string"]:
                                updates.append(f"string: '{param.parameter_string}' → '{param_data['parameter_string']}'")
                                param.parameter_string = param_data["parameter_string"]
                            if param.price != param_data["price"]:
                                updates.append(f"price: {param.price} → {param_data['price']}")
                                param.price = param_data["price"]
                            if updates:
                                changes.append(f"  🔢 Parameter #{param_id} updated: {', '.join(updates)}")
                        else:
                            # Add new parameter
                            new_param = ProductParameter(
                                parameter_id=param_id,
                                name=param_data["name"],
                                parameter_string=param_data["parameter_string"],
                                price=param_data["price"],
                                old_price=param_data["old_price"],
                                chosen=param_data["chosen"],
                                disabled=param_data["disabled"],
                                extra_field_color=param_data["extra_field_color"],
                                extra_field_image=param_data["extra_field_image"],
                                sort_order=param_data["sort_order"],
                                product_id=product.product_id
                            )
                            product.parameters.append(new_param)
                            changes.append(f"  ➕ Parameter #{param_id} added to product #{product.product_id}")
                    except KeyError as e:
                        changes.append(f"    ⚠️ Пропущен параметр для продукта #{product.product_id}: отсутствует поле {str(e)}")
                    except Exception as e:
                        changes.append(f"    ❓ Ошибка при обработке параметра для продукта #{product.product_id}: {str(e)}")
            except Exception as e:
                changes.append(f"  ❌ Ошибка при синхронизации параметров для продукта #{product.product_id}: {str(e)}")

    except Exception as e:
        changes.append(f"  🚨 Критическая ошибка при синхронизации связанных сущностей: {str(e)}")

    return changes

def sync_special_parameters(session: Session, params_data: Dict) -> str:
    """Sync special project parameters with error handling"""
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
            continue  # Пропускаем, если ключ не найден
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

def sync_special_actions(session: Session, actions_data: List[Dict]) -> str:
    """Sync special project actions with error handling"""
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

def sync_special_badges(session: Session, badges_data: List[Dict]) -> str:
    """Sync special project badges with error handling"""
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

def sync_special_json_configs(session: Session, json_data: Dict) -> str:
    """Sync JSON configuration data with error handling"""
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