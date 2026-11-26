# /merch 3D build spec: the NA2 tee on a figure

Every design decision is made here. Put each number below in `merch/v/src/config.js` and use it as given: they are clamped starting values.

Where the page code departs from a number or rule here, a comment in `merch/v/src/config.js` marks the departure; the reason is given there or in the module the comment points to. There are two kinds:

- **Look.** Light intensities, the lights-out factors, the cloth colour and its rim gain were tuned on software renders. The spec value stays the reference, and the tuning is judged again on real hardware.
- **Geometry.** Two fixes change where things are rather than how they look, and are not reverted without the screenshots of 7.2 in hand. The three lamps and the environment turn with the camera's azimuth, so the back is lit like the front when the camera stands behind the figure (6.3 has the lamps fixed in the world). Each leg of the walk back to the front, BACK → az 265° → ITEM(−1), gets at least 0.30 S of scroll and later anchors move along, because a short facts plate leaves less scroll than that half circle needs (2.3).

Nothing has been measured on a real phone so far: headless Chromium with software WebGL2 was the only test bed, so every technique is a cheap, known one. On the owner's PC the page can now be tested on a real GPU and on real phones; do that before trusting any timing, quality tier or compositing decision below. The test hook `?3d=1` stays, because software-rendered headless tests still need it (5.1, 6.12, 7.2).

All paths are relative to the repository root (`.`). The page is `merch/`; the work folder is `work3d/` (dependencies, model, print art, reference material, tests, this spec). URLs that start with `/merch/` are the same files as served by the site.

## 0. Ground rules

- **Content source:** `merch/index.html`. Reuse its Lithuanian texts, alts, head tags, footer and lightbox verbatim. `work3d/spec/CONTENT-RULES.md` binds for facts, voice, allowed links and head tags.
- **Page work writes only** `merch/index.html` and `merch/v/**`. Models, art, tests and screenshots stay in `work3d/`. Never touch `merch/p/`. No commit, push, pull request or merge unless the owner asks for it.
- **Never add:** price, sizes, cart, buy button, stock or edition numbers, new links, or third-party names, logos or wordmarks (the album link already on the page stays). New microcopy is limited to the list in 2.5; product texts are the ones in 2.6.
- **Reference material:** `work3d/ref/` holds the owner's photos of the worn tee (back and front), a close-up of the chest print, a mock-up sheet and a short video with frames taken from it. Only the two files that show no person, `print-closeup.jpg` and `mockup-sheet.jpg`, are in git. Everything else in the folder is local-only: the owner supplies it on the working computer. The repository is public, so no original photo, video or frame that shows a person is ever committed; the page uses only the tight crops the build writes to `merch/v/ph/` (2.7). The person in the photos and video is only a fit reference: never reproduce her face or likeness, never publish the video.

### 0.1 Product

The page is about one real garment the brand has made:

- a black, oversized, heavy T-shirt;
- front: small lettering „NA2“ on the wearer's left chest, the letters built from euro banknotes;
- back: a large white line map of Šilainiai (labels „IX FORTAS“, „A1 HIGHWAY“, „BALTŲ PR.“, „ŽEMAIČIŲ PL.“, „BALTIJOS G.“) with the caption „ŠILAINIAI, KAUNAS“ under it.

In 3D the shirt is worn by a stylised human figure: the owner asked for a 3D model of the shirt and of a person.

### 0.2 Model contract

File: `work3d/model/current.glb`. It is work in progress and is replaced whenever a better version exists (it starts as a crude stand-in). Pass it to the build as `MODEL`. GLB, metres, Y up, the figure faces +Z and stands on y = 0, about 1.68 m tall, at most 130k triangles, may carry normal and occlusion maps on cloth meshes. The model must carry no size text (sizes are unknown).

Meshes are recognised by name exactly as the reference viewer `work3d/harness/viewer.html` does: first by mesh name, then by mesh + material + parent name. The classes and their patterns:

```
printFront   /print.?front/i
printBack    /print.?back/i
hair         /hair/i
pants        /pants|trouser/i
shoes        /shoe|sneaker|boot/i
body         /body|skin|mannequin|figure/i
tee          /tee|fabric|shirt|collar|rib|sleeve/i
```

| class | notes |
|---|---|
| printFront | exactly one. Decal on the wearer's left chest (+X), faces +Z, about 0.105 × 0.070 m, UV 0..1, v = 0 at the top, u grows to the viewer's right |
| printBack | exactly one. Decal centred on the back, faces −Z, about 0.38 × 0.507 m, UV 0..1, v = 0 at the top, u grows to the right as seen from behind |
| hair | optional |
| pants | wide trousers |
| shoes | optional |
| body | head, neck, arms, hands; faces hidden under clothes may be missing |
| tee | one or more cloth meshes |

Read every dimension from the file at load; tolerate missing optional classes; never hard-code geometry. Anchors computed at load:

- `F` = bounding box of everything; `T` = box of the tee meshes; `PF`, `PB` = boxes of the two prints.
- `TOP` = the box with T's x and z extent, from `T.min.y − 0.06` up to `F.max.y` (head to just below the hem). `C` = centre of `TOP`.
- The yaw axis is the vertical line through the centre of `F` in x and z.
- `Yr = F.max.y + 0.10` (rail height).

### 0.3 Print art

Print textures are RGBA PNG files, replaced when better versions exist: `work3d/art/front.png` (3:2), `work3d/art/back.png` (3:4, white lines on transparent), `work3d/art/meta.json` (pixel sizes and, for the back, `captionBox` = the UV box of „ŠILAINIAI, KAUNAS“). They reach the build as `FRONT`, `BACK` and `ARTMETA` (6.1). If `meta.json` is missing use `captionBox = {u0:.17, u1:.82, v0:.895, v1:.945}`.

### 0.4 Settled decisions

| question | decision |
|---|---|
| Base | A red line and a rack on a rail, in a black void. No courtyard, fog, floor, haze, far block or sign reflection; with no floor there is no shadow to fake. |
| Colour | Black void, bone text, one red line. Purple and pink exist only as light (6.5). |
| Type and figure | The real `<h1>` „NA2“ sits behind a transparent canvas; the front line „ŠILAINIAI, KAUNAS“ is HTML in front. An opaque-canvas switch is the escape hatch (6.11). |
| Figure | A sculpture wearing the shirt, not a simulated real person: plaster body and hair, no skin texture, no eye colour, no make-up. It stands; it does not hang. Its legs fade into the dark and no frame shows the feet as lit objects (6.4). |
| Scroll | The stage is viewport-fixed; text lives on solid black plates in normal flow. Nothing in WebGL is aligned to a natively scrolling element. |
| Ownership | The hand owns the figure's yaw. Scroll owns camera and light. Scroll never turns the figure: the camera walks round it, and the story only changes the allowed detents. |
| Red | One thin line, three stations: under the giant „NA2“ (the loader), under the caption of the back print, and as the rack rail. Never two at once. No glow. |
| Not built | Cloth vertex shader, flash, lamp rail, turn counter, poster image, 3D dimension line, hover parallax and pitch, stills mode, scripted focus scrolling, rack brush physics, double-tap, pendulum and lean, tap poke, slide-in arrival. |

