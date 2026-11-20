"""SEO сторінок закладів ТЦ Garden Plaza New: заголовок, опис для видачі, вступне речення й розмітка schema.org.

Дані закладів (назва, опис, графік, телефони) пише сам заклад у кабінеті — тут їх не змінюємо, лише
подаємо пошуковикам охайно: без емодзі в описі, без крапки в кінці назви, з графіком у зрозумілому Google вигляді.
Тести:  python3 -m unittest discover -s tools
"""
import re

BASE_URL = "https://tcgardenplaza.com.ua/"
MALL_ID = BASE_URL + "#mall"
MALL_NAME = "ТЦ Garden Plaza New"
MALL_NAME_SHORT = "ТЦ Garden Plaza"
# так назву пишуть у пошуку кирилицею
MALL_NAME_CYR = "Гарден Плаза"
LOCALITY = "Нересниця"
LOCALITY_IN = "Нересниці"
STREET = "вул. Грушевського, 30"
REGION_TEXT = "Тячівський район, Закарпаття"
GEO = {"latitude": 48.1196052, "longitude": 23.7721827}
MAPS_URL = "https://www.google.com/maps/search/?api=1&query=48.1196052,23.7721827"
FLOOR_NAMES = {1: "1 поверх", 2: "2 поверх", 3: "3 поверх", 4: "4 поверх"}
FLOOR_IN = {1: "1 поверсі", 2: "2 поверсі", 3: "3 поверсі", 4: "4 поверсі"}

# опис у видачі Google обрізається приблизно тут
DESCRIPTION_MAX = 160
# довший заголовок Google обрізає — тоді беремо коротку назву центру
TITLE_MAX = 65

# Що це за заклад — словами, якими його шукають («аптека в Нересниці»), і тип для schema.org.
# named: назва вже сама каже, що це («Аптека Подорожник»), тож у заголовку не повторюємо.
# Ключ — адреса сторінки закладу (slug). Нового закладу тут немає — тоді береться загальне за категорією.
KINDS = {
    "kopiyochka": {"kind": "магазин товарів для дому", "schema": "HomeGoodsStore"},
    "apteka": {"kind": "аптека", "schema": "Pharmacy", "named": True},
    "obmin-valyut": {"kind": "обмін валют", "schema": "FinancialService", "named": True},
    "prostor": {"kind": "магазин косметики й побутової хімії", "schema": "Store"},
    "zhasmin": {"kind": "магазин жіночого одягу", "schema": "ClothingStore"},
    "odyag": {"kind": "магазин жіночого одягу", "schema": "ClothingStore"},
    "kylymovyjdim": {"kind": "килими й покриття для підлоги", "schema": "HomeGoodsStore"},
    "versal": {"kind": "ювелірний магазин", "schema": "JewelryStore"},
    "alma": {"kind": "супермаркет", "schema": "GroceryStore"},
    "furt-servis": {"kind": "ремонт телефонів і ноутбуків", "schema": "ElectronicsStore"},
    "zhasmin-ostrivok": {"kind": "сувеніри й декор для дому", "schema": "HomeGoodsStore"},
    "zolotyi-vik": {"kind": "ювелірний магазин", "schema": "JewelryStore"},
    "shafron": {"kind": "східні солодощі й сухофрукти", "schema": "GroceryStore"},
    "dzhentelmen": {"kind": "магазин чоловічого одягу", "schema": "MensClothingStore"},
    "faina-pani": {"kind": "прикраси, біжутерія й аксесуари", "schema": "Store"},
    "kredo-klinika": {"kind": "медична клініка", "schema": "MedicalClinic"},
    "shtory": {"kind": "салон штор", "schema": "HomeGoodsStore"},
    "sharm": {"kind": "магазин жіночого одягу", "schema": "ClothingStore"},
    "astel": {"kind": "магазин жіночого одягу", "schema": "ClothingStore"},
    "la-butik": {"kind": "магазин взуття", "schema": "ShoeStore"},
    "restoran-garden-plaza": {"kind": "ресторан", "schema": "Restaurant", "named": True},
    "gym-maxi": {"kind": "спортзал", "schema": "ExerciseGym"},
    "mezey-shop": {"kind": "техніка Apple і ремонт", "schema": "ElectronicsStore"},
    "tiffany-beauty-salon": {"kind": "салон краси", "schema": "BeautySalon"},
    "monotaxi": {"kind": "служба таксі", "schema": "LocalBusiness"},
    "dytiacha-kimnata": {"kind": "ігрова кімната для дітей", "schema": "EntertainmentBusiness", "named": True},
    "goddes": {"kind": "магазин жіночого взуття", "schema": "ShoeStore"},
    "banketnyi-zal": {"kind": "банкетний зал", "schema": "EventVenue", "named": True},
    "hotel": {"kind": "готель", "schema": "Hotel"},
}
KIND_BY_CAT = {
    "grocery": {"kind": "продуктовий магазин", "schema": "GroceryStore"},
    "fashion": {"kind": "магазин одягу і взуття", "schema": "ClothingStore"},
    "kids": {"kind": "товари й розваги для дітей", "schema": "Store"},
    "tech": {"kind": "магазин техніки", "schema": "ElectronicsStore"},
    "home": {"kind": "товари для дому", "schema": "HomeGoodsStore"},
    "services": {"kind": "послуги", "schema": "LocalBusiness"},
    "food": {"kind": "заклад харчування", "schema": "FoodEstablishment"},
    "fun": {"kind": "спорт і розваги", "schema": "SportsActivityLocation"},
    "beauty": {"kind": "краса і прикраси", "schema": "Store"},
    "shop": {"kind": "магазин", "schema": "Store"},
}
KIND_DEFAULT = KIND_BY_CAT["shop"]

