#!/usr/bin/env bash
# Фаза 1 целиком: склейки/движение, транскрипт, звук, контакт-листы.
# Зависимости: pip install sherpa-onnx librosa soundfile; ffmpeg.
set -euo pipefail
cd "$(dirname "$0")/.."
python3 scripts/cuts.py
python3 scripts/transcribe.py > /dev/null
python3 scripts/audio.py
rm -f analysis/sheets/*.jpg
scripts/sheets.sh 0 121.5 1 overview 4 3 480 > /dev/null
scripts/cut_sheet.sh > /dev/null
du -sh analysis
