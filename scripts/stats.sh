#!/usr/bin/env bash

if [[ $# -lt 1 || ! -f $1 ]]; then
    echo "Использование: $0 <путь к CSV-файлу>" >&2
    exit 1
fi

echo "Число строк: $(wc -l < "$1")"
echo "Распределение классов:"
tail -n +2 "$1" | cut -d, -f15 | sort | uniq -c
