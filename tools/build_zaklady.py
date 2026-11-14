"""Збирає окрему сторінку для кожного закладу ТЦ Garden Plaza New.

Заклади беруться з бази кабінету (Supabase, адреса в gp-config.js), а якщо базу ще не налаштовано —
з даних, вбудованих в index.html (CATS, UNITS_BASE, SHOP_INFO, SHOP_LINKS, POPULAR).

    python3 tools/build_zaklady.py .              # із бази, якщо вона є, інакше з index.html
    python3 tools/build_zaklady.py . --from-base  # лише з бази; без бази нічого не змінює (так запускає GitHub)

Пише: zaklady/<slug>/index.html (сторінка закладу), zaklady/index.html (усі заклади), sitemap.xml.
GitHub запускає його кожні 15 хвилин (.github/workflows/zaklady.yml) і заливає сторінки, якщо щось змінилось.
"""
import html
import json
import re
import shutil
import sys
import urllib.request
from pathlib import Path

BASE_URL = "https://black-eagle666.github.io/garden-plaza-new/"
ADDRESS = "вул. Грушевського, 30, с. Нересниця"
MAPS_URL = "https://www.google.com/maps/search/?api=1&query=48.1196052,23.7721827"
FLOOR_NAMES = {1: "1 поверх", 2: "2 поверх", 3: "3 поверх", 4: "4 поверх"}
FLOOR_IN = {1: "1 поверсі", 2: "2 поверсі", 3: "3 поверсі", 4: "4 поверсі"}


# ——— читання даних із JS на головній ———

def js_block(src, marker):
    """Повертає текст об'єкта чи масиву, що йде після marker (з урахуванням рядків у лапках)."""
    start = src.index(marker)
    i = min(p for p in (src.find("{", start), src.find("[", start)) if p != -1)
    depth, quote, k = 0, None, i
    while True:
        c = src[k]
        if quote:
            if c == "\\":
                k += 1
            elif c == quote:
                quote = None
        elif c in "\"'`":
            quote = c
        elif c in "{[":
            depth += 1
        elif c in "}]":
            depth -= 1
            if depth == 0:
                return src[i:k + 1]
        k += 1


def js_to_json(text):
    """Перетворює JS-літерал (ключі без лапок, рядки в одинарних лапках) на JSON і розбирає його."""
    out, i, n = [], 0, len(text)
    last = ""  # останній значущий символ поза рядками: ключ стоїть лише після { або ,
    while i < n:
        c = text[i]
        if c in "\"'":
            j, buf = i + 1, []
            while text[j] != c:
                if text[j] == "\\":
                    buf.append(text[j + 1])
                    j += 2
                    continue
                buf.append(text[j])
                j += 1
            out.append(json.dumps("".join(buf), ensure_ascii=False))
            last = '"'
            i = j + 1
        elif re.match(r"[A-Za-z_]", c) and last in "{,":
            word = re.match(r"[A-Za-z_][A-Za-z0-9_]*", text[i:]).group(0)
            rest = text[i + len(word):].lstrip()
            out.append(f'"{word}"' if rest.startswith(":") else word)
            last = "w"
            i += len(word)
        else:
            out.append(c)
            if not c.isspace():
                last = c
            i += 1
    return json.loads(re.sub(r",(\s*[}\]])", r"\1", "".join(out)))


def js_const(src, name):
    return re.search(rf'const {name} = "([^"]*)"', src).group(1)


def load_site(index_html):
    src = index_html.read_text(encoding="utf-8")
    return {
        "cats": js_to_json(js_block(src, "const CATS =")),
        "units": js_to_json(js_block(src, "const UNITS_BASE =")),
        "info": js_to_json(js_block(src, "const SHOP_INFO =")),
        "links": js_to_json(js_block(src, "const SHOP_LINKS =")),
        "popular": js_to_json(js_block(src, "const POPULAR =")),
        "colors": dict(re.findall(r"(--c-[a-z]+):(#[0-9A-Fa-f]{6})", src)),
        "apple": re.search(r'<symbol id="i-apple"[^>]*>(<path d="[^"]*"/>)</symbol>', src).group(1),
        "mall_phone": js_const(src, "MALL_PHONE"),
        "default_hours": js_const(src, "DEFAULT_HOURS"),
        "fonts": re.findall(r"@font-face\{[^}]*\}", src),
    }


# ——— заклади ———

