export const meta = {
  name: 'merch-3d-notext',
  description: 'Rework the 3D /merch page to the owner decision (no text except the giant NA2 and one info block), finish the rack and robustness, then a four-lens review with fixes and verification',
  phases: [
    { title: 'Strip', detail: 'remove all visible text and controls, add the info block, update the spec, verify the core' },
    { title: 'Rack', detail: 'nine photo panels on the rail, lazy textures, flick and tap, quality governor, context loss' },
    { title: 'Review', detail: 'four independent lenses: visual, interaction, fallback and content, performance and code' },
    { title: 'Fix', detail: 'fix confirmed findings, final screenshots' },
    { title: 'Verify', detail: 'independent re-check of every fix and a regression pass' },
  ],
}

const R = '<REPO>'
const S = '<CLOUD>'

const CTX = `
## Context
Repository ${R} is a static site (Vercel, no build step, built files are committed). Its page /merch (merch/index.html, assets and sources in merch/v/) is being rebuilt as a phone-first interactive 3D page with three.js r187: a stylised plaster figure wears the brand's real black oversized NA2 T-shirt (small „NA2“ lettering made of banknotes on the left chest, a white line map of Šilainiai with the caption „ŠILAINIAI, KAUNAS“ on the back). The visitor spins the figure with a finger; scrolling pushes the camera into the chest print, walks it round to the back, switches the lights off so that only the map glows with a red line under its caption, and ends at a rack of photos. Without WebGL the same document is a flat page.

Read first, in this order: ${R}/work3d/README.md (state, quick start, house rules), ${R}/work3d/spec/SPEC.md (the binding build spec: model contract, poses, storyboard, interaction, loading, fallback, architecture, budgets, test matrix, cut list), ${R}/work3d/spec/CONTENT-RULES.md, then the code: merch/index.html, merch/v/src/*.js, merch/v/build.cjs, and the test scripts in work3d/tests/. The page already works for the hero, the spin, the camera walk and the lights-out beat (the last builder was interrupted before finishing its own verification; nothing was independently reviewed).

## The owner's decision of 2026-11-26 (it overrides the spec wherever they differ)
The owner looked at the page and said: remove all texts; the only information will be the shirt's material, the price and shipping. Asked what else stays, the owner chose exactly one thing: the giant „NA2“ behind the figure. So:

STAYS VISIBLE: the giant „NA2“ sign behind the figure with its red loader line; the 3D canvas; two small round colour swatches without any text (see COLOURS); the photo grid; the lightbox; and ONE info block (see THE INFO BLOCK).
REMOVED (markup, styles, scripts, tests and every mention in the spec): the top bar (brand link, album link); the meta row and the visible status label; the front line „ŠILAINIAI, KAUNAS“ and its scrim; the tagline; the buttons „Priekis“ / „Nugara“ / „Iš arti“ and the close-up toggle behaviour; all hints („Suk.“, „← → Suk.“, „Trauk.“); the plates „Priekis“ and „Nugara“ with their texts, captions and photos; the plate „Kol kas tiek“ with its rows and the availability sentence; the sticky „Šviesa“ button and the light override (lights follow scroll only); the rack bar with its counter; the album section; the footer; the skip link; the „Įjungti 3D“ button and calm mode (visitors with reduced motion, Save-Data or forced colours simply get the static page).
ASSISTIVE TEXT STAYS (not visible): the visually hidden „ marškinėliai“ in the <h1>, aria labels, the live region messages for loading and for the settled side („Priekis.“ / „Nugara.“), image alts, and the visually hidden range input that lets a keyboard or screen-reader user turn the figure (it shows a focus ring on the figure when focused). Add a visually hidden <h2> „Informacija“ for the info block so the heading order holds.

THE INFO BLOCK: after the first decision the owner added that the shirt is sold as two types (a heavier, more expensive one and a lighter, cheaper one), each in black and in white, and that the information is: material and price per type, and shipping. So the block is a <section id="info"> with, for each of the two types, an <article> holding an optional type name (<h3 data-info="a.name"> and "b.name"), and a <dl> with the rows „Medžiaga“ (<dd data-info="a.material">, which will hold several short lines: build it so that each line is its own element) and „Kaina“ (<dd data-info="a.price">); then one common <dl> with the row „Pristatymas“ (<dd data-info="shipping">, also possibly several lines). On a phone the two types stack; from about 700 px they sit side by side. The values are NOT known yet: the owner will supply the exact wording. Never invent them and never ship sample values. Every value element is empty for now; a row whose value is empty is not displayed, a type with nothing to show is not displayed, and while everything is empty the whole block displays nothing. In 3D mode the block is the one solid black plate of the page, where „Kol kas tiek“ used to be (after the lights-out beat, before the rack); while it is empty it must still occupy a fixed scroll length as a transparent spacer so that the story's anchors do not move when the values arrive (and when it is filled the plate may be taller than one screen on a phone: the story must cope with any plate height). Design: grey monospace micro-labels, values in the large sans in bone, generous spacing, nothing else. For screenshots and tests fill the values from the test script (page.evaluate) with obvious dummies such as „—“ on one, two and five lines; do not add a URL switch for that and leave the file empty.

COLOURS: the visitor can see the shirt in black (the default) and in white. The control is two round swatches with no visible text: 44 px targets with a 22 px dot (a black dot with a thin bone ring, a white dot), aria-label „Juoda“ and „Balta“, aria-pressed, in a role="group" labelled „Spalva“, fixed at the bottom centre of the stage above the safe area. They are shown while the figure is the subject (the hero, the walk round, the figure-as-item beat), fade out during the close-ups if they would sit on the subject, during the info block, the rack photos and the grid, and are inert while hidden; Tab reaches them, Enter or Space switches. Switching eases over about 250 ms and changes only: the cloth colour (black #0e0e10 as now; white about #ecebe6, with the rim gain and exposure tuned by eye so the white shirt keeps its folds and does not blow out), and the ink of the back print (the back texture is one-colour line art with alpha: tint it bone-white on the black shirt and near-black #141414 on the white shirt). The front print is the same on both. In the lights-out beat the map glows in bone on either colour (the lit copy ignores the ink tint). The choice lasts for the page view only (no storage); expose it as window.__m.color. The static page has no swatches and shows the photos of the black shirt.

PRINT SIZE: the back artwork's real size is now known from the print-ready file: 29.7 cm wide, 33.6 cm tall. The model's PrintBack decal will be 0.297 x 0.396 m (its 3:4 canvas with the artwork at the top); the current model file may still carry a larger decal until the model team delivers the draped shirt. Read sizes from the file as always, and correct the numbers in SPEC section 0.2 and anywhere else they are quoted.

PHOTOS: the three real photos (print close-up, worn back, worn front; built by build.cjs into merch/v/ph/) leave the plates and become the first three tiles of the grid, so the grid has twelve tiles (3 x 4 at every width in 3D mode, 3 or 2 columns on the static page as today) and stays bare: no captions. They open in the lightbox like the others. The rack keeps the nine NA2 photos 01 to 09.

SCROLL STORY: the same camera beats in the same order (hero, push-in to the chest lettering, hold, walk round, back with the map, lights out with the red line, info block, figure as an item, rack, grid). The former plates „Priekis“ and „Nugara“ become short transparent holds; trim dead scroll so the whole page is about six to seven screens on a 390 x 664 phone before the grid. The sign „NA2“ is still eclipsed and fades during the push-in.

HEAD: <title> and og:title stay „NA2 marškinėliai – OG VERSION merch“; meta description and og:description become „Juodi NA2 marškinėliai. Priekyje – „NA2“ iš eurų banknotų, nugaroje – Šilainių žemėlapis.“; keep noindex, canonical, og:image, favicon.

STATIC PAGE (no WebGL, no JavaScript, reduced motion, Save-Data, failure): the giant „NA2“ with the worn-back photo as the hero image, the info block, the grid of twelve. Nothing else, and no swatches.

DOCUMENTS: update ${R}/work3d/spec/SPEC.md and ${R}/work3d/spec/CONTENT-RULES.md in place so they describe the page as decided (blocks, cluster, microcopy lists, page texts, storyboard HTML and interaction columns, controls, rack access, reduced motion, tab order, checklists, cut list; in CONTENT-RULES: the only visible text is „NA2“, the info block's labels and the owner's values; type names, material, price and shipping are stated only in the owner's own wording; the two types and two colours are facts; everything else stays unstated). Keep both files coherent and free of leftovers; do not add a history section, just one dated line in the ground rules that the owner removed all other text.

## Tools and inputs
- cd ${R}/work3d : node_modules is present (three r187, esbuild, sharp, gltf-transform; Playwright is installed globally: require('playwright') works, chromium.launch() needs no options, never install browsers). npm run build rebuilds the code and re-checks budgets; a full rebuild of model, prints and photos is: cd ${R}/merch/v && NODE_PATH=../../work3d/node_modules MODEL=${S}/na2/model/current.glb FRONT=../../work3d/art/front.png BACK=../../work3d/art/back.png ARTMETA=../../work3d/art/meta.json PHOTOS=../../work3d/ref node build.cjs . The model file is being improved by another team right now (a properly draped shirt will replace the crude shell): always do a full rebuild with the newest file right before your final verification, and never hard-code geometry.
- The print textures are final (built from the owner's original artwork). Note that the back canvas is 3:4 with the artwork top-aligned and an empty band under the caption; work3d/art/meta.json has artBox, mapBox and captionBox (fractions of the canvas, v from the top) and the build passes captionBox to the page. Frame the map and place the red line from those boxes, not from fixed fractions of the decal.
- Static server: node ${R}/work3d/tests/serve.js 8361 (root = the repository). Screenshot and test scripts: work3d/tests/shots-na2.js, test-int-na2.js, static-na2.js, tune-na2.js (update them to the new page; outputs under work3d/tests/shots-na2/ and work3d/tests/tmp/ are not committed). Stop any server you start.
- Headless Chromium renders WebGL in software: every 3D test URL needs ?3d=1 (which also disables the frame-rate fallback and tier drops). deviceScaleFactor 1 for your own checks, one browser at a time; the machine has 4 CPUs shared with other jobs, allow 60 to 120 s for a load.

## Hard rules
- Write only: merch/index.html, files under merch/v/, work3d/spec/*.md and work3d/tests/ . Never touch merch/p/, work3d/art, work3d/model, work3d/ref or any other file.
- No git commands that change anything (no add, commit, checkout, stash, reset); reading is fine.
- Do not call environment, credential, repository or session tools; no web search or fetch.
- No third-party assets or scripts, no external requests from the page, everything self-hosted under /merch/ ; runtime fetches resolve relative to the bundle.
- No price, material, shipping, size, stock or any other fact invented by you. No visible text beyond what the decision allows. Keep <meta name="robots" content="noindex">.
- No AI model names or tool names in code, comments or page text. Plain, readable, commented source; the committed bundle is merch/v/app.js .
`

