(function () {
  var roots = document.querySelectorAll('.ak-tf');
  var root = roots[roots.length - 1];
  if (!root || root.getAttribute('data-ready')) return;
  root.setAttribute('data-ready', '1');

  var side = root.getAttribute('data-side');
  var raw = root.querySelector('.ak-raw-ans').textContent.trim().toLowerCase();
  var truth = /^(1|true|t|yes|y|对|是|正确|√|✓)$/.test(raw) ? '1' : '0';
  var btns = root.querySelectorAll('.ak-tf-btn');

  var h = 0, s = root.querySelector('.ak-statement').textContent;
  for (var i = 0; i < s.length; i++) h = (h * 31 + s.charCodeAt(i)) | 0;
  var key = 'ak-tf-' + h;

  if (side === 'front') {
    try { sessionStorage.removeItem(key); } catch (e) {}
    Array.prototype.forEach.call(btns, function (b) {
      b.addEventListener('click', function () {
        Array.prototype.forEach.call(btns, function (o) { o.classList.toggle('is-selected', o === b); });
        try { sessionStorage.setItem(key, b.getAttribute('data-v')); } catch (e) {}
      });
    });
    return;
  }

  var chosen = null;
  try { chosen = sessionStorage.getItem(key); sessionStorage.removeItem(key); } catch (e) {}
  root.querySelector('.ak-tf-btns').classList.add('is-revealed');
  Array.prototype.forEach.call(btns, function (b) {
    var v = b.getAttribute('data-v');
    if (v === truth) b.classList.add('is-correct');
    else if (v === chosen) b.classList.add('is-wrong');
  });
  var verdict = root.querySelector('.ak-verdict');
  if (chosen !== null && verdict) {
    var ok = chosen === truth;
    verdict.classList.add(ok ? 'is-good' : 'is-bad');
    verdict.textContent = ok ? '[[t:correct]]' : '[[t:wrong]]';
  }
})();
