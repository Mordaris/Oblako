"""Дерево решений kb/02-design-system.md §7 в виде лексических правил (без LLM).

Вход: транскрипт (пословный, без пунктуации) -> edit plan в формате kb/ref01_events.csv.
Назначение: (1) обратная проверка базы знаний на референсе (Фаза 6);
            (2) черновая авторазметка для агента — он уточняет её смысловым анализом.
Ограничение: правила видят только слова и время. Функции «термин», «сравнение», «рост» без
маркерных слов им недоступны — это зона смысловой разметки агентом (шаг 2 промпта).

Запуск: python3 scripts/decide.py [transcript.json] [out.csv]
        по умолчанию analysis/transcript.json -> analysis/backtest.csv
"""
import csv
import json
import sys
from pathlib import Path

from refcfg import OUT

ROOT = Path(__file__).resolve().parent.parent
F = 1 / 30
CFG = json.loads((ROOT / "kb" / "style.config.json").read_text(encoding="utf-8"))
PUSH_GAP = CFG["camera"]["push"]["min_gap_s"]            # 7.0
MAX_STATIC = CFG["camera"]["max_static_s"]               # 5.3

STOP = set("и в во не на но а что это как по к ко с со у о об от до из за же ли бы то так все уже еще ещё "
           "я ты он она мы вы они мне тебе тебя его ее её их мой моя твой твоя наш наша этот эта эти "
           "который которая которые где когда если или либо да нет вот там тут чтобы потому".split())
BRANDS = {"телеграм", "телеграмм", "макс", "вк", "вконтакте", "вотсап", "ватсап", "whatsapp", "инстаграм",
          "ютуб", "тикток", "фейсбук", "авито", "яндекс"}
QUANT = {"тысячи", "тысячам", "тысяч", "тысячу", "сотни", "сотней", "миллионы", "миллион", "миллионов", "несколько"}
NEG_PRON = {"некому", "нечего", "никому", "ничего", "никого", "негде", "некогда", "незачем"}
PROCESS = {"находит", "прогоняет", "отправляет", "смотрит", "читает", "следит", "анализирует", "проверяет",
           "фильтрует", "собирает", "присылает"}
CONNECT_BLOCK = {"поэтому", "итак"}
ADDRESS = {"понимаешь", "согласись", "смотри", "представь"}
ADJ_END = ("ая", "ый", "ий", "ой", "ое", "ие", "ые")


def load_words(path):
    tr = json.loads(Path(path).read_text(encoding="utf-8"))
    ws = []
    for p in tr["phrases"]:
        for w in p["words"]:
            ws.append({"w": w["w"].lower(), "t": w["start"], "end": w["end"]})
    return ws


