#!/usr/bin/env bash
# Контакт-лист: кадры референса в сетке COLSxROWS, на каждом тайле таймкод (с) и номер кадра.
# Использование: scripts/sheets.sh START END FPS NAME [COLS ROWS TILE_W]
#   scripts/sheets.sh 0 121.5 1 overview            # обзор 1 кадр/с
#   scripts/sheets.sh 2.0 2.6 29.97 cut01 4 4 480   # каждый кадр вокруг склейки
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SRC="$ROOT/reference/ref01.mp4"
START=$1; END=$2; RATE=$3; NAME=$4
COLS=${5:-4}; ROWS=${6:-3}; TW=${7:-480}
TH=$(( TW * 9 / 16 ))
FONT=/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf
OUT="$ROOT/analysis/sheets"
mkdir -p "$OUT"
# copyts сохраняет исходные pts, поэтому таймкод на тайле = время в референсе
ffmpeg -v error -y -copyts -ss "$START" -to "$END" -i "$SRC" -an \
  -vf "fps=${RATE}:start_time=${START},scale=${TW}:${TH},drawtext=fontfile=${FONT}:text='%{e\:t} f%{eif\:t*29.97+0.5\:d}':x=6:y=6:fontsize=$(( TH / 9 )):fontcolor=yellow:box=1:boxcolor=black@0.7,tile=${COLS}x${ROWS}:padding=4:color=white" \
  -q:v 4 "$OUT/${NAME}_%02d.jpg"
ls "$OUT"/"${NAME}"_*.jpg