def tel_label(n):
    return f"0 800 {n[4:7]} {n[7:]}" if n.startswith("0800") else f"({n[:3]}) {n[3:6]}-{n[6:8]}-{n[8:]}"


def base_config(site):
    """Адреса бази й publishable-ключ із gp-config.js; None, якщо поля порожні."""
    src = (site / "gp-config.js").read_text(encoding="utf-8")
    url = re.search(r'supabaseUrl:\s*"([^"]*)"', src).group(1)
    key = re.search(r'supabaseKey:\s*"([^"]*)"', src).group(1)
    return (url.rstrip("/"), key) if url and key else None


def load_base_rows(cfg):
    url, key = cfg
    req = urllib.request.Request(f"{url}/rest/v1/units?select=*&order=unit_id", headers={"apikey": key})
    with urllib.request.urlopen(req, timeout=30) as res:
        return json.loads(res.read().decode("utf-8"))


def builtin_units(data, site):
    """Заклади, вбудовані в index.html, у тому ж вигляді, що й рядки бази."""
    rows = []
    for base in data["units"]:
        u = {**base, **data["info"].get(base["id"], {})}
        pics = u["pics"] if "pics" in u else [f"shops/{u['id']}-{n}.webp" for n in (1, 2)]
        rows.append({
            "unit_id": u["id"], "floor": u["f"], "vacant": bool(u.get("vacant")), "slug": u.get("slug"),
            "name": u["name"], "cat": u["cat"], "about": u.get("about", ""), "hours": u.get("hours", ""),
            "phones": u["phones"] if "phones" in u else ([u["phone"]] if u.get("phone") else []),
            "links": data["links"].get(u["id"], []), "logo_url": u.get("logo"), "wordmark_url": None,
            "photos": [p for p in pics if (site / p).exists()],
        })
    return rows


def build_places(rows, data):
    """Заклади зі спільним slug (одна мережа в кількох приміщеннях) зводимо в один запис зі списком приміщень.
    Вбудований знак (POPULAR) беремо, лише поки в приміщенні той самий заклад, що й у вбудованих даних."""
    builtin_slug = {u["id"]: u.get("slug") for u in data["units"]}
    places = {}
    for r in sorted(rows, key=lambda r: r["unit_id"]):
        if r["vacant"] or not r.get("slug"):
            continue
        place = places.get(r["slug"])
        if place:
            places[r["slug"]] = {**place, "spots": [*place["spots"], r["unit_id"]]}
            continue
        cat = data["cats"].get(r["cat"]) or data["cats"]["shop"]
        same_tenant = builtin_slug.get(r["unit_id"]) == r["slug"]
        mark = next((p for p in data["popular"] if p["unit"] == r["unit_id"] or r["unit_id"] in p.get("also", [])), None)
        places[r["slug"]] = {
            "slug": r["slug"], "id": r["unit_id"], "name": r["name"], "floor": r["floor"], "spots": [r["unit_id"]],
            "cat": cat["name"], "color": data["colors"][cat["c"]],
            "about": r.get("about") or "", "hours": r.get("hours") or data["default_hours"],
            "phones": r.get("phones") or [data["mall_phone"]],
            "logo": r.get("logo_url"), "pics": r.get("photos") or [],
            "links": [l for l in (r.get("links") or []) if str(l.get("href", "")).startswith(("https://", "http://"))],
            "wordmark": r.get("wordmark_url"),
            "mark": mark if same_tenant else None,
        }
    return places


def asset(path, up):
    """Адреса файлу: зі сховища бази — як є, файл сайту — відносно сторінки."""
    return path if path.startswith(("https://", "http://")) else up + path


def absolute(path):
    return path if path.startswith(("https://", "http://")) else BASE_URL + path


# ——— розмітка ———

