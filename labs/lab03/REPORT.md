# Лабораторная работа № 3. Контейнеризация сервиса

## Цель

Собрать самодостаточный Docker-образ сервиса детектирования аномалий и проверить его работу без установленного на машине Python. Уменьшить контекст и размер образа, ускорить пересборку и запускать приложение без прав `root`.

## Ход работы

### Подготовка и первый образ

```text
$ docker --version
Docker version 29.7.2, build a7dcaa6
$ docker run --rm hello-world
Hello from Docker!
```

Первый вариант `Dockerfile` использовал `python:3.12-slim`, рабочий каталог `/app`, устанавливал зависимости после `COPY . .`, генерировал данные и обучал модель при сборке. `uvicorn` слушал `0.0.0.0:8000`.

```text
$ /usr/bin/time -p docker build --progress=plain -t nids-service:v1 .
#5 transferring context: 352.41MB 4.4s done
...
записано: /app/data/connections.csv (1.3 МБ)
строк: 20000, доля атак: 48.0%
модель:   artifacts/model.joblib
...
real 105.22
$ docker images nids-service:v1
nids-service   v1   ...   915MB
```

```text
$ docker run -d --rm --name nids-lab03-v1 -p 127.0.0.1:8000:8000 nids-service:v1
$ curl -s localhost:8000/health
{"status":"ok","model_loaded":true,"model_version":"0.1.0"}
```

Через `http://127.0.0.1:8000/docs` выполнен `POST /predict` с примером нормального соединения. Веб-интерфейс показал ответ `200`:

```json
{"prediction":"normal","probability":0.0827,"model_version":"0.1.0"}
```

### Контекст сборки и кэш слоёв

В `.dockerignore` исключены `.git`, `.venv`, `__pycache__`, `data/*.csv`, `artifacts`, `.env` и другие файлы, не требующиеся при сборке. В текущем BuildKit объём переданного контекста выводится как `transferring context`.

| Контекст | Объём по выводу Docker |
| --- | ---: |
| До `.dockerignore` | 352,41 МБ |
| После `.dockerignore` | 5,02 КБ |

После изменения строки описания в `src/nids/api.py` пересборка с исходным порядком инструкций заново выполнила `pip install`:

```text
$ /usr/bin/time -p docker build --progress=plain -t nids-service:v1 .
#5 transferring context: 5.02kB 0.4s done
...
real 73.47
```

Затем установка зависимостей была перенесена после `COPY pyproject.toml .`, а копирование исходников — после неё. После прогрева нового слоя зависимостей ещё одно изменение описания и пересборка дали:

```text
$ /usr/bin/time -p docker build --progress=plain -t nids-service:v1 .
#6 CACHED
#7 CACHED
#8 CACHED
...
real 5.81
```

| Замер | Время |
| --- | ---: |
| Первая сборка | 105,22 с |
| Пересборка после правки кода до оптимизации | 73,47 с |
| Пересборка после правки кода с оптимизацией | 5,81 с |

Использовано свойство кэша: изменение исходников инвалидирует слой их копирования и следующие слои, но не предшествующий слой установки зависимостей. Если `.env` с паролем скопировать в образ, а следующей инструкцией удалить, пароль останется в прежнем слое и его можно будет извлечь. Поэтому файл исключён из контекста до сборки.

### Многоступенчатый образ

Итоговый `Dockerfile` использует две стадии на `python:3.12-slim`. Первая устанавливает зависимости в `/opt/venv`, генерирует CSV и обучает модель. В финальную стадию копируются только окружение Python, исходники сервиса и артефакты модели; CSV и файлы, нужные только при сборке, в неё не переходят.

```text
$ docker build -t nids-service:v2 .
... naming to docker.io/library/nids-service:v2 done
$ docker images nids-service
nids-service   v1   ...   649MB
nids-service   v2   ...   564MB
```

Здесь размер `v1` приведён после настройки `.dockerignore` и кэша. Он на 85 МБ больше `v2`. Самый тяжёлый слой финального образа — виртуальное окружение с библиотеками для машинного обучения:

```text
$ docker history nids-service:v2
...  8.33MB  COPY /app/artifacts ./artifacts
...  46kB   COPY /app/src ./src
...  411MB   COPY /opt/venv /opt/venv
```

### Пользователь и модель через том

До добавления `USER` промежуточный вариант работал от `root`; итоговый образ запускается от непривилегированного пользователя:

```text
$ docker run --rm nids-service:v2-root whoami
root
$ docker run --rm nids-service:v2 whoami
app
```