## 1. Experience

A plaster figure in a black oversized tee stands in a void in front of a giant bone „NA2“ whose red underline is the loading bar. When it fills, the lights come on and the figure fades in turning and clicks to its front. Flick it: it coasts with weight and lands on front or back. Scrolling pushes the camera into the chest lettering while the „NA2“ sinks behind the figure. A black plate about the front wipes past; then the camera walks round to the back until the map fills the frame, and a second plate passes. When it leaves, the lights die and only the map and its caption stay lit, a red line under the caption. After the facts plate the camera completes its circle and the figure is one item under a red rail that also carries the nine NA2 photos. Grid, album and footer follow.

Signature moments:

1. **Flick and click.** Inertia, front/back detents, overshoot, a 10 ms haptic tick. Cost: transforms.
2. **The eclipse.** The „NA2“ behaves like a sign 2 m behind the figure and is swallowed in the push-in. Cost: one CSS transform per frame.
3. **The walk round.** The camera circles the figure once, 0° to 360°: chest, side, back, the other side, front again. Cost: keyframes.
4. **Only the map.** Lights out; the map and its caption stay lit; a red line draws under the caption and stays glued to the cloth while you wiggle the figure. Cost: three intensities, one unlit copy of the back print, one quad.
5. **The rail.** The loader line returns as a rail; nine lit panels swing on it when flicked. Cost: about 40 quads, no lights, no render targets.

## 2. Layout and storyboard

### 2.1 Page blocks

One document. Without `class="gl"` on `<html>` it renders as the static page (5.3). 3D-only elements (canvas, HUD, status label, frames, `ap`, `sk`, `stovas`, the facts row „Figūra – 3D modelis“) are `display:none` without the class; static-only elements (the hero photo, the photo `front`) are `display:none` with it and `loading="lazy"`.

`S` = 100svh in px. Anchor `id@t` = the scrollY at which the block's top edge has travelled `t` screens up from the viewport bottom (`top(id) − S + t·S`). Resolve on layout; a keyframe is never less than 0.05 S after the previous one.

| block | id | height in 3D mode | kind |
|---|---|---|---|
| Hero | `hero` | 180svh | spacer holding the fixed stage |
| Priekis | `priekis` | auto | plate: text and the photo `print` (2.6, 2.7) |
| Aplink | `ap` | 110svh; in portrait 130svh | transparent window (the camera walks round to the back) |
| Nugara | `nugara` | auto | plate: texts and the photo `back` (2.6, 2.7) |
| Tik žemėlapis | `sk` | 80svh; in portrait 100svh | transparent window; sticky „Šviesa“ |
| Kol kas tiek | `tiek` | auto | plate: the facts rows and the availability sentence (2.6) |
| Stovas | `stovas` | 230svh; in portrait 280svh | transparent window; sticky rack bar |
| Grid, Albumas, footer | as on the static page | auto | opaque black; grid 3×3 at every width |

Plates: `background:#000`, full width in portrait with 64 px gradient lips above and below; in landscape (aspect ≥ 1) a left card, `width:min(460px,40vw)`. Blocks are `position:relative; z-index:1`, above the stage. The three windows are taller in portrait because a full-width plate hides the stage while it passes (2.3).

### 2.2 Stage, frames, poses

`.stage`: `position:fixed; top:0; left:0; width:100vw; height:100svh`. Inside, by z-index: the h1's `.n` span (0), `<canvas>` (1, `pointer-events:none`, 100vw × 100lvh), HUD (2). The h1 and `.hero__t` must not create stacking contexts (`container-type:normal` under `.gl`).

Frames are empty fixed elements placed by CSS; script reads their rects on resize.

| frame | portrait | landscape |
|---|---|---|
| `.fr-hero` | figure slot of the cluster (2.4) | same |
| `.fr-print` | left/right 4vw, top `52px + 3svh`, height 46svh | left 42vw, right 4vw, top/bottom 10svh |
| `.fr-item` | 78vw square, centred, top `52px + 6svh` | 50svh square, centred at (50vw, 44svh) |

Camera: vertical FOV 40° if aspect < 1, else 30°; near 0.05, far 30. With `f = canvasCssHeight / (2·tan(fov/2))`, a pose fits a subject box to a frame: `d = max(w·f/rect.w, h·f/rect.h)`, where `w` is the box's extent across the view from the pose's azimuth; position = target + d·(sin az·cos el, sin el, cos az·cos el), the target being the centre of the subject; roll rotates `camera.up`; `camera.setViewOffset(W, H, W/2 − rect.cx, H/2 − rect.cy, W, H)` puts the target on the frame centre. Between keyframes interpolate target, ln d, az, el, roll and frame centre with easeInOutCubic.

Subjects are boxes in world space (anchors in 0.2). `az` is the camera azimuth around the yaw axis (0° = in front, 180° = behind); it is interpolated as a plain number and never wrapped, so the story makes one full circle from 0° to 360°.

| pose | subject | frame | az | el | roll |
|---|---|---|---|---|---|
| HERO | `TOP` | `.fr-hero` | 0° | −2° | 0° |
| CHEST | `PF` grown to 2.4 × its size | `.fr-print` | +10° | +3° | 0° |
| SIDE | `TOP` | `.fr-print` | 95° | +4° | 0° |
| BACK | `PB` grown to 1.12 × | `.fr-print` | 180° | 0° | 0° |
| MAP | portrait: the upper 62 % of `PB`; landscape: `PB` from 8 % below its top edge down to its bottom edge | `.fr-print` | 186° | +3° | −3° |
| SIDE, mirrored | `TOP` | `.fr-print` | 265° | +4° | 0° |
| ITEM(u) | u = −1: `TOP`; panels: 0.60 × 0.60 m at (X(u), Yr − 0.35, 0) | `.fr-item` | 360° | 0° | 0° |

`X(−1) = 0` (the figure), `X(k) = 1.15 + 0.66·k` for k = 0…8, linear between. For the trip from BACK to ITEM(−1) the azimuth runs 180° → 360° through the intermediate keyframe "SIDE, mirrored".

MAP has one subject per orientation because the caption and the red line under it must be on screen in the dark beat (7.2). In portrait they sit below the frame and still on screen. In landscape the frame is nearly as high as the screen, so they have to be inside it; the top 8 % of the map runs past the frame's upper edge instead.

CHEST distance = `max(solved, (PF width / front texture width in px)·f·dpr / 1.5)`: never closer than the distance at which one texel of the front print covers 1.5 device pixels.