ICON_PHONE = '<svg viewBox="0 0 24 24" aria-hidden="true"><path fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" d="M22 16.9v3a2 2 0 0 1-2.2 2 19.8 19.8 0 0 1-8.6-3.1 19.5 19.5 0 0 1-6-6A19.8 19.8 0 0 1 2.1 4.2 2 2 0 0 1 4.1 2h3a2 2 0 0 1 2 1.7c.1 1 .4 1.9.7 2.8a2 2 0 0 1-.5 2.1L8.1 9.9a16 16 0 0 0 6 6l1.3-1.3a2 2 0 0 1 2.1-.4c.9.3 1.8.6 2.8.7a2 2 0 0 1 1.7 2z"/></svg>'
ICON_CUBE = '<svg viewBox="0 0 24 24" aria-hidden="true"><path fill="none" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round" d="M12 2.8 20 7.3v9.4l-8 4.5-8-4.5V7.3zM4 7.3l8 4.6 8-4.6M12 11.9v9.3"/></svg>'
ICON_PIN = '<svg viewBox="0 0 24 24" aria-hidden="true"><g fill="none" stroke="currentColor" stroke-width="1.7"><path d="M12 21s-7-6.2-7-11.5a7 7 0 0 1 14 0C19 14.8 12 21 12 21z"/><circle cx="12" cy="9.5" r="2.5"/></g></svg>'


def esc(s):
    return html.escape(str(s), quote=True)


def mark_html(place, data, up):
    """Знак закладу (як на плитках головної) або назва."""
    if place["wordmark"]:
        return f'<span class="wm wm-img wm-up"><img src="{esc(asset(place["wordmark"], up))}" alt=""></span>'
    m = place["mark"]
    if not m:
        return f'<span class="wm wm-plain">{esc(place["name"])}</span>'
    inner = m["html"].replace('<use href="#i-apple"/>', data["apple"]).replace('src="shops/', f'src="{up}shops/')
    return f'<span class="wm {m["cls"]}">{inner}</span>'


def logo_html(place, data, up):
    if place["logo"]:
        return f'<div class="logo"><img src="{esc(asset(place["logo"], up))}" alt="Логотип {esc(place["name"])}" width="160" height="160"></div>'
    if place["mark"] or place["wordmark"]:
        return f'<div class="logo wide" role="img" aria-label="Логотип {esc(place["name"])}">{mark_html(place, data, up)}</div>'
    return f'<div class="logo" aria-hidden="true"><span class="mono">{esc(place["name"][0])}</span></div>'


def rooms(place):
    return " і ".join(place["spots"])


def tile_html(place, data, up, href):
    return (f'<a class="tile" href="{href}">{mark_html(place, data, up)}'
            f'<small>{FLOOR_NAMES[place["floor"]]} · {esc(place["id"])}</small></a>')


def head_html(title, description, canonical, image, up, data, extra=""):
    fonts = "\n".join(f.replace("url(fonts/", f"url({up}fonts/") for f in data["fonts"])
    return f"""<!doctype html>
<html lang="uk">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{esc(title)}</title>
<meta name="description" content="{esc(description)}">
<link rel="canonical" href="{canonical}">
<meta property="og:type" content="website">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(description)}">
<meta property="og:url" content="{canonical}">
<meta property="og:image" content="{image}">
<meta name="theme-color" content="#07080C">
<link rel="icon" type="image/png" sizes="64x64" href="{up}favicon.png">
<link rel="icon" type="image/svg+xml" href="{up}favicon.svg">
<link rel="apple-touch-icon" href="{up}apple-touch-icon.png">
<link rel="preload" as="font" type="font/woff2" href="{up}fonts/geist-normal-cyrillic.woff2" crossorigin>
<style>
{fonts}
{PAGE_CSS}
</style>
{extra}
</head>"""


def topbar_html(up, data):
    phone = data["mall_phone"]
    return f"""<header class="top"><div class="wrap">
  <a class="brand" href="{up}"><img src="{up}gp-mark.svg" alt="" width="38" height="38"><span>GARDEN<br>PLAZA</span></a>
  <a class="call" href="tel:+38{phone}" aria-label="Подзвонити адміністрації центру">{ICON_PHONE}<span>{tel_label(phone)}</span></a>
</div></header>"""


def footer_html(up, data):
    phone = data["mall_phone"]
    return f"""<footer><div class="wrap">
  <p><strong>ТЦ Garden Plaza New</strong><br>{ADDRESS}, Тячівський район, Закарпаття</p>
  <p><a href="tel:+38{phone}">{tel_label(phone)}</a> · щодня 10:00–22:00</p>
  <p class="foot-links"><a href="{up}">Головна</a><a href="{up}zaklady/">Усі заклади</a><a href="{up}#map">Мапа поверхів</a></p>
</div></footer>"""


