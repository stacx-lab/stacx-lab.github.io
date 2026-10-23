(() => {
  let theme;
  try { theme = localStorage.getItem('theme'); } catch {}
  if (theme !== 'light' && theme !== 'dark') theme = matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
  document.documentElement.dataset.theme = theme;
  document.addEventListener('DOMContentLoaded', () => {
    document.querySelector('[data-theme-toggle]')?.addEventListener('click', () => {
      const next = document.documentElement.dataset.theme === 'dark' ? 'light' : 'dark';
      document.documentElement.dataset.theme = next;
      try { localStorage.setItem('theme', next); } catch {}
    });
  });
})();