### 2.3 Storyboard

The light states „Tipas“ and „Stendas“ and the lights-out factor `L` are defined in 6.5; `k` is the coast constant of section 3. The scroll anchors in the table hold in landscape; portrait moves some of them (below the table).

| beat | scroll | camera | figure | light | HTML layer | interaction |
|---|---|---|---|---|---|---|
| Arrival (timed, once; only if scrollY < 0.3 S and not calm) | none | HERO | fades in turning: a synthetic flick from yaw −200° (ω₀ = 200°·k) that the spin code lands on 0°; no slide | canvas opacity 0 → .25 → .05 → 1 at 0/60/120/180 ms; „Tipas“ | „Jungiam šviesą“ becomes „3D modelis“; buttons and „Suk.“ appear 300 ms after settling | any pointerdown takes over |
| Hero | 0–0.2 S | HERO, d creeps to ×0.97 | free; detents 0°, 180°; idle sway ±2° at 0.2 Hz, ends 4 s after the last input | „Tipas“ | cluster and HUD (2.4) | spin, flick, tap (pulses „Suk.“), view buttons, range input |
| Artyn | 0.2–0.8 S | HERO → CHEST | from 0.25 S the yaw target is 0° only, limit ±35° | blends to „Stendas“ | HUD off at 0.15 S (back below 0.10 S); „NA2“ is eclipsed and fades | spin |
| Priekis | plate enters at 0.8 S | CHEST, az 10° → 4°, until `ap@0.10` | front, ±35° | „Stendas“ | plate „Priekis“ | wiggle above the plate |
| Aplink | `ap@0.10` → `ap@1.00` | CHEST → SIDE (by `ap@0.50`) → BACK (by `ap@1.00`) | front, ±35° | „Stendas“ | none | wiggle |
| Nugara | plate | BACK, hold until `sk@0.45` | ±35° | „Stendas“ | plate „Nugara“ | wiggle above the plate |
| Tik žemėlapis | `sk@0.45` → `tiek@0.55` | → MAP by `sk@0.85`, hold | ±35° | out at `sk@0.62` (L → 1: only the map and its caption stay lit); red line draws over `sk@0.75–0.95` | sticky „Šviesa“ | wiggle, „Šviesa“ |
| Kol kas tiek | plate | → BACK by `tiek@0.80`; → az 265° by `stovas@0.15`; → ITEM(−1) by `stovas@0.40` | detents 0°/180° again from `stovas@0.30` | on at `tiek@0.55`; „Stendas“ until `tiek@0.80`, then back to „Tipas“ by `stovas@0.40` | plate „Kol kas tiek“ | none |
| Stovas, figure | `stovas@0.40–0.90` | ITEM(−1) | free | rail draws left to right over `stovas@0.70–0.90` | rack bar | spin, flick |
| Stovas, photos | `stovas@0.90–2.30` | ITEM(u), u −1 → 8 (4.2) | stays at X = 0, leaves the frame | rims × (1 − smoothstep(0.5, 2.5, cameraX)); key 0.8 | rack bar, „Trauk.“ | flick, tap a panel, bar |
| Grid, Albumas, footer | after `stovas` | asleep | none | none | as on the static page | lightbox, links |

**Portrait.** In landscape a plate is a card to the left of `.fr-print`, and the anchors hold as given. In portrait a plate is full width: whatever is scheduled while a plate or its lip still covers `.fr-print` or `.fr-item` happens behind it and is not seen. A beat that has to be seen therefore starts once its frame is clear. That is why the windows are taller in portrait (2.1) and why these beats start later there:

| beat | landscape | portrait |
|---|---|---|
| „Priekis“ ends and „Aplink“ starts; SIDE; BACK | `ap@0.10`; `ap@0.50`; `ap@1.00` | `ap@0.50`; `ap@0.90`; `ap@1.30` |
| „Stovas, figure“ | `stovas@0.40–0.90` | `stovas@0.40–1.40` |
| rail draws | `stovas@0.70–0.90` | `stovas@1.05–1.30` |
| „Stovas, photos“ | `stovas@0.90–2.30` | `stovas@1.40–2.80` |

Every other anchor is the same in both orientations. The taller `sk` keeps the lip of „Kol kas tiek“ off the caption until the red line is complete at `sk@0.95`. Where sections 3 and 4.2 name `stovas@0.90` as the start of the photos, portrait uses `stovas@1.40`; the span of 1.40 S stays.

### 2.4 Hero cluster and HUD

One fixed cluster sized by `--u`. Portrait: centred; tune `--u` (for example `min(1vw, .94svh / 2)`) so that the cluster, the tagline and the buttons all fit a 390 × 664 viewport without overlap. Landscape: `min(.72svh, .62vw)`, centred on x = 68vw, with tagline, buttons and labels in a 40vw left column.

- „NA2“ (`.n`), the giant sign: real text in the `<h1>`, followed by a visually hidden „ marškinėliai“ so the heading reads „NA2 marškinėliai“. Size it so its glyph box is about 88u wide; `line-height:.72; letter-spacing:-.045em`. No text-decoration under `.gl`; its `::after` is the red line: glyph-box width, 0.035em thick, 3u below the baseline, `transform-origin:left; transform:scaleX(var(--p))`.
- Figure slot `.fr-hero`: fits the subject `TOP`. Size and place it so the head and shoulders cover roughly the lower third of the „NA2“ glyphs and the hem sits above the front line.
- Front line „ŠILAINIAI, KAUNAS“: letter-spaced, spanning the cluster width, over the trousers just below the hem. Behind it, in front of the canvas: a scrim `rgba(0,0,0,.62)`, feathered 12 px.
- Then the tagline „Priekyje tylu. Nugara daro visą darbą.“ (two lines, break after the first sentence) and one row: `[Priekis] [Nugara] [Iš arti]` (44 px high, solid black, 1 px `--line` border), hint at the right end.
- Meta row at the top of the stage: „Nieko asmeniško 2“ left; status label `#st` right („Jungiam šviesą“ → „3D modelis“). The top bar stays in normal flow.
- All fixed rows keep the existing safe-area paddings (`--gl`, `--gr`, `--st`, `--sb`).

Each rendered frame, script writes one transform and one opacity to `.n`: the sign's rest rect, un-projected at HERO onto the plane z = C.z − 2.0 m, is projected through the live camera to a translate and scale; opacity = smoothstep(1.2·d_CHEST, 2.2·d_CHEST, d). `.n` is `visibility:hidden` whenever applied scroll > 0.8 S.

### 2.5 Microcopy of the 3D layer (complete)

The 3D layer adds exactly these strings to the page.

Visible: „Jungiam šviesą“, „3D modelis“, „Suk.“, „← → Suk.“, „Trauk.“, „Priekis“, „Nugara“, „Iš arti“, „Šviesa“, „Įjungti 3D“.

