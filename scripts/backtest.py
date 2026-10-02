"""Сравнение плана (analysis/backtest.csv) с эталоном (kb/ref01_events.csv).

Сопоставление жадное по времени, допуск ±0,5 с. Три уровня совпадения:
  ANY    — в эталоне в пределах допуска есть любое событие;
  FAMILY — совпала семья приёма (переход / камера / наложение / сцена);
  EXACT  — совпал приём.
Метрики: precision = совпавшие / предсказанные, recall = совпавшие / эталон.
Запуск: python3 scripts/backtest.py [pred.csv] [ref.csv]
"""
import csv
import sys
from pathlib import Path

from refcfg import EVENTS, OUT

ROOT = Path(__file__).resolve().parent.parent
TOL = 0.5
FAM = {
    "TR_RING": "transition", "TR_ZOOMBLUR": "transition", "TR_XSTAMP": "transition", "CUT_HARD": "transition",
    "TR_FLASH": "transition", "TR_WIPE": "transition", "TR_WHIP": "transition", "TR_DISSOLVE": "transition",
    "TR_PAPER": "transition", "TR_GLITCH": "transition", "TR_SILHOUETTE": "transition", "FADE_BLACK": "transition",
    "ZOOM_PUSH": "camera", "ZOOM_PULL": "camera", "CUT_PUNCH_IN": "camera", "CUT_PUNCH_OUT": "camera",
    "CUT_RAPID": "camera", "GRADE_BW": "camera",
    "TITLE_KINETIC": "overlay", "ICON_POP": "overlay", "ICON_DRAW": "overlay", "PIP_IMAGE": "overlay",
    "KEYWORD_CAPTION": "overlay", "TITLE_GIANT": "overlay", "SIDE_TITLES": "overlay", "STAT_STICKER": "overlay",
    "OBJECT_LABEL": "overlay", "EMOJI_STACK": "overlay", "INFOGRAPHIC": "overlay", "SPLIT_SOCIAL": "overlay",
    "TEXT_CENTER": "overlay", "SPOTLIGHT_ROW": "overlay", "SPLIT_UI": "overlay",
    "MUSIC_IN": "audio",
}
fam = lambda t: FAM.get(t, "scene")


def load(p):
    return [{"t": float(r["t"]), "tech": r["technique"], "word": r["word"]}
            for r in csv.DictReader(open(p, encoding="utf-8"))]


def match(pred, ref, key):
    used, hits, pairs = set(), 0, []
    for p in pred:
        cands = [(abs(r["t"] - p["t"]), k) for k, r in enumerate(ref)
                 if k not in used and abs(r["t"] - p["t"]) <= TOL and key(p, r)]
        if cands:
            d, k = min(cands)
            used.add(k); hits += 1; pairs.append((p, ref[k], d))
    return hits, used, pairs


def main():
    pred = load(sys.argv[1] if len(sys.argv) > 1 else OUT / "backtest.csv")
    ref = load(sys.argv[2] if len(sys.argv) > 2 else EVENTS)
    print(f"предсказано {len(pred)}, эталон {len(ref)}, допуск ±{TOL} с\n")
    print(f"{'уровень':8s} {'совп.':>5s} {'precision':>9s} {'recall':>7s} {'F1':>5s}")
    res = {}
    for name, key in (("ANY", lambda p, r: True), ("FAMILY", lambda p, r: fam(p["tech"]) == fam(r["tech"])),
                      ("EXACT", lambda p, r: p["tech"] == r["tech"])):
        h, used, pairs = match(pred, ref, key)
        pr, rc = h / len(pred), h / len(ref)
        f1 = 2 * pr * rc / (pr + rc) if pr + rc else 0
        res[name] = (used, pairs)
        print(f"{name:8s} {h:5d} {pr:9.2f} {rc:7.2f} {f1:5.2f}")
    used, pairs = res["EXACT"]
    if pairs:
        import statistics
        print(f"\nсреднее |Δt| точных совпадений: {statistics.mean(d for *_, d in pairs) * 1000:.0f} мс")
    print("\nПропущено (эталон без точного совпадения):")
    for k, r in enumerate(ref):
        if k not in used:
            print(f"  {r['t']:7.2f} {r['tech']:24s} {r['word']}")
    hit_pred = {id(p) for p, *_ in pairs}
    print("\nЛожные/неточные (предсказание без точного совпадения):")
    for p in pred:
        if id(p) not in hit_pred:
            print(f"  {p['t']:7.2f} {p['tech']:24s} {p['word']}")


if __name__ == "__main__":
    main()
