(function () {
  var path = window.location.pathname.replace(/\/$/, '');
  var links = document.querySelectorAll('[data-nav-link]');
  links.forEach(function (link) {
    var href = link.getAttribute('href').replace(/\/$/, '');
    if (href === path || (href === '/index.html' && (path === '' || path === '/'))) {
      link.setAttribute('aria-current', 'page');
    }
  });

  var observer = new IntersectionObserver(function (entries, obs) {
    entries.forEach(function (entry) {
      if (entry.isIntersecting) {
        entry.target.classList.add('visible');
        obs.unobserve(entry.target);
      }
    });
  }, { threshold: 0.14 });

  document.querySelectorAll('.reveal').forEach(function (el) {
    observer.observe(el);
  });
})();