const BUILD_SCHEMA = {
  type: 'object',
  properties: {
    summary: { type: 'string' },
    done: { type: 'array', items: { type: 'string' } },
    notDone: { type: 'array', items: { type: 'string' } },
    deviations: { type: 'array', items: { type: 'object', properties: { spec: { type: 'string' }, actual: { type: 'string' }, why: { type: 'string' } }, required: ['spec', 'actual', 'why'] } },
    tests: { type: 'array', items: { type: 'object', properties: { name: { type: 'string' }, pass: { type: 'boolean' }, note: { type: 'string' } }, required: ['name', 'pass'] } },
    sizes: { type: 'object', properties: { htmlBytes: { type: 'number' }, appJsGzipBytes: { type: 'number' }, figureGlbBytes: { type: 'number' }, firstViewBytes: { type: 'number' } } },
    modelUsed: { type: 'string' },
    screenshotsDir: { type: 'string' },
    notesForNext: { type: 'string' },
  },
  required: ['summary', 'done', 'notDone', 'deviations', 'tests', 'modelUsed', 'screenshotsDir', 'notesForNext'],
}

phase('Strip')
const strip = await agent(`${CTX}

## Your task: stage A, apply the owner's decision and finish the core
1. Rework merch/index.html and the sources to the decision above, in both modes. Remove dead code and dead styles with the removed elements (HUD buttons, close-up toggle, light override, hints, plates, bar, album, footer), keep the modules tidy. The hidden range input stays as the keyboard way to turn the figure.
2. Add the info block exactly as specified (two types plus shipping, empty values, block invisible while empty, transparent spacer of constant scroll length in 3D mode), and the two colour swatches with the white variant of the shirt.
3. Move the three real photos into the grid (twelve tiles) and update the lightbox list.
4. Retime the scroll story for the page without plates; frame the map and place the red line from meta boxes.
5. Update SPEC.md and CONTENT-RULES.md as described.
6. Verify, by running it (do not guess): storyboard screenshots through ?s= and real scrolling at 390x664 (touch emulation), 844x390 and 1440x900 for every beat, plus hero yaw 90 and 180; LOOK at them and iterate until the picture is right: the giant „NA2“ with head and shoulders over its lower part and nothing else on screen in the hero; the chest lettering filling the frame; the figure from the side half way round; the map filling the frame; in the dark only the map and caption lit with the red line exactly under the caption; the info block (with dummy values injected by the test) readable and well composed at phone and desktop widths, and absent without values; the white shirt in the hero, from behind (black ink map) and in the dark beat, with its folds visible and nothing blown out; the swatches small, clear and never on top of the subject; the figure as an item under the rail; legs fading into black. A cheap or empty-looking frame is a defect: with the text gone the 3D picture carries everything, so tune framing, light and timing within the spec's intent and report what you changed.
7. Interaction and mode checks, measured through window.__m : drag and flick with detents; vertical touch drag scrolls, horizontal spins; edge drags ignored; wheel never blocked; keyboard rotation through the hidden range input; colour switching by pointer, touch and keyboard (window.__m.color), including in the middle of a spin and in the dark beat; lightbox from all twelve tiles; ?3d=0, no WebGL, blocked app.js, blocked figure.glb, timeout: each ends as the complete static page with reading position kept; no console errors, 404s, external requests or horizontal scroll at 360, 390, 768, 1024, 1440 and 1920 px in both modes; a grep proving no removed text is left in index.html, the sources, the bundle and the two spec files.
Return the structured result with honest notDone and notesForNext for the builder who adds the rack and robustness features.`,
  { label: 'build:strip', phase: 'Strip', schema: BUILD_SCHEMA })
