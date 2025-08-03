class SyncError(Exception):
    """Базовый класс для ошибок синхронизации"""
    pass

class APIError(SyncError):
    """Ошибка при работе с API"""
    pass

class DatabaseError(SyncError):
    """Ошибка при работе с базой данных"""
    pass

class ValidationError(SyncError):
    """Ошибка валидации данных"""
    pass