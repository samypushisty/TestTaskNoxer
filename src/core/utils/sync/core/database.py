from sqlalchemy.orm import Session
from typing import TypeVar, Generic, Optional
from sqlalchemy.exc import SQLAlchemyError, DataError, IntegrityError, OperationalError

T = TypeVar('T')


class Repository(Generic[T]):
    """Базовый репозиторий для операций с сущностями"""

    def __init__(self, session: Session, model: T):
        self.session = session
        self.model = model

    def get_by_id(self, id) -> Optional[T]:
        """Получить сущность по ID"""
        try:
            return self.session.get(self.model, id)
        except Exception as e:
            raise RuntimeError(f"Ошибка при получении сущности по ID: {str(e)}")

    def add(self, entity: T) -> T:
        """Добавить новую сущность"""
        try:
            self.session.add(entity)
            return entity
        except (DataError, IntegrityError) as e:
            self.session.rollback()
            raise
        except Exception as e:
            self.session.rollback()
            raise RuntimeError(f"Ошибка при добавлении сущности: {str(e)}")

    def commit(self):
        """Зафиксировать изменения"""
        try:
            self.session.commit()
        except (IntegrityError, DataError) as e:
            self.session.rollback()
            raise
        except SQLAlchemyError as e:
            self.session.rollback()
            raise
        except Exception as e:
            self.session.rollback()
            raise

    def rollback(self):
        """Откатить изменения"""
        try:
            self.session.rollback()
        except Exception as e:
            raise RuntimeError(f"Ошибка при откате транзакции: {str(e)}")