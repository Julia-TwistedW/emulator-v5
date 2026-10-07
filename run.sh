#!/bin/bash
set -e
VFS_PATH="${1:-data/vfs.json}"
SCRIPT_PATH="${2:-data/startup.txt}"
echo "=== Запуск эмулятора оболочки ОС ==="
python3 scr/emulator-v5.py -vfs "$VFS_PATH" -script "SCRIPT_PATH"