Assistive only: „Marškinėlių 3D vaizdas“, „Pasukti marškinėlius“, „Šonas“, „Priekis.“, „Nugara.“, „Kraunamas 3D vaizdas.“, „3D vaizdas paruoštas.“, „Nuotraukų stovas“, „Ankstesnis vaizdas“, „Kitas vaizdas“, „Padidinti: “ + the photo's existing alt.

### 2.6 Page texts

In the tables of 2.6 and 2.7 the outer „…“ pair marks where a text starts and ends and is not part of it; quotes inside it are part of the text.

| place | text |
|---|---|
| `<title>`, og:title | „NA2 marškinėliai – OG VERSION merch“ |
| meta description | „Juodi NA2 marškinėliai. Priekyje – „NA2“ iš eurų banknotų, nugaroje – Šilainių žemėlapis. Kaina ir dydžiai skelbiami kartu su dropu.“ |
| og:description | „Priekyje tylu. Nugara daro visą darbą.“ |
| plate „Priekis“ | h2 „Priekis“; „Kairėje krūtinės pusėje – „NA2“. Raidės sudėtos iš eurų banknotų.“; photo `print` with the caption „Spauda iš arti“ |
| plate „Nugara“ | h2 „Nugara“; „Nugaroje – Šilainių žemėlapis baltomis linijomis: Baltų prospektas, Žemaičių plentas, Baltijos gatvė, IX fortas, A1.“; „Po juo – „ŠILAINIAI, KAUNAS“.“; „NA2 – albumas „Nieko asmeniško 2“. Žemėlapis – rajonas, iš kurio OG VERSION.“; photo `back` |
| plate „Kol kas tiek“ | h2 „Kol kas tiek“; rows „Daiktas – Marškinėliai“, „Spalva – Juoda“, „Priekis – „NA2“ iš eurų banknotų“, „Nugara – Šilainių žemėlapis“, „Figūra – 3D modelis“; then „Kaina ir dydžiai skelbiami kartu su dropu.“ |
| HUD description | „Juodi NA2 marškinėliai ant 3D figūros. Priekyje – „NA2“ iš eurų banknotų, nugaroje – Šilainių žemėlapis.“ |
| footer | „OG Version · Kaunas, Šilainiai“ and the three existing links (listed in `work3d/spec/CONTENT-RULES.md`). The footer carries this line and the three links, nothing else. |

### 2.7 Real photos

Sources: `worn-back.jpg`, `worn-front.jpg` and `print-closeup.jpg` in `work3d/ref/`. The build writes them to `/merch/v/ph/` at 1600 px and 800 px on the long side, JPEG quality 82. Crop the two worn photos tightly to the garment so the room behind is barely visible and nothing of the wearer's face is in the picture.

The two worn sources are prepared copies, not the owner's originals. The originals are 1125 × 2436 px. `worn-front.jpg` is the full width of its original and 1800 rows from row 612 down (1125 × 1800 px): its top edge is at the neck, below the face. `worn-back.jpg` is the full width and 1500 rows from row 468 down (1125 × 1500 px): it still shows the back of the head, and the build's crop starts below it, at the nape. A lost copy can be cut again from its original with these numbers.

The build crops by fixed fractions of the source (the `PHOTOS` table in `build.cjs`). They fit only this framing, and the build does not notice another one. Given an original under the same name, it cuts about 560 px higher on the front photo and about 250 px higher on the back photo, into the part the prepared copy leaves out, and still finishes without an error. So:

- Pass `PHOTOS` to the build only when sources with exactly this framing are in `work3d/ref/`. Without `PHOTOS` the committed files in `merch/v/ph/` and `og.jpg` are kept and stay valid (6.1).
- For a source with any other framing, work out new crop fractions first.
- After every build with `PHOTOS`, look at each file in `merch/v/ph/` and at `og.jpg` before committing: no face, and nothing by which the wearer could be recognised.

| name | source | alt |
|---|---|---|
| `back` | worn-back.jpg | „Dėvimi juodi NA2 marškinėliai iš nugaros: baltas Šilainių žemėlapis ir užrašas „ŠILAINIAI, KAUNAS“.“ |
| `front` | worn-front.jpg | „Dėvimi juodi marškinėliai iš priekio: kairėje krūtinės pusėje – „NA2“ iš eurų banknotų.“ |
| `print` | print-closeup.jpg | „Spauda iš arti: raidės „NA2“, sudėtos iš eurų banknotų, ant juodo audinio.“ |

They are `<button class="z" data-src>` figures that open in the existing lightbox. In 3D mode `print` sits in the plate „Priekis“ and `back` in the plate „Nugara“; `front` appears only on the static page. og:image and twitter:image: `/merch/v/og.jpg` (1200 × 630, built from the `back` crop centred on black). Favicon: `/merch/v/ph/print-800.jpg`.

## 3. Interaction

**Scroll versus spin.** `html.gl main` has `touch-action:pan-y pinch-zoom`. All listeners are passive; nothing calls `preventDefault`; no wheel or touch listeners; script never sets scroll position (sole exception: 5.4). A primary pointerdown is tracked unless it is within 20 px of the left or right screen edge, or on `a, button, input, dialog` or a plate. After 8 px: if |dx| > 1.2·|dy| it is a horizontal gesture (`setPointerCapture`); otherwise it is dropped and the browser scrolls. A second pointer cancels it. None starts while `visualViewport.scale > 1.01`. A horizontal gesture spins the figure, or moves the rack once applied scroll ≥ `stovas@0.90` (in portrait `stovas@1.40`, 2.3).

**Spin** (fixed 1/120 s steps, at most 4 per frame, dt clamped to 50 ms). θ is the yaw, ω its speed, D the detent a flick or spring is heading for:

| item | value |
|---|---|
| Drag | 1:1, yaw only; touch 220° per viewport width, clamped 0.35–0.60°/px; mouse 0.40°/px |
| Release velocity | mean of the last 80 ms, clamped ±1440°/s |
| Coast | ω̇ = −k·ω − 20°/s²·sign ω, k = 1.6 s⁻¹ |
| Flick (≥ 180°/s) | D = allowed detent nearest θ + ω₀/k; k′ = ω₀/(D − θ), clamped 0.75k…1.4k; spring takes over when the speed is under 90°/s or θ is within 18° of D |
| Slow release | stays where left; within 18° of a detent the spring takes it |
| Spring | K = 90 s⁻², damping ratio 0.55 (about 12 % overshoot) |
| Close-up (the story hold, and while „Iš arti“ is on) | limit ±35°, drag beyond ×0.35, release springs to the held detent (damping ratio 0.8) |
| Settled (speed under 2°/s, within 0.3° of the target) | `navigator.vibrate?.(10)`; live region „Priekis.“ / „Nugara.“ if the detent changed; buttons and range input updated |

