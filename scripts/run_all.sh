#!/usr/bin/env bash
# Полный конвейер анализа референса (Фазы 1–3, 6). ~4 мин на 4 ядрах.
# Зависимости: ffmpeg; pip install sherpa-onnx librosa soundfile opencv-python-headless scipy pyyaml matplotlib fonttools
set -euo pipefail
cd "$(dirname "$0")/.."
python3 scripts/cuts.py                 # склейки, движение, события -> analysis/{cuts,shots,motion,events,scene_scores}.csv
python3 scripts/transcribe.py > /dev/null   # GigaAM -> analysis/transcript.{json,srt,txt}
python3 scripts/audio.py                # онсеты, полосы -> analysis/{onsets,bands}.csv
python3 scripts/zoom_track.py           # цифровой зум -> analysis/zoom.csv
python3 scripts/fit_easing.py > /dev/null   # кривые наездов -> analysis/easing_zoom.csv
rm -f analysis/sheets/overview_*.jpg analysis/sheets/cuts_*.jpg
scripts/sheets.sh 0 121.5 1 overview 4 3 480 > /dev/null
scripts/cut_sheet.sh > /dev/null
python3 scripts/rhythm_stats.py > analysis/rhythm_stats.txt
python3 scripts/decide.py > /dev/null   # черновой план по правилам -> analysis/backtest.csv
python3 scripts/backtest.py | tee analysis/backtest_report.txt | sed -n 1,8p
python3 scripts/config_to_yaml.py
du -sh analysis
