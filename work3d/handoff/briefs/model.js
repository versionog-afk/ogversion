export const meta = {
  name: 'na2-figure-model-v2',
  description: 'Phases 2 and 3 with the approved tools: finish the figure, write the MPFB2 recipe for the PC, build the oversized NA2 tee from a sewing pattern with Blender cloth simulation, independent critique and refinement',
  phases: [
    { title: 'Figure', detail: 'finish the interrupted figure stage; in parallel, an MPFB2 recipe for Blender on the PC' },
    { title: 'Garment', detail: 'sewing pattern, Blender cloth drape on the figure, two print decals, bake, export' },
    { title: 'Critique', detail: 'art director against the owner photos, technical artist against the contract' },
    { title: 'Refine', detail: 'fix findings, re-verify, up to two rounds' },
  ],
}

const S = '<CLOUD>'
const M = S + '/na2/model'

const CTX = `
## Situation
OG VERSION is a small music / streetwear brand from Kaunas (Šilainiai). Its web page /merch is being rebuilt as an interactive 3D page (three.js r187, phone-first): a stylised human figure wearing a real garment the brand has made. You are on the model team. The work is also being handed over to the owner's own PC, where it will continue in Blender with a GUI, so everything you build must be reproducible from scripts and documented briefly.

The garment (the owner's own photos and video are the truth):
- a black, heavy, OVERSIZED boxy T-shirt: dropped shoulders, wide sleeves that reach the elbow, thick ribbed crew collar sitting close to the neck, hem at the hip / upper thigh, thick cloth that falls in a few large soft folds rather than many small wrinkles;
- front: small lettering "NA2" (letters built from euro banknotes) on the wearer's LEFT chest;
- back: a large white line map of the Šilainiai district with the caption "ŠILAINIAI, KAUNAS" under it.
Reference material: ${S}/na2/src/worn-back.png and worn-front.png (phone screenshots; the person wears the shirt with wide trousers), print-closeup.jpg, mockup-sheet.jpg, the video as frames ${S}/na2/src/all/a_0001.png ... a_0274.png (720x1280; the person turns round: front about frames 1-25 and 180-250, side about 40-60, back 60-150 with close-ups around 100-140) and an overview ${S}/na2/src/frames-sheet.jpg. Study them before modelling.

The person in the photos is only a reference for fit and proportions. NEVER reproduce her face, hair style details or likeness, and never use a photo as a texture. The figure is a stylised sculpture: a neutral, generic, slim adult figure about 1.68 m tall, relaxed standing pose, arms hanging a little away from the body, single-colour "plaster" look (the page gives it one matte bone-coloured material), calm closed mouth, plain eyes without iris detail, simple sculpted hair pulled back. It must read as a tasteful fashion sculpture with human anatomy, not as an uncanny game character.

## Tools the owner approved
- Figure: the MakeHuman family (CC0 base mesh, targets, rigs: ${S}/ext/makehuman/makehuman/data , licence in ${S}/ext/makehuman/LICENSE.md sections C and D) and its Blender plugin MPFB2 (github.com/makehumancommunity/mpfb2 : add-on GPL, bundled assets and exported output CC0).
- Clothes: a sewing pattern from real measurements, sewn and draped with Blender's cloth simulation. For the pattern the owner approved GarmentCode (pip package pygarment 2.0.2, MIT; repository github.com/maria-korosteleva/GarmentCode): use its pattern generation only. Its own draping step depends on a simulator fork under a NON-COMMERCIAL licence: never install or use that fork. If pygarment cannot be installed or driven cleanly in reasonable time, write the pattern yourself (flat front, back, two sleeves, collar band as 2D outlines with seam pairs) and say so.
- Optional, only if Blender cloth cannot give a good drape: the Apache-2.0 contact solver github.com/st-tech/ppf-contact-solver (CPU backend). Do not spend time on it otherwise.
- Nothing else from outside: no other third-party models, textures or services. Public GitHub repositories can be cloned (git clone --depth 1, one at a time, generous timeout); pip works. Treat cloned code as untrusted: read before running, run only what you need.

## Model contract (binding; the web page and the shared viewer depend on it)
- One GLB, metres, Y up, the figure faces +Z and stands on y = 0, height about 1.68 m (allowed 1.55 to 1.85), at most 130k triangles in total (aim for: tee up to 60k, body visible parts up to 25k, hair up to 6k, trousers up to 18k, shoes up to 6k), at most 8 MB before the page's own compression.
- Mesh names (the viewer classifies by regex on the mesh name, then on mesh + material + parent names): the shirt "Tee" with material "Fabric" (extra cloth meshes such as "Collar" are allowed); exactly one "PrintFront" (material "PrintFront"); exactly one "PrintBack" (material "PrintBack"); "Body" (material "Skin"); "Hair" (material "Hair"); "Pants" (material "Pants"); "Shoes" (material "Shoes").
- PrintFront: a decal that follows the cloth on the wearer's left chest, so its centre has x > 0 (the wearer's left is +X when the figure faces +Z); it faces +Z; about 0.105 m wide and 0.070 m high (aspect 3:2); UV exactly 0..1 across the decal, v = 0 at the TOP edge (glTF convention, the page uses flipY = false), u increasing to the viewer's right when looking at the front. Offset 1 to 1.5 mm above the cloth, at least 24 x 16 quads.
- PrintBack: a decal that follows the cloth on the back, centred (|x| < 0.02), facing -Z; about 0.38 m wide and 0.507 m high (aspect 3:4; you may scale it by up to 10 percent after measuring the photos, keeping the aspect); its top edge roughly 9 to 12 cm below the collar seam; UV 0..1, v = 0 at the top, u increasing to the right AS SEEN FROM BEHIND; offset 1 to 1.5 mm; at least 60 x 80 quads.
- The shirt must look right from every angle of a 360 degree spin and when the camera comes close to the chest and to the back; the inside of the collar and sleeve openings must not show holes (double-sided cloth or an inner layer); nothing pokes through; body faces hidden under the shirt and trousers should be deleted (keep a safe margin at openings).
- Cloth meshes may carry a tangent-space normal map and an occlusion map (at most 2048 px, embedded) with clean UVs.
- The page fades everything below about y = 0.85 m into black, so trousers and shoes need a correct silhouette but little detail. Trousers: wide straight legs, plain, waistband hidden under the shirt.
- Print textures for test renders: ${S}/na2/art/front.png (3:2) and ${S}/na2/art/back.png (3:4). They are placeholders; never edit them.

## Working environment
- Blender 5.3 as a Python module: ${S}/bvenv/bin/python your_script.py (import bpy; headless; cloth simulation, BVH, baking with Cycles CPU and glTF export work). numpy is installed there. System python3 (3.13) has numpy, opencv, PIL. For packages that need another Python, make a venv under your own folder.
- Earlier work you may reuse (read it first): ${M}/body/ (the interrupted figure stage: shape and pose from the CC0 base mesh, hair, trousers, shoes; build.sh, figure.py, hair_bl.py, pants.py, shoes_bl.py, assemble.py, standin.py; outputs body.glb, collide.obj, landmarks.json), ${S}/tee/cand-B/teegen/ (a complete pipeline for a regular-fit tee: lofted shell, Blender cloth simulation over a mannequin, decal projection in printpatch.py, UVs, normal / occlusion bake in textures.py, GLB export in glb.py) and ${S}/tee/cand-A/ (sewn flat panels with seams, unfinished). Copy what you need; do not edit ${S}/tee .
- Shared viewer and contract checker (never edit): cd ${S}/na2/harness && node shot.js <absolute path to .glb> <output dir>   writes sheet-studio-full.png, sheet-studio-top.png, sheet-clay-top.png, sheet-dark.png, sheet-prints.png, sheet-uv.png, hero-dark-*.png and stats.json with contractWarnings. About a minute. The machine has 4 CPUs shared with other jobs: one heavy thing at a time, be patient.
- House rules: write only under ${M}/ (your own subfolder) unless told otherwise; never edit ${S}/na2/harness, ${S}/na2/art, ${S}/na2/src or the repository <REPO>. No git commands in the repository. Do not call environment, credential, repository or session tools; no web search.
- ${M}/current.glb is the file the web page is built from. Replace it only with a version that passes the contract check, and always atomically (write ${M}/current.tmp.glb, then rename over current.glb).
- Scripts must not contain absolute paths of this machine except through one clearly marked ROOT variable at the top, because they will be moved to another computer.
`