VOWELS = "аеєиіїоуюяaeiouy"
SENTENCE_END = ".!?…"
EMOJI_RE = re.compile("[\U0001F000-\U0001FAFF←-⇿⌀-⏿☀-➿⬀-⯿️‍]")
BULLET_RE = re.compile(r"^[\s•·*✓✔▪◦-]+")
# телефони-заглушки, які стояли на сайті до справжніх даних закладу: (068) 000-0X-XX
PLACEHOLDER_PHONE_RE = re.compile(r"^0680000\d{3}$")


# ——— назва й тексти ———

def clean_name(name):
    """Назва для пошуковиків: без крапки чи пробілів, які власник лишив у кінці."""
    return str(name).strip().rstrip(".").strip()


def kind_of(place):
    found = KINDS.get(place["slug"]) or KIND_BY_CAT.get(place.get("cat_code")) or KIND_DEFAULT
    return {"named": False, **found}


def in_locality(before):
    """«у Нересниці» після приголосної, «в Нересниці» після голосної."""
    last = before.rstrip(" .»\"”)")[-1:].lower()
    return f"{'в' if last in VOWELS else 'у'} {LOCALITY_IN}"


def headline(place):
    """«La Butik — магазин взуття в Нересниці»: назва, що це і де."""
    name, kind = clean_name(place["name"]), kind_of(place)
    lead = name if kind["named"] else f"{name} — {kind['kind']}"
    return f"{lead} {in_locality(lead)}"


def seo_title(place):
    full = f"{headline(place)} | {MALL_NAME}"
    return full if len(full) <= TITLE_MAX else f"{headline(place)} | {MALL_NAME_SHORT}"


def intro(place):
    """Вступне речення на сторінці: що за заклад, у якому селі, на якому поверсі й за якою адресою."""
    return (f"{headline(place)}. Шукайте на {FLOOR_IN[place['floor']]} {MALL_NAME} ({MALL_NAME_CYR}): "
            f"{STREET}, {REGION_TEXT}.")


def lower_first(text):
    """Пункт списку всередині речення — з малої; латинські назви й абревіатури не чіпаємо."""
    is_plain_word = re.match(r"[А-ЯІЇЄҐ][а-яіїєґ'’]", text)
    return text[0].lower() + text[1:] if is_plain_word else text