The figure stands: it has no pendulum, no lean and no tap poke. A tap never moves it.

**Story hold.** From 0.25 S until `stovas@0.30` the story holds the yaw at the front (detent 0° only, limit ±35°). The camera, not the figure, goes round to the back, so the hand only wiggles the figure there.

**First touch.** Vertical: the page scrolls. Horizontal: the figure follows; after 12 px „Suk.“ goes for good. A tap in the hero (a press shorter than 250 ms that moves less than 8 px): „Suk.“ pulses once, and the figure stays as it is.

**Controls.**
- „Priekis“ / „Nugara“: send the spring to 0° / 180°. `aria-pressed` mirrors the settled detent; neither is pressed off-detent.
- „Iš arti“: toggle; eases the camera in 700 ms, without scrolling, to the print that faces it: at detent 0° the CHEST pose, at detent 180° the BACK pose computed for the rotated figure (az 0°). Released by a second press, Esc, or 0.35 S of scrolling.
- `#rot`: visually hidden `<input type="range" min="0" max="345" step="15">`, label „Pasukti marškinėlius“, `aria-valuetext` „Priekis“ (0), „Šonas“ (90, 270), „Nugara“ (180), otherwise degrees. `input` sets the spring target (damping ratio 0.9, no detent pull). While focused: 2 px bone ring on `.fr-hero`; the hint reads „← → Suk.“.
- The hero HUD is `inert` while off.
- „Šviesa“: `aria-pressed` = lights on. Scroll sets the default; a press overrides it until applied scroll leaves `sk@0.2 … tiek@0.7`. Every light change eases with a 0.12 s time constant.
- Esc closes, in order: lightbox, „Iš arti“, lights override.
- Mouse: `cursor:grab` / `grabbing` where a spin can start; wheel is native.

**Hints.** Two in total: „Suk.“, and „Trauk.“ in the rack bar (gone after the first rack drag).

## 4. The nine photos

### 4.1 Layout

A red rail (10 × 10 mm box, `#c6362b`, unlit) at `Yr`, from x = −0.9 to X(8) + 0.6, hidden (scale.x = 0) until the rack beat. Nine 0.60 m square panels at X(k), each on two dark clips (one `InstancedMesh`), top edge at `Yr − 0.05`, rest yaw alternating ±4°. Material: `MeshBasicMaterial`, photo × 0.87, `toneMapped:false`. Under each, a reflection quad: mirrored below `panelBottom − 0.06`, height × 1.35, a 64 px copy of the photo, opacity 0.22 with a vertical fade, no depth write. No captions, no prices.

### 4.2 Browsing

- `u = clamp(uScroll + uUser, −1, 8)`.
- Scroll: with `t` from `stovas@t`, `f = 9·clamp((t − 0.90)/1.40, 0, 1)`, `uScroll = −1 + f − 0.6·sin(2πf)/(2π)`: a soft dwell per panel, not scroll snapping. In portrait the photos start at `stovas@1.40` (2.3), so there `f = 9·clamp((t − 1.40)/1.40, 0, 1)`.
- Flick: `Δu = −dx / (0.66·f/d)` (here `f` is the focal length of 2.2); on release friction 2.2 s⁻¹, velocity clamped ±9 panels/s, rest point rounded to an integer, spring K = 110 s⁻², damping ratio 0.8.
- Scroll reclaims: with `u0`, `sR` taken at release, `uUser = u0·(1 − smoothstep(0.05 S, 0.40 S, |s − sR|))`.
- Each panel swings about the rail: 1.0 Hz × (0.88 + 0.03·((5k) mod 9)), damping ratio 0.2, clamped ±12°, `swing'' += 6·ü`.

### 4.3 Opening and the accessible equivalent

- Tap a panel (a press shorter than 250 ms that moves less than 8 px; raycast of nine quads): it squares up and moves 0.25 m toward the camera in 160 ms; at 80 ms the existing `<dialog>` opens on that photo with the 1024 px file as placeholder. The renderer sleeps while it is open.
- Rack bar (sticky at the viewport bottom inside `stovas`; `role="group"` „Nuotraukų stovas“; solid black; 46 px targets): `[‹]` „Ankstesnis vaizdas“; a button showing „03 / 09“ (`aria-label` „Padidinti: “ + alt) that opens the current photo; `[›]` „Kitas vaizdas“. Current photo = `max(0, round(u))`.
- The bare grid right after the rack is the full equivalent: the same nine `<button class="z" data-src>` with existing alts. Images: `src="/merch/v/g/01.jpg" srcset="/merch/v/g/01.jpg 1024w, /merch/p/01.jpg 4096w" sizes="(max-width:700px) 50vw, 34vw"`.
- The lightbox script in `merch/index.html` stays as it is. The 3D code relies on three things in it: `links` is built at open time from `button[data-src]` that are not `display:none`; `window.__lb.open(button, returnFocusEl)` is exposed; an `lb` event is dispatched on open and close.

### 4.4 Lazy loading

One texture at a time, 01 → 09, starting when applied scroll ≥ `sk@0`, or 4 s after ready unless the connection is 2g/3g. `ImageBitmapLoader` with `imageOrientation:'flipY'`; phones resize to 512 px, desktop keeps 1024 px. Same URLs as the grid, so each photo downloads once. Until decoded, a panel shows the photo's average colour × 0.35 (injected at build), then cross-fades in 250 ms.

## 5. Loading, first paint, fallback

### 5.1 Gate (inline in `<head>`, under 1 KB)

Adds `class="gl"` and injects the module preload, fetch preloads for `figure.glb`, `front.webp` and `back.webp`, and `<script type="module" src="/merch/v/app.js">` only if all hold: a WebGL2 context is created with `failIfMajorPerformanceCaveat:true` (then released via `WEBGL_lose_context`); the unmasked renderer does not match `/swiftshader|llvmpipe|software/i`; no `prefers-reduced-motion: reduce`; no `forced-colors: active`; no `connection.saveData`; `effectiveType` is not `2g` or `slow-2g`. `?3d=1` forces 3D; `?3d=0` forces static. Otherwise it adds an image preload for the hero photo. Static visitors download no 3D code or assets.

Headless browsers render WebGL in software, which the gate rejects on purpose, so headless tests need `?3d=1`. On a real GPU the gate passes without it.

### 5.2 Sequence in 3D mode

1. **First paint, HTML and inline CSS only:** black, top bar, bone „NA2“, the front line, tagline, „Jungiam šviesą“, red line at `--p:0`. The page scrolls; all text is readable.
2. `app.js` fetches the model and both prints through a stream reader; `--p` = bytes received / total (sizes injected at build; JS counts as received when it runs). Status: „Kraunamas 3D vaizdas.“
3. Parse, build the environment, `renderer.compileAsync`, one hidden frame.
4. Lights on and arrival (2.3). If scrollY ≥ 0.3 S: a 300 ms fade at the pose for that scroll. Status: „3D vaizdas paruoštas.“
5. After 1.5 s idle, on Q0–Q1 with `deviceMemory` ≥ 4 or unknown: if the build produced `front-hi.webp`, load it and swap it in.