const UPDATE = `

## UPDATE from the owner (newer than everything above; it overrides the contract and the description wherever they differ)
- Two shirt types: the brand sells this shirt in two types, each in black and in white, and the page will let the visitor switch between both types on the figure. Build the LIGHTER type now; the heavier one (370 g/m2 cotton interlock, a different cut) will be built later from pictures the owner has not sent yet. So the pipeline must take a shirt specification (measurements.json plus a named fabric preset) and rebuild everything from it with one command, so that a second specification later yields the second shirt on the same figure.
- The lighter type, to build now: a unisex oversized tee in 220 g/m2 cotton jersey (single jersey: clearly thinner and softer than interlock, it drapes more readily and shows more and softer folds, but it is still a streetwear tee with body, not a thin undershirt), dropped shoulders, collar in 1x1 rib, double stitching on the sleeves and the bottom hem (two parallel stitch lines about 2 cm from the edge: they belong in the normal map), reinforcing tape inside the back of the neck, and a small custom label there. Its cut is shown in ${S}/na2/src/shirt-black-front.png and ${S}/na2/src/shirt-white-front.png (1000 x 1000 each: the brand's own shirt laid flat, front view, in black and in white): a long straight body, dropped shoulders, wide sleeves ending near the elbow, a close crew collar. Derive the pattern proportions from these two pictures (ratio of body width to length, sleeve length and width, shoulder drop, collar opening and rib width). It is not known which of the two types the person wears in the video and the worn photos: use those for how such a shirt hangs on a body and for scale, the flat pictures for the cut. Earlier studio pictures of a shorter blank shirt were withdrawn by the owner: if you find files named blank-* anywhere, or notes derived from them, ignore them. The owner will send tape measurements later, so keep every dimension in measurements.json.
- Extra outputs for the two-type page (in addition to the complete figure.glb the contract asks for): shirt-only.glb (Tee, PrintFront, PrintBack, Label) and body-only.glb (Body, Hair, Pants, Shoes), both in the same coordinates. Delete body faces hidden under the shirt only where a shirt reaching just to the hip bone would hide them too (the heavier type is shorter), and say in the README where that limit is set.
- Neck label: model it as its own small mesh named "Label" with material "Label": a thin, slightly curved rectangle about 20 x 14 mm, sewn by its top edge to the inside of the back collar seam, lying 1 mm off the cloth and facing the front through the neck opening; UV 0..1 across it with v = 0 at the top and u increasing to the viewer's right when seen from the front. The shared viewer classifies the name as "label" and renders it dark; the page will give it a texture.
- Two colours: the shirt is sold in black and in white, and the page recolours the cloth and the ink. Normal and occlusion maps must therefore carry no colour and must look right on a white shirt too (a white shirt shows every shading flaw and every dark smear in the occlusion). The shared viewer renders black only: make your own white-cloth renders (cloth about #ecebe6, black ink on the back) and judge both.
- Back print, real size: the print-ready artwork is 29.7 cm wide and 33.6 cm tall (map 29.7 x 29.7 cm, then the caption). The back texture ${S}/na2/art/back.png is a 3:4 canvas with that artwork at the top (the lowest 16 percent is an empty transparent band). So PrintBack is exactly 0.297 m wide and 0.396 m high, centred, and placed so that the TOP of the artwork is where it is on the real shirt (measure on the worn photos and frames; about 7 to 10 cm below the collar seam). The checker now expects a width of about 0.297 m. ${S}/na2/art/meta.json has the boxes of the artwork, the map and the caption inside the canvas.
- Front print: the texture ${S}/na2/art/front.png is the real artwork (lettering centred on a 3:2 canvas). Its real width in centimetres is still to come from the owner; keep about 0.105 m for the canvas and keep the value in measurements.json.
- Both textures are final artwork now, not placeholders. Never edit them.
- Earlier attempts at the garment stage were interrupted within minutes: ${M}/v1/ may already hold its first files (a venv, downloads, notes). Look before you start and continue from what is sound.`