if (!strip) return { error: 'stage A returned nothing' }
log(`stage A: ${strip.done.length} done, ${strip.notDone.length} not done`)

phase('Rack')
const rack = await agent(`${CTX}

## Your task: stage B, the rack and the robustness features
Stage A is done. Its report: ${JSON.stringify({ summary: strip.summary, notDone: strip.notDone, deviations: strip.deviations, notesForNext: strip.notesForNext })}

Build what the (updated) spec still lists as missing, keeping everything that works:
1. The rack (spec section 4 as updated: no bar, no counter): the red rail, nine photo panels 01 to 09 on clips with their reflections, placeholders in the average colour until a texture decodes, one texture at a time lazily, the camera travelling along the panels by scroll with the soft dwell, the horizontal flick with inertia and snap, scroll reclaiming control, panel swing, tap on a panel opening the existing lightbox on that photo; the grid of twelve remains the complete keyboard and screen-reader path. merch/v/src/rack.js documents the seam at its top.
2. The quality governor and tiers, context-loss recovery, the late frame-rate goStatic (all disabled under ?3d=1 as now), loop sleeping when the tab is hidden, the lightbox is open or the page is scrolled past the rack, the sharper front texture swap after idle. Calm mode and the „Įjungti 3D“ button are NOT built (removed by the owner's decision). Build the opaque escape hatch only if it costs under an hour; otherwise leave it out and say so.
3. First, finish anything stage A left undone.
4. Verify by running it: rack screenshots at the three viewports (panel filling the frame, several panels in transit, the reflection, the rail drawing in), a flick that changes window.__m.u and settles on an integer, a tap opening the right photo, lazy loading order in the network log, no /merch/p/ request in 3D mode before the lightbox opens, draw calls within budget in the hero and in the rack, no rAF callbacks for 2 s when hidden / dialog open / scrolled past, one simulated context loss recovering and a second one falling back to the static page with position kept, budgets after a full rebuild with the newest model. Update the test scripts so the next person can rerun everything with one command each, and update SPEC.md if you had to settle anything it left open.
Return the structured result.`,
  { label: 'build:rack', phase: 'Rack', schema: BUILD_SCHEMA })
