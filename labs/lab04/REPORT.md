# Лабораторная работа № 4. PostgreSQL и журнал предсказаний

## Цель

Подключить PostgreSQL к сервису детектирования аномалий, записывать успешные предсказания и извлекать эксплуатационные показатели SQL-запросами. Проверить сохранность данных в томе и влияние индекса на план и время выполнения запроса.

## Ход работы

Команды выполнялись из корня проекта 15 ноября 2026 года. На машине уже работал локальный PostgreSQL на порту 5432, поэтому для контейнера использован порт 5433; внутри контейнера остался стандартный 5432. Данные и модель созданы ранее из учебного набора `data/connections.csv`, модель имеет версию `0.1.0`.

### Запуск базы и схема

Добавил `psycopg[binary]` в зависимости и установил пакет:

```console
$ .venv/bin/python -m pip install -e '.[dev]'
Successfully installed nids-service-0.1.0 psycopg-3.3.9 psycopg-binary-3.3.9
```

Создал БД с именованным томом и проверил версию:

```bash
docker run -d --name nids-db \
  -e POSTGRES_PASSWORD=devpassword -e POSTGRES_USER=nids -e POSTGRES_DB=nids \
  -p 127.0.0.1:5433:5432 -v nids-pgdata:/var/lib/postgresql/data \
  postgres:16-alpine
docker exec nids-db psql -U nids -d nids -c 'SELECT version();'
```

```text
PostgreSQL 16.16 on aarch64-unknown-linux-musl, 64-bit
```

Миграция `001_create_predictions.sql` создала таблицу с идентификатором, временем, всеми 14 признаками соединения, версией модели, классом, вероятностью атаки и временем вычисления ответа. Поле `created_at` имеет тип `timestamptz`: он хранит момент времени независимо от часового пояса клиента; `timestamp` без зоны мог бы дать неоднозначные интервалы при работе клиентов из разных зон.

```console
$ docker exec -i nids-db psql -U nids -d nids -v ON_ERROR_STOP=1 < migrations/001_create_predictions.sql
CREATE TABLE
```

### Сохранность данных

Том `nids-pgdata` сохраняет файлы БД независимо от жизненного цикла контейнера. После применения первой миграции я остановил и удалил `nids-db`, создал его заново с тем же томом и проверил таблицу:

```bash
docker stop nids-db
docker rm nids-db
docker run -d --name nids-db \
  -e POSTGRES_PASSWORD=devpassword -e POSTGRES_USER=nids -e POSTGRES_DB=nids \
  -p 127.0.0.1:5433:5432 -v nids-pgdata:/var/lib/postgresql/data \
  postgres:16-alpine
docker exec nids-db psql -U nids -d nids \
  -Atc "SELECT count(*) FROM information_schema.tables WHERE table_name = 'predictions';"
```

```text
1
```

Для обратной проверки я создал отдельный `nids-db-temp` без параметра `-v`. После вставки `retention_probe` содержала одну строку. Затем я удалил и пересоздал контейнер без подключения прежнего тома:

```bash
docker run -d --name nids-db-temp \
  -e POSTGRES_PASSWORD=tempdevpassword -e POSTGRES_USER=nids -e POSTGRES_DB=nids \
  postgres:16-alpine
docker exec nids-db-temp psql -U nids -d nids \
  -c "CREATE TABLE retention_probe (value integer); INSERT INTO retention_probe VALUES (1); SELECT count(*) FROM retention_probe;"
docker stop nids-db-temp
docker rm nids-db-temp
docker run -d --name nids-db-temp \
  -e POSTGRES_PASSWORD=tempdevpassword -e POSTGRES_USER=nids -e POSTGRES_DB=nids \
  postgres:16-alpine
docker exec nids-db-temp psql -U nids -d nids \
  -Atc "SELECT COALESCE(to_regclass('public.retention_probe')::text, 'absent');"
```

```text
CREATE TABLE
INSERT 0 1
 count
-------
     1
(1 row)

absent
```

Образ PostgreSQL автоматически получает анонимный том, даже если `-v` опущен. При пересоздании Docker выдал новый анонимный том, поэтому прежняя таблица не появилась; старый том при обычном `docker rm` остался сиротой. Оба временных тома после опыта удалены, а `nids-pgdata` сохранён.

### Запись, нагрузка и отказ БД

`/predict` измеряет время от начала вычисления признаков до формирования ответа, затем пытается записать одну строку. Время подключения и записи в БД в `response_time_ms` не входит. Если `DATABASE_URL` не задан или запись не удалась, сервис логирует ошибку и возвращает уже полученное предсказание. Для детектора трафика это означает, что временный отказ журнала не прерывает обработку соединений; в платёжной системе с обязательным аудитом операцию, напротив, нельзя подтверждать без успешной фиксации.