const BUILD_SCHEMA = {
  type: 'object',
  properties: {
    summary: { type: 'string' },
    glb: { type: 'string' },
    shotsDir: { type: 'string' },
    stats: { type: 'object', properties: { triangles: { type: 'number' }, fileBytes: { type: 'number' }, heightM: { type: 'number' }, contractWarnings: { type: 'array', items: { type: 'string' } } } },
    howBuilt: { type: 'string', description: 'pipeline in a few sentences and the exact command that rebuilds everything' },
    files: { type: 'array', items: { type: 'string' } },
    thirdParty: { type: 'array', items: { type: 'string' }, description: 'every outside tool or asset actually used, with licence' },
    knownIssues: { type: 'array', items: { type: 'string' } },
    notesForNext: { type: 'string' },
  },
  required: ['summary', 'glb', 'shotsDir', 'howBuilt', 'thirdParty', 'knownIssues', 'notesForNext'],
}

const RECIPE_SCHEMA = {
  type: 'object',
  properties: {
    summary: { type: 'string' },
    worksHeadless: { type: 'boolean' },
    blenderVersionsChecked: { type: 'string' },
    recipeDir: { type: 'string' },
    files: { type: 'array', items: { type: 'string' } },
    steps: { type: 'array', items: { type: 'string' }, description: 'what the owner or an assistant does in Blender on the PC, in order' },
    assetPacks: { type: 'array', items: { type: 'object', properties: { name: { type: 'string' }, neededFor: { type: 'string' }, source: { type: 'string' }, licence: { type: 'string' } }, required: ['name', 'neededFor', 'source', 'licence'] } },
    problems: { type: 'array', items: { type: 'string' } },
  },
  required: ['summary', 'worksHeadless', 'recipeDir', 'files', 'steps', 'assetPacks', 'problems'],
}