### 5.3 Static and no-JS page

No `gl` class: the flat layout. Hero with „NA2“, the front line, the tagline and the photo `back`; section „Priekis“ (text, `print`, `front`); section „Nugara“ (text, `back`); „Kol kas tiek“ (the row „Figūra – 3D modelis“ is hidden here); grid; album; footer. The grid images use the `srcset` of 4.3. The hero photo is lazy in the markup (2.1), so only static visitors load it.

### 5.4 `goStatic(reason)`

Remove `gl`, dispose the renderer, remove the canvas, bring the same block and fraction back into view (the one permitted scripted scroll). Triggers: model, print or decode failure; not ready 10 s after `app.js` starts (fetches aborted); context lost and not restored (6.10); under 15 fps at Q3 during the first 5 s on the hero, never later.

### 5.5 Reduced motion and Save-Data

Static page plus a micro-label button „Įjungti 3D“ in the hero meta row (only if WebGL2 exists). It starts 3D without a reload in calm mode (`html.gl.calm`): no arrival, flicker, idle sway, panel swing or scroll smoothing; light changes still ease.

## 6. Technical architecture

### 6.1 Files and build

```
merch/index.html     HTML, inline CSS, gate, lightbox script
merch/v/app.js       bundle (output)
merch/v/figure.glb   front.webp   front-hi.webp (optional)   back.webp   (outputs)
merch/v/ph/          back, front, print as <name>-1600.jpg and <name>-800.jpg (outputs)
merch/v/og.jpg       share image (output)
merch/v/art.json     print pixel sizes and captionBox, kept between builds (output)
merch/v/g/           01.jpg … 09.jpg (outputs)
merch/v/build.cjs    build script (CommonJS, so NODE_PATH resolves)
merch/v/src/*.js     sources
```

The site is served as static files and the host runs no build step, so every output of `build.cjs` is committed.

```
cd merch/v && NODE_PATH=../../work3d/node_modules MODEL=../../work3d/model/current.glb FRONT=../../work3d/art/front.png BACK=../../work3d/art/back.png ARTMETA=../../work3d/art/meta.json PHOTOS=../../work3d/ref node build.cjs
```

This is the full build, in POSIX shell syntax; in another shell set the same six environment variables first.

- `NODE_PATH` is required: `work3d/node_modules` must hold `three`, `esbuild`, `sharp` and `@gltf-transform/cli` (three 0.187, esbuild 0.28 and gltf-transform 4.5 were used so far). Run `npm install` in `work3d/` to get them; `work3d/package.json` lists them, together with Playwright for the tests of 7.2.
- Each other variable is optional: without it, the committed output it would have produced is kept, so `NODE_PATH` alone rebuilds the code and re-checks every budget.
- `PHOTOS` is the folder with the three source photos of 2.7. Leave it out on a clone without the owner's worn photos, where the build would stop with "photo missing", and whenever the worn sources do not have the framing that 2.7 describes.
- `work3d/package.json` has both forms as scripts, run from `work3d/`: `npm run build` (`NODE_PATH` alone) and `npm run build:full` (the command above).

`build.cjs`, in order:

1. **Model** with `work3d/node_modules/.bin/gltf-transform`: `dedup $MODEL a.glb --materials false` (the default would merge the two print materials); `weld a.glb b.glb`; only above 130k triangles `simplify b.glb b.glb --ratio 0.75 --error 0.0005`; shrink and re-encode the embedded textures as WebP until the file meets its budget; `meshopt b.glb figure.glb --level medium`. No `join`. Intermediates go to `os.tmpdir()`. Fail without exactly one printFront mesh, exactly one printBack mesh and at least one tee mesh, above 130k triangles, or above 1.4 MB.
2. **Prints** (sharp): front `resize(1024).webp({quality:80, alphaQuality:90})` → `front.webp` (1024 px wide); optionally the source at full size, quality 82 → `front-hi.webp`; back → `back.webp` (1536 × 2048, near-lossless; it is line art and compresses well).
3. **Photos** (sharp): only with `PHOTOS`, the three real photos → `ph/` as in 2.7, and `og.jpg` (1200 × 630, the `back` crop centred on black); always, `/merch/p/0k.jpg` → `resize(1024,1024).jpeg({quality:78, progressive:true, mozjpeg:true})` → `g/0k.jpg`; average colour from a 1 × 1 resize.
4. **Code:** `esbuild.build({entryPoints:['src/main.js'], bundle:true, minify:true, format:'esm', target:'es2020', outfile:'app.js', nodePaths:[process.env.NODE_PATH], define:{__BYTES__, __ART__, __AVG__}})`: the byte sizes for the loader line, the pixel sizes of both prints with `captionBox`, and the nine average colours. Import by name from `three`, plus `GLTFLoader` and `MeshoptDecoder` from `three/addons/`; not `RoomEnvironment`.
5. **Budgets:** fail if `app.js` gzip > 260 KB or the first view (HTML + JS as transferred, + GLB + `front.webp` + `back.webp`) > 2.3 MB. Expected: three subset 163 KB gzip (measured), app code ≤ 30 KB.

### 6.2 Modules

| module | responsibility |
|---|---|
| `config` | every constant in this spec |
| `main` | boot order, ready sequence, `goStatic`, test hooks |
| `load` | byte-progress fetch, abort, timeout, GLB parse, print bitmaps, lazy queues |
| `stage` | renderer, canvas size, DPR, resize, frame rects, pose solver, sign projection |
| `scene` | environment, lights, materials, lit-map overlay, red line, `uvToWorld` |
| `timeline` | anchors, applied scroll, jump dip, camera and light per frame, HUD classes |
| `spin` | pointer arbitration, spin physics; drag/inertia/snap core shared with the rack |
| `rack` | rail, panels, placeholders, reflections, `u`, swings, tap raycast, rack bar |
| `hud` | buttons, range input, hints, live region, Esc order, lightbox bridge |
| `quality` | cadence calibration, governor, tier changes |
| `loop` | on-demand rAF, sleep and wake, fixed-step tick |

### 6.3 Scene graph

```
scene (environment, no background)
├ key, rimL, rimR                  3 DirectionalLights, fixed in the world
├ figureYaw (the yaw axis of 0.2) ─ figure meshes, PrintFront, PrintBack, printLit, lineRed
└ rack ─ rail, clips (instanced), panel[0..8] (pivot at the rail), reflection[0..8]
```

Find the meshes as the reference viewer does (0.2). `uvToWorld(u, v)` on a print: find the triangle containing the UV, interpolate the position, apply `matrixWorld` (meshopt quantisation puts scale into node transforms; never read raw positions without it).

