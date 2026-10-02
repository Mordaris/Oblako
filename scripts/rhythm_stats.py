"""Сводка ритма по эталонным событиям kb/ref01_events.csv + analysis/*.

Печатает:
  - частоту приёмов, интервалы между визуальными событиями (по 10-с сегментам),
  - доли времени спикер / графические сцены,
  - смещение «событие -> начало слова-триггера»,
  - ASL по сегментам 0–30 / 30–60 / 60–90 / 90–121 с.
Запуск: python3 scripts/rhythm_stats.py
"""
import collections
import csv
import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
FPS = 2997 / 100
DUR = 121.42
ev = list(csv.DictReader(open(ROOT / "kb" / "ref01_events.csv", encoding="utf-8")))
tr = json.loads((ROOT / "analysis" / "transcript.json").read_text(encoding="utf-8"))
words = [(w["w"], w["start"]) for p in tr["phrases"] for w in p["words"]]


def word_time(word, t):
    c = [ws for w, ws in words if w == word and abs(ws - t) < 1.5]
    return min(c, key=lambda x: abs(x - t)) if c else None


# 1. частота приёмов
cnt = collections.Counter(e["technique"] for e in ev)
print("Частота приёмов:")
for k, v in cnt.most_common():
    print(f"  {k:26s} {v}")

# 2. интервалы между визуальными событиями (MUSIC_IN не визуальное)
vis = sorted(float(e["t"]) for e in ev if e["technique"] != "MUSIC_IN")
gaps = np.diff([0.0] + vis + [DUR])
print(f"\nВизуальных событий {len(vis)}, средний интервал {np.mean(np.diff(vis)):.2f} с, "
      f"медиана {np.median(np.diff(vis)):.2f} с, макс. пауза без событий {gaps.max():.2f} с")
for a in range(0, 121, 10):
    n = sum(1 for t in vis if a <= t < a + 10)
    print(f"  {a:3d}-{a + 10:3d} с: {n} событий")

# 3. спикер vs сцены: сцены = интервалы между входом и выходом из графики
scenes = [(5.072, 11.111), (14.581, 17.818), (20.120, 22.69), (33.066, 39.840), (45.913, 49.983),
          (67.968, 73.674), (88.59, 96.20), (104.97, 113.146)]
gfx = sum(b - a for a, b in scenes)
print(f"\nГрафические сцены: {len(scenes)} шт, {gfx:.1f} с ({gfx / DUR * 100:.0f}%), "
      f"длительность {min(b - a for a, b in scenes):.2f}–{max(b - a for a, b in scenes):.2f} с, "
      f"медиана {np.median([b - a for a, b in scenes]):.2f} с")
spk = [(0, 5.072)] + [(scenes[i][1], scenes[i + 1][0]) for i in range(len(scenes) - 1)] + [(113.146, DUR)]
print(f"Спикер: {DUR - gfx:.1f} с; отрезки между сценами: " + ", ".join(f"{b - a:.1f}" for a, b in spk))

# 4. смещение событие -> слово
off = collections.defaultdict(list)
for e in ev:
    wt = word_time(e["word"], float(e["t"]))
    if wt is not None:
        off[e["technique"]].append(wt - float(e["t"]))
print("\nСмещение «начало слова − момент события», мс (медиана [мин; макс]):")
for k, v in off.items():
    v = np.array(v) * 1000
    print(f"  {k:26s} {np.median(v):+6.0f} [{v.min():+5.0f}; {v.max():+5.0f}]  n={len(v)}")

# 5. ASL по сегментам
shots = list(csv.DictReader(open(ROOT / "analysis" / "shots.csv")))
for a, b in ((0, 30), (30, 60), (60, 90), (90, 122)):
    d = [float(s["dur_s"]) for s in shots if a <= float(s["start"]) < b]
    print(f"ASL {a}-{b} с: {np.mean(d):.2f} с (планов {len(d)})")
