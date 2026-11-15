# Лабораторная работа №2

## Цель

Разобраться с путями, правами доступа, переменными окружения и потоками командной оболочки. Проверить, какие части проекта можно запустить в текущем окружении.

## Ход работы

### 1. Ориентирование

Команды для проекта выполнялись в терминале macOS. Опыт с виртуальной машиной проводился отдельно; его описание восстановлено по памяти. Текущий каталог проекта:

```text
$ pwd
/Users/mihailkalinin/учеба/pgtu/3/info_systems_with_ai/project
$ cd ..; pwd; cd project; pwd
/Users/mihailkalinin/учеба/pgtu/3/info_systems_with_ai
/Users/mihailkalinin/учеба/pgtu/3/info_systems_with_ai/project
```

`ls -la` показал в том числе скрытые файлы и права доступа:

```text
$ ls -la
total 72
drwxr-xr-x@ 17 mihailkalinin  staff   544 Nov 14 08:08 .
drwxr-xr-x   5 mihailkalinin  staff   160 Oct 19 13:59 ..
-rw-r--r--@  1 mihailkalinin  staff  6148 Oct 20 17:19 .DS_Store
-rw-r--r--@  1 mihailkalinin  staff    19 Nov  7 07:34 .env
drwxr-xr-x@ 16 mihailkalinin  staff   512 Nov 14 08:24 .git
-rw-r--r--@  1 mihailkalinin  staff   541 Nov  7 07:26 .gitignore
-rw-r--r--@  1 mihailkalinin  staff     5 Sep 20 00:16 .python-version
-rw-r--r--@  1 mihailkalinin  staff   222 Nov  7 07:26 AUTHOR.md
-rw-r--r--@  1 mihailkalinin  staff  3674 Nov 14 08:08 README.md
drwxr-xr-x@  3 mihailkalinin  staff    96 Nov  7 07:34 __pycache__
drwxr-xr-x@  3 mihailkalinin  staff    96 Sep 20 00:39 artifacts
drwxr-xr-x@  4 mihailkalinin  staff   128 Sep 20 00:39 data
-rw-r--r--@  1 mihailkalinin  staff   128 Nov  7 07:34 model.pkl
-rw-r--r--@  1 mihailkalinin  staff   768 Sep 20 00:14 pyproject.toml
drwxr-xr-x@  3 mihailkalinin  staff    96 Sep 20 00:39 src
drwxr-xr-x   8 mihailkalinin  staff   256 Oct 19 06:42 tasks
drwxr-xr-x@  5 mihailkalinin  staff   160 Sep 20 00:19 tests
```

Дерево проекта до создания новых файлов:

```text
$ tree -L 2
.
├── AUTHOR.md
├── README.md
├── __pycache__
│   └── example.py
├── artifacts
├── data
│   ├── README.md
│   └── make_dataset.py
├── model.pkl
├── pyproject.toml
├── src
│   └── nids
├── tasks
│   ├── lab01.pdf
│   ├── lab02.pdf
│   ├── lab03.pdf
│   ├── lab04.pdf
│   ├── lab05.pdf
│   └── lab06.pdf
└── tests
    ├── conftest.py
    ├── test_api.py
    └── test_features.py

8 directories, 16 files
```

Для сравнения путей использовался временный каталог `/private/tmp/lab02.yh2ZXg`:

```text
$ mkdir -p /tmp/example
$ mkdir -p tmp/example
$ mkdir -p ~/tmp/example
$ mkdir -p ../tmp/example
$ realpath /tmp/example
/private/tmp/example
$ realpath tmp/example
/private/tmp/lab02.yh2ZXg/tmp/example
$ realpath ~/tmp/example
/Users/mihailkalinin/tmp/example
$ realpath ../tmp/example
/private/tmp/tmp/example
```

`/tmp/example` — абсолютный путь, `tmp/example` отсчитывается от текущего каталога, `~/tmp/example` — от домашнего каталога, а `../tmp/example` — от родительского. В macOS `/tmp` указывает на `/private/tmp`.

В задании PDF команда для подсчёта файлов напечатана с ошибками в кавычках и конвейере. Рабочий вариант:

```text
$ find . -type f -name '*.py' | wc -l
      10
```

`find .` обходит текущий каталог, `-type f` оставляет только файлы, `-name '*.py'` отбирает имена с расширением `.py`, `|` передаёт найденные пути в `wc -l`, который считает строки.
Подсчёт сделан до создания `.venv`; после этого команда также захватывает файлы Python внутри виртуального окружения.

### 2. Права доступа

Проверка проводилась на временном файле:

