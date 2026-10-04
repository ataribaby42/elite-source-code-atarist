# Elite — Amiga & Atari ST website

This directory is a standalone English static website for the enhanced Atari ST
game and native Amiga port. It adapts the companion Elite: Unbound website's
black-and-yellow layout, navigation and page structure.

## Preview

From the repository root:

```text
python -m http.server 8000 --bind 127.0.0.1 --directory web
```

Open `http://127.0.0.1:8000/`. No package installation or build step is required.
The site also uses relative links so it can be hosted under a subdirectory.

## Pages and maintenance

- `index.html`: introduction, features and the Leaving Lave artwork switch.
- `instruction-manual.html`: controls, trading, combat, contracts, docking,
  identity, radio, all twelve Game Options entries and commander saves.
- `technical-info.html`: hull specifications, AI weapons, native implementation
  and source references.
- `download.html`: release links, disk images and Amiga display-mode guidance.
- `credits.html`: original creators, project contributors and asset provenance.
- `galnet.html`: the author's public community and artwork links.

Edit the HTML files directly. Shared presentation is in `css/style.css` and
interaction is in `js/menu.js` and `js/site.js`. The game sources and current
platform READMEs are the authority for gameplay and Options descriptions;
`readme.txt` supplies the distribution names and display recommendations.
Keep documentation in English. Updating the website does not require rebuilding
the game or changing its changelog.

The menu supports keyboard navigation and Escape; page navigation remains
available without JavaScript. Artwork changes on mouse hover, and can be pinned
with a click, tap, Enter or Space. Wide reference tables scroll independently on
small screens. There are no external fonts, analytics or runtime dependencies.

## Assets and publication

The base stylesheet, navigation structure, favicon, portrait and original
Leaving Lave illustration come from the author's Elite: Unbound website:
<https://github.com/ataribaby42/elite-source-code-commodore-64> (`docs/`).
`assets/leaving-lave-16bit.png` is the user-supplied alternate image, preserved
byte for byte, with its Ham 2026 signature. Game screenshots are captured from
the enhanced versions. See the Credits page for the original game and music
attributions. Existing rights and licences continue to apply.

To publish, serve the contents of this directory as a static site. `.nojekyll`
is included for hosts that recognise it. Downloads point to the project's
release page; executable files and system ROMs are not copied into the site.
