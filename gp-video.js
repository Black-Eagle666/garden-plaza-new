// Відео закладів і новин: файл зі сховища або посилання на YouTube.
// Один файл на весь сайт (головна, сторінки закладів, кабінет): розбір адреси, розмітка плеєра і його стилі.
// YouTube вантажиться лише після натискання — до того показуємо обкладинку, щоб сторінка лишалась швидкою.
(function () {
  'use strict';

  var YOUTUBE_ID = '[A-Za-z0-9_-]{11}';
  var YOUTUBE_RE = new RegExp('^https?://(?:www\\.|m\\.)?(?:youtube\\.com/(?:watch\\?(?:[^#]*&)?v=|shorts/|embed/|live/)|youtu\\.be/)(' + YOUTUBE_ID + ')(?:[?&#/].*)?$');
  var FILE_RE = /^https:\/\/[^"'<>\s]+\.(?:mp4|webm)$/i;
  var SHORTS_RE = /youtube\.com\/shorts\//;
  var EMBED_HOST = 'https://www.youtube-nocookie.com/embed/';
  var COVER_HOST = 'https://i.ytimg.com/vi/';

  function escapeHtml(value) {
    return String(value == null ? '' : value).replace(/[&<>"']/g, function (ch) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[ch];
    });
  }

  // Повертає {kind:'youtube', id, tall} або {kind:'file', src}; null — якщо це не відео, яке сайт уміє показати.
  function parse(url) {
    if (typeof url !== 'string') return null;
    var value = url.trim();
    var match = value.match(YOUTUBE_RE);
    if (match) return { kind: 'youtube', id: match[1], tall: SHORTS_RE.test(value) };
    if (FILE_RE.test(value)) return { kind: 'file', src: value };
    return null;
  }

  // Адреса, яку зберігаємо в базі: для YouTube — завжди один вигляд, для файлу — як є.
  function normalize(url) {
    var video = parse(url);
    if (!video) return null;
    if (video.kind === 'file') return video.src;
    return 'https://www.youtube.com/' + (video.tall ? 'shorts/' : 'watch?v=') + video.id;
  }

  // Розмітка плеєра. title — підпис для читачів екрана; poster — обкладинка для відеофайлу (необов'язково).
  function html(url, title, poster) {
    var video = parse(url);
    if (!video) return '';
    var label = escapeHtml(title || 'Відео');
    if (video.kind === 'file') {
      return '<video class="gp-vid" controls playsinline preload="metadata" src="' + escapeHtml(video.src) + '"' +
        (poster ? ' poster="' + escapeHtml(poster) + '"' : '') + ' aria-label="' + label + '"></video>';
    }
    return '<button type="button" class="gp-vid gp-yt' + (video.tall ? ' is-tall' : '') + '" data-yt="' + video.id + '" aria-label="Увімкнути відео: ' + label + '">' +
      '<img src="' + COVER_HOST + video.id + '/hqdefault.jpg" alt="" loading="lazy" decoding="async">' +
      '<span class="gp-yt-play" aria-hidden="true"></span></button>';
  }

  function play(button) {
    var frame = document.createElement('iframe');
    frame.className = button.className.replace('gp-yt', 'gp-yt-frame');
    frame.src = EMBED_HOST + button.getAttribute('data-yt') + '?autoplay=1&rel=0&playsinline=1';
    frame.title = (button.getAttribute('aria-label') || 'Відео').replace('Увімкнути відео: ', '');
    frame.allow = 'autoplay; encrypted-media; picture-in-picture; fullscreen';
    frame.allowFullscreen = true;
    button.replaceWith(frame);
  }

  var CSS =
    '.gp-vid{display:block;width:100%;aspect-ratio:16/9;border:1px solid rgba(201,164,106,.3);border-radius:10px;background:#000;overflow:hidden}' +
    'video.gp-vid{height:auto;max-height:80vh;object-fit:contain}' +
    '.gp-vid.is-tall{aspect-ratio:9/16;max-height:80vh;width:auto;max-width:100%;margin:0 auto}' +
    '.gp-yt{position:relative;padding:0;cursor:pointer}' +
    '.gp-yt img{display:block;width:100%;height:100%;object-fit:cover}' +
    '.gp-yt-play{position:absolute;left:50%;top:50%;width:64px;height:64px;margin:-32px 0 0 -32px;border-radius:50%;background:rgba(14,11,8,.82);border:1px solid rgba(232,204,148,.8)}' +
    '.gp-yt-play::after{content:"";position:absolute;left:25px;top:19px;border-style:solid;border-width:13px 0 13px 21px;border-color:transparent transparent transparent #E8CC94}' +
    '.gp-yt:hover .gp-yt-play,.gp-yt:focus-visible .gp-yt-play{background:rgba(201,164,106,.9)}' +
    '.gp-yt:hover .gp-yt-play::after,.gp-yt:focus-visible .gp-yt-play::after{border-left-color:#14100B}';

  var style = document.createElement('style');
  style.textContent = CSS;
  document.head.appendChild(style);

  document.addEventListener('click', function (event) {
    var button = event.target.closest ? event.target.closest('.gp-yt') : null;
    if (button) play(button);
  });

  window.GPVideo = Object.freeze({ parse: parse, normalize: normalize, html: html });
})();