phase('Figure')
const [body, recipe] = await parallel([
  () => agent(`${CTX}

## Your task: stage 1, finish the figure
An earlier builder was interrupted while refining the figure in ${M}/body/ (its last renders are in ${M}/body/shots/, for example fig3-head.png, hands-clay.png, pants3.png; the stand-in ${M}/current.glb was built by standin.py from that figure). Take over that folder: read build.sh and the scripts, rebuild once to confirm it runs, look at the renders, then finish:
1. Shape and pose: neutral slim adult figure about 1.68 m, relaxed stance, arms hanging a little away from the body (about 12 to 18 degrees, slight elbow bend), feet a little apart, head straight. Check shoulders, armpits, elbows and wrists for collapsed or twisted geometry after skinning and repair it.
2. Head and hands: a calm sculpture face (closed mouth, plain eyes or closed lids, no eyelashes, no teeth), tidy ears, clean hands with separated fingers. Fix anything uncanny or lumpy.
3. Hair: a simple sculpted volume pulled back with a low bun, a clean hair line, no strands, no transparency.
4. Trousers: wide straight legs from the waist to the ankle, a few soft vertical folds, an even hem; shoes: plain low shoes. No interpenetration between trousers, shoes and legs.
5. Clean up: consistent normals, smooth shading with sensible hard edges, no specks or loose fragments.
6. Outputs in ${M}/body/ : body.glb (Body, Hair, Pants, Shoes), collide.obj (the full posed body WITH the torso and with the trousers, inflated by 2 to 3 mm, closed), landmarks.json (metres: neck base centre and radius, shoulder points, armpits, chest front, upper back, waist, hip width and depth, crotch height, elbows, wrists, top of head) and a short README.md (how to rebuild, what each script does, which outside assets are used and their licence).
7. Run the checker on body.glb (the missing shirt and prints are expected warnings here) and LOOK at the sheets; iterate until it reads as a deliberate sculpture from every angle. Then rebuild the stand-in with the improved figure and, if it passes the contract check, replace ${M}/current.glb atomically.
Return the structured result; in notesForNext tell the garment builder where the files are, the pose, the landmarks and what matters for draping an oversized shirt.`,
    { label: 'model:figure', phase: 'Figure', schema: BUILD_SCHEMA }),
  () => agent(`${CTX}

## Your task: an MPFB2 recipe for the owner's PC
The owner approved MPFB2 (the MakeHuman plugin for Blender) as the way to make the figure in Blender on their own computer, where an assistant will drive Blender. Find out, by actually trying, how to use it from Python, and write a recipe. Work in ${M}/mpfb/ .
1. Clone https://github.com/makehumancommunity/mpfb2 into ${S}/ext/mpfb2 (shallow). Read its README, LICENSE files, blender_manifest.toml and the documentation about scripting / developer use. Record the exact licence statements for the add-on, the bundled assets and exported output.
2. Try to load it in the Blender 5.3 Python module here (${S}/bvenv/bin/python): register the extension from the clone (the package is under src/mpfb), create a human through its services or operators (for example the human creation service with macro settings: female, young adult, slim, height about 1.68 m), add a rig, and export a GLB. If headless use needs workarounds (preferences, asset paths, UI-only code), find them and note them; if it cannot work headless in this Blender version, establish why and what does work (for example calling its target and mesh services directly).
3. Establish what is bundled and what needs extra asset packs (skins, eyes, eyebrows, hair, clothes, proxies / topologies): pack names, where they are downloaded from, and each pack's licence as stated in the repository or documentation. Do not download packs from hosts that are blocked here; just document them.
4. Deliver: ${M}/mpfb/make_figure.py (a script that creates the figure with MPFB2 in Blender: runnable both as blender --python and with the bpy module; one ROOT / settings block at the top; produces a posed figure matching the contract's Body naming, or as close as MPFB2 allows, plus notes on what remains manual), ${M}/mpfb/README.md (installation of MPFB2 from extensions.blender.org on Windows and macOS, the recipe step by step for someone driving Blender on the PC, how it relates to the existing numpy pipeline in ${M}/body/ which uses the same CC0 base mesh, licences), and test renders if you got a figure out (run the shared checker on the exported GLB into ${M}/mpfb/shots/ ; missing shirt and prints are expected warnings).
Be honest about what you could not verify here. Return the structured result.`,
    { label: 'recipe:mpfb2', phase: 'Figure', schema: RECIPE_SCHEMA }),
])

