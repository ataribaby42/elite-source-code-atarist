(() => {
  const artwork = document.querySelector('.artwork-toggle');
  if (!artwork) return;
  let selected = false;
  const show = value => artwork.classList.toggle('is-alternative', value);
  artwork.addEventListener('pointerenter', event => {
    if (event.pointerType === 'mouse') show(true);
  });
  artwork.addEventListener('pointerleave', () => show(selected));
  artwork.addEventListener('click', () => {
    selected = !selected;
    artwork.setAttribute('aria-pressed', String(selected));
    artwork.setAttribute('aria-label', selected
      ? 'Show original Leaving Lave artwork' : 'Show 16-bit Leaving Lave artwork');
    show(selected);
  });
})();