```text
$ touch example.txt
$ ls -l example.txt
-rw-r--r--@ 1 mihailkalinin  wheel  0 Nov 14 08:26 example.txt
$ chmod 640 example.txt
$ ls -l example.txt
-rw-r-----@ 1 mihailkalinin  wheel  0 Nov 14 08:26 example.txt
$ chmod 000 example.txt
$ echo abc > example.txt
zsh:1: permission denied: example.txt
$ sudo echo abc > example.txt
zsh:1: permission denied: example.txt
```

Права `640` означают чтение и запись для владельца, чтение для группы, отсутствие прав для остальных. При `000` файл закрыт для обычной записи. В команде с `sudo` перенаправление `>` выполняет текущая оболочка до запуска `sudo`, поэтому результат тот же.

Для перенаправления с правами администратора оболочку можно запустить внутри `sudo`:

```bash
sudo sh -c 'echo abc > example.txt'
```

Проверка этой команды закончилась сообщением `sudo: a password is required`; запись не выполнялась. Права временного файла после опыта возвращены к `640`.

### 3. Переменные окружения

```text
$ echo PATH
PATH
$ echo $PATH
/Users/mihailkalinin/.codex/packages/app-server-daemon/releases/0.169.0-aarch64-apple-darwin/codex-path:/opt/homebrew/opt/node@22/bin:/Users/mihailkalinin/.local/bin:/Library/Frameworks/Python.framework/Versions/3.14/bin:...
$ which python3
/Library/Frameworks/Python.framework/Versions/3.14/bin/python3
$ python3 -m venv .venv
$ source .venv/bin/activate
$ which python3
/Users/mihailkalinin/учеба/pgtu/3/info_systems_with_ai/project/.venv/bin/python3
$ echo ${PATH%%:*}
/Users/mihailkalinin/учеба/pgtu/3/info_systems_with_ai/project/.venv/bin
```

В строке `PATH` выше показано начало длинного значения. `echo PATH` печатает буквальное слово, а `$PATH` подставляет значение переменной. Активация окружения ставит `.venv/bin` в начало `PATH`, поэтому первой находится другая команда `python3`. Создание `.venv` не устанавливало зависимости проекта.

Переменная для одной команды:

```text
$ TEMP_FLAG=lab02 zsh -c 'printf "во время: %s\n" "$TEMP_FLAG"'
во время: lab02
$ printf 'после: %s\n' "${TEMP_FLAG-не задана}"
после: не задана
```

### 4. Потоки и конвейеры

Генератор использовал уже имеющиеся библиотеки Python:

```text
$ python3 data/make_dataset.py
записано: /Users/mihailkalinin/учеба/pgtu/3/info_systems_with_ai/project/data/connections.csv (1.3 МБ)
строк: 20000, доля атак: 48.0%
$ head -3 data/connections.csv
duration,protocol_type,service,flag,src_bytes,dst_bytes,count,srv_count,serror_rate,rerror_rate,same_srv_rate,diff_srv_rate,dst_host_count,dst_host_srv_count,label
15.7,tcp,telnet,RSTO,702,387,7,1,0.028,0.0,0.982,0.169,12,34,attack
0.0,tcp,http,S0,33,0,465,335,0.992,0.237,0.877,0.006,216,243,attack
$ wc -l data/connections.csv
   20001 data/connections.csv
$ cut -d, -f15 data/connections.csv | sort | uniq -c
9600 attack
   1 label
10400 normal
```

`head` показал заголовок и две записи. `wc -l` посчитал 20 001 строку вместе с заголовком. В последнем конвейере `cut` выделил 15-й столбец, `sort` сгруппировал одинаковые значения, а `uniq -c` подсчитал их. Строка `1 label` — заголовок.

Подсчёт `udp` и пяти самых частых значений `service`:

```text
$ cut -d, -f2 data/connections.csv | grep -c '^udp$'
2593
$ cut -d, -f3 data/connections.csv | tail -n +2 | sort | uniq -c | sort -rn | head -5
7551 http
2553 other
2267 dns
2251 ssh
2003 ftp
```

`>` перезаписывает файл, а `>>` дописывает в конец:

```text
$ echo первая > output.txt
$ echo вторая >> output.txt
$ cat output.txt
первая
вторая
```

Ошибка была отправлена в файл, на экран команда ничего не вывела:

```text
$ does_not_exist 2> error.txt
$ cat error.txt
zsh:1: command not found: does_not_exist
```

### 5. Скрипт

Создан `scripts/stats.sh`, затем выполнено `chmod +x scripts/stats.sh`. Проверки:

```text
$ scripts/stats.sh; echo "код: $?"
Использование: scripts/stats.sh <путь к CSV-файлу>
код: 1
$ scripts/stats.sh data/connections.csv; echo "код: $?"
Число строк:    20001
Распределение классов:
9600 attack
10400 normal
код: 0
$ scripts/stats.sh no-such-file.csv; echo "код: $?"
Использование: scripts/stats.sh <путь к CSV-файлу>
код: 1
```