### 6.4 Materials

- **Tee cloth, Q1–Q3:** `MeshStandardMaterial({color:0x0e0e10, roughness:0.9, metalness:0})` plus the model's normal and AO maps if present. One `onBeforeCompile` patch: after `vec3 outgoingLight = totalDiffuse + totalSpecular + totalEmissiveRadiance;` add `outgoingLight += totalDiffuse * 8.0 * pow(1.0 - saturate(dot(normal, normalize(vViewPosition))), 3.0);`. A model without normal maps is valid: then folds must read from geometry normals alone.
- **Tee cloth, Q0:** `MeshPhysicalMaterial`, same base, `sheen:1, sheenRoughness:0.75, sheenColor:0x2a2a30`, no patch.
- **Pants:** the same cloth shader, colour `#2b2a28`. **Shoes:** `#121213`, roughness 0.55.
- **Body and hair:** one matte "plaster" material, bone `#d6cfc3`, roughness 0.62, metalness 0 (hair may be 12 % darker). No skin texture, no eye colour, no make-up.
- **Leg fade:** in the fragment shader of pants, shoes and any body part below the hem multiply the outgoing light by `smoothstep(0.30, 0.85, worldY)` (one `onBeforeCompile` patch, world position varying). No frame may show the feet as lit objects.
- **Prints** (one material per print): `MeshStandardMaterial({map, transparent:true, roughness:0.82, metalness:0, side:FrontSide, depthWrite:false, polygonOffset:true, polygonOffsetFactor:-4, polygonOffsetUnits:-4, emissive:0xffffff, emissiveMap:map, emissiveIntensity:0})`, `renderOrder 2`. Texture: sRGB, `flipY=false`, anisotropy min(8, max).
- **`printLit`:** an unlit copy of PrintBack with the whole back texture and no mask: same geometry, `MeshBasicMaterial({map, transparent:true, toneMapped:false, depthWrite:false, polygonOffset:true, polygonOffsetFactor:-6})`, `renderOrder 3`, opacity = L, invisible at 0.
- **`lineRed`:** an unlit red quad 2.5 mm high, 0.5 mm off the cloth, from `uvToWorld(captionBox.u0, captionBox.v1 + 0.022)` to `uvToWorld(captionBox.u1, captionBox.v1 + 0.022)` on PrintBack, origin at its left end as seen from behind; `scale.x` 0 → 1; opacity L.
- **Renderer:** `{antialias:true, alpha:true, stencil:false, powerPreference:'high-performance'}` (`antialias:false` if `deviceMemory ≤ 2`), clear alpha 0, ACES Filmic, sRGB output. No shadow maps, no post-processing.

### 6.5 Lights and environment

| state | key `#fff4e6` from (0.8, 2, 2.5) | rimL from (−2, 1.2, −2) | rimR from (2.2, 0.6, −1.8) | environment | print emissive (both prints) |
|---|---|---|---|---|---|
| „Tipas“ (hero) | 1.6 | `#efece6` 4.0 | `#efece6` 2.5 | 0.35 | 0 |
| „Stendas“ (close) | 1.6 | `#b06cff` 6.0 | `#ff5a7a` 4.0 | 0.35 | 0.22 |
| Lights out (L = 1) | × 0.05 | × 0.1 | × 0.1 | 0.03 | 0 |

`L` is the lights-out factor: 0 with the lights on, 1 in the dark beat.

Blend „Tipas“ → „Stendas“ by `m = 1 − smoothstep(1.2·d_CHEST, 0.8·d_HERO, d)` on the push-in. From CHEST (0.8 S) through the walk round and the map beat the storyboard holds „Stendas“ (m = 1) until `tiek@0.80`, although SIDE and BACK stand further from the figure than CHEST; between `tiek@0.80` and `stovas@0.40` it returns to „Tipas“, which lights the rack. „Iš arti“ takes m to 1 with its camera ease. Purple and pink exist only here, as light.

Environment: one `PMREMGenerator.fromScene(room, 0.04)`. `room` is a 6 × 4 × 6 m box (`BackSide`, `#020203`) with unlit panels whose colours are multiplied past 1: bone `#efece6` × 6, 2.4 × 1.2 m at (0, 1.6, −2.9), the light from the type; purple `#b06cff` × 8, 1.6 × 2.4 m at (−2.9, 0.6, −1.2); pink `#ff5a7a` × 6, 1.6 × 2.4 m at (2.9, 0.4, −1.2); cool strip `#dfe6f0` × 2, 3 × 0.4 m at (0, 1.95, 1).

### 6.6 Scroll mapping

A passive scroll listener only sets a flag. Each frame: read `scrollY` once; applied scroll `s` follows it with a 0.12 s time constant (none in calm mode); evaluate keyframes at `s`. If `|scrollY − s| > 2 S` in one frame (anchor, End key, restored position): canvas opacity 0 for 220 ms and `s` snaps. Under `.gl`, `scroll-behavior:auto`. Per-frame DOM writes: `.n` only. HUD changes are class toggles with 180 ms CSS transitions.

### 6.7 Render loop

On demand: runs while scroll is unsettled, a pointer is down, a spring or tween is unsettled, a texture just arrived, or within 4 s of the last input (idle sway, every second frame). Fully stopped when the tab is hidden, the dialog is open, `stovas` has left above the viewport, the context is lost, or the page is static. Wakes on scroll, pointer, key, resize, visibility change, texture decode.

### 6.8 Resize and DPR

Canvas CSS size 100vw × 100lvh, so the mobile toolbar never resizes the buffer. `ResizeObserver`, debounced 150 ms; on coarse pointers ignore height-only changes under 150 px. Recompute FOV, frame rects, poses, sign plane, anchors. DPR = min(devicePixelRatio, 1.5 on coarse pointers, 2 otherwise), then the tier.

### 6.9 Quality tiers

| tier | start | content |
|---|---|---|
| Q0 | fine pointer | DPR ≤ 2, physical cloth, 1024 px rack textures, reflections |
| Q1 | coarse pointer | DPR ≤ 1.5, standard cloth with the patch, 512 px rack textures, reflections |
| Q2 | governor | DPR ≤ 1.25 (from Q0: 1.5), reflections off |
| Q3 | governor | DPR 1.0, `rimR` off, idle sway off, no `front-hi.webp` |

Governor: while loading, time 20 empty rAFs; `c` = median interval; target = max(c, 16.7 ms); if c < 12 ms render every second frame. Step down one tier when the mean interval over 45 consecutive rendered frames exceeds 1.3 × target. Ignore frames within 300 ms of load, resize, tab return or a texture upload. Apply only between gestures. Never step up; never below DPR 1.0. A 30 fps rAF cap (iOS Low Power Mode) therefore does not trigger it.

### 6.10 Context loss

