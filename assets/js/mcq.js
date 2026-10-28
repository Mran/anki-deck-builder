(function () {
  // 包在 IIFE 中:Anki 桌面端复用 webview,顶层 const/let 会在第二张卡上重复声明报错。
  var roots = document.querySelectorAll('.ak-mcq');
  var root = roots[roots.length - 1];
  if (!root || root.getAttribute('data-ready')) return;
  root.setAttribute('data-ready', '1');

  var side = root.getAttribute('data-side');
  var box = root.querySelector('.ak-opts');
  var rawOpts = root.querySelector('.ak-raw-opts').innerHTML;
  var rawAns = root.querySelector('.ak-raw-ans').textContent;
  var shuffle = /^\s*(1|true|yes|y|是)\s*$/i.test(root.querySelector('.ak-raw-shuffle').textContent);
  var L = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ';

  // Anki 编辑器把换行存成 <br>、<div> 或 \n,三种都要支持
  var opts = rawOpts
    .replace(/<div[^>]*>/gi, '').replace(/<\/div>/gi, '<br>').replace(/\n/g, '<br>')
    .split(/<br\s*\/?>/i)
    .map(function (s) { return s.trim(); })
    .filter(function (s) { return s.replace(/<[^>]*>|&nbsp;/g, '').trim() !== ''; });

  var answer = {};
  (rawAns.toUpperCase().match(/[A-Z]|\d+/g) || []).forEach(function (t) {
    var i = /\d/.test(t) ? parseInt(t, 10) - 1 : L.indexOf(t);
    if (i >= 0 && i < opts.length) answer[i] = true;
  });
  var nAns = Object.keys(answer).length;
  var multi = nAns > 1;

  function hash(s) {
    var h = 0;
    for (var i = 0; i < s.length; i++) h = (h * 31 + s.charCodeAt(i)) | 0;
    return 'ak-mcq-' + h;
  }
  var key = hash(root.querySelector('.ak-q').textContent + rawOpts);
  function load() { try { return JSON.parse(sessionStorage.getItem(key)); } catch (e) { return null; } }
  function save(v) { try { sessionStorage.setItem(key, JSON.stringify(v)); } catch (e) {} }

  var state = (side === 'back' ? load() : null) || { order: null, sel: [] };
  if (!state.order) {
    state.order = opts.map(function (_, i) { return i; });
    if (shuffle && side === 'front') {
      for (var i = state.order.length - 1; i > 0; i--) {
        var j = Math.floor(Math.random() * (i + 1));
        var t = state.order[i]; state.order[i] = state.order[j]; state.order[j] = t;
      }
    }
  }
  if (side === 'front') save(state);

  var els = [];
  state.order.forEach(function (orig, pos) {
    var el = document.createElement('div');
    el.className = 'ak-opt';
    el.innerHTML = '<span class="ak-letter">' + L[pos] + '</span><span class="ak-opt-text">' + opts[orig] + '</span>';
    el.setAttribute('data-i', orig);
    box.appendChild(el);
    els.push(el);
  });

  if (side === 'front') {
    var hint = root.querySelector('.ak-mcq-hint');
    if (hint) hint.textContent = multi ? '[[t:select_all]]' : '[[t:select_one]]';
    els.forEach(function (el) {
      el.addEventListener('click', function () {
        var i = parseInt(el.getAttribute('data-i'), 10);
        var at = state.sel.indexOf(i);
        if (multi) {
          if (at >= 0) state.sel.splice(at, 1); else state.sel.push(i);
        } else {
          state.sel = at >= 0 ? [] : [i];
        }
        els.forEach(function (e) {
          var k = parseInt(e.getAttribute('data-i'), 10);
          e.classList.toggle('is-selected', state.sel.indexOf(k) >= 0);
        });
        save(state);
      });
    });
    return;
  }

  // 背面:标出正确/错误/漏选;没有作答记录时只标正确答案
  box.classList.add('is-revealed');
  var answered = state.sel && state.sel.length > 0;
  var allRight = true;
  els.forEach(function (el) {
    var i = parseInt(el.getAttribute('data-i'), 10);
    var chosen = state.sel.indexOf(i) >= 0;
    if (answer[i]) {
      el.classList.add('is-correct');
      if (answered && !chosen) { el.classList.add('is-missed'); allRight = false; }
    } else if (chosen) {
      el.classList.add('is-wrong');
      allRight = false;
    }
  });
  var verdict = root.querySelector('.ak-verdict');
  if (answered && verdict) {
    verdict.classList.add(allRight ? 'is-good' : 'is-bad');
    verdict.textContent = allRight ? '[[t:correct]]' : '[[t:wrong]]';
  }
  try { sessionStorage.removeItem(key); } catch (e) {}
})();
