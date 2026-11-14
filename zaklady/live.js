(function () {
  'use strict';
  var cfg = window.GP_CONFIG || {};
  var main = document.querySelector('main[data-unit]');
  if (!main || !cfg.supabaseUrl || !cfg.supabaseKey || !window.fetch) return;
  var UP = '../../';
  var TIMEOUT_MS = 5000;
  var ICON_PHONE = "<svg viewBox=\"0 0 24 24\" aria-hidden=\"true\"><path fill=\"none\" stroke=\"currentColor\" stroke-width=\"1.8\" stroke-linecap=\"round\" stroke-linejoin=\"round\" d=\"M22 16.9v3a2 2 0 0 1-2.2 2 19.8 19.8 0 0 1-8.6-3.1 19.5 19.5 0 0 1-6-6A19.8 19.8 0 0 1 2.1 4.2 2 2 0 0 1 4.1 2h3a2 2 0 0 1 2 1.7c.1 1 .4 1.9.7 2.8a2 2 0 0 1-.5 2.1L8.1 9.9a16 16 0 0 0 6 6l1.3-1.3a2 2 0 0 1 2.1-.4c.9.3 1.8.6 2.8.7a2 2 0 0 1 1.7 2z\"/></svg>";
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