def plain_text(raw):
    """Опис закладу одним абзацом: без емодзі, рядки зведено в речення, списки — через кому."""
    lines = []
    for line in str(raw or "").splitlines():
        no_emoji = EMOJI_RE.sub("", line).strip()
        text = re.sub(r"\s+", " ", BULLET_RE.sub("", no_emoji)).strip()
        if text:
            # пункт списку: рядок починався з емодзі чи позначки
            lines.append((text, not line.strip().startswith(text[:1])))
    out, prev_bullet = "", False
    for text, bullet in lines:
        end = out[-1:]
        if not out:
            out = text
        elif end == ":":
            out += " " + (lower_first(text) if bullet else text)
        elif end in SENTENCE_END:
            out += " " + text
        elif end == "," or (bullet and prev_bullet):
            out += ("" if end == "," else ",") + " " + lower_first(text)
        else:
            out += ". " + text
        prev_bullet = bullet
    return out + "." if out and out[-1] not in SENTENCE_END else out


def clip(text, limit):
    """Обрізає текст по слову й ставить три крапки, якщо він довший за limit."""
    return text if len(text) <= limit else text[:max(limit - 1, 1)].rsplit(" ", 1)[0].rstrip(" ,.;:—-") + "…"


def seo_description(place):
    """Опис для видачі: що за заклад + де він і коли працює. Адреса й графік мають уміститись завжди."""
    where = f"{FLOOR_NAMES[place['floor']]} {MALL_NAME}, {LOCALITY}."
    hours = f" Графік: {place['hours']}." if place.get("hours") else ""
    tail = where + hours if len(where + hours) <= DESCRIPTION_MAX // 2 else where
    lead = plain_text(place.get("about")) or headline(place) + "."
    return f"{clip(lead, DESCRIPTION_MAX - len(tail) - 1)} {tail}"


def photo_alt(place, number):
    return f"{headline(place)}, {MALL_NAME} — фото {number}"


# ——— графік ———

WEEK = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")
DAY_STEMS = ("пн", "вт", "ср", "чт", "пт", "сб", "нд")
DAY_WORDS = ("понеділ", "вівтор", "серед", "четвер", "п.?ятниц", "субот", "неділ")
LETTER = "а-яіїєґ'’"
HOURS_TOKEN_RE = re.compile(
    rf"(?P<nonstop>цілодобово|24/7)"
    rf"|(?P<off>вихідн[{LETTER}]*|зачинен[{LETTER}]*)"
    rf"|(?P<all>щодня|щоденно|кожного дня|без вихідних)"
    rf"|(?P<word>(?:{'|'.join(DAY_WORDS)})[{LETTER}]*)"
    rf"|(?<![{LETTER}])(?P<short>{'|'.join(DAY_STEMS)})(?![{LETTER}])"
    rf"|(?<!\d)(?P<h>\d{{1,2}})[:.](?P<m>\d{{2}})(?!\d)")
DAY_RANGE_RE = re.compile(r"\s*(?:[-–—]|по|до)\s*")
# перерви, винятки й свята словами не розібрати надійно — з ними графіка в розмітку не даємо
HOURS_UNCLEAR_RE = re.compile(r"перерв|обід|крім|свят")
ALL_DAYS = tuple(range(7))


def day_index(match):
    if match.group("short"):
        return DAY_STEMS.index(match.group("short"))
    return next(i for i, stem in enumerate(DAY_WORDS) if re.match(stem, match.group("word")))


def day_span(first, last):
    """Дні від first до last включно («Пт–Пн» переходить через неділю)."""
    return [(first + step) % 7 for step in range((last - first) % 7 + 1)]