```bash
DATABASE_URL=postgresql://nids:devpassword@127.0.0.1:5433/nids \
  .venv/bin/uvicorn nids.api:app --app-dir src --host 127.0.0.1 --port 8000
.venv/bin/python scripts/load.py
docker exec nids-db psql -U nids -d nids -c 'SELECT count(*) FROM predictions;'
```

```text
Отправлено 500 запросов на /predict
 count
-------
   500
```

После `docker stop nids-db` я отправил ещё один запрос. Ответ пришёл, хотя запись не удалась:

```text
HTTP 200
{"prediction":"attack","probability":0.9784,"model_version":"0.1.0"}

Не удалось записать предсказание в журнал БД
psycopg.OperationalError: connection failed: connection to server at "127.0.0.1", port 5433 failed: could not receive data from server: Connection refused
```

После `docker start nids-db` в таблице осталось 500 строк: неудавшаяся запись не была представлена как сохранённая.

### Аналитика

Результаты получены на 500 запросах, выбранных скриптом с фиксированным зерном `42`. `probability` — вероятность **атаки** из ответа API, даже когда `prediction = 'normal'`.

**1. Общее число и доля атак**

```sql
SELECT count(*) AS total,
       count(*) FILTER (WHERE prediction = 'attack') AS attacks,
       round(100.0 * count(*) FILTER (WHERE prediction = 'attack')
             / NULLIF(count(*), 0), 2) AS attack_pct
FROM predictions;
```

```text
 total | attacks | attack_pct
-------+---------+-----------
   500 |     212 |     42.40
```

Из 500 успешных предсказаний 212 классифицированы как атаки (42,40 %).

**2. Классы по протоколам**

```sql
SELECT protocol_type,
       count(*) FILTER (WHERE prediction = 'attack') AS attacks,
       count(*) FILTER (WHERE prediction = 'normal') AS normal
FROM predictions
GROUP BY protocol_type
ORDER BY protocol_type;
```

```text
 protocol_type | attacks | normal
---------------+---------+-------
 icmp          |      27 |      9
 tcp           |     164 |    226
 udp           |      21 |     53
```

Большинство запросов использовали TCP, а среди ICMP-запросов предсказаний атак было больше, чем нормальных.

**3. Запросы по часам за последние сутки**

```sql
SELECT date_trunc('hour', created_at) AS hour, count(*) AS requests
FROM predictions
WHERE created_at >= now() - interval '24 hours'
GROUP BY 1
ORDER BY 1;
```

```text
          hour          | requests
------------------------+---------
 2026-11-15 16:00:00+00 |      500
```

Все 500 запросов поступили в течение одного часа по времени UTC.

**4. Вероятность по классам**

```sql
SELECT prediction,
       round(avg(probability)::numeric, 4) AS avg_probability,
       round(min(probability)::numeric, 4) AS min_probability,
       round(max(probability)::numeric, 4) AS max_probability
FROM predictions
GROUP BY prediction
ORDER BY prediction;
```

```text
 prediction | avg_probability | min_probability | max_probability
------------+-----------------+-----------------+----------------
 attack     |          0.9579 |          0.5008 |          1.0000
 normal     |          0.1246 |          0.0407 |          0.4992
```

У ответов `attack` вероятность атаки в среднем 0,9579, у `normal` — 0,1246; это не оценка уверенности в классе normal.

**5. Пять сервисов с наибольшей долей атак**

```sql
SELECT service, count(*) AS requests,
       round(100.0 * count(*) FILTER (WHERE prediction = 'attack')
             / count(*), 2) AS attack_pct
FROM predictions
GROUP BY service
HAVING count(*) >= 10
ORDER BY attack_pct DESC, requests DESC, service
LIMIT 5;
```

```text
 service | requests | attack_pct
---------+----------+-----------
 telnet  |       35 |     97.14
 ftp     |       51 |     64.71
 ssh     |       57 |     54.39
 smtp    |       47 |     46.81
 other   |       65 |     46.15
```

У telnet самая высокая доля срабатываний среди сервисов как минимум с десятью запросами.

**6. Перцентили времени вычисления ответа**

```sql
SELECT round((percentile_cont(0.50) WITHIN GROUP
              (ORDER BY response_time_ms))::numeric, 3) AS p50_ms,
       round((percentile_cont(0.95) WITHIN GROUP
              (ORDER BY response_time_ms))::numeric, 3) AS p95_ms,
       round((percentile_cont(0.99) WITHIN GROUP
              (ORDER BY response_time_ms))::numeric, 3) AS p99_ms
FROM predictions;
```