### 6. Виртуальная машина и снэпшоты

Опыт выполнялся в другом окружении с VirtualBox. После установки и обновления Ubuntu Server был создан снэпшот `clean`. Затем права на `/usr/bin/apt` были изменены на `000`: `apt` перестал запускаться. После возврата к `clean` работа `apt` восстановилась.

Промежуточный вывод терминала и скриншоты дерева снэпшотов не сохранились. Точный текст ошибки и размер снэпшота сейчас указать нельзя без повторной проверки. По самому снэпшоту трудно понять состав установленных пакетов: это большой двоичный файл, который неудобно сравнивать с другой версией и передавать коллеге вместо текстового описания настройки.

### 7. Проект в текущем окружении

Сначала генерация и обучение были выполнены с библиотеками, уже доступными в системном `python3`:

```text
$ PYTHONPATH=src python3 -m nids.train
модель:   artifacts/model.joblib
паспорт:  artifacts/metadata.json
  accuracy   0.92
  precision  0.984
  recall     0.8471
  f1         0.9104
```

Затем в созданное ранее `.venv` установлены зависимости проекта, и модель переобучена в том же окружении, в котором запускаются тесты и сервис:

```text
$ .venv/bin/python -m pip install -e '.[dev]'
$ .venv/bin/python -m nids.train
модель:   artifacts/model.joblib
паспорт:  artifacts/metadata.json
  accuracy   0.92
  precision  0.984
  recall     0.8471
  f1         0.9104
```

Команда установки завершилась с кодом `0`.

В `artifacts/metadata.json` записаны `n_samples: 20000`, `n_train: 15000`, `n_test: 5000`, `attack_share: 0.48`, `seed: 42` и метрики выше. В README приведены округлённые `accuracy 0,92`, `precision 0,98`, `recall 0,85`; результаты совпадают после округления. Генератор использует фиксированный `seed`, а разделение выборки и модель — фиксированный `random_state`. Поэтому при одинаковых данных и версиях библиотек результат воспроизводится, а не определяется новым случайным выбором при каждом запуске.

После переобучения проверены тесты:

```text
$ .venv/bin/python -m pytest -q
..........                                                               [100%]
10 passed, 1 warning in 0.67s
```

Единственное предупреждение относится к использованию `httpx` внутри `starlette.testclient`; на результат тестов оно не повлияло.

Сервис запущен на `127.0.0.1:8000` и проверен из другого терминала:

```text
$ .venv/bin/uvicorn nids.api:app --app-dir src --host 127.0.0.1 --port 8000
INFO:     Application startup complete.
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
$ curl -sS --fail 127.0.0.1:8000/health
{"status":"ok","model_loaded":true,"model_version":"0.1.0"}
```

После проверки сервер остановлен.

Без дополнительных пакетов отдельно проверены функции подготовки данных и сохранённая модель: два вызова генератора с одним `seed` дали одинаковые таблицы, порядок признаков совпал с `ALL_FEATURES`, отсутствие обязательного столбца вызвало `ValueError`, а загруженная модель выполнила предсказание. Результат проверки:

```text
OK: генерация, признаки, проверка колонок и предсказание сохранённой модели
```

## Ответы на контрольные вопросы

1. Абсолютный путь начинается от `/`, относительный — от текущего каталога. Например, `mkdir -p /tmp/example` и `mkdir -p tmp/example` создали каталоги в разных местах; замена первого пути вторым изменила бы результат.
2. `640` означает `rw-` владельцу, `r--` группе и `---` всем остальным.
3. В `sudo echo abc > file` команда `echo` могла бы запускаться от администратора, но файл открывает текущая оболочка пользователя. Её права `sudo` не меняет.
4. `PATH` содержит каталоги поиска команд через двоеточие. При совпадении имён запускается первая найденная программа, поэтому порядок каталогов важен.
5. Активация `.venv` меняет `PATH`: каталог `.venv/bin` оказывается первым. После этого `python3` находится именно там.
6. `>` создаёт или перезаписывает файл, `>>` дописывает. `2>` перенаправляет сообщения об ошибках (`stderr`), а `>` — обычный вывод (`stdout`).
7. В WSL2 путь `/mnt/c` ведёт к файловой системе Windows через слой доступа из Linux. Операции с файлами, особенно многочисленные мелкие операции с метаданными, обычно медленнее, чем в Linux-файловой системе домашнего каталога. На этом Mac сравнение не измерялось.
8. Снэпшот фиксирует состояние виртуальной машины для возврата к нему. Для коллеги он неудобен как инструкция по настройке: двоичный слепок большой и непрозрачный; лучше перечислять шаги установки и настройки текстом.