log(`stage B: ${rack ? rack.done.length + ' done, ' + rack.notDone.length + ' not done' : 'returned nothing'}`)

const FINDINGS_SCHEMA = {
  type: 'object',
  properties: {
    lens: { type: 'string' },
    overall: { type: 'string' },
    score: { type: 'number', description: '1 to 10 from this lens' },
    findings: { type: 'array', items: { type: 'object', properties: {
      id: { type: 'string' }, severity: { type: 'string', enum: ['blocker', 'major', 'minor'] }, title: { type: 'string' },
      evidence: { type: 'string' }, repro: { type: 'string' }, suggestedFix: { type: 'string' } },
      required: ['id', 'severity', 'title', 'evidence', 'repro', 'suggestedFix'] } },
    screenshotsDir: { type: 'string' },
  },
  required: ['lens', 'overall', 'score', 'findings'],
}

const LENSES = [
  { key: 'visual', prompt: `Lens: art direction. Screenshot every beat of the story at 390x664 (touch emulation), 844x390 and 1440x900 through ?s= and also by real scrolling, plus hero yaw 0, 45, 90, 180 and the rack in transit. Judge like a demanding art director and like a 19-year-old arriving from Instagram: with all text gone, does every frame hold on its own? Is the „NA2“ / figure composition striking; does the black shirt separate from the black void and read as cloth; does the plaster figure look deliberate; do the legs fade; is the camera walk smooth with no jump, flip, clipping through the figure or empty frame; do the chest lettering and the map fill their frames; in the dark are only the map and caption lit with the red line exactly under the caption and glued to the cloth when the figure is wiggled; is the info block (inject dummy values of one, two and five lines per value from your script) well composed on a phone and on a desktop and truly absent when empty; does the white shirt look as good as the black one in every beat (folds visible, not blown out, black-ink map crisp, body and shirt still distinguishable) and are the swatches discreet, clear and never over the subject; do rack panels fill the frame with clean reflections; is there dead scroll where nothing changes for more than about half a screen; any z-order mistake, flash of a half-loaded state, banding or aliasing on the thin map lines at phone size. The model's shirt may still be a crude stand-in if the other team has not delivered: do not report the stand-in's shape itself, report everything the page does with it. Every finding needs a screenshot path.` },
  { key: 'interaction', prompt: `Lens: interaction, with real pointer and touch events, measured through window.__m. Scroll versus spin arbitration (vertical drag scrolls and leaves yaw alone, horizontal spins and does not scroll, drags starting within 20 px of the screen edge do nothing, a second finger cancels, nothing ever traps scrolling, wheel from top to bottom never blocked, script never sets scroll position except in the documented fallback), drag ratio, inertia, flick landing on detents with overshoot, the ±35 degree limit while the story holds the front, keyboard rotation through the hidden range input (arrows, Home, End, focus ring on the figure, value text), live region messages, the rack flick settling on an integer, scroll reclaiming the rack, tap on each panel opening the right photo, colour swatches by pointer, touch and keyboard at every beat (state, aria-pressed, inert while hidden, no accidental spin or scroll when tapping them), lightbox focus trap / Esc / arrows / focus return from all twelve tiles and from a rack tap, resize and orientation change in the middle of each beat, anchor jumps and restored scroll positions (dip, no fly-through), pinch zoom not hijacked. Also confirm that no removed control survives as a focusable or clickable ghost.` },
  { key: 'fallback-content', prompt: `Lens: loading, fallback, content and accessibility. First paint without JavaScript and with app.js blocked; the loader line monotonic under throttling; ?3d=0, no WebGL2, software renderer without ?3d=1, reduced motion, Save-Data, forced colours, figure.glb blocked, a print texture blocked, the timeout, context lost twice: each ends as the complete static page (giant „NA2“, hero photo, info block when it has values, grid of twelve) with the reading position kept; static mode downloads no 3D code or model; 3D mode downloads nothing from /merch/p/ before the lightbox opens; no external requests, console errors or 404s; no horizontal scroll at 360x640, 390x664, 390x844, 430x932, 768x1024, 844x390, 1024x768, 1440x900, 1920x1080 in both modes. Content against the owner's decision: grep index.html, merch/v/src, the bundle and both spec files for every removed text and control; confirm the ONLY visible text on the rendered page is „NA2“ plus the info block when filled (the swatches carry no visible text) (take a text dump of visible nodes in both modes, with and without injected values); the info block ships empty and invisible, with no sample values anywhere; no invented fact; head tags as decided; noindex kept; alts present on all twelve photos; one h1, hidden h2, sensible landmark structure, lang="lt"; the hidden range input reachable and announced; focus visible on every focusable thing; nothing hidden takes focus; no person's face in any image the page uses. Also read SPEC.md and CONTENT-RULES.md for leftovers of removed elements and for contradictions with the page.` },
  { key: 'perf-code', prompt: `Lens: performance, budgets and code. Budgets after a full rebuild (bundle gzip, figure.glb, first view, triangles, draw calls in the hero and in the rack, three lights, no shadow maps, DPR caps by pointer type); the on-demand loop really stops (no rAF callbacks for 2 s) when the tab is hidden, the lightbox is open, the page is scrolled past the rack, and after the fallback; per-frame DOM writes limited to what the spec allows; listeners passive; texture uploads staggered; memory after goStatic (renderer disposed, canvas removed, listeners gone); governor logic and tier contents; context-loss handling; resize debounce and the toolbar-height rule; behaviour when optional mesh classes are missing or when the model has several cloth meshes or no normal maps; azimuth interpolation never wrapping. Then read all of merch/v/src and build.cjs as a reviewer: real bugs, dead code left from removed features, constants that should come from the model or meta.json but are hard-coded, error paths that swallow failures, anything that would break on Safari or Firefox (features without support checks, non-standard APIs), and whether the build is reproducible from a clean checkout with the documented command. Run the test scripts in work3d/tests and report which pass.` },
]

