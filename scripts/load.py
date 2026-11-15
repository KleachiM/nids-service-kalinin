"""Отправить 500 случайных соединений на локальный /predict."""

import csv
import json
import random
from pathlib import Path
from urllib.request import Request, urlopen


def main() -> None:
    data_file = Path(__file__).resolve().parents[1] / "data/connections.csv"
    with data_file.open(newline="", encoding="utf-8") as file:
        rows = list(csv.DictReader(file))
    if not rows:
        raise ValueError(f"Нет строк в {data_file}")

    for row in random.Random(42).choices(rows, k=500):
        payload = {key: value for key, value in row.items() if key != "label"}
        request = Request(
            "http://localhost:8000/predict",
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"},
        )
        with urlopen(request, timeout=10) as response:
            if response.status != 200:
                raise RuntimeError(f"/predict вернул HTTP {response.status}")
    print("Отправлено 500 запросов на /predict")


if __name__ == "__main__":
    main()
