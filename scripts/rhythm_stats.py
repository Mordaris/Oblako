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

from refcfg import EVENTS, FPS, OUT

ROOT = Path(__file__).resolve().parent.parent
DUR = float(__import__("subprocess").run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0",
                                           str(__import__("refcfg").SRC)], capture_output=True, text=True).stdout)
ev = list(csv.DictReader(open(EVENTS, encoding="utf-8")))
tr = json.loads((OUT / "transcript.json").read_text(encoding="utf-8"))
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
for a in range(0, int(DUR) + 1, 10):
    n = sum(1 for t in vis if a <= t < a + 10)
    print(f"  {a:3d}-{a + 10:3d} с: {n} событий")

# 3. спикер vs сцены: сцены = интервалы между входом и выходом из графики
scenes = sorted((float(e["t"]), float(e["t_end"])) for e in ev if e.get("t_end"))   # сцены = строки с t_end
gfx = sum(b - a for a, b in scenes)
print(f"\nГрафические сцены: {len(scenes)} шт, {gfx:.1f} с ({gfx / DUR * 100:.0f}%), "
      f"длительность {min(b - a for a, b in scenes):.2f}–{max(b - a for a, b in scenes):.2f} с, "
      f"медиана {np.median([b - a for a, b in scenes]):.2f} с")
spk = [(0, scenes[0][0])] + [(scenes[i][1], scenes[i + 1][0]) for i in range(len(scenes) - 1)] + [(scenes[-1][1], DUR)]
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
shots = list(csv.DictReader(open(OUT / "shots.csv")))
for a, b in [(x, x + 30) for x in range(0, int(DUR) + 1, 30)]:
    d = [float(s["dur_s"]) for s in shots if a <= float(s["start"]) < b]
    print(f"ASL {a}-{b} с: {np.mean(d):.2f} с (планов {len(d)})")
