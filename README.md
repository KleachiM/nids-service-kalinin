# nids-service

Сервис детектирования аномалий сетевого трафика с помощью модели машинного обучения и HTTP API. Учебный сквозной проект
дисциплины «Инструментальные средства разработки инфокоммуникационных
систем с ИИ».

## Что здесь есть сейчас

Модель, HTTP-сервис и журнал предсказаний — готовые. Остальные части добавляются по ходу курса:

| Цикл | Что добавляете | Чего пока нет в репозитории |
|---|---|---|
| 2 | история, ветки, PR | — |
| 3 | воспроизводимое окружение | — |
| 4 | контейнер | `Dockerfile`, `.dockerignore` |
| 5 | журнал предсказаний в БД | — |
| 6 | стек одной командой | `compose.yaml` |
| 7 | автосборка и тесты в CI | `.github/workflows/` |

Отсутствие этих файлов — не недоработка шаблона, а ваша программа на семестр.

## Быстрый старт

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -e ".[dev]"

python data/make_dataset.py      # сгенерировать данные
python -m nids.train             # обучить модель
uvicorn nids.api:app --app-dir src --reload
```

Документация API откроется на http://localhost:8000/docs

Проверка:

```bash
curl -s localhost:8000/health
```

## Структура

```
data/make_dataset.py    генератор учебного набора соединений
src/nids/features.py    описание признаков и препроцессор
src/nids/train.py       обучение, сохранение модели и паспорта
src/nids/api.py         HTTP-сервис
src/nids/db.py          запись журнала в PostgreSQL
src/nids/schemas.py     контракт API
tests/                  контрактные тесты и тесты признаков
artifacts/              сюда попадают model.joblib и metadata.json
migrations/             SQL-миграции журнала и индекса
scripts/load.py         500 запросов к /predict
```

## Тесты

```bash
pytest
```

Тринадцать тестов, проходят примерно за секунду. Модель для тестов обучается
на лету во временном каталоге — заранее запускать `train` не нужно.

## Качество модели

На сгенерированных данных (20 000 записей, seed 42):

| Метрика | Значение |
|---|---|
| accuracy | 0,92 |
| precision | 0,98 |
| recall | 0,85 |

Recall заметно ниже precision, и это не дефект. В наборе есть класс
медленных скрытных атак, которые по имеющимся признакам неотличимы от
обычного трафика — примерно их модель и пропускает. Для детектора вторжений
такое соотношение — предмет отдельного инженерного разговора, а не повод
крутить гиперпараметры.

## Переменные окружения

| Переменная | По умолчанию | Назначение |
|---|---|---|
| `MODEL_DIR` | `artifacts` | где искать `model.joblib` |
| `DATABASE_URL` | не задан | подключение к PostgreSQL для журнала предсказаний |

Если `DATABASE_URL` не задан или база недоступна, `/predict` возвращает предсказание и пишет ошибку записи в лог приложения.

## Журнал предсказаний в PostgreSQL

Поднимите базу с именованным томом (учебный пароль замените для другого окружения):

```bash
docker run -d --name nids-db \
  -e POSTGRES_PASSWORD=devpassword -e POSTGRES_USER=nids -e POSTGRES_DB=nids \
  -p 127.0.0.1:5432:5432 -v nids-pgdata:/var/lib/postgresql/data \
  postgres:16-alpine
docker exec nids-db psql -U nids -d nids -c 'SELECT version();'
docker exec -i nids-db psql -U nids -d nids -v ON_ERROR_STOP=1 < migrations/001_create_predictions.sql
docker exec -i nids-db psql -U nids -d nids -v ON_ERROR_STOP=1 < migrations/002_index_created_at.sql
```

Если локальный PostgreSQL уже занимает порт `5432`, замените левую часть `-p` на `127.0.0.1:5433:5432` и укажите порт `5433` в `DATABASE_URL`.

Создайте `.env` из `.env.example` и заполните `DATABASE_URL` адресом вида `postgresql://nids:<пароль>@127.0.0.1:5432/nids`. При пустом `MODEL_DIR` используется `artifacts`. Запустите сервис, а во втором терминале — нагрузку:

```bash
cp .env.example .env
uvicorn nids.api:app --app-dir src --env-file .env
python scripts/load.py
docker exec nids-db psql -U nids -d nids -c 'SELECT count(*) FROM predictions;'
```

`.env` исключён из Git. В журнал попадают все 14 входных признаков, ответ, вероятность атаки и время вычисления ответа до записи в БД.