```text
 p50_ms | p95_ms | p99_ms
--------+--------+-------
 16.050 | 18.561 | 18.768
```

Половина предсказаний была вычислена не дольше 16,050 мс, а 99 % — не дольше 18,768 мс; время записи в БД сюда не включено.

### Индекс по времени

Перед обоими измерениями выполнено `ANALYZE predictions`. Запрос и фиксированный порог не менялись:

```sql
EXPLAIN (ANALYZE, BUFFERS)
SELECT id, created_at, prediction
FROM predictions
WHERE created_at >= TIMESTAMPTZ '2026-11-15 16:43:50+00'
ORDER BY created_at;
```

До миграции `002_index_created_at.sql`:

```text
Sort  (cost=22.24..22.59 rows=140 width=23) (actual time=0.067..0.076 rows=140 loops=1)
  Sort Key: created_at
  Sort Method: quicksort  Memory: 31kB
  Buffers: shared hit=11
  ->  Seq Scan on predictions  (cost=0.00..17.25 rows=140 width=23) (actual time=0.022..0.043 rows=140 loops=1)
        Filter: (created_at >= '2026-11-15 16:43:50+00'::timestamp with time zone)
        Rows Removed by Filter: 360
        Buffers: shared hit=11
Planning:
  Buffers: shared hit=39
Planning Time: 0.172 ms
Execution Time: 0.105 ms
```

Индекс создан отдельной миграцией:

```console
$ docker exec -i nids-db psql -U nids -d nids -v ON_ERROR_STOP=1 < migrations/002_index_created_at.sql
CREATE INDEX
```

После миграции и повторного `ANALYZE predictions`:

```text
Index Scan using predictions_created_at_idx on predictions  (cost=0.27..17.72 rows=140 width=23) (actual time=0.022..0.053 rows=140 loops=1)
  Index Cond: (created_at >= '2026-11-15 16:43:50+00'::timestamp with time zone)
  Buffers: shared hit=4 read=3
Planning:
  Buffers: shared hit=27 read=1
Planning Time: 0.199 ms
Execution Time: 0.098 ms
```

План сменился с полного просмотра 500 строк и сортировки на чтение по индексу. Разница `0.105 → 0.098 мс` слишком мала для вывода о стабильном ускорении: на таблице такого размера оба варианта быстры, а время зависит от кэша и фона. Если индекс не выбирается, планировщик может обоснованно предпочесть `Seq Scan` из-за размера таблицы, низкой избирательности фильтра и стоимости переходов между индексом и строками.

## Ответы на контрольные вопросы

1. `WHERE` отбирает отдельные строки до группировки, `HAVING` — группы после неё. Например, `SELECT service FROM predictions GROUP BY service HAVING count(*) >= 10` нельзя написать с тем же условием в `WHERE`.
2. Именованный том привязывает данные к устойчивому имени вне контейнера. Без явного подключения прежнего тома новый контейнер получает пустую БД; анонимный том старого контейнера может при этом оставаться на диске.
3. Переменная окружения позволяет менять адрес и учётные данные между средами без правки и публикации исходного кода.
4. Версия модели связывает каждое решение с конкретным артефактом. Без неё изменения доли срабатываний или вероятностей после переобучения нельзя надёжно разделить по версиям.
5. `EXPLAIN ANALYZE` показывает выбранный план и фактические затраты исполнения. `Seq Scan` читает таблицу последовательно; `Index Scan` ищет подходящие ключи через индекс и затем получает строки таблицы.
6. Индекс занимает место и замедляет вставку; для маленькой таблицы или фильтра, выбирающего большую часть строк, последовательное чтение бывает дешевле.
7. Журнал хранит решения модели, а не истинные метки. Для точности нужны проверенные метки тех же соединений и их однозначное сопоставление с записями журнала.
8. Миграция хранится в Git, повторяемо применяется в другой среде и показывает историю схемы; ручной `ALTER TABLE` в консоли без фиксации этого не обеспечивает.

## Возникшие затруднения и их устранение

- Песочница не давала доступ к Docker и локальному сетевому порту; команды установки пакета, запуска сервиса и эксперимента выполнены с разрешённым доступом.
- Порт `localhost:5432` уже слушал системный PostgreSQL. Первые 500 HTTP-запросов вернули предсказания, но журнал остался пустым; лог показал `role "nids" does not exist`. После проверки `lsof` контейнер пересоздан с прежним именованным томом на порту `5433`, и повторная нагрузка записала ровно 500 строк.
- При остановке БД запись вызвала `psycopg.OperationalError`. Обработка ошибки в `/predict` сохранила HTTP 200, а лог оставил причину отказа.
