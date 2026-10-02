"""Универсальный черновик edit plan: только законы, подтверждённые на ДВУХ референсах (kb/04-editing-grammar.md).

Отличие от decide.py (лексика ref01): правила не зависят от темы и стиля, выдают СЕМЬЮ события
(transition / camera / overlay / scene), а конкретный приём выбирает профиль стиля.
Используется как каркас ритма «когда что-то происходит». Смысловую разметку делает агент.

Запуск: REF=ref02 python3 scripts/decide_universal.py [transcript.json] [out.csv]
"""
import csv
import json
import re
import sys
from pathlib import Path

from refcfg import OUT

F = 1 / 30
CONTRAST = {"но", "однако"}
BLOCK = {"поэтому", "итак", "поехали"}
NUM = re.compile(r"^(\d+|ноль|один|одна|два|две|три|четыре|пять|шесть|семь|восемь|девять|десять|"
                 r"\w*надцать|двадцать|тридцать|сорок|пятьдесят|шестьдесят|семьдесят|восемьдесят|девяносто|"
                 r"сто|сотн\w*|тысяч\w*|миллион\w*|миллиард\w*|процент\w*|половин\w*)$")
SOURCE = re.compile(r"^(исследовани\w*|отчет\w*|отчёт\w*|институт\w*|статистик\w*|данны[мх])$")
QUOTE_LEAD = {"мол", "мыслью", "пишут", "спрашивают"}
ASK = {"куда", "почему", "зачем", "сколько"}
STOP = set("и в во не на но а что это как по к с у о от до из за же ли бы то так все уже я ты мы вы они он она "
           "мне нас вас их его ее её там вот да".split())


def plan(ws):
    ev, n = [], len(ws)
    last = {"camera": -9.0, "transition": -9.0, "overlay": -9.0, "any": 0.0}
    punch = False

    def add(t, fam, tech, i, fn):
        ev.append({"t": round(max(t, 0), 3), "technique": tech, "word": ws[i]["w"], "function": fn, "note": fam})
        last[fam] = t; last["any"] = t

    for i, x in enumerate(ws):
        w, t = x["w"], x["t"]
        prev = ws[i - 1]["w"] if i else ""
        nxt = ws[i + 1]["w"] if i + 1 < n else ""
        # 1. Граница блока — световой переход
        if (w in BLOCK or (w == "а" and nxt == "теперь")) and t - last["transition"] > 2.3:
            add(t - 2 * F, "transition", "TR_FLASH", i, "block_end"); punch = False; continue
        # 2. Противопоставление в начале фразы — смена крупности склейкой
        if w in CONTRAST and nxt != "и" and t - last["camera"] > 1.5:
            add(t - 2 * F, "camera", "CUT_PUNCH_OUT" if punch else "CUT_PUNCH_IN", i, "contrast")
            punch = not punch; continue
        # 3. Числа и доли — оверлей-число (первое числительное группы)
        if NUM.match(w) and not NUM.match(prev) and t - last["overlay"] > 1.0:
            add(t, "overlay", "STAT_STICKER", i, "statistic"); continue
        # 4. Ссылка на источник — показать источник
        if SOURCE.match(w) and t - last["overlay"] > 2.0:
            add(t - 0.4, "overlay", "PIP_IMAGE", i, "source"); continue
        # 5. Прямая речь / мысль — отдельный регистр (тёмный фон, слова по центру)
        if w in QUOTE_LEAD and i + 1 < n:
            add(ws[i + 1]["t"] - 2 * F, "transition", "TR_XSTAMP", i + 1, "enter_quote"); continue
        # 6. Вопрос к зрителю (вопросительное слово в начале фразы) — акцент камерой
        if w in ASK and t - last["camera"] > 3.0 and t - last["any"] > 1.0:
            add(t - 0.2, "camera", "ZOOM_PUSH", i, "question"); continue
        # 7. Статика > 5,3 с — смена крупности на начале ближайшего значимого слова
        if t - last["any"] > 5.3 and w not in STOP:
            add(t - 2 * F, "camera", "CUT_PUNCH_OUT" if punch else "CUT_PUNCH_IN", i, "rhythm")
            punch = not punch
    return ev


def main():
    src = Path(sys.argv[1]) if len(sys.argv) > 1 else OUT / "transcript.json"
    out = Path(sys.argv[2]) if len(sys.argv) > 2 else OUT / "backtest_universal.csv"
    tr = json.loads(src.read_text(encoding="utf-8"))
    ws = [{"w": w["w"].lower(), "t": w["start"]} for p in tr["phrases"] for w in p["words"]]
    ev = plan(ws)
    with open(out, "w", newline="", encoding="utf-8") as fh:
        wr = csv.DictWriter(fh, fieldnames=["t", "technique", "word", "function", "note"])
        wr.writeheader(); wr.writerows(ev)
    print(f"событий: {len(ev)} -> {out}")


if __name__ == "__main__":
    main()
