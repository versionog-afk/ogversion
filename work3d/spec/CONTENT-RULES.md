# /merch content rules

What the `/merch` page may say and show. Every sentence, alt text and link on the page is checked against this file. The design and build of the page are in `work3d/spec/SPEC.md`; where that spec lists exact texts (its sections 2.5 to 2.7), those texts already follow these rules.

Lithuanian texts are given exactly as they must appear. Where a text stands inside „…“ here, that outer pair only marks where it starts and ends; quotes inside it are part of the text.

## 1. Brand and site

- OG VERSION is a music project and streetwear name from Kaunas (Šilainiai district), Lithuania.
- Its album is „Nieko asmeniško 2“ (short: NA2), 26 tracks.
- The brand's site is ogversion.com. It also leads to the brand's tattoo studio and to its radio (links in section 4).
- The repository is a plain static site: no framework, and the host runs no build step. `merch/index.html` is served at `https://ogversion.com/merch`. All asset URLs are absolute (`/merch/p/01.jpg`).
- `/merch` is a full page about one T-shirt. The nine earlier merch photos stay on it as a bare grid (section 8).

## 2. The product

A real garment the brand has made:

- a black T-shirt, oversized, of heavy cloth;
- front: small lettering „NA2“ on the wearer's left chest, the letters built from euro banknotes;
- back: a large white line map of Šilainiai with the labels „IX FORTAS“, „A1 HIGHWAY“, „BALTŲ PR.“, „ŽEMAIČIŲ PL.“, „BALTIJOS G.“, and under it the caption „ŠILAINIAI, KAUNAS“.

On the page it is called „NA2 marškinėliai“. In the 3D view it is worn by a stylised figure, a sculpture rather than a portrait of anyone (section 9).

## 3. Facts

A reviewer will check every sentence.

**May be stated:**

- It is a T-shirt and it is black.
- Front: „NA2“ on the left side of the chest; the letters are made of euro banknotes.
- Back: a map of Šilainiai in white lines (Baltų prospektas, Žemaičių plentas, Baltijos gatvė, IX fortas, A1) with „ŠILAINIAI, KAUNAS“ under it.
- NA2 stands for the album „Nieko asmeniško 2“; the map shows the district OG VERSION comes from.
- Album facts: „Nieko asmeniško 2“, 26 trekai, klausyti YouTube.
- The words printed on the shirt may be quoted exactly as printed.
- The figure in the 3D view is a 3D model. The page says so quietly, in the status label „3D modelis“ and the facts row „Figūra – 3D modelis“.

**Unknown, and must not be stated or implied:** price, sizes, fabric weight or composition, print technique, stock or quantity, release date, shipping, returns, any contact channel, any limited-edition number.

- The cut and the weight of the cloth guide the 3D model and can be seen in the photos, but the page does not put them into words: they would read as claims about sizes and fabric.
- No size appears anywhere, including on the 3D model (no neck label with a size).