phase('Review')
const reviews = (await parallel(LENSES.map(l => () => agent(`${CTX}

## Your task: independent review
You did not write this code and you should distrust the builders' reports (stage A: ${JSON.stringify(strip.summary)} ; stage B: ${JSON.stringify(rack ? rack.summary : 'no report')}). Do NOT edit anything in ${R} except your own scratch files under ${R}/work3d/tests/tmp/review-${l.key}/ (scripts and screenshots; that folder is not committed). Start your own server on a free port and stop it when done. ${l.prompt}

Report every real defect you reproduced as a finding (blocker = broken or embarrassing; major = clearly wrong against the decision or the spec, or visibly poor; minor = polish) with precise evidence, a way to reproduce it and a concrete fix. Leave out what you could not reproduce. Give an honest overall verdict and a score.`,
  { label: `review:${l.key}`, phase: 'Review', schema: FINDINGS_SCHEMA }).then(r => r ? { ...r, lens: l.key } : null)))).filter(Boolean)

const all = reviews.flatMap(r => r.findings.map(f => ({ lens: r.lens, ...f })))
log(`review: ${reviews.map(r => r.lens + ' ' + r.score + '/10').join(', ')}; ${all.filter(f => f.severity === 'blocker').length} blockers, ${all.filter(f => f.severity === 'major').length} majors, ${all.filter(f => f.severity === 'minor').length} minors`)

