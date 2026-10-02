#!/usr/bin/env bash
# Пары кадров «до | после» для каждой склейки из analysis/cuts.csv (проверка детектора).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
FONT=/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf
SEL=$(tail -n +2 "$ROOT/analysis/cuts.csv" | awk -F, '{printf "eq(n\\,%d)+eq(n\\,%d)+", $2-1, $2}' | sed 's/+$//')
mkdir -p "$ROOT/analysis/sheets"
ffmpeg -v error -y -i "$ROOT/reference/ref01.mp4" -an \
  -vf "select='${SEL}',scale=400:225,drawtext=fontfile=${FONT}:text='f%{n} %{e\:t}':x=4:y=4:fontsize=20:fontcolor=yellow:box=1:boxcolor=black@0.7,tile=4x4:padding=4:color=white" \
  -vsync vfr -q:v 4 "$ROOT/analysis/sheets/cuts_%02d.jpg"
ls "$ROOT"/analysis/sheets/cuts_*.jpg