On `webglcontextlost`: `preventDefault`, stop the loop, canvas opacity 0 (the type stays). If `webglcontextrestored` arrives within 3 s of the page being visible: rebuild the environment, flag all textures for upload, `compileAsync`, fade in. A second loss, or no restore: `goStatic`.

### 6.11 Opaque escape hatch

`SANDWICH = true` in config; `?opaque=1` overrides. When off: `alpha:false`, clear `#000`, `.n` gets `color:transparent` and no line, and the scene gains a quad on the sign plane with a 1024 px `CanvasTexture`: „NA2“ in `.n`'s computed font, `#efece6`, red line under it. Flip the default only if device testing shows compositing faults.

### 6.12 Test hooks

`?3d=1|0`, `?q=0..3`, `?calm=1`, `?opaque=1`, `?s=<scroll in S>` (jump and freeze). `window.__m = {ready, tier, dpr, calls, tris, yaw, detent, u, L, fallback}`. `?3d=1` is what lets software-rendered headless tests past the gate (5.1) and stays for that purpose.

## 7. Checklists

### 7.1 Accessibility

- [ ] One `<h1>` („NA2 marškinėliai“, real text); order h1 → h2; `lang="lt"`.
- [ ] Canvas is `aria-hidden`; the HUD group is labelled „Marškinėlių 3D vaizdas“ and described by the HUD description of 2.6.
- [ ] Tab order: skip link, brand, Albumas, range input, Priekis, Nugara, Iš arti, photo `print`, photo `back`, Šviesa, rack bar (3), nine grid buttons, album link, footer links. Nothing hidden or inert takes focus.
- [ ] Arrows, Home and End on the range input rotate the figure; outside it, PgUp, PgDn, Space and arrows scroll the page.
- [ ] Every action has a visible control; nothing needs a pointer.
- [ ] Focus is visible everywhere (2 px bone, 4 px offset).
- [ ] Every text box has at least 4.5:1 against the brightest pixel behind it, at every scroll stop and yaw. The giant „NA2“ is exempt only where the figure covers it. Grey labels sit only on solid black.
- [ ] No light change is faster than 250 ms except the single arrival flicker; automatic motion ends within 5 s of the last input.
- [ ] Targets are at least 44 × 44 px; safe-area insets respected; pinch zoom works.
- [ ] Dialog: focus in, trap, Esc, arrows, focus back to the opener (the lightbox script is not changed, 4.3).

### 7.2 Test matrix (Playwright, headless Chromium, `?3d=1`)

Test scripts, including a small static server, live in `work3d/tests/` and need Playwright with its Chromium; screenshots and other results go to `work3d/out/`. Serve the repository root, so that `/merch` returns `merch/index.html` and the absolute asset URLs resolve.

The headless matrix runs on software WebGL2. On the owner's PC, also run it in a headed browser on the real GPU without `?3d=1`, and open the page on real phones over the local network. Frame rate, the governor's tier changes (6.9), the DPR caps, the compositing of the transparent canvas over the type (6.11) and the touch arbitration (3) have never been seen on real hardware.

Viewports: 360×640, 390×664, 390×844, 430×932, 768×1024, 844×390, 1024×768, 1440×900, 1920×1080.

- [ ] No horizontal scroll, console errors, 404s or external requests at any viewport, in 3D and static mode.
- [ ] With `/merch/v/app.js` blocked, 390×664 shows „NA2“, the front line, the tagline and the red line.
- [ ] Throttled load: `--p` grows monotonically to 1, then `__m.ready` is true.
- [ ] Screenshots at `?s=` 0, 0.5, 0.8, every anchor in 2.3 (the portrait anchors at 390×664) and the end of `stovas`, at 390×664, 844×390 and 1440×900, match the storyboard: head and shoulders over the lower part of the giant „NA2“; the chest lettering filling the frame in „Priekis“; the figure seen from the side half way through „Aplink“; the map filling `.fr-print` in „Nugara“; in the dark beat only the map and caption lit, the red line exactly under the caption and glued to the cloth while the figure is wiggled; the figure framed as an item under the rail in „Stovas“; a panel fills `.fr-item`; legs fading into black, never a lit foot.
- [ ] A 200 px horizontal drag in the hero changes `__m.yaw`; a flick settles with `__m.detent` 0 or 180; a vertical touch drag scrolls and leaves yaw unchanged; a drag starting 10 px from the edge does nothing.
- [ ] Wheel-scrolling top to bottom is never blocked; `scrollY` is never changed by script.
- [ ] Jump to `#albumas` and back: dip, no fly-through, no errors.
- [ ] Rack: a flick changes `__m.u` and settles on an integer; bar buttons step it; tapping a panel and pressing the counter button both open the right photo; the counter reads „0k / 09“.
- [ ] Contrast audit: at 40 scroll stops × 4 viewports × yaw 0/90/180, screenshot with text made transparent, take the brightest pixel inside every visible text box, fail under 4.5:1.
- [ ] These give the static page with all content: `?3d=0`; reduced motion; Save-Data; forced colours; WebGL2 disabled; `figure.glb` blocked; 10 s timeout; context lost twice. One loss plus a restore recovers the scene. A late `goStatic` keeps the block in view.
- [ ] „Įjungti 3D“ starts calm mode with no automatic motion.
- [ ] Static mode downloads nothing from `/merch/v/` except the grid JPEGs (`g/`) and the real photos (`ph/`, which also holds the favicon); 3D mode downloads nothing from `/merch/p/` before the dialog opens.
- [ ] Budgets: JS ≤ 260 KB gzip; `figure.glb` ≤ 1.4 MB after meshopt and texture compression; first view (HTML + JS + GLB + `front.webp` + `back.webp`) ≤ 2.3 MB; `__m.tris` ≤ 140k; draw calls ≤ 14 in the hero, ≤ 50 in the rack; 3 lights; no shadow maps; `__m.dpr` ≤ 1.5 with a coarse pointer.
- [ ] `?q=3` and `?opaque=1` render every beat without errors.
- [ ] Tab hidden, dialog open, or scrolled past the rack: no rAF callbacks for 2 s.
- [ ] The model shows no size text; both prints are upright and unmirrored.

## 8. Cut list (in this order)

1. Reflection quads.
2. Panel swing springs.
3. The panel's square-up move before the dialog.
4. The sharper `front-hi.webp` (the chest close-up stays at the 1024 px clamp).
5. The bone-to-purple rim handover („Stendas“ everywhere).
6. The opaque escape hatch.
7. Physical sheen on desktop (phone material everywhere).
8. Rack flick (scroll and bar buttons only).
9. The turning arrival (a plain 400 ms fade).
10. The 3D rack itself (`stovas` removed; the grid follows the facts plate).

Never cut: grab, inertia and the detent click; „NA2“ behind the figure; the walk round to the back and the lit-map beat with its red line; native scrolling; the static fallback; keyboard access; the budgets.
