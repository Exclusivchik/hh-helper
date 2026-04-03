#!/usr/bin/env bash

set -u

SCRIPT_PATH="02_enrich_vacancies.py"
PYTHON_BIN="../.venv/bin/python"
LOG_FILE="enrich_loop.log"

while true; do
    echo "========================================" | tee -a "$LOG_FILE"
    echo "Запуск: $(date '+%Y-%m-%d %H:%M:%S')" | tee -a "$LOG_FILE"

    "$PYTHON_BIN" "$SCRIPT_PATH" 2>&1 | tee -a "$LOG_FILE"
    EXIT_CODE=${PIPESTATUS[0]}

    echo "Код завершения: $EXIT_CODE" | tee -a "$LOG_FILE"
    echo "Жду 5 секунд..." | tee -a "$LOG_FILE"
    sleep 5
done