def place_page(place, places, data):
    up = "../../"
    canonical = f"{BASE_URL}zaklady/{place['slug']}/"
    title = f"{place['name']} — ТЦ Garden Plaza New, Нересниця"
    about = place["about"] or f"{place['name']} у ТЦ Garden Plaza New."
    description = about if len(about) <= 160 else about[:157].rsplit(" ", 1)[0] + "…"
    image = absolute(place["logo"] or (place["pics"][0] if place["pics"] else "og.jpg"))

    phones = "".join(f'<a class="btn main live" href="tel:+38{n}">{ICON_PHONE}{tel_label(n)}</a>' for n in place["phones"])
    links = "".join(f'<a class="btn live" href="{esc(l["href"])}" target="_blank" rel="noopener">{esc(l["label"])}</a>' for l in place["links"])
    acts = (phones + links
            + f'<a class="btn" href="{up}?zaklad={esc(place["id"])}">{ICON_CUBE}Показати на 3D-плані</a>'
            + f'<a class="btn" href="{MAPS_URL}" target="_blank" rel="noopener">{ICON_PIN}Прокласти маршрут</a>')
    imgs = "".join(f'<img src="{esc(asset(p, up))}" alt="{esc(place["name"])}, фото {i + 1}" loading="lazy" decoding="async" width="640" height="480">'
                   for i, p in enumerate(place["pics"]))
    # секція є завжди (порожня схована): скрипт покаже її, якщо фото з'являться в базі
    pics = f'<section data-live="pics"{"" if imgs else " hidden"}><h2>Фото</h2><div class="pics">{imgs}</div></section>'
    phones_text = ", ".join(tel_label(n) for n in place["phones"]) or "уточнюйте в закладі"
    neighbours = sorted((p for p in places.values() if p["floor"] == place["floor"] and p["slug"] != place["slug"]),
                        key=lambda p: p["name"].lower())
    tiles = "".join(tile_html(p, data, up, f"{up}zaklady/{p['slug']}/") for p in neighbours)
    more = f'<section><h2>Ще на {FLOOR_IN[place["floor"]]}</h2><div class="tiles">{tiles}</div></section>' if tiles else ""

    ld = {
        "@context": "https://schema.org", "@type": "LocalBusiness", "name": place["name"],
        "description": about, "url": canonical, "image": image,
        "address": {"@type": "PostalAddress", "streetAddress": "вул. Грушевського, 30", "addressLocality": "Нересниця",
                    "addressRegion": "Закарпатська область", "addressCountry": "UA"},
        "containedInPlace": {"@type": "ShoppingCenter", "name": "ТЦ Garden Plaza New", "url": BASE_URL},
    }
    if place["phones"]:
        ld["telephone"] = "+38" + place["phones"][0]
    if place["links"]:
        ld["sameAs"] = [l["href"] for l in place["links"]]
    extra = f'<script type="application/ld+json">{json.dumps(ld, ensure_ascii=False)}</script>'

    return f"""{head_html(title, description, canonical, image, up, data, extra)}
<body>
{topbar_html(up, data)}
<main class="wrap" data-unit="{esc(place["id"])}" data-slug="{esc(place["slug"])}" data-default-hours="{esc(data["default_hours"])}" data-mall-phone="{esc(data["mall_phone"])}">
  <nav class="crumbs" aria-label="Ви тут"><a href="{up}">Головна</a> <span>›</span> <a href="{up}zaklady/">Заклади</a> <span>›</span> {FLOOR_NAMES[place["floor"]]}</nav>
  <article class="hero">
    {logo_html(place, data, up)}
    <div>
      <span class="tag" style="--c:{place["color"]}"><i></i>{esc(place["cat"])}</span>
      <h1>{esc(place["name"])}</h1>
      <p class="where">{FLOOR_NAMES[place["floor"]]}, приміщення {esc(rooms(place))} · ТЦ Garden Plaza New</p>
      <p class="hrs">Графік: <span data-live="hours">{esc(place["hours"])}</span></p>
    </div>
  </article>
  <div class="acts">{acts}</div>
  <section><h2>Про заклад</h2><p class="about" data-live="about">{esc(about)}</p></section>
  {pics}
  <section><h2>Як знайти</h2>
    <dl class="facts">
      <dt>Поверх</dt><dd>{FLOOR_NAMES[place["floor"]]}</dd>
      <dt>Приміщення</dt><dd>{esc(rooms(place))}</dd>
      <dt>Графік</dt><dd data-live="hours">{esc(place["hours"])}</dd>
      <dt>Телефон</dt><dd data-live="phones">{esc(phones_text)}</dd>
      <dt>Адреса</dt><dd>ТЦ Garden Plaza New, {ADDRESS}</dd>
    </dl>
  </section>
  {more}
</main>
{footer_html(up, data)}
<script src="{up}gp-config.js"></script>
<script src="../live.js" defer></script>
<script src="{up}gp-lightbox.js" defer></script>
</body>
</html>
"""


