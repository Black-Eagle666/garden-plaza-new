/* Вікно обрізки фото для кабінету: форма кадру, наближення, зсув, перетягування.
   GPCrop.open(img, { shapes, allowOriginal, hint }) → Promise: File (обрізане фото, PNG без втрат),
   рядок 'original' («Без обрізки») або null («Скасувати»). Стискає файл уже той, хто його завантажує. */
(function () {
  'use strict';

  var CROP = Object.freeze({ maxZoom: 4, frameMax: 560, frameMaxHeight: 0.42, margin: 56, outSide: 1600 });
  var STYLE_ID = 'gp-crop-style';
  var CSS = '.crop{position:fixed;inset:0;z-index:60;display:grid;place-items:center;padding:12px;background:rgba(5,4,3,.9);overflow:auto}' +
    '.crop-card{width:min(100%,620px);background:var(--panel);border:1px solid var(--line-strong);border-radius:16px;padding:16px}' +
    '.crop-card h2{font-family:var(--serif);font-weight:500;font-size:26px;margin:0 0 4px}' +
    '.crop-card .hint{margin:0 0 12px}' +
    '.crop-frame{position:relative;margin:0 auto 14px;overflow:hidden;border-radius:10px;border:1px solid var(--gold);background:#000;cursor:grab;touch-action:none;user-select:none;-webkit-user-select:none}' +
    '.crop-frame.is-drag{cursor:grabbing}' +
    '.crop-frame img{position:absolute;left:0;top:0;max-width:none;transform-origin:0 0;pointer-events:none;-webkit-user-drag:none}' +
    '.crop-shapes{display:flex;flex-wrap:wrap;gap:8px;margin:0 0 12px}' +
    '.crop-shapes button{min-height:38px;padding:6px 14px;border-radius:999px;border:1px solid var(--line);background:var(--panel-2);color:var(--cream);font-size:14px;cursor:pointer}' +
    '.crop-shapes button[aria-pressed=true]{background:linear-gradient(135deg,#EED39C,#C9A46A);color:#1A130A;border-color:transparent;font-weight:600}' +
    '.crop-range{display:grid;grid-template-columns:118px 1fr;align-items:center;gap:10px;margin:0 0 8px;font-size:14px;color:var(--gold-light)}' +
    '.crop-range input{width:100%;accent-color:#C9A46A;min-height:32px}' +
    '.crop-actions{display:flex;flex-wrap:wrap;gap:8px;justify-content:flex-end;margin-top:14px}';

  function ensureStyle() {
    if (document.getElementById(STYLE_ID)) return;
    var style = document.createElement('style');
    style.id = STYLE_ID;
    style.textContent = CSS;
    document.head.appendChild(style);
  }

  function clamp01(v) { return Math.min(1, Math.max(0, v)); }

  function open(img, options) {
    var shapes = options.shapes;
    var hint = options.hint || 'Тягніть фото в рамці або рухайте повзунки. У рамці те, що буде видно на сайті.';
    ensureStyle();
    return new Promise(function (resolve) {
      var view = Object.freeze({ shape: shapes[0], zoom: 1, px: 0.5, py: 0.5, w: 0, h: 0 });
      var drag = null;
      var box = document.createElement('div');
      box.className = 'crop';
      box.setAttribute('role', 'dialog');
      box.setAttribute('aria-modal', 'true');
      box.setAttribute('aria-label', 'Обрізка фото');
      box.innerHTML = '<div class="crop-card"><h2>Обрізати фото</h2><p class="hint"></p>' +
        '<div class="crop-shapes" role="group" aria-label="Форма кадру"></div>' +
        '<div class="crop-frame"></div>' +
        '<label class="crop-range">Наблизити<input type="range" data-range="zoom" min="1" max="' + CROP.maxZoom + '" step="0.01" value="1"></label>' +
        '<label class="crop-range">По горизонталі<input type="range" data-range="px" min="0" max="1" step="0.005" value="0.5"></label>' +
        '<label class="crop-range">По вертикалі<input type="range" data-range="py" min="0" max="1" step="0.005" value="0.5"></label>' +
        '<div class="crop-actions"><button type="button" class="btn btn-small" data-crop="cancel">Скасувати</button>' +
          (options.allowOriginal ? '<button type="button" class="btn btn-small" data-crop="original">Без обрізки</button>' : '') +
          '<button type="button" class="btn btn-small btn-main" data-crop="done">Готово</button></div></div>';
      box.querySelector('.hint').textContent = hint;
      var shapesBox = box.querySelector('.crop-shapes');
      shapes.forEach(function (sh) {
        var button = document.createElement('button');
        button.type = 'button';
        button.setAttribute('data-shape', sh.id);
        button.textContent = sh.label;
        shapesBox.appendChild(button);
      });
      var frame = box.querySelector('.crop-frame');
      var inputs = { zoom: box.querySelector('[data-range="zoom"]'), px: box.querySelector('[data-range="px"]'), py: box.querySelector('[data-range="py"]') };
      frame.appendChild(img);

      function setView(patch) { view = Object.freeze(Object.assign({}, view, patch)); }
      // масштаб, за якого фото повністю закриває рамку, помножений на наближення
      function scale() { return Math.max(view.w / img.naturalWidth, view.h / img.naturalHeight) * view.zoom; }
      function slack() { return { x: img.naturalWidth * scale() - view.w, y: img.naturalHeight * scale() - view.h }; }

      function paint() {
        var s = scale(), free = slack();
        img.style.transform = 'translate(' + (-free.x * view.px) + 'px,' + (-free.y * view.py) + 'px) scale(' + s + ')';
        inputs.zoom.value = view.zoom;
        inputs.px.value = view.px;
        inputs.py.value = view.py;
        // повзунок зсуву має сенс, лише коли фото в цьому напрямку ширше за рамку
        inputs.px.disabled = free.x < 1;
        inputs.py.disabled = free.y < 1;
        shapesBox.querySelectorAll('[data-shape]').forEach(function (b) {
          b.setAttribute('aria-pressed', String(b.getAttribute('data-shape') === view.shape.id));
        });
      }

      function layout() {
        var maxW = Math.min(CROP.frameMax, window.innerWidth - CROP.margin);
        var maxH = Math.max(180, window.innerHeight * CROP.frameMaxHeight);
        var w = Math.min(maxW, maxH * view.shape.ratio);
        setView({ w: Math.round(w), h: Math.round(w / view.shape.ratio) });
        frame.style.width = view.w + 'px';
        frame.style.height = view.h + 'px';
        paint();
      }

      function finish(result) {
        document.removeEventListener('keydown', onKey, true);
        window.removeEventListener('resize', layout);
        box.remove();
        resolve(result);
      }

      function exportFile() {
        var s = scale(), free = slack();
        var sw = view.w / s, sh = view.h / s;
        var k = Math.min(1, CROP.outSide / Math.max(sw, sh));
        var canvas = document.createElement('canvas');
        canvas.width = Math.max(1, Math.round(sw * k));
        canvas.height = Math.max(1, Math.round(sh * k));
        var ctx = canvas.getContext('2d');
        ctx.imageSmoothingQuality = 'high';
        ctx.drawImage(img, free.x * view.px / s, free.y * view.py / s, sw, sh, 0, 0, canvas.width, canvas.height);
        canvas.toBlob(function (blob) {
          finish(blob ? new File([blob], 'obrizane.png', { type: 'image/png' }) : null);
        }, 'image/png');
      }

      function onKey(event) {
        if (event.key !== 'Escape') return;
        event.preventDefault();
        event.stopImmediatePropagation();
        finish(null);
      }

      box.addEventListener('click', function (event) {
        var shapeBtn = event.target.closest('[data-shape]');
        if (shapeBtn) {
          var picked = shapes.find(function (sh) { return sh.id === shapeBtn.getAttribute('data-shape'); });
          setView({ shape: picked, zoom: 1, px: 0.5, py: 0.5 });
          layout();
          return;
        }
        var act = event.target.closest('[data-crop]');
        if (!act) return;
        var what = act.getAttribute('data-crop');
        if (what === 'done') exportFile();
        else finish(what === 'original' ? 'original' : null);
      });
      Object.keys(inputs).forEach(function (name) {
        inputs[name].addEventListener('input', function () {
          var patch = {};
          patch[name] = Number(inputs[name].value);
          setView(patch);
          paint();
        });
      });
      frame.addEventListener('pointerdown', function (event) {
        drag = { x: event.clientX, y: event.clientY, px: view.px, py: view.py };
        // захоплення вказівника — зручність (рух за межами рамки); якщо браузер відмовив, тягнути все одно можна
        try { frame.setPointerCapture(event.pointerId); } catch (err) { console.warn('[кабінет] захоплення вказівника не вдалося:', err); }
        frame.classList.add('is-drag');
      });
      frame.addEventListener('pointermove', function (event) {
        if (!drag) return;
        var free = slack();
        setView({
          px: free.x > 0 ? clamp01(drag.px - (event.clientX - drag.x) / free.x) : view.px,
          py: free.y > 0 ? clamp01(drag.py - (event.clientY - drag.y) / free.y) : view.py
        });
        paint();
      });
      ['pointerup', 'pointercancel'].forEach(function (name) {
        frame.addEventListener(name, function () { drag = null; frame.classList.remove('is-drag'); });
      });
      document.addEventListener('keydown', onKey, true);
      window.addEventListener('resize', layout);
      document.body.appendChild(box);
      layout();
      box.querySelector('[data-crop="done"]').focus();
    });
  }

  window.GPCrop = Object.freeze({ open: open });
})();
