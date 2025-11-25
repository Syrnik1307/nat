# Azure Cosmos DB Emulator Guide

## 1. Установка / Запуск

### Вариант A: Локальный установщик (Windows)
1. Скачайте инсталлятор: https://learn.microsoft.com/azure/cosmos-db/emulator
2. Установите и запустите. По умолчанию слушает `https://localhost:8081/`.
3. Ключ находится в значке уведомлений или используйте переменную окружения.

### Вариант B: Docker
```bash
docker pull mcr.microsoft.com/cosmosdb/linux/azure-cosmos-emulator:latest
docker run -p 8081:8081 -p 10251:10251 -p 10252:10252 -p 10253:10253 -p 10254:10254 \
  -e AZURE_COSMOS_EMULATOR_PARTITION_COUNT=3 \
  -e AZURE_COSMOS_EMULATOR_ENABLE_DATA_PERSISTENCE=true \
  --name cosmos-emulator mcr.microsoft.com/cosmosdb/linux/azure-cosmos-emulator:latest
```
Ожидаемый URL: `https://localhost:8081/`.

## 2. Переменные окружения (пример .env.local)
```bash
COSMOS_DB_ENABLED=1
COSMOS_DB_URL=https://localhost:8081/
COSMOS_DB_KEY=YOUR_EMULATOR_KEY==
COSMOS_DB_DATABASE=teaching_panel
```

## 3. Проверка подключения
В `django shell`:
```python
from cosmos_db import get_database, is_enabled
print(is_enabled())
db = get_database()
print(db)
```

## 4. Первичная миграция данных
```bash
python manage.py shell -c "import manage_cosmos_migration as m; m.run()"
```
Для проверки содержимого можно использовать Data Explorer в UI эмулятора.

## 5. Диагностика и производительность
- При высоких задержках логируйте diagnostic string из SDK (расширить обёртку позже).
- Следите за равномерностью распределения ключей partition key.

## 6. Ограничения / Замечания
- Эмулятор поддерживает только SQL API.
- Размер одного документа < 2MB.
- В текущей интеграции используется упрощённый upsert без ETag контроля.

## 7. Следующие шаги
- Добавить ETag оптимистичные проверки.
- Вынести репозитории в отдельный модуль при росте домена.
- Подключить аналитические события в отдельный контейнер `analyticsEvents`.
