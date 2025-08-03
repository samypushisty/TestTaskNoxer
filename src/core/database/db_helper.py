from typing import Generator
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from core.config import settings


class DatabaseHelper:
    def __init__( self,
        url: str,
        echo: bool = False,
        echo_pool: bool = False,
        pool_size: int = 5,
        max_overflow: int = 10):
        self.engine = create_engine(
            url=url,
            echo=echo,
            echo_pool=echo_pool,
            pool_size=pool_size,
            max_overflow=max_overflow,
        )
        self.SessionLocal = sessionmaker(bind=self.engine)

    @contextmanager
    def session_getter(self) -> Generator[Session, None, None]:
        with self.SessionLocal() as session:
            yield session

db_helper = DatabaseHelper(
    url=str(settings.db.url),
    echo=settings.db.echo,
    echo_pool=settings.db.echo_pool,
    pool_size=settings.db.pool_size,
    max_overflow=settings.db.max_overflow,
)