if (!body) return { error: 'figure stage returned nothing', recipe }
log('figure done: ' + body.summary.slice(0, 140) + (recipe ? ' | MPFB2 headless: ' + recipe.worksHeadless : ' | MPFB2 recipe failed'))

phase('Garment')
const garment = await agent(`${CTX}${UPDATE}

## Your task: stage 2, the shirt on the figure
The figure is finished. Stage 1 report: ${JSON.stringify(body)}
Work in ${M}/v1/ .

1. Study the references again and write down the target measurements you derive from them (flat chest width, body length, shoulder width and drop, sleeve length and opening, collar rib height, hem line relative to the hip, print positions and sizes relative to the shirt) in ${M}/v1/measurements.json. Typical heavy oversized tee for scale: flat chest width 62 to 66 cm, body length 74 to 78 cm, sleeve opening 24 to 27 cm, collar rib 2.5 to 3 cm. The owner may later supply real tape measurements, so every dimension must come from that one file.
2. Pattern: make the sewing pattern from those measurements: front, back, two sleeves, collar band, with seam pairs. Try the approved GarmentCode route first (pip install pygarment in a venv under ${M}/v1/venv with a Python version it supports; use only its pattern classes and its pattern output: panel outlines and stitch definitions; do not install its simulator fork). Give it at most about 30 minutes; if it does not work cleanly, write the pattern code yourself and say so. Save the pattern as data (JSON with panels and seams) and a picture (pattern.png).
3. Sew and drape in Blender: triangulate the panels at a cloth-appropriate resolution, place them around ${M}/body/collide.obj , sew the seams (sewing springs or welded seams) and simulate with settings for THICK heavy cotton (high bending stiffness, real thickness / collision distance, enough mass, self-collision) so it hangs from the shoulders in a few broad folds, stands away from the waist, and the wide sleeves hang open to the elbow. Keep the collar a clean ribbed ring close to the neck. Let it settle completely. Adapt the earlier pipeline in ${S}/tee/cand-B/teegen/ where that is faster.
4. Construction detail that survives real-time shading: collar rib as its own thicker band, folded hems at the bottom and the sleeves, shoulder and sleeve seams as slight creases, real thickness at the openings or an inner layer so that looking into a sleeve or the collar never shows a hole.
5. Decals PrintFront and PrintBack per the contract, projected onto the SETTLED cloth so they follow the folds, positions and sizes measured from the photos.
6. Remove body and trousers faces hidden under the shirt (with margins), check for poke-through from all sides.
7. UVs for the cloth; baked tangent-space normal map (folds, collar rib texture, a faint knit grain) and occlusion map, at most 2048 px, embedded. Keep triangle counts inside the budget.
8. Export ${M}/v1/figure.glb with everything (Tee, PrintFront, PrintBack, Body, Hair, Pants, Shoes), run the checker into ${M}/v1/shots/ , LOOK at every sheet and compare side by side with the reference photos and frames. Iterate until: no contract warnings; silhouette, proportions and drape clearly read as that oversized shirt; prints in the right place and size, upright and unmirrored; nothing pokes through; collar, hems and sleeves look made, not extruded. Then replace ${M}/current.glb atomically.
9. Write ${M}/v1/README.md : the pipeline, the one command that rebuilds it, how to change measurements, which outside tools were used with licences, and what a person with Blender's GUI should check or improve by hand.
Return the structured result with honest knownIssues.`,
  { label: 'model:garment', phase: 'Garment', schema: BUILD_SCHEMA })