**The only availability sentence allowed** (the brand's own earlier line):

> Kaina ir dydžiai skelbiami kartu su dropu.

**Never on the page:** a buy button, a cart, a form, an email address, a phone number, a social-media contact.

**No third parties.** Do not claim or imply a partnership, licence, collaboration or "official" status with anyone. No third-party names, logos or wordmarks, neither in the copy nor as page chrome nor as imitated typography. The one exception is the word YouTube in the album link. The footer carries the line and the three links of section 6, nothing else.

## 4. Links

Allowed links, and no others:

| link | where | note |
|---|---|---|
| `https://ogversion.com/` | top bar brand „OG Version“; footer „ogversion.com“ | |
| `https://ogversion.com/47` | footer „47 Studio“ | the brand's tattoo studio |
| `https://ogversion.com/radio` | footer „Radio“ | |
| `https://www.youtube.com/channel/UCVeUe4Q80BmOzmjQXNHzBBA/releases` | album section, „Klausyti YouTube“ | opens in a new tab with `rel="noreferrer"`; hidden text „ (atsidaro naujame skirtuke)“ |
| same-page anchors | „Albumas“ → `#albumas`; skip link „Į turinį“ → `#turinys` | |

## 5. Voice and copy

- Language: Lithuanian, `lang="lt"`, correct diacritics (ą č ę ė į š ų ū ž), Lithuanian quotes „…“.
- Voice: terse, dry, street, confident. Short sentences. No marketing fluff, no emojis, no exclamation marks, no fake urgency.
- Keep the total copy small. Every sentence must be true under section 3.
- Voice samples from the brand's earlier page (for tone only; they are not page text):
  - „Albumas jau čia. Dabar jį galima apsivilkti.“
  - „Keturi daiktai, viena taisyklė: priekyje tylu, nugara daro visą darbą.“
  - „Kainos ir dydžiai paskelbiami kartu su dropu.“
- The page's own tagline is in that voice: „Priekyje tylu. Nugara daro visą darbą.“
- The third sample is close to the availability sentence but is not it. On the page only the wording of section 3 is used.

## 6. Required page content

1. A hero that makes the NA2 tee the unmistakable subject on first paint: the name, one line, an image.
2. The print story: what is on the front and what is on the back, and what the two stand for.
3. A small truthful facts block under the heading „Kol kas tiek“, as rows of label and value: „Daiktas – Marškinėliai“, „Spalva – Juoda“, „Priekis – „NA2“ iš eurų banknotų“, „Nugara – Šilainių žemėlapis“ and, in 3D mode only, „Figūra – 3D modelis“; then the availability sentence.
4. The nine existing photos as a bare grid with a click-to-fullscreen lightbox (section 8).
5. A way to the album: the section „Albumas“ with the album's name (in quotes, as on the page), „26 trekai“ and the link „Klausyti YouTube“.
6. Footer: „OG Version · Kaunas, Šilainiai“ and the three footer links of section 4 (site, tattoo studio, radio).

## 7. Head tags

Keep in `<head>`:

```html
<title>NA2 marškinėliai – OG VERSION merch</title>
<meta name="description" content="Juodi NA2 marškinėliai. Priekyje – „NA2“ iš eurų banknotų, nugaroje – Šilainių žemėlapis. Kaina ir dydžiai skelbiami kartu su dropu.">
<meta name="robots" content="noindex">
<link rel="canonical" href="https://ogversion.com/merch">
<link rel="icon" type="image/jpeg" href="/merch/v/ph/print-800.jpg">
<meta name="theme-color" content="#000000">
<meta property="og:type" content="website">
<meta property="og:url" content="https://ogversion.com/merch">
<meta property="og:title" content="NA2 marškinėliai – OG VERSION merch">
<meta property="og:description" content="Priekyje tylu. Nugara daro visą darbą.">
<meta property="og:image" content="https://ogversion.com/merch/v/og.jpg">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:image" content="https://ogversion.com/merch/v/og.jpg">
```

The page also carries, and keeps: the viewport tag with `viewport-fit=cover`, `color-scheme` dark, `og:site_name` „OG VERSION“, `og:locale` `lt_LT`, and `og:image:alt` with the alt of the photo `back` (section 9). Title, descriptions and alts are Lithuanian.

## 8. The nine gallery photos

`merch/p/01.jpg` … `09.jpg` are the existing NA2 merch photos, 4096 × 4096 px each. Do not modify these files and do not add files to `merch/p/`. The build writes 1024 px copies to `merch/v/g/`.

The owner deliberately made this grid bare. Keep it bare: edge to edge, square tiles, no captions, no prices, no text at all; a click opens the photo full screen. On the static page the grid has three columns, two on narrow screens; in 3D mode it is three by three at every width. Its only heading is visually hidden: „„Nieko asmeniško 2“ merch nuotraukos“.

Each photo has a short descriptive alt. The alts below are the exact texts, without an outer pair of quotes:

| file | shows | alt |
|---|---|---|
| 01 | black tee with NA2 money letters | Juodi marškinėliai su raidėmis „NA2“ iš eurų banknotų. |
| 02 | hoodie from the back at night | Juodas džemperis su gobtuvu iš nugaros naktį kieme, ant nugaros – daugiabutis. |
| 03 | cream long-sleeve with a collage | Kreminiai marškinėliai ilgomis rankovėmis su daugiabučio ir banknotų koliažu. |
| 04 | white tee from the back | Balti marškinėliai iš nugaros su užrašu „NIEKO ASMENIŠKO“. |
| 05 | NA2 "testing" tee, worn | Dėvimi juodi marškinėliai: perbraukta „NA2“ ir raudonas užrašas „testing“. |
| 06 | yellow tape tee, worn | Dėvimi juodi marškinėliai su geltona juosta „NEPERŽENGTI · NIEKO ASMENIŠKO“. |
| 07 | black tee with a small burning-car mark | Juodi marškinėliai su mažu oranžiniu degančio automobilio ženklu apačioje. |
| 08 | blue 112 cap | Mėlyna kepurė su baltu skaičiumi „112“. |
| 09 | sleeve tag detail | Rankogalio detalė: oranžinis dirželis su juoda etikete „NA2“. |

## 9. Real photos and the person in the reference material

The page shows three real photos of the tee. The build crops them from source photos in `work3d/ref/` and writes them to `merch/v/ph/`; their alts, again exact and without an outer pair of quotes:

| name | shows | alt |
|---|---|---|
| `back` | the tee worn, from the back | Dėvimi juodi NA2 marškinėliai iš nugaros: baltas Šilainių žemėlapis ir užrašas „ŠILAINIAI, KAUNAS“. |
| `front` | the tee worn, from the front | Dėvimi juodi marškinėliai iš priekio: kairėje krūtinės pusėje – „NA2“ iš eurų banknotų. |
| `print` | close-up of the chest print, caption „Spauda iš arti“ | Spauda iš arti: raidės „NA2“, sudėtos iš eurų banknotų, ant juodo audinio. |

Rules for the person who wears the tee in the owner's photos and video:

- She is a fit reference only: how the shirt hangs, where the prints sit, how large they are.
- Never reproduce her face or her likeness, neither in a published photo nor in the 3D figure. The two worn photos are cropped tightly to the garment: the room behind is barely visible and no part of her face is in the picture.
- Never publish the video.
- The 3D figure is a sculpture wearing the shirt: one matte plaster material for body and hair, no skin texture, no eye colour, no make-up.
- The owner's photos and video live in `work3d/ref/`. Only the two files that show no person, `print-closeup.jpg` and `mockup-sheet.jpg`, are in git; everything else there is local-only material that the owner supplies on the working computer.
- The repository is public: no original photo, video or frame that shows a person is ever committed. The page uses only the tight crops that the build writes to `merch/v/ph/`, and the share image `merch/v/og.jpg` made from one of them.
- The build does not take the two worn photos from the originals but from prepared copies: `worn-front.jpg`, 1125 × 1800 px, with its top edge at the neck, below the face, and `worn-back.jpg`, 1125 × 1500 px. Its crop fits only that framing, and it does not notice another one: given an uncut original it cuts higher and still finishes without an error. Run the photo step (the build variable `PHOTOS`) only with such sources; without it the committed crops and `og.jpg` are kept and stay valid. The spec has the details in its section 2.7.
- Before any commit that changes `merch/v/ph/` or `merch/v/og.jpg`, look at every one of those files: no face, and nothing by which she could be recognised.

## 10. Accessibility and performance

The spec has its own checklists for the 3D layer (its section 7). These rules come on top and hold for the static page as well:

- The body background is dark from the first paint: no white flash.
- Responsive from 360 px to 1920 px wide with no horizontal scroll; `env(safe-area-inset-*)` respected.
- One `<h1>`, logical heading order.
- Every product image has a meaningful Lithuanian alt; the nine grid photos have the short alts of section 8.
- Visible `:focus-visible` styles; every interactive element is reachable by keyboard.
- The lightbox is a proper dialog: `role="dialog"` and `aria-modal`, Esc closes it, a click closes it, focus moves in and returns to the trigger, there is a visible close button („Uždaryti“), and the page behind does not scroll while it is open.
- `prefers-reduced-motion` switches animation off.
- Text contrast is at least 4.5:1.
- Images: the static hero photo uses the 800 px file with a `srcset` to the 1600 px file and correct `sizes`; `fetchpriority="high"` on the hero image only; `loading="lazy"` and `decoding="async"` below the fold; `width` and `height` (or `aspect-ratio`) on every `<img>` so nothing shifts.
- Fonts: system font stacks only, as the page has them. No web fonts and no other external requests, so no late font can shift the layout.
- No console errors, no 404s.
