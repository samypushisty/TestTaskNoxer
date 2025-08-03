from sqlalchemy.orm import Session
from typing import Dict, List
from core.database.base import Category, ProductMark, ProductColor, ProductParameter
from sqlalchemy.exc import SQLAlchemyError


def sync_product_relations(session: Session, product, prod_data: Dict) -> List[str]:
    """Синхронизация всех связанных сущностей продукта с обработкой ошибок"""
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
                        changes.append(
                            f"    ⚠️ Пропущена категория для продукта #{product.product_id}: отсутствует поле {str(e)}")
                    except Exception as e:
                        changes.append(
                            f"    ❓ Ошибка при обработке категории для продукта #{product.product_id}: {str(e)}")
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
                        changes.append(
                            f"    ⚠️ Пропущена метка для продукта #{product.product_id}: отсутствует поле {str(e)}")
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
                        changes.append(
                            f"    ⚠️ Пропущен цвет для продукта #{product.product_id}: отсутствует поле {str(e)}")
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
                                updates.append(
                                    f"string: '{param.parameter_string}' → '{param_data['parameter_string']}'")
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
                        changes.append(
                            f"    ⚠️ Пропущен параметр для продукта #{product.product_id}: отсутствует поле {str(e)}")
                    except Exception as e:
                        changes.append(
                            f"    ❓ Ошибка при обработке параметра для продукта #{product.product_id}: {str(e)}")
            except Exception as e:
                changes.append(f"  ❌ Ошибка при синхронизации параметров для продукта #{product.product_id}: {str(e)}")

    except Exception as e:
        changes.append(f"  🚨 Критическая ошибка при синхронизации связанных сущностей: {str(e)}")

    return changes