def plan(ws):
    ev = []
    add = lambda t, tech, i, fn, note="": ev.append(
        {"t": round(max(t, 0), 3), "technique": tech, "word": ws[i]["w"], "function": fn, "note": note})
    n = len(ws)
    scene_until = -1.0           # конец текущей графической сцены
    bw = False
    last_push = -99.0
    last_event = 0.0
    pull_at = None               # запланированный отъезд после наезда
    PUSH_S = CFG["camera"]["push"]["frames"] * F

    def nxt(i, k=1):
        return ws[i + k]["w"] if i + k < n else ""

    # 0. Хук: первое содержательное слово после 0,5 с
    h = next(i for i, x in enumerate(ws) if x["t"] > 0.5 and x["w"] not in STOP and len(x["w"]) >= 5)
    add(ws[h]["t"] - 3 * F, "TITLE_KINETIC", h, "thesis_keyword")
    add(ws[h]["t"] - 0.2, "ZOOM_PUSH", h, "hook_emphasis")
    add(ws[h]["t"], "MUSIC_IN", h, "hook_emphasis")
    last_push = ws[h]["t"]
    # конец хука: слово после «ключевое + 2 слова»
    he = min(h + 3, n - 1)
    add(ws[he]["t"] - 2 * F, "TR_RING", he, "block_end")
    last_event = ws[he]["t"]

    # кластеры повторов «кто то … кто то …» (примеры) и «X чаты, чаты Y…» (категории)
    def repeats(i, token, window=8.0):
        return [j for j in range(i, n) if ws[j]["t"] - ws[i]["t"] <= window and ws[j]["w"] == token]

    i = he + 1
    while i < n:
        x = ws[i]; w = x["w"]; t = x["t"]
        in_scene = t < scene_until
        # отъезд после наезда: если до push_end + 1,2 с не было другого события (правило §2)
        if pull_at is not None:
            if last_event > pull_at - 1.2 - PUSH_S + 0.25:   # после наезда было другое событие -> отъезд не нужен
                pull_at = None
            if t >= pull_at:
                if not in_scene:
                    add(pull_at, "ZOOM_PULL", i, "release"); last_event = pull_at
                pull_at = None

        # 1. Связки смены блока
        if w in CONNECT_BLOCK and not in_scene:
            add(t - 2 * F, "TR_RING", i, "block_end"); last_event = t; i += 1; continue
        if w == "а" and nxt(i) == "теперь":
            add(t - 2 * F, "TR_RING", i + 1, "pivot_solution", "вариант B" if bw else "")
            bw = False; scene_until = -1; last_event = t; i += 2; continue
        if w == "давай" and nxt(i) in ("покажу", "посмотрим", "разберем", "разберём"):
            add(t - 2 * F, "TR_RING", i, "block_end"); last_event = t; i += 1; continue

        # 2. Демо
        if w == "вот" and nxt(i) == "перед":
            add(t - 2 * F, "TR_XSTAMP", i, "enter_demo"); add(t, "SPLIT_UI", i, "demo"); last_event = t
            i += 1; continue

        # 3. Критика: «но как по мне / на мой взгляд»
        if w == "но" and (nxt(i) == "как" and nxt(i, 2) == "по" or nxt(i) == "на" and nxt(i, 2) == "мой"):
            add(t - 1 * F, "GRADE_BW", i, "opinion_negative"); bw = True; last_event = t; i += 1; continue
        # 3а. Последствия внутри ч/б
        if bw and w == "потому" and nxt(i) == "что" and not in_scene:
            add(t - 2 * F, "TR_ZOOMBLUR", i, "enter_illustration")
            add(t + 0.4, "SCENE_GREY_CARDS", i + 2, "consequences")
            end = next((ws[j]["t"] for j in range(i, n) if ws[j]["w"] == "а" and j + 1 < n and ws[j + 1]["w"] == "теперь"), t + 8)
            scene_until = min(end, t + 8.2); last_event = t; i += 2; continue

        # 4. Прямая речь
        if w == "мол" and not in_scene:
            add(t - 2 * F, "TR_XSTAMP", i, "enter_quote"); add(t, "SCENE_DARK_QUOTE", i, "direct_speech")
            ex = next((j for j in range(i + 1, n) if ws[j]["w"] in ADDRESS and ws[j]["t"] - t < 8.2), None)
            if ex is not None:
                add(ws[ex]["t"] - 1 * F, "TR_ZOOMBLUR", ex, "address_viewer"); scene_until = ws[ex]["t"]
                last_event = ws[ex]["t"]; i = ex + 1; continue
            scene_until = t + 4; last_event = t; i += 1; continue

        # 5. Кластер глаголов процесса (≥3 за 6 с) -> сцена-талисман
        if w in PROCESS and not in_scene:
            cl = [j for j in range(i, n) if ws[j]["t"] - t <= 6 and ws[j]["w"] in PROCESS]
            if len(cl) >= 3:
                s0 = t - 1.2
                k = min(range(max(0, i - 15), n), key=lambda j: abs(ws[j]["t"] - s0))
                add(ws[k]["t"] - 2 * F, "TR_ZOOMBLUR", k, "enter_mascot")
                add(ws[k]["t"], "SCENE_DARK_MASCOT", k, "process")
                e = ws[cl[-1]]["t"] + 2.5
                ke = min(range(i, n), key=lambda j: abs(ws[j]["t"] - e))
                add(ws[ke]["t"] - 2 * F, "TR_ZOOMBLUR", ke, "exit_illustration")
                scene_until = ws[ke]["t"]; last_event = ws[ke]["t"]; i = ke + 1; continue

        # 5а. Параллельные отрицательные конструкции («некому…, нечего…, не из чего…») ≥3 за 8 с -> иллюстрация
        negs = lambda j: ws[j]["w"] in NEG_PRON or (ws[j]["w"] == "не" and j + 2 < n and ws[j + 1]["w"] == "из")
        if negs(i) and not in_scene:
            cl = [j for j in range(i, n) if ws[j]["t"] - t <= 8 and negs(j)]
            if len(cl) >= 3:
                add(t - 2 * F, "TR_ZOOMBLUR", i, "enter_illustration")
                add(t + 0.4, "SCENE_GREY_ILLUSTRATION", i, "enumeration")
                e = ws[cl[-1]]["t"] + 1.0
                ke = min(range(i, n), key=lambda j: abs(ws[j]["t"] - e))
                add(ws[ke]["t"] - 2 * F, "TR_RING", ke, "block_end")
                scene_until = ws[ke]["t"]; last_event = ws[ke]["t"]; pull_at = None; i = ke + 1; continue

        # 6. Перечисление-примеры «кто то … кто то …» (≥3 за 8 с)
        if w == "кто" and nxt(i) == "то" and not in_scene:
            reps = repeats(i, "кто", 9)
            if len(reps) >= 3:
                add(t - 2 * F, "CUT_HARD", i, "examples")
                add(ws[i + 2]["t"] - 14 * F if i + 2 < n else t, "SCENE_GREY_CARDS", min(i + 3, n - 1), "examples")
                # сцена ≤6,8 с, затем продолжение списка на спикере + mind-map (правило 2.4)
                cut = next((j for j in reps if ws[j]["t"] - t >= 5.5), None)
                if cut is not None:
                    add(ws[cut]["t"] - 2 * F, "CUT_HARD", cut, "exit_illustration")
                    add(ws[cut]["t"], "TITLE_KINETIC", cut, "enumeration")
                    last_event = ws[cut]["t"]; scene_until = ws[cut]["t"]
                    # закрыть список кольцом на первом слове после последнего «кто то …» + 2 слова
                    last = [j for j in repeats(cut, "кто", 6)][-1]
                    k = min(last + 4, n - 1)
                    add(ws[k]["t"] - 2 * F, "TR_RING", k, "block_end"); last_event = ws[k]["t"]
                    i = k + 1; continue
                scene_until = t + 6.8; last_event = t; i += 1; continue

        # 7. Перечисление категорий «… чаты, чаты …» (одно существительное ≥3 раз за 8 с)
        if w not in STOP and len(w) >= 4 and not in_scene and w not in BRANDS:
            reps = repeats(i, w, 8)
            if len(reps) >= 3:
                st = max(i - 1, 0) if ws[i - 1]["w"] not in STOP else i
                add(ws[st]["t"] - 2 * F, "TR_RING", st, "enter_illustration")
                add(ws[st]["t"] + 0.1, "SCENE_GREY_ILLUSTRATION", st, "enumeration")
                e = ws[reps[-1]]["t"] + 1.0
                ke = min(range(i, n), key=lambda j: abs(ws[j]["t"] - e))
                add(ws[ke]["t"] - 2 * F, "TR_RING", ke, "block_end")
                scene_until = ws[ke]["t"]; last_event = ws[ke]["t"]; i = ke + 1; continue

        # 8. Бренды (≥2 за 3 с) на спикере -> иконки
        if w in BRANDS and not in_scene:
            br = [j for j in range(i, n) if ws[j]["t"] - t <= 3 and ws[j]["w"] in BRANDS]
            if len(br) >= 2:
                add(t - 6 * F, "ICON_POP", i, "brand_enumeration"); last_event = t; i = br[-1] + 1; continue

        # 9. УТП «двадцать четыре на семь»
        if w == "двадцать" and nxt(i) == "четыре" and nxt(i, 2) == "на" and nxt(i, 3) == "семь":
            add(t - 4 * F, "ICON_DRAW", i, "feature"); last_event = t; i += 4; continue

        # 10. Название продукта «наш <слово>»
        if w == "наш" and nxt(i) and nxt(i) not in STOP and not in_scene:
            add(t - 2 * F, "CUT_PUNCH_IN", i, "product_name"); add(t + 0.06, "TITLE_KINETIC", i, "product_name")
            last_event = t; i += 2; continue

        # 11. Противительная «однако» на спикере -> сброс punch / вход в сравнение
        if w == "однако" and not in_scene:
            nxt_words = [ws[j]["w"] for j in range(i, min(i + 6, n))]
            if "первый" in nxt_words or "второй" in nxt_words:
                add(t - 2 * F, "TR_ZOOMBLUR", i, "contrast"); add(t + 0.15, "SCENE_GREY_COMPARE", i, "comparison_fail")
                scene_until = t + 2.6; last_event = t
            else:
                add(t - 2 * F, "CUT_PUNCH_OUT", i, "contrast"); last_event = t
            i += 1; continue

        # 12. Акцент-пик: количество / сравнительная степень / «не + прилагательное»
        accent = (w in QUANT or (w.endswith("ее") and len(w) >= 8)
                  or (ws[i - 1]["w"] == "не" and w.endswith(ADJ_END) and len(w) >= 6))
        if accent and not in_scene:
            if t - last_push >= PUSH_GAP:
                add(t - 0.2, "ZOOM_PUSH", i, "accent_peak"); last_push = t
                pull_at = t - 0.2 + PUSH_S + 1.2; last_event = t; i += 1; continue
            else:
                add(t - 2 * F, "CUT_PUNCH_IN", i, "accent_peak")
            last_event = t; i += 1; continue

        # 13. Нет событий > MAX_STATIC на спикере -> punch-in на ближайшем слове
        if not in_scene and t - last_event > MAX_STATIC:
            add(t - 2 * F, "CUT_PUNCH_IN", i, "rhythm"); last_event = t; i += 1; continue

        i += 1
    ev = sorted(ev, key=lambda e: e["t"])
    # отъезд не нужен, если в течение 1 с после него план и так режется (после наезда — склейка ИЛИ отъезд)
    return [e for k, e in enumerate(ev) if not (e["technique"] == "ZOOM_PULL" and any(
        0 < o["t"] - e["t"] <= 1.0 and o["technique"] != "MUSIC_IN" for o in ev[k + 1:k + 4]))]


def main():
    src = sys.argv[1] if len(sys.argv) > 1 else OUT / "transcript.json"
    out = sys.argv[2] if len(sys.argv) > 2 else OUT / "backtest.csv"
    ev = plan(load_words(src))
    with open(out, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["t", "technique", "word", "function", "note"])
        w.writeheader(); w.writerows(ev)
    print(f"событий: {len(ev)} -> {out}")


if __name__ == "__main__":
    main()
