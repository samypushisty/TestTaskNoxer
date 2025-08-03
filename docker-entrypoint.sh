#!/bin/bash
set -e

# Ожидаем доступность PostgreSQL
echo "Ожидание готовности базы данных..."
until pg_isready -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" -d "$POSTGRES_DB" -t 5; do
  echo "База данных недоступна, повторная проверка через 5 секунд..."
  sleep 5
done
echo "База данных готова к подключению!"

if [ "$INIT_DB" = "true" ]; then
  if PGPASSWORD="$POSTGRES_PASSWORD" psql -h "$POSTGRES_HOST" -U "$POSTGRES_USER" -d "$POSTGRES_DB" -tAc "SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' LIMIT 1" | grep -q 1; then
    echo "База данных уже инициализирована, пропускаем создание таблиц."
  else
    echo "Инициализация базы данных..."
    python -m core.database.base
    echo "Инициализация завершена!"
    export INIT_DB="false"
  fi
fi

# Запуск основного приложения
echo "Запуск приложения..."
exec "$@"