if (!garment) return { error: 'garment stage returned nothing', body, recipe }
log('garment done: ' + garment.summary.slice(0, 160))

const CRIT_SCHEMA = {
  type: 'object',
  properties: {
    lens: { type: 'string' },
    verdict: { type: 'string', enum: ['ship', 'ship-after-fixes', 'rework'] },
    score: { type: 'number' },
    summary: { type: 'string' },
    issues: { type: 'array', items: { type: 'object', properties: { severity: { type: 'string', enum: ['blocker', 'major', 'minor'] }, where: { type: 'string' }, issue: { type: 'string' }, evidence: { type: 'string' }, fix: { type: 'string' } }, required: ['severity', 'where', 'issue', 'evidence', 'fix'] } },
    shotsDir: { type: 'string' },
  },
  required: ['lens', 'verdict', 'score', 'summary', 'issues'],
}

function critics(glb, round) {
  return [
    { key: 'art-director', prompt: `${CTX}${UPDATE}

## Your task: independent art-direction review (round ${round})
You did not build this model; distrust the builders' reports. Model: ${glb}. Do NOT edit any model file; write your own renders and notes to ${M}/crit-ad-r${round}/ (run the shared checker there; you may write your own three.js or Blender renders for extra angles: a turntable every 30 degrees, a camera 0.5 m from the chest, 0.9 m from the back, looking slightly down into the collar and up into a sleeve).
Compare with the owner's photos and video frames side by side. Judge like the art director of a fashion brand and like the shirt's owner: Is this recognisably THAT shirt (oversized boxy cut, dropped shoulders, wide elbow-length sleeves, thick collar, hem length, heavy cloth with a few broad folds)? Do the prints sit where they sit on the real shirt, at the right size, following the cloth without distortion, upright and unmirrored, readable? Does the figure look like a deliberate, tasteful sculpture (proportions, pose, hands, neck, head, hair) or uncanny, stiff, lumpy, doll-like? Does it hold up from every angle of a spin, in the dark look with coloured rim lights, and close up? Poke-through, a hollow collar or sleeve, faceting, shading seams, melted or noisy cloth? Report concrete issues with the render path and where to look, by severity (blocker = cannot be shown to the owner), with a fix a technical artist can execute. Score 1 to 10 and a verdict.` },
    { key: 'tech-artist', prompt: `${CTX}${UPDATE}

## Your task: independent technical review (round ${round})
You did not build this model; distrust the builders' reports. Model: ${glb}. Do NOT edit any model file; write scratch files to ${M}/crit-tech-r${round}/ .
Verify by measurement: the shared checker (zero contract warnings required); ${S}/v3/node_modules/.bin/gltf-transform inspect and validate; mesh and material names; triangle counts per mesh against the budget; scale, orientation, feet on y = 0; decal sizes, positions, facing, offset from the cloth (gap distribution: no z-fighting risk, nothing floating more than 3 mm, no decal vertex under the cloth), UV range exactly 0..1 and orientation (sheet-uv.png: TOP-LEFT upright at the top left seen from each decal's own side); cloth normals consistent, no flipped faces, no degenerate triangles, no unwelded seams that shade as cracks; double-sidedness or inner layer at collar, sleeves and hem; no body or trousers triangle outside the cloth within the shirt region (ray casts from many directions); hidden faces removed; UV overlaps and texel density of the cloth; normal map correct for three.js / glTF (tangent space, green channel, no seams); texture sizes and formats; that the file survives the page's pipeline (gltf-transform dedup --materials false, weld, meshopt --level medium, textures to 1024 px WebP): report the compressed size (target at most 1.4 MB) and whether names survive. Load it in the shared viewer and check for console errors. Also check that the build scripts are reproducible from their README and contain no machine-specific absolute paths outside one ROOT variable. Report issues by severity with exact numbers and a concrete fix.` },
  ]
}

