"""Собирает kb/ENCYCLOPEDIA.md: главы энциклопедии (kb/encyclopedia/*.md) + приложение
«Лист приёмов по трём видео», сгенерированное из kb/ref0N_events.csv.

Запуск: python3 scripts/build_encyclopedia.py
"""
import collections
import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PARTS = sorted((ROOT / "kb" / "encyclopedia").glob("*.md"))

# ID приёма -> (русское название, раздел энциклопедии)
NAMES = {
    "CUT_HARD": ("Прямая склейка", "§4.1"), "CUT_PUNCH_IN": ("Врезка крупнее", "§3.2"),
    "CUT_PUNCH_OUT": ("Возврат на общий план", "§3.2"), "CUT_RAPID": ("Рубленые склейки (повтор-усиление)", "§3.2"),
    "ZOOM_PUSH": ("Плавный наезд", "§3.3"), "ZOOM_PULL": ("Плавный отъезд", "§3.4"),
    "TR_FOCUS": ("Вход из расфокуса", "§3.5"), "GRADE_BW": ("Ч/б-регистр (критика)", "§3.6"),
    "ROTO_BLACK": ("Спикер, вырезанный на чёрном (главный вопрос)", "§3.7"),
    "TR_RING": ("Световое кольцо (граница блока)", "§4.2"), "TR_FLASH": ("Вспышка / light leak (граница блока)", "§4.2"),
    "TR_ZOOMBLUR": ("Зум-бленд (фраза продолжается)", "§4.3"), "TR_XSTAMP": ("X-штамп (смена регистра)", "§4.4"),
    "TR_WIPE": ("Слайд-вайп", "§4.5"), "TR_WHIP": ("Whip-pan", "§4.6"), "TR_DISSOLVE": ("Растворение", "§4.7"),
    "TR_PAPER": ("Рваная бумага", "§4.8"), "TR_GLITCH": ("Глитч", "§4.9"), "TR_SILHOUETTE": ("Силуэт-вайп", "§4.10"),
    "FADE_BLACK": ("Затемнение", "§4.11"), "TR_SCROLL": ("Вертикальный скролл по таймлайну", "§4.12"),
    "TITLE_KINETIC": ("Кинетический титр", "§5.3"), "KEYWORD_CAPTION": ("Подпись-слово внизу", "§5.2"),
    "TITLE_GIANT": ("Гигантский титр / титр-вопрос", "§5.4"), "SIDE_TITLES": ("Боковые титры (рубрика)", "§5.5"),
    "TEXT_CENTER": ("Центральный текст по словам", "§5.6"), "QUOTE_BLACK": ("Слова по одному на чёрном (мысль людей)", "§5.7"),
    "SCENE_DARK_QUOTE": ("Красные слова на тёмной сетке (голос клиента)", "§5.7"),
    "YELLOW_QUOTE": ("Жёлтая плашка-цитата с курсором", "§5.8"), "CHAPTER_CARD": ("Заставка главы / карточка раздела", "§5.9"),
    "ICON_POP": ("Иконка / логотип / флаг / эмодзи", "§6.1"), "EMOJI_STACK": ("Накопление эмодзи-людей", "§6.2"),
    "ICON_DRAW": ("Иконка-рисовка (УТП)", "§6.3"), "PIP_IMAGE": ("Картинка в окне (PIP)", "§6.4"),
    "STAT_STICKER": ("Стикер-число", "§6.5"), "OBJECT_LABEL": ("3D-объект с подписью-плашкой", "§6.6"),
    "SPLIT_SOCIAL": ("Вертикальные видео из соцсетей", "§6.7"), "SPLIT_UI": ("Спикер + интерфейс (демо)", "§6.8"),
    "INFOGRAPHIC": ("Инфографика-индикатор (спидометр)", "§6.9"),
    "SCENE_GREY_ILLUSTRATION": ("Серая студия: силуэты / сетка иконок", "§7.1"),
    "SCENE_GREY_COMPARE": ("Серая студия: сравнение двух вариантов + ошибка", "§7.1–7.2"),
    "SCENE_GREY_CARDS": ("Карусель карточек / мем-карточки", "§7.4"),
    "SCENE_DARK_CHART": ("Тёмная сетка: гистограмма роста", "§7.2"),
    "SCENE_DARK_MASCOT": ("Тёмная сетка: талисман + белые слова (голос системы)", "§7.2"),
    "BROLL_FULL": ("Сток / B-roll на весь экран", "§7.3"), "CARD_TO_FULL": ("Карточка → на весь экран", "§7.4"),
    "SCREEN_DOC": ("Скриншоты источника / рубленый монтаж", "§7.5"), "SPOTLIGHT_ROW": ("Подсветка строки таблицы", "§7.5"),
    "HIGHLIGHT": ("Жёлтый маркер на числе", "§7.5"), "PRICE_TIMELINE": ("Таймлайн цен", "§7.6"),
    "TOC_CARDS": ("Оглавление UI-карточками", "§7.7"), "CHECKLIST": ("Чек-лист в UI-карточке", "§7.7"),
    "MAP_3D": ("3D-карта", "§7.8"), "OBJECT_3D": ("3D-объект в пустоте", "§7.8"), "ANIM_2D": ("2D-анимация объекта-метафоры", "§7.9"),
    "TV_WALL": ("Стена телевизоров", "§7.11"), "MUSIC_IN": ("Вход музыки", "§8.1"),
}
FUNC = {
    "thesis_keyword": "ключевое слово хука", "hook_emphasis": "акцент хука", "block_end": "граница блока",
    "enter_illustration": "вход в иллюстрацию", "exit_illustration": "возврат к спикеру", "enumeration": "перечисление",
    "term": "термин", "negation": "отрицание", "enumeration_growth": "перечисление-рост", "contrast": "противопоставление",
    "comparison_fail": "сравнение, оба плохие", "promise": "обещание", "rhythm": "ритм", "brand_enumeration": "перечисление брендов",
    "scale_number": "масштаб / число", "examples": "примеры", "enter_quote": "вход в прямую речь",
    "direct_speech": "прямая речь", "address_viewer": "обращение к зрителю", "accent_peak": "акцент-пик",
    "make_room": "место под титр", "key_concept": "ключевое понятие", "release": "выдох после наезда",
    "opinion_negative": "критика", "consequences": "последствия", "pivot_solution": "поворот к решению",
    "feature": "УТП", "enter_mascot": "вход в работу системы", "process": "процесс", "product_name": "название продукта",
    "enter_demo": "вход в демо", "demo": "демо", "metaphor": "метафора", "illustration": "иллюстрация",
    "transition": "переход", "question": "вопрос", "comparison": "сравнение", "irony": "ирония", "source": "источник",
    "evidence": "доказательство", "statistic": "статистика / число", "emotional": "драма", "thesis": "тезис",
    "topic": "рубрика", "chapter": "структура / глава", "main_question": "главный вопрос", "solution": "решение",
    "cta": "оффер", "personal_example": "личный пример", "emphasis": "акцент", "hook_keyword": "хук",
}
VIDEOS = [
    ("ref01", "ref01 — профиль A (моушн-дизайн): сервис лидогенерации из Telegram-чатов, 121 с, 29,97 fps"),
    ("ref02", "ref02 — профиль B (документальный разбор): экономика Казахстана, «Магия чисел и мёртвый ВВП», 180 с, 30 fps"),
    ("ref03", "ref03 — профиль C (продуктовый разбор, Apple-стиль): «Apple — развод?», магазин техники, 61 с, 25 fps"),
]


