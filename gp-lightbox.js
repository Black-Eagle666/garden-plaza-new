// Перегляд фото на весь екран: фото закладів (картки, сторінки закладів) і фото новин.
// Натиснули на фото — воно відкривається великим; якщо поруч є інші фото того самого закладу, їх можна гортати.
(function () {
  'use strict';

  // фото, які можна відкрити: у галереях закладів і в картках новин
  var PHOTO_SELECTOR = '.pics img, .post > img';
  var GALLERY_SELECTOR = '.pics, .post';
  // жест пальцем: коротший за стільки пікселів вважаємо дотиком, а не гортанням
  var SWIPE_MIN_PX = 40;

  var style = document.createElement('style');
  style.textContent =
    PHOTO_SELECTOR.split(',').map(function (s) { return s.trim(); }).join(',') + '{cursor:zoom-in}' +
    '.gp-lb{position:fixed;inset:0;z-index:300;display:grid;place-items:center;background:rgba(5,4,3,.94);touch-action:none}' +
    '.gp-lb[hidden]{display:none}' +
    '.gp-lb img{max-width:calc(100vw - 24px);max-height:calc(100vh - 120px);max-height:calc(100dvh - 120px);width:auto;height:auto;object-fit:contain;border-radius:10px;box-shadow:0 20px 60px rgba(0,0,0,.6);cursor:zoom-out}' +
    '.gp-lb button{position:absolute;width:48px;height:48px;border-radius:50%;border:1px solid rgba(201,164,106,.5);background:rgba(14,11,8,.86);color:#E8CC94;font:400 26px/1 system-ui,sans-serif;cursor:pointer;display:grid;place-items:center;padding:0}' +
    '.gp-lb button:hover{background:rgba(201,164,106,.2)}' +
    '.gp-lb button:focus-visible{outline:2px solid #E8CC94;outline-offset:2px}' +
    '.gp-lb .gp-lb-close{top:max(14px,env(safe-area-inset-top));right:max(14px,env(safe-area-inset-right))}' +
    '.gp-lb .gp-lb-prev{left:max(10px,env(safe-area-inset-left));top:50%;margin-top:-24px}' +
    '.gp-lb .gp-lb-next{right:max(10px,env(safe-area-inset-right));top:50%;margin-top:-24px}' +
    '.gp-lb .gp-lb-count{position:absolute;left:0;right:0;bottom:max(16px,env(safe-area-inset-bottom));text-align:center;color:#B5A998;font:500 14px/1.4 system-ui,sans-serif;pointer-events:none}' +
    '@media (max-width:640px){.gp-lb .gp-lb-prev,.gp-lb .gp-lb-next{top:auto;bottom:max(52px,calc(env(safe-area-inset-bottom) + 44px));margin-top:0}}';
  document.head.appendChild(style);

  var box = document.createElement('div');
  box.className = 'gp-lb';
  box.hidden = true;
  box.setAttribute('role', 'dialog');
  box.setAttribute('aria-modal', 'true');
  box.setAttribute('aria-label', 'Перегляд фото');
  box.innerHTML =
    '<img alt="">' +
    '<button type="button" class="gp-lb-close" aria-label="Закрити перегляд">×</button>' +
    '<button type="button" class="gp-lb-prev" aria-label="Попереднє фото">‹</button>' +
    '<button type="button" class="gp-lb-next" aria-label="Наступне фото">›</button>' +
    '<p class="gp-lb-count" aria-live="polite"></p>';
  var view = box.querySelector('img');
  var prevBtn = box.querySelector('.gp-lb-prev');
  var nextBtn = box.querySelector('.gp-lb-next');
  var closeBtn = box.querySelector('.gp-lb-close');
  var counter = box.querySelector('.gp-lb-count');

  // items — фото відкритої галереї ({src, alt}); opener — фото, з якого відкрили (повертаємо на нього фокус)
  var state = Object.freeze({ items: [], index: 0, opener: null, touchX: null });
  function setState(patch) { state = Object.freeze(Object.assign({}, state, patch)); }
  function isOpen() { return !box.hidden; }

  function show(index) {
    var count = state.items.length;
    var next = (index + count) % count;
    setState({ index: next });
    view.src = state.items[next].src;
    view.alt = state.items[next].alt;
    var many = count > 1;
    prevBtn.hidden = !many;
    nextBtn.hidden = !many;
    counter.textContent = many ? (next + 1) + ' / ' + count : '';
  }

  function open(img) {
    var gallery = img.closest(GALLERY_SELECTOR);
    var all = gallery ? Array.prototype.slice.call(gallery.querySelectorAll(PHOTO_SELECTOR)) : [img];
    if (all.indexOf(img) === -1) all = [img];
    setState({
      items: all.map(function (el) { return { src: el.currentSrc || el.src, alt: el.alt || '' }; }),
      opener: img
    });
    if (!box.isConnected) document.body.appendChild(box);
    box.hidden = false;
    document.documentElement.style.overflow = 'hidden';
    show(all.indexOf(img));
    closeBtn.focus({ preventScroll: true });
  }

  function close() {
    if (!isOpen()) return;
    box.hidden = true;
    view.removeAttribute('src');
    document.documentElement.style.overflow = '';
    var opener = state.opener;
    setState({ items: [], opener: null, touchX: null });
    if (opener && opener.isConnected && typeof opener.focus === 'function') opener.focus({ preventScroll: true });
  }

  document.addEventListener('click', function (event) {
    if (isOpen()) return;
    var img = event.target.closest ? event.target.closest(PHOTO_SELECTOR) : null;
    if (!img || !(img.currentSrc || img.src)) return;
    event.preventDefault();
    event.stopPropagation();
    open(img);
  }, true);

  box.addEventListener('click', function (event) {
    if (event.target === prevBtn) { show(state.index - 1); return; }
    if (event.target === nextBtn) { show(state.index + 1); return; }
    close();
  });

  // перехоплюємо клавіші раніше за сторінку: Esc має закрити фото, а не план поверху під ним
  document.addEventListener('keydown', function (event) {
    if (!isOpen()) return;
    if (event.key === 'Escape') { event.preventDefault(); event.stopImmediatePropagation(); close(); return; }
    if (state.items.length > 1 && (event.key === 'ArrowLeft' || event.key === 'ArrowRight')) {
      event.preventDefault();
      event.stopImmediatePropagation();
      show(state.index + (event.key === 'ArrowRight' ? 1 : -1));
      return;
    }
    // фокус не має виходити з перегляду
    if (event.key === 'Tab') {
      var buttons = [closeBtn, prevBtn, nextBtn].filter(function (b) { return !b.hidden; });
      var at = buttons.indexOf(document.activeElement);
      event.preventDefault();
      buttons[(at + (event.shiftKey ? buttons.length - 1 : 1)) % buttons.length].focus();
    }
  }, true);

  box.addEventListener('touchstart', function (event) {
    setState({ touchX: event.touches.length === 1 ? event.touches[0].clientX : null });
  }, { passive: true });
  box.addEventListener('touchend', function (event) {
    if (state.touchX === null || state.items.length < 2) return;
    var dx = event.changedTouches[0].clientX - state.touchX;
    setState({ touchX: null });
    if (Math.abs(dx) < SWIPE_MIN_PX) return;
    // гортання не має спрацювати ще й як дотик, що закриває перегляд
    event.preventDefault();
    show(state.index + (dx < 0 ? 1 : -1));
  });
})();
