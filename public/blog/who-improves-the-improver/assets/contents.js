(function () {
  var links = Array.prototype.slice.call(document.querySelectorAll('.rail a'));
  var map = {};
  links.forEach(function (a) {
    var el = document.querySelector(a.getAttribute('href'));
    if (el) { map[a.getAttribute('href').slice(1)] = a; }
  });
  var targets = Object.keys(map).map(function (id) { return document.getElementById(id); });
  if (!targets.length || !('IntersectionObserver' in window)) return;

  var visible = {};
  var io = new IntersectionObserver(function (entries) {
    entries.forEach(function (e) { visible[e.target.id] = e.isIntersecting ? e.boundingClientRect.top : null; });
    var best = null;
    targets.forEach(function (t) {
      if (visible[t.id] !== null && visible[t.id] !== undefined) {
        if (best === null || visible[t.id] < visible[best]) { best = t.id; }
      }
    });
    if (best) {
      links.forEach(function (a) { a.classList.remove('on'); });
      map[best].classList.add('on');
    }
  }, { rootMargin: '-10% 0px -72% 0px', threshold: 0 });

  targets.forEach(function (t) { io.observe(t); });
})();