# Сторінки закладів — готові файли, які перезбираються з бази лише кілька разів на добу.
# Цей скрипт при відкритті сторінки бере свіжий запис закладу з бази й оновлює назву, опис, графік,
# телефони, посилання, логотип і фото — тож зміни з кабінету видно одразу. Якщо база не відповіла
# або в приміщенні вже інший заклад (інша адреса сторінки), сторінка лишається як є.
LIVE_JS = r"""(function () {
  'use strict';
  var cfg = window.GP_CONFIG || {};
  var main = document.querySelector('main[data-unit]');
  if (!main || !cfg.supabaseUrl || !cfg.supabaseKey || !window.fetch) return;
  var UP = '../../';
  var TIMEOUT_MS = 5000;
  var ICON_PHONE = __ICON_PHONE__;
  var COLUMNS = 'unit_id,vacant,slug,name,about,hours,phones,links,logo_url,photos';

  function safeUrl(s) { return typeof s === 'string' && /^(https:\/\/|shops\/)[^"'<>\s]+$/.test(s) ? s : null; }
  function assetUrl(s) { return /^https:\/\//.test(s) ? s : UP + s; }
  function telLabel(n) {
    return n.indexOf('0800') === 0 ? '0 800 ' + n.slice(4, 7) + ' ' + n.slice(7)
      : '(' + n.slice(0, 3) + ') ' + n.slice(3, 6) + '-' + n.slice(6, 8) + '-' + n.slice(8);
  }
  function setText(selector, text) {
    document.querySelectorAll(selector).forEach(function (el) { el.textContent = text; });
  }

  function applyButtons(phones, links) {
    var box = document.querySelector('.acts');
    if (!box) return;
    box.querySelectorAll('.live').forEach(function (el) { el.remove(); });
    var first = box.firstChild;
    phones.forEach(function (n) {
      var a = document.createElement('a');
      a.className = 'btn main live';
      a.href = 'tel:+38' + n;
      a.innerHTML = ICON_PHONE;
      a.appendChild(document.createTextNode(telLabel(n)));
      box.insertBefore(a, first);
    });
    links.forEach(function (l) {
      var a = document.createElement('a');
      a.className = 'btn live';
      a.href = l.href;
      a.target = '_blank';
      a.rel = 'noopener';
      a.textContent = l.label;
      box.insertBefore(a, first);
    });
  }

  function applyLogo(url, name) {
    var box = document.querySelector('article.hero .logo');
    if (!box || !url) return;
    var img = document.createElement('img');
    img.src = assetUrl(url);
    img.alt = 'Логотип ' + name;
    img.width = 160;
    img.height = 160;
    box.className = 'logo';
    box.removeAttribute('aria-hidden');
    box.removeAttribute('role');
    box.removeAttribute('aria-label');
    box.replaceChildren(img);
  }

  function applyPhotos(photos, name) {
    var section = document.querySelector('[data-live="pics"]');
    if (!section) return;
    var box = section.querySelector('.pics');
    box.replaceChildren.apply(box, photos.map(function (src, i) {
      var img = document.createElement('img');
      img.src = assetUrl(src);
      img.alt = name + ', фото ' + (i + 1);
      img.loading = 'lazy';
      img.decoding = 'async';
      img.width = 640;
      img.height = 480;
      return img;
    }));
    section.hidden = photos.length === 0;
  }

  function apply(row) {
    var name = String(row.name || '').trim();
    if (!name) return;
    var hours = String(row.hours || '').trim() || main.dataset.defaultHours;
    var phones = (Array.isArray(row.phones) ? row.phones : []).filter(function (n) { return /^0\d{9}$/.test(n); });
    if (!phones.length) phones = [main.dataset.mallPhone];
    var links = (Array.isArray(row.links) ? row.links : []).filter(function (l) { return l && /^https?:\/\//.test(l.href || ''); })
      .map(function (l) { return { href: String(l.href), label: String(l.label || l.href) }; });
    var photos = (Array.isArray(row.photos) ? row.photos : []).map(safeUrl).filter(Boolean);
    var h1 = document.querySelector('article.hero h1');
    if (h1 && h1.textContent !== name) {
      document.title = document.title.replace(h1.textContent, name);
      h1.textContent = name;
    }
    setText('[data-live="about"]', String(row.about || '').trim() || name + ' у ТЦ Garden Plaza New.');
    setText('[data-live="hours"]', hours);
    setText('[data-live="phones"]', phones.map(telLabel).join(', '));
    applyButtons(phones, links);
    applyLogo(safeUrl(row.logo_url), name);
    applyPhotos(photos, name);
  }

  var ctrl = 'AbortController' in window ? new AbortController() : null;
  var timer = setTimeout(function () { if (ctrl) ctrl.abort(); }, TIMEOUT_MS);
  fetch(cfg.supabaseUrl + '/rest/v1/units?unit_id=eq.' + encodeURIComponent(main.dataset.unit) + '&select=' + COLUMNS,
      { headers: { apikey: cfg.supabaseKey }, signal: ctrl ? ctrl.signal : undefined })
    .then(function (res) { if (!res.ok) throw new Error('база відповіла ' + res.status); return res.json(); })
    .then(function (rows) {
      var row = rows && rows[0];
      // вільне приміщення або вже інший заклад: ця сторінка про попереднього орендаря, її не чіпаємо
      if (!row || row.vacant || row.slug !== main.dataset.slug) return;
      apply(row);
    })
    .catch(function (err) { console.warn('Свіжі дані закладу не завантажились, показуємо збережені:', err); })
    .then(function () { clearTimeout(timer); });
})();
"""


