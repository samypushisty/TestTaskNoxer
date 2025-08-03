import requests
from typing import Dict, Any, Optional
from requests.exceptions import RequestException, Timeout


class APIClient:
    """Клиент для работы с API синхронизации"""

    def __init__(self, base_url: str = "https://bot-igor.ru"):
        self.base_url = base_url

    def get_products(self, on_main: bool) -> Dict[str, Any]:
        """
        Получает данные продуктов из API
        Args:
            on_main: Фильтр по флагу on_main
        Returns:
            Словарь с данными от API
        """
        url = f"{self.base_url}/api/products?on_main={str(on_main).lower()}"
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            api_data = response.json()

            if api_data.get("status") != "ok":
                raise ValueError(f"API вернул статус ошибки: {api_data.get('status', 'unknown')}. "
                                 f"Сообщение: {api_data.get('message', '')}")

            return api_data
        except Timeout:
            raise TimeoutError(f"Таймаут при запросе к API: {url}")
        except requests.exceptions.JSONDecodeError:
            raise ValueError(f"Ошибка парсинга JSON от API: некорректный ответ от {url}")
        except RequestException as e:
            raise ConnectionError(f"Ошибка запроса к API: {str(e)}")