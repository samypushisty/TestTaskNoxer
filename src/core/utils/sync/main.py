from sqlalchemy.orm import Session
from typing import List, Dict
from core.utils.sync.core.api_client import APIClient
from core.utils.sync.services import (
    sync_categories,
    sync_product_marks,
    sync_products,
    sync_special_parameters,
    sync_special_actions,
    sync_special_badges,
    sync_special_json_configs
)
from core.utils.sync.utils.logging import setup_logger, log_sync_start, log_sync_complete
import logging
from datetime import datetime


def sync_api_data(session: Session, on_main: bool) -> str:
    """
    Основная функция синхронизации данных из API в БД
    """
    logger = setup_logger("sync_logger", f"sync_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
    log_sync_start(logger, on_main)

    try:
        # Инициализация клиента API
        api_client = APIClient()
        api_data = api_client.get_products(on_main)

        # Сбор всех функций синхронизации
        sync_functions = [
            ("categories", sync_categories, api_data.get("categories", [])),
            ("product_marks", sync_product_marks, api_data.get("product_marks", [])),
            ("products", sync_products, api_data.get("products", [])),
            ("special_parameters", sync_special_parameters, api_data.get("special_project_parameters", {})),
            ("special_actions", sync_special_actions, api_data.get("special_project_parameters_actions", [])),
            ("special_badges", sync_special_badges, api_data.get("special_project_parameters_badges", [])),
            ("special_json_configs", sync_special_json_configs, api_data.get("special_project_parameters_json", {})),
        ]

        # Выполнение синхронизации для каждого типа данных
        reports = []
        for name, func, data in sync_functions:
            if not data:
                continue

            try:
                report = func(session, data)
                if report and "No changes" not in report:
                    reports.append(report)
            except Exception as e:
                error_msg = f"💥 Error syncing {name}: {str(e)}"
                reports.append(error_msg)
                logger.error(error_msg)

        # Формирование финального отчета
        if not reports:
            report = "✨ All systems green! No changes detected in the database."
        else:
            report = f"🔄 Data synchronization complete for on_main={on_main}:\n" + "\n\n".join(reports)

        log_sync_complete(logger, report)
        return report

    except Exception as e:
        error_msg = f"🚨 Critical error during synchronization: {str(e)}"
        logger.critical(error_msg, exc_info=True)
        return error_msg