let current = { glb: garment.glb, shotsDir: garment.shotsDir, report: garment }
let crit = []
let round = 1
while (true) {
  phase('Critique')
  crit = (await parallel(critics(current.glb, round).map(c => () => agent(c.prompt, { label: `crit:${c.key}:r${round}`, phase: 'Critique', schema: CRIT_SCHEMA }).then(r => r ? { ...r, lens: c.key } : null)))).filter(Boolean)
  log(`critique round ${round}: ` + crit.map(x => `${x.lens}: ${x.verdict} ${x.score}/10, ${x.issues.filter(i => i.severity === 'blocker').length} blockers, ${x.issues.filter(i => i.severity === 'major').length} majors`).join(' | '))
  const must = crit.flatMap(c => c.issues.filter(i => i.severity !== 'minor'))
  if (must.length === 0 || round > 2) break
  phase('Refine')
  const next = await agent(`${CTX}${UPDATE}

## Your task: refine the model (round ${round})
Current model: ${current.glb} (pipeline in ${M}/v${round}/ ; reports: ${JSON.stringify({ figure: { howBuilt: body.howBuilt, files: body.files, notesForNext: body.notesForNext }, garment: current.report })}).
Two independent reviewers found these problems (their renders: ${crit.map(c => c.shotsDir || '').join(', ')}):
${JSON.stringify(crit.map(c => ({ lens: c.lens, verdict: c.verdict, score: c.score, summary: c.summary, issues: c.issues })), null, 1)}

Work in ${M}/v${round + 1}/ (copy the pipeline there). Reproduce each problem in your own renders first, then fix every blocker and major and each cheap minor; if a finding is wrong, say why. Prefer fixing causes (pattern, simulation settings, pose, decal projection) over hiding symptoms. Re-run the checker into ${M}/v${round + 1}/shots/ , look at every sheet, compare with the reference photos again, update the README, and only then replace ${M}/current.glb atomically. Return the structured result (glb = the new file) with honest knownIssues.`,
    { label: `refine:r${round}`, phase: 'Refine', schema: BUILD_SCHEMA })
  if (!next) break
  current = { glb: next.glb, shotsDir: next.shotsDir, report: next }
  round++
}

return { final: current, critique: crit, rounds: round, figure: { glb: body.glb, shotsDir: body.shotsDir, howBuilt: body.howBuilt, thirdParty: body.thirdParty }, mpfbRecipe: recipe, firstGarment: { glb: garment.glb, shotsDir: garment.shotsDir } }
