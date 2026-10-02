#!/usr/bin/env bash
# Пары кадров «до | после» для каждой склейки из analysis/cuts.csv (проверка детектора).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
REF="${REF:-ref01}"
if [ "$REF" = ref01 ]; then ADIR="$ROOT/analysis"; else ADIR="$ROOT/analysis/$REF"; fi
FPSV=$(ffprobe -v error -select_streams v:0 -show_entries stream=r_frame_rate -of csv=p=0 "$ROOT/reference/$REF.mp4" | awk -F/ '{printf "%.4f", $1/$2}')
FONT=/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf
SEL=$(tail -n +2 "$ADIR/cuts.csv" | awk -F, '{printf "eq(n\\,%d)+eq(n\\,%d)+", $2-1, $2}' | sed 's/+$//')
mkdir -p "$ADIR/sheets"
ffmpeg -v error -y -i "$ROOT/reference/$REF.mp4" -an \
  -vf "select='${SEL}',scale=400:225,drawtext=fontfile=${FONT}:text='f%{n} %{e\:t}':x=4:y=4:fontsize=20:fontcolor=yellow:box=1:boxcolor=black@0.7,tile=4x4:padding=4:color=white" \
  -vsync vfr -q:v 4 "$ADIR/sheets/cuts_%02d.jpg"
ls "$ADIR"/sheets/cuts_*.jpg