def all_places_page(places, data):
    up = "../"
    canonical = f"{BASE_URL}zaklady/"
    title = "Усі заклади — ТЦ Garden Plaza New, Нересниця"
    description = "Магазини, ресторан, готель, спортзал, клініка й послуги ТЦ Garden Plaza New у Нересниці: поверх, графік і телефон кожного закладу."
    floors = ""
    for f in (1, 2, 3, 4):
        group = sorted((p for p in places.values() if p["floor"] == f), key=lambda p: p["name"].lower())
        tiles = "".join(tile_html(p, data, up, f"{p['slug']}/") for p in group)
        floors += f'<section><h2>{FLOOR_NAMES[f]}</h2><div class="tiles">{tiles}</div></section>'
    return f"""{head_html(title, description, canonical, BASE_URL + "og.jpg", up, data)}
<body>
{topbar_html(up, data)}
<main class="wrap">
  <nav class="crumbs" aria-label="Ви тут"><a href="{up}">Головна</a> <span>›</span> Заклади</nav>
  <h1 class="page-title">Усі заклади</h1>
  <p class="lead">{len(places)} закладів на чотирьох поверхах. Оберіть заклад: покажемо опис, графік, телефон і де він на плані.</p>
  {floors}
</main>
{footer_html(up, data)}
</body>
</html>
"""


def sitemap_xml(places):
    # без lastmod: інакше файл мінявся б щодня й GitHub щодня робив би зайвий коміт
    urls = [BASE_URL, f"{BASE_URL}zaklady/"] + [f"{BASE_URL}zaklady/{slug}/" for slug in places]
    rows = "".join(f"  <url><loc>{u}</loc></url>\n" for u in urls)
    return f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n{rows}</urlset>\n'