const FIX_SCHEMA = {
  type: 'object',
  properties: {
    summary: { type: 'string' },
    fixed: { type: 'array', items: { type: 'object', properties: { id: { type: 'string' }, lens: { type: 'string' }, how: { type: 'string' }, verifiedBy: { type: 'string' } }, required: ['id', 'how', 'verifiedBy'] } },
    rejected: { type: 'array', items: { type: 'object', properties: { id: { type: 'string' }, why: { type: 'string' } }, required: ['id', 'why'] } },
    remaining: { type: 'array', items: { type: 'object', properties: { id: { type: 'string' }, why: { type: 'string' } }, required: ['id', 'why'] } },
    sizes: { type: 'object', properties: { htmlBytes: { type: 'number' }, appJsGzipBytes: { type: 'number' }, figureGlbBytes: { type: 'number' }, firstViewBytes: { type: 'number' } } },
    modelUsed: { type: 'string' },
    finalShotsDir: { type: 'string' },
    finalShots: { type: 'array', items: { type: 'string' } },
    notesForNext: { type: 'string' },
  },
  required: ['summary', 'fixed', 'rejected', 'remaining', 'modelUsed', 'finalShotsDir', 'finalShots', 'notesForNext'],
}

phase('Fix')
const fix = await agent(`${CTX}

## Your task: fix what the reviewers found
Four independent reviewers returned these verdicts and findings (their evidence is under ${R}/work3d/tests/tmp/review-*/):
${JSON.stringify(reviews.map(r => ({ lens: r.lens, score: r.score, overall: r.overall, findings: r.findings })), null, 1)}

First do a full rebuild with the newest model. For each finding: reproduce it; if real, fix it in the source, rebuild and verify with a screenshot or a measured value; if not real, or against the owner's decision or the spec, reject it with the reason. Fix every blocker and major and each cheap minor. Act on the overall verdicts too: where a reviewer calls a frame weak or empty, improve it within the spec's intent until your own screenshots look premium, and report what you changed. Keep SPEC.md in step with any behaviour you change. Rerun all test scripts, the removed-text grep, the mode checks and the budget checks after your changes. Stop any server you started.

Finish with the final screenshot set in ${S}/send3/ at deviceScaleFactor 2 (they will be shown to the owner): 390x664 touch emulation: hero settled, hero yaw 180, chest close-up, half way round, back with the map, lights-out with the red line, info block with dummy values „—“ injected, figure under the rail, a rack panel, the grid, then the white shirt: hero, hero yaw 180, back with the map; and 1440x900: hero, chest, lights-out, rack, white hero. Name them <viewport>-<nn>-<stop>.png .`,
  { label: 'fix:all', phase: 'Fix', schema: FIX_SCHEMA })

