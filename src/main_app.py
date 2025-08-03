from flask import Flask,jsonify
import os
from sqlalchemy import select
from apscheduler.schedulers.background import BackgroundScheduler

from core.config import settings
from core.database.base import Product
from core.database.db_helper import db_helper
from core.utils.sync.main import sync_api_data


app = Flask(__name__)


def run_sync():
    with db_helper.session_getter() as session:
        sync_api_data(session, True)
        sync_api_data(session, False)

scheduler = BackgroundScheduler()
scheduler.add_job(run_sync, 'interval', seconds=settings.time_sleep)
scheduler.start()

@app.route("/info")
def info():
    with db_helper.session_getter() as session:
        query = (
            select(Product)
        )
        result = session.execute(query)
        result = result.scalars().all()

        products_list = [product.to_dict() for product in result]

        return jsonify(products_list)


@app.route('/last_update')
def last_update():
    try:
        # Получаем список всех файлов в текущей директории
        all_files = os.listdir('.')

        # Фильтруем только файлы логов синхронизации
        sync_logs = [f for f in all_files if f.startswith('sync_') and f.endswith('.log')]

        if not sync_logs:
            return jsonify({"error": "No sync logs found"}), 404

        # Сортируем файлы по имени в обратном порядке
        # Формат sync_YYYYMMDD_HHMMSS.log гарантирует, что лексикографический порядок = хронологическому
        sync_logs.sort(reverse=True)

        # Берем самый новый файл (первый в отсортированном списке)
        latest_log = sync_logs[0]

        # Читаем содержимое файла
        with open(latest_log, 'r') as f:
            log_content = f.read()

        # Возвращаем информацию о логе
        return jsonify({
            "log_file": latest_log,
            "timestamp": latest_log[5:19],  # Извлекаем временную метку из имени файла
            "content": log_content
        })

    except Exception as e:
        return jsonify({"error": f"Failed to read logs: {str(e)}"}), 500