def video_list(ref, title):
    rows = list(csv.DictReader(open(ROOT / "kb" / f"{ref}_events.csv", encoding="utf-8")))
    out = [f"### {title}", "", "| # | Время, с | Приём | Раздел | Слово-триггер | Смысловая функция | Что именно |",
           "|---|---|---|---|---|---|---|"]
    for i, r in enumerate(sorted(rows, key=lambda r: float(r["t"])), 1):
        name, sec = NAMES.get(r["technique"], (r["technique"], "—"))
        end = f"–{float(r['t_end']):.2f}" if r.get("t_end") else ""
        note = r["note"].replace("|", "/")
        out.append(f"| {i} | {float(r['t']):.2f}{end} | {name} | {sec} | «{r['word']}» | "
                   f"{FUNC.get(r['function'], r['function'])} | {note} |")
    cnt = collections.Counter(NAMES.get(r["technique"], (r["technique"],))[0] for r in rows)
    out += ["", "**Частота приёмов:** " + "; ".join(f"{k} — {v}" for k, v in cnt.most_common()), ""]
    return "\n".join(out)


def main():
    body = "\n".join(p.read_text(encoding="utf-8") for p in PARTS)
    app = ["", "---", "", "## 13. Лист приёмов по трём видео (все события по порядку)", "",
           "Сгенерировано из эталонных разметок `kb/ref01_events.csv`, `kb/ref02_events.csv`, `kb/ref03_events.csv`. "
           "Время — секунды референса. «Раздел» — где в энциклопедии описана логика приёма.", ""]
    for ref, title in VIDEOS:
        app.append(video_list(ref, title))
    (ROOT / "kb" / "ENCYCLOPEDIA.md").write_text(body + "\n".join(app) + "\n", encoding="utf-8")
    print("kb/ENCYCLOPEDIA.md:", sum(1 for _ in open(ROOT / "kb" / "ENCYCLOPEDIA.md", encoding="utf-8")), "строк")


if __name__ == "__main__":
    main()
