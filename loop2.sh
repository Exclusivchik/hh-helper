#!/usr/bin/env bash

set -u

SCRIPT_PATH="vacancy_parser_full.py"
PYTHON_BIN=".venv/bin/python"

while true; do
    echo "========================================"
    echo "Запуск: $(date '+%Y-%m-%d %H:%M:%S')"

    "$PYTHON_BIN" "$SCRIPT_PATH" 2>&1
    EXIT_CODE=${PIPESTATUS[0]}

    echo "Код завершения: $EXIT_CODE"
    echo "Жду 5 секунд..."
    sleep 5
done