phase('Verify')
const VER_SCHEMA = {
  type: 'object',
  properties: {
    verdict: { type: 'string', enum: ['pass', 'pass-with-minor', 'fail'] },
    summary: { type: 'string' },
    results: { type: 'array', items: { type: 'object', properties: { id: { type: 'string' }, status: { type: 'string', enum: ['fixed', 'not-fixed', 'partly', 'regressed', 'rejected-correctly', 'rejected-wrongly'] }, evidence: { type: 'string' } }, required: ['id', 'status', 'evidence'] } },
    newFindings: { type: 'array', items: { type: 'object', properties: { severity: { type: 'string', enum: ['blocker', 'major', 'minor'] }, title: { type: 'string' }, evidence: { type: 'string' }, suggestedFix: { type: 'string' } }, required: ['severity', 'title', 'evidence', 'suggestedFix'] } },
  },
  required: ['verdict', 'summary', 'results', 'newFindings'],
}
const verify = fix ? await agent(`${CTX}

## Your task: independent verification of the fixes
You did not write or fix this code. The reviewers' findings were: ${JSON.stringify(all.map(f => ({ id: f.id, lens: f.lens, severity: f.severity, title: f.title, repro: f.repro })), null, 1)}
The fixer reports: ${JSON.stringify({ fixed: fix.fixed, rejected: fix.rejected, remaining: fix.remaining })}
Do NOT edit anything in ${R} except scratch files under ${R}/work3d/tests/tmp/verify/ . For every finding re-run its reproduction on the current build and state whether it is fixed, partly fixed, not fixed, or was rejected correctly or wrongly, with evidence. Then a regression pass: run the test scripts in work3d/tests, the removed-text check on the rendered page in both modes (visible text must be only „NA2“ plus the info block when filled), the mode checks and the budgets, and look at a fresh storyboard screenshot set at 390x664 and 1440x900 for anything that got worse. Report new problems as newFindings.`,
  { label: 'verify:fixes', phase: 'Verify', schema: VER_SCHEMA }) : null

return { strip, rack, reviews: reviews.map(r => ({ lens: r.lens, score: r.score, overall: r.overall, counts: { blocker: r.findings.filter(f => f.severity === 'blocker').length, major: r.findings.filter(f => f.severity === 'major').length, minor: r.findings.filter(f => f.severity === 'minor').length } })), fix, verify }