Сервис продолжает работать. Переменная `MODEL_DIR` позволяет подменить модель через том только для чтения:

```text
$ docker run -d --rm --name nids-lab03-v2 -p 127.0.0.1:8000:8000 nids-service:v2
$ curl -s localhost:8000/health
{"status":"ok","model_loaded":true,"model_version":"0.1.0"}
$ docker stop nids-lab03-v2
$ docker run -d --rm --name nids-lab03-volume -p 127.0.0.1:8000:8000 -v "$(pwd)/artifacts:/models:ro" -e MODEL_DIR=/models nids-service:v2
$ curl -s localhost:8000/health
{"status":"ok","model_loaded":true,"model_version":"0.1.0"}
$ curl -s -X POST localhost:8000/predict -H 'Content-Type: application/json' --data '{"protocol_type":"tcp","service":"other","flag":"S0","duration":0,"src_bytes":0,"dst_bytes":0,"count":480,"srv_count":470,"serror_rate":1,"rerror_rate":0.05,"same_srv_rate":1,"diff_srv_rate":0,"dst_host_count":255,"dst_host_srv_count":255}'
{"prediction":"attack","probability":1.0,"model_version":"0.1.0"}
```

Модель в образе делает запуск самодостаточным и связывает версию сервиса с версией модели, но обновление модели требует новой сборки. Модель в томе можно заменить без пересборки, но запуск зависит от доступности и совместимости внешнего файла.

### Проверка без локальных артефактов

Образ собран при отсутствии готовых `artifacts/model.joblib`, `data/connections.csv` и `.venv`. Генерация данных и обучение прошли внутри сборки. После запуска:

```text
$ docker build --no-cache -t nids-service:clean .
записано: /app/data/connections.csv (1.3 МБ)
модель:   artifacts/model.joblib
... naming to docker.io/library/nids-service:clean done
$ docker run -d --rm --name nids-lab03-clean -p 127.0.0.1:8000:8000 nids-service:clean
$ curl -s localhost:8000/health
{"status":"ok","model_loaded":true,"model_version":"0.1.0"}
$ curl -s -X POST localhost:8000/predict -H 'Content-Type: application/json' --data '{"protocol_type":"tcp","service":"other","flag":"S0","duration":0,"src_bytes":0,"dst_bytes":0,"count":480,"srv_count":470,"serror_rate":1,"rerror_rate":0.05,"same_srv_rate":1,"diff_srv_rate":0,"dst_host_count":255,"dst_host_srv_count":255}'
{"prediction":"attack","probability":1.0,"model_version":"0.1.0"}
```

## Ответы на контрольные вопросы

1. **Образ и контейнер.** Образ — неизменяемый набор слоёв; контейнер — его запущенный экземпляр с собственным записываемым слоем. После удаления контейнера записанные только в этот слой файлы исчезнут; данные в томе сохранятся.
2. **Скорость запуска.** Контейнер запускает процесс, используя уже работающий системный kernel. Виртуальной машине нужно запустить отдельную гостевую ОС; поэтому её старт обычно дольше.
3. **Контекст и `.dockerignore`.** Контекст — файлы, передаваемые Docker для сборки. `.dockerignore` уменьшает объём передачи и не допускает туда ненужные файлы и секреты.
4. **Порядок инструкций.** Docker повторно использует слой, пока инструкция и её входные данные не изменились. Часто меняющийся код располагают после редко меняющихся зависимостей, чтобы его правка не повторяла их установку.
5. **Удалённый секрет.** Он останется доступным в более раннем неизменяемом слое образа. Удаление создаёт новый слой и не переписывает старый.
6. **Многоступенчатая сборка.** Финальная стадия получает только нужные для запуска файлы, оставляя в сборочной стадии кэш, промежуточные данные и инструменты. За счёт этого образ меньше.
7. **Адрес прослушивания.** `127.0.0.1` внутри контейнера доступен только ему самому; `0.0.0.0` принимает подключения через опубликованный Docker-порт.
8. **`python:latest`.** Этот тег меняет версию Python и состав базового образа без изменения Dockerfile. Фиксированный тег, а для строгой повторяемости digest, делают сборку предсказуемее.

## Возникшие затруднения и способы их устранения

Первая попытка `docker run --rm hello-world` завершилась ошибкой подключения к `docker.sock`: Docker daemon ещё не работал. После запуска Docker Desktop та же команда успешно вывела `Hello from Docker!`, и сборки стали доступны.