PAGE_CSS = """
:root{--gold:#C9A46A;--gold-hi:#E8CC94;--cream:#F4EADC;--muted:#B5A998;
  --serif:'Cormorant Garamond',Georgia,serif;--sans:'Geist',system-ui,sans-serif;
  --sal:env(safe-area-inset-left,0px);--sar:env(safe-area-inset-right,0px)}
*{box-sizing:border-box}
html{-webkit-text-size-adjust:100%}
body{margin:0;min-height:100vh;background:radial-gradient(120% 50% at 50% -10%,rgba(201,164,106,.13),transparent 62%),#0A0806;color:var(--cream);font:400 16px/1.6 var(--sans);-webkit-font-smoothing:antialiased}
a{color:inherit}
a,button{-webkit-tap-highlight-color:transparent}
:focus-visible{outline:2px solid var(--gold-hi);outline-offset:3px}
.wrap{max-width:940px;margin:0 auto;padding:0 max(18px,var(--sar)) 0 max(18px,var(--sal))}
.top{position:sticky;top:0;z-index:10;padding-top:env(safe-area-inset-top);background:rgba(10,8,6,.86);-webkit-backdrop-filter:blur(12px);backdrop-filter:blur(12px);border-bottom:1px solid rgba(201,164,106,.15)}
.top .wrap{display:flex;align-items:center;justify-content:space-between;gap:12px;min-height:64px}
.brand{display:flex;align-items:center;gap:10px;text-decoration:none}
.brand img{display:block;width:38px;height:38px}
.brand span{font:600 14px/1.05 var(--sans);letter-spacing:.1em}
.call{display:flex;align-items:center;gap:8px;padding:9px 15px;border-radius:99px;border:1px solid rgba(201,164,106,.45);color:var(--gold-hi);text-decoration:none;font:600 13px/1 var(--sans);white-space:nowrap}
.call svg{width:15px;height:15px}
.crumbs{margin:22px 0 14px;font-size:13px;color:var(--muted)}
.crumbs a{color:var(--muted);text-decoration:none}
.crumbs a:hover{color:var(--gold-hi)}
.crumbs span{margin:0 4px;opacity:.6}
.hero{display:grid;grid-template-columns:auto 1fr;gap:22px;align-items:center;padding:22px;border-radius:22px;border:1px solid rgba(201,164,106,.22);background:linear-gradient(180deg,rgba(28,22,16,.92),rgba(14,11,8,.92))}
.logo{width:120px;height:120px;border-radius:20px;border:1px solid rgba(201,164,106,.3);background:#0B0907;display:grid;place-items:center;overflow:hidden}
.logo img{display:block;width:100%;height:100%;object-fit:cover}
.logo.wide{width:auto;min-width:120px;max-width:260px;padding:0 20px}
.logo .wm{zoom:1.9}
.mono{font:500 60px/1 var(--serif);color:var(--gold-hi)}
.tag{display:inline-flex;align-items:center;gap:8px;font-size:13px;color:var(--muted)}
.tag i{width:9px;height:9px;border-radius:3px;background:var(--c)}
h1{margin:6px 0 6px;font:500 clamp(38px,7vw,60px)/1.02 var(--serif);color:#fff}
.where{margin:0;font-size:14px;color:var(--muted)}
.hrs{margin:4px 0 0;font-size:15px;color:var(--gold-hi)}
.acts{display:flex;flex-wrap:wrap;gap:10px;margin-top:18px}
.btn{flex:1 1 210px;display:flex;align-items:center;justify-content:center;gap:9px;padding:14px 18px;border-radius:99px;border:1px solid var(--gold);color:var(--gold-hi);text-decoration:none;font:600 14px/1.2 var(--sans);text-align:center;transition:background .2s}
.btn:hover{background:rgba(201,164,106,.14)}
.btn.main{background:linear-gradient(180deg,#EED39C,#C9A46A);color:#100C08;border-color:#EED39C}
.btn.main:hover{filter:brightness(1.06)}
.btn svg{flex:none;width:16px;height:16px}
section{margin-top:36px}
h2{margin:0 0 14px;font:500 32px/1.1 var(--serif)}
.page-title{margin:4px 0 10px}
.lead{max-width:60ch;color:#D9CDBB}
.about{margin:0;max-width:64ch;font-size:16.5px;line-height:1.7;color:#D9CDBB}
.pics{display:grid;grid-template-columns:repeat(auto-fill,minmax(240px,1fr));gap:10px}
.pics img{display:block;width:100%;height:auto;aspect-ratio:4/3;object-fit:cover;border-radius:14px;border:1px solid rgba(201,164,106,.25);background:#1A140F}
.facts{display:grid;grid-template-columns:max-content 1fr;gap:10px 22px;margin:0;padding:18px 20px;border-radius:16px;border:1px solid rgba(201,164,106,.18);background:rgba(20,16,12,.7)}
.facts dt{color:var(--muted)}
.facts dd{margin:0}
.tiles{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:10px}
.tile{display:flex;flex-direction:column;align-items:center;justify-content:center;gap:9px;min-height:94px;padding:10px;border-radius:14px;border:1px solid rgba(201,164,106,.18);background:linear-gradient(180deg,#14100C,#0B0907);text-decoration:none;text-align:center;transition:border-color .2s}
.tile:hover{border-color:var(--gold)}
.tile small{font:400 11.5px/1 var(--sans);color:var(--muted)}
footer{margin-top:52px;padding:26px 0 calc(32px + env(safe-area-inset-bottom));border-top:1px solid rgba(201,164,106,.15);font-size:14px;color:var(--muted)}
footer p{margin:0 0 8px}
footer strong{color:var(--cream)}
footer a{color:var(--gold-hi);text-decoration:none}
.foot-links{display:flex;flex-wrap:wrap;gap:8px 18px}
.wm{line-height:1;white-space:nowrap;color:#fff}
.wm-gp{font:600 15px/1 var(--serif);color:var(--gold-hi);text-align:center;letter-spacing:.06em;text-transform:uppercase}
.wm-mezey{display:flex;flex-direction:column;align-items:center;gap:4px}
.wm-mezey svg{display:block;width:15px;height:18px;fill:#fff}
.wm-mezey span{font:500 13px/1 var(--sans);letter-spacing:.02em;color:#fff}
.wm-gent{font:500 11px var(--serif);letter-spacing:.14em}
.wm-credo{font:800 16px/1 var(--sans);color:#5FB3C9;letter-spacing:.06em;text-align:center}
.wm-credo small{display:block;font:400 10px var(--sans);color:#9FCFDB;letter-spacing:.2em;margin-top:3px;text-transform:uppercase}
.wm-gymmaxi{display:flex;align-items:center;gap:7px;text-align:left}
.wm-gymmaxi svg{flex:none;width:15px;height:21px;fill:#FFE100}
.wm-gymmaxi span{font:900 11px/1 var(--sans);letter-spacing:.03em;color:#fff}
.wm-gymmaxi b{display:block;margin-top:1px;font-size:15px}
.wm-tiffany{font:600 14px/1 var(--serif);letter-spacing:.16em;color:#81D8D0;text-align:center}
.wm-tiffany small{display:block;margin-top:4px;font:400 9px var(--sans);letter-spacing:.18em;color:#A9E3DE;text-transform:uppercase}
.wm-img img{display:block;width:auto;height:15px;max-width:100%}
.wm-mid img{height:20px}
.wm-tall img{height:30px}
.wm-up img{height:28px;max-width:100%;object-fit:contain}
.wm-hotel{font:500 12px var(--serif);color:var(--gold-hi);letter-spacing:.18em}
.wm-plain{font:600 14px/1.15 var(--serif);letter-spacing:.1em;text-transform:uppercase;color:var(--gold-hi);white-space:normal;text-align:center}
@media (max-width:560px){
  .hero{grid-template-columns:1fr;gap:16px;padding:18px}
  .logo{width:96px;height:96px;border-radius:18px}
  .logo.wide{width:auto;height:96px}
  .logo .wm{zoom:1.6}
  .btn{flex-basis:100%}
  .facts{grid-template-columns:1fr;gap:2px}
  .facts dd{margin-bottom:10px}
  .tiles{grid-template-columns:repeat(2,1fr)}
}
"""