def parse_hours(text):
    """Графік, написаний людиною («Пн–Сб 8:00–21:00, Нд 9:00–21:00»), у вигляді для schema.org.
    Повертає [{days, opens, closes}]; порожньо, якщо часу немає або запис можна зрозуміти по-різному:
    неправильний графік у Google гірший, ніж жодного."""
    low = str(text or "").lower()
    if HOURS_UNCLEAR_RE.search(low):
        return []
    specs, days, times, last_day, closed, days_off = [], [], [], None, True, set()
    for token in HOURS_TOKEN_RE.finditer(low):
        if token.group("off"):
            # «Нд вихідний»: дні мають стояти перед словом, інакше не знаємо, яких днів воно стосується
            if closed or times or not days:
                return []
            days_off |= set(days)
            days, last_day, closed = [], None, True
        elif times and not token.group("h"):
            return []
        elif token.group("nonstop"):
            specs.append((ALL_DAYS, "00:00", "23:59"))
            days, times, last_day, closed = [], [], None, True
        elif token.group("all"):
            days, times, last_day, closed = list(ALL_DAYS), [], None, False
        elif token.group("h"):
            hour, minute = int(token.group("h")), int(token.group("m"))
            if hour > 23 or minute > 59:
                return []
            times = [*times, f"{hour:02d}:{minute:02d}"]
            if len(times) == 2:
                if times[0] != times[1]:
                    specs.append((tuple(days) or ALL_DAYS, times[0], times[1]))
                times, last_day, closed = [], None, True
        else:
            index = day_index(token)
            is_range = last_day is not None and DAY_RANGE_RE.fullmatch(low[last_day[1]:token.start()])
            if closed:
                days = [index]
            elif is_range:
                days = [*days[:-1], *day_span(last_day[0], index)]
            else:
                days = [*days, index]
            times, last_day, closed = [], (index, token.end()), False
    if times or not closed:
        return []
    groups = [(sorted(set(group) - days_off), opens, closes) for group, opens, closes in specs]
    listed = [day for group, _, _ in groups for day in group]
    if len(listed) != len(set(listed)):
        return []
    return [{"days": [WEEK[d] for d in group], "opens": opens, "closes": closes} for group, opens, closes in groups if group]


# ——— розмітка schema.org ———

def is_real_phone(number):
    return not PLACEHOLDER_PHONE_RE.match(number)


def absolute(path):
    return path if path.startswith(("https://", "http://")) else BASE_URL + path


def business_schema(place, about, canonical, images):
    """Заклад для Google: тип, адреса, графік, телефон, сторінки в соцмережах."""
    business = {
        "@context": "https://schema.org",
        "@type": kind_of(place)["schema"],
        "@id": canonical + "#place", "name": clean_name(place["name"]), "description": about, "url": canonical,
        "address": {"@type": "PostalAddress", "streetAddress": STREET, "addressLocality": LOCALITY,
                    "addressRegion": "Закарпатська область", "addressCountry": "UA"},
        "geo": {"@type": "GeoCoordinates", **GEO},
        "hasMap": MAPS_URL,
        "containedInPlace": {"@type": "ShoppingCenter", "@id": MALL_ID, "name": MALL_NAME, "url": BASE_URL},
    }
    if images:
        business["image"] = images
    if place.get("logo"):
        business["logo"] = absolute(place["logo"])
    phones = ["+38" + n for n in place.get("phones_own", place.get("phones")) or [] if is_real_phone(n)]
    if phones:
        business["telephone"] = phones[0]
    # графік — лише той, що вказав сам заклад: години центру закладу не приписуємо
    hours = parse_hours(place.get("hours_own", place.get("hours")))
    if hours:
        business["openingHoursSpecification"] = [
            {"@type": "OpeningHoursSpecification", "dayOfWeek": h["days"], "opens": h["opens"], "closes": h["closes"]}
            for h in hours]
    links = [l["href"] for l in place.get("links") or []]
    if links:
        business["sameAs"] = links
    return business


def breadcrumbs_schema(trail):
    """trail — [(назва, адреса), …] від головної до поточної сторінки."""
    return {
        "@context": "https://schema.org", "@type": "BreadcrumbList",
        "itemListElement": [{"@type": "ListItem", "position": i + 1, "name": name, "item": url}
                            for i, (name, url) in enumerate(trail)],
    }


def places_list_schema(places):
    """Список усіх закладів центру для сторінки «Усі заклади»."""
    return {
        "@context": "https://schema.org", "@type": "ItemList", "name": f"Заклади {MALL_NAME}",
        "numberOfItems": len(places),
        "itemListElement": [{"@type": "ListItem", "position": i + 1, "name": clean_name(p["name"]),
                             "url": f"{BASE_URL}zaklady/{p['slug']}/"} for i, p in enumerate(places)],
    }
