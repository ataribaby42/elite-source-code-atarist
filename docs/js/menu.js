// Adapted from the companion Elite: Unbound site.
(() => {
  const toggle = document.getElementById('menu-toggle');
  const menu = document.getElementById('site-menu');
  const backdrop = document.querySelector('.menu-backdrop');
  const page = document.querySelector('.page-frame');
  const home = document.querySelector('.home-link');
  if (!toggle || !menu || !backdrop) return;
  const links = [...menu.querySelectorAll('a')];
  let open = false;
  menu.inert = true;
  backdrop.tabIndex = -1;

  function setOpen(value, returnFocus = false) {
    open = value;
    document.body.classList.toggle('menu-open', open);
    toggle.setAttribute('aria-expanded', String(open));
    toggle.setAttribute('aria-label', open ? 'Close menu' : 'Open menu');
    menu.inert = !open;
    if (page) page.inert = open;
    if (home) home.inert = open;
    backdrop.hidden = !open;
    if (open) {
      menu.setAttribute('aria-hidden', 'false');
      links[0]?.focus();
    } else {
      if (returnFocus) toggle.focus();
      menu.setAttribute('aria-hidden', 'true');
    }
  }

  toggle.addEventListener('click', () => setOpen(!open, open));
  backdrop.addEventListener('click', () => setOpen(false, true));
  links.forEach(link => link.addEventListener('click', () => setOpen(false, true)));
  document.addEventListener('keydown', event => {
    if (!open) return;
    if (event.key === 'Escape') {
      event.preventDefault();
      setOpen(false, true);
    } else if (event.key === 'Tab') {
      const cycle = [toggle, ...links];
      const index = cycle.indexOf(document.activeElement);
      event.preventDefault();
      cycle[(index + (event.shiftKey ? cycle.length - 1 : 1)) % cycle.length].focus();
    }
  });
})();