def main():
    site = Path(sys.argv[1]).expanduser().resolve()
    from_base_only = "--from-base" in sys.argv[2:]
    data = load_site(site / "index.html")
    cfg = base_config(site)
    if cfg:
        rows = load_base_rows(cfg)
        print(f"дані з бази: {len(rows)} приміщень")
    elif from_base_only:
        print("базу ще не налаштовано (gp-config.js порожній) — сторінки не змінено")
        return
    else:
        rows = builtin_units(data, site)
        print("базу ще не налаштовано — дані з index.html")
    places = build_places(rows, data)
    out = site / "zaklady"
    if out.exists():
        shutil.rmtree(out)
    for slug, place in places.items():
        page = out / slug / "index.html"
        page.parent.mkdir(parents=True, exist_ok=True)
        page.write_text(place_page(place, places, data), encoding="utf-8")
    (out / "index.html").write_text(all_places_page(places, data), encoding="utf-8")
    (out / "live.js").write_text(LIVE_JS.replace("__ICON_PHONE__", json.dumps(ICON_PHONE)), encoding="utf-8")
    (site / "sitemap.xml").write_text(sitemap_xml(places), encoding="utf-8")
    print(f"сторінок закладів: {len(places)}")
    for slug, p in places.items():
        print(f"  zaklady/{slug}/  {p['name']}  ({rooms(p)})  фото: {len(p['pics'])}  телефонів: {len(p['phones'])}")


if __name__ == "__main__":
    main()
