/* Scene: environment, three lights, the figure's materials (cloth in its two
   colours, plaster, the fade of the legs into the dark), the two prints, the
   lit copy of the back print, the red line under its caption, and uvToWorld.

   Graph:
     scene (environment, no background)
     ├ rig ─ key, rimL, rimR        the lamps; the rig turns with the camera's azimuth
     └ yaw (vertical axis through the figure) ─ content (model coordinates)
                                                 └ model, printLit, lineRed
*/
import {
  Scene, Group, Box3, Vector2, Vector3, Color, DirectionalLight, PMREMGenerator,
  Mesh, MeshBasicMaterial, MeshStandardMaterial, MeshPhysicalMaterial,
  BoxGeometry, PlaneGeometry, BufferGeometry, BufferAttribute, BackSide, FrontSide, DoubleSide,
  Texture, SRGBColorSpace
} from 'three';
import { CFG, ART, lerp, smoothstep } from './config.js';

export const world = {
  scene: null,
  rig: null, yaw: null, content: null,
  key: null, rimL: null, rimR: null,
  /* meshes by class */
  groups: { printFront: [], printBack: [], hair: [], pants: [], shoes: [], body: [], tee: [], other: [] },
  printFront: null, printBack: null, printLit: null, lineRed: null,
  frontTex: null, backTex: null,
  teeMats: [],               // the cloth materials of the tee: the colour switch drives them
  /* measured from the model at load, never hard-coded */
  F: new Box3(),             // everything
  T: new Box3(),             // the tee
  PF: new Box3(),            // chest print
  PB: new Box3(),            // back print (the whole decal: its canvas is taller than the artwork)
  art: null,                 // { c, w, h }: the back artwork (map and caption) on the cloth
  mapShot: null,             // { c, w, h }: the artwork plus the red line under its caption
  hemR: 0.3,                 // the hem never reaches further from the yaw axis than this
  TOP: new Box3(),           // head to just below the hem, as wide and deep as the tee
  C: new Vector3(),          // centre of TOP
  axis: new Vector3(),       // the yaw axis: centre of F in x and z
  printR: 0.15,              // how far the prints are from the yaw axis
  Yr: 0                      // rail height
};

const tipasL = new Color(CFG.LIGHT.rimL.tipas[0]), stendasL = new Color(CFG.LIGHT.rimL.stendas[0]);
const tipasR = new Color(CFG.LIGHT.rimR.tipas[0]), stendasR = new Color(CFG.LIGHT.rimR.stendas[0]);

/* ---- environment ------------------------------------------------------ */

/* A dark room with four unlit panels brighter than white. Blurred into a
   PMREM it gives the cloth its soft edge light: bone from the type behind,
   purple and pink from the sides, a cool strip overhead. */
export function buildEnvironment(renderer) {
  const R = CFG.ROOM, room = new Scene(), trash = [];
  const add = (geo, mat) => { const m = new Mesh(geo, mat); trash.push(geo, mat); room.add(m); return m; };
  add(new BoxGeometry(R.size[0], R.size[1], R.size[2]), new MeshBasicMaterial({ color: R.wall, side: BackSide }));
  for (const [hex, mul, w, h, pos, facing] of R.panels) {
    const m = add(new PlaneGeometry(w, h), new MeshBasicMaterial({ color: new Color(hex).multiplyScalar(mul), side: DoubleSide }));
    m.position.set(pos[0], pos[1], pos[2]);
    if (facing === 'x') m.rotation.y = Math.PI / 2;
    else if (facing === '-x') m.rotation.y = -Math.PI / 2;
    else if (facing === '-y') m.rotation.x = Math.PI / 2;
  }
  const pmrem = new PMREMGenerator(renderer);
  const target = pmrem.fromScene(room, R.sigma);
  pmrem.dispose();
  trash.forEach(x => x.dispose());
  return target.texture;
}

/* ---- materials -------------------------------------------------------- */

/* heights (world y) between which the legs fade into the dark; set once the model is measured */
const fade = { value: new Vector2(CFG.FADE[0], CFG.FADE[1]) };

/* Two small shader patches, combined as a material needs them.

   cloth: black cotton gives almost nothing back, so a view-angle term is
          added to the diffuse light: edges and fold flanks pick up the rim
          lights and the garment separates from the void.
          uCloth = (gain on all diffuse light, extra gain at grazing angles, its falloff power).
          The first may be negative: the white tee takes its diffuse light down a little.
   fade:  everything below the hem sinks into the black: the outgoing light
          is multiplied by smoothstep(uFade.x, uFade.y, world y). */
function patch(m, cloth, fades) {
  const u = cloth ? (m.userData.cloth = { value: new Vector3(cloth.base, cloth.rim, cloth.rimPow) }) : null;
  m.onBeforeCompile = shader => {
    let vs = shader.vertexShader, fs = shader.fragmentShader;
    if (u) {
      shader.uniforms.uCloth = u;
      const out = 'vec3 outgoingLight = totalDiffuse + totalSpecular + totalEmissiveRadiance;';
      fs = 'uniform vec3 uCloth;\n' + fs.replace(out, out +
        '\noutgoingLight += totalDiffuse * ( uCloth.x + uCloth.y * pow( 1.0 - saturate( dot( normal, normalize( vViewPosition ) ) ), uCloth.z ) );');
    }
    if (fades) {
      shader.uniforms.uFade = fade;
      vs = 'varying float vFadeY;\n' + vs.replace('#include <project_vertex>',
        '#include <project_vertex>\nvFadeY = ( modelMatrix * vec4( transformed, 1.0 ) ).y;');
      fs = 'uniform vec2 uFade;\nvarying float vFadeY;\n' + fs.replace('#include <opaque_fragment>',
        'outgoingLight *= smoothstep( uFade.x, uFade.y, vFadeY );\n#include <opaque_fragment>');
    }
    shader.vertexShader = vs;
    shader.fragmentShader = fs;
  };
  /* programs are cached by this key: the variants must not share one */
  m.customProgramCacheKey = () => 'fig' + (u ? '-cloth' : '') + (fades ? '-fade' : '');
  return m;
}

/* what every replacement keeps from the model's own material */
function keep(src) {
  return {
    side: src && src.side !== undefined ? src.side : FrontSide,
    normalMap: (src && src.normalMap) || null,
    aoMap: (src && src.aoMap) || null
  };
}
function carry(src, m) {
  if (src && src.normalMap && src.normalScale) m.normalScale.copy(src.normalScale);
  if (src && src.aoMap) m.aoMapIntensity = src.aoMapIntensity;
  return m;
}

/* Tee and trousers. Desktop (tier 0) adds physical sheen on top; the rim patch is shared by every tier. */
function clothMaterial(src, tier, C, fades) {
  const base = Object.assign(keep(src), { color: C.color, roughness: C.roughness, metalness: 0 });
  const m = tier === 0
    ? new MeshPhysicalMaterial(Object.assign(base, { sheen: C.sheen, sheenRoughness: C.sheenRoughness, sheenColor: new Color(C.sheenColor) }))
    : new MeshStandardMaterial(base);
  return patch(carry(src, m), C, fades);
}

/* Body and hair: one matte plaster. The figure is a sculpture wearing the tee. */
function plasterMaterial(src, darker, fades) {
  const P = CFG.PLASTER, k = keep(src);
  const m = new MeshStandardMaterial({ color: new Color(P.color).multiplyScalar(1 - darker), roughness: P.roughness, metalness: 0, side: k.side, normalMap: k.normalMap });
  if (k.normalMap && src.normalScale) m.normalScale.copy(src.normalScale);
  return patch(m, null, fades);
}

function shoeMaterial(src) {
  const m = new MeshStandardMaterial({ color: CFG.SHOES.color, roughness: CFG.SHOES.roughness, metalness: 0, side: keep(src).side });
  return patch(m, null, true);
}

function printTexture(image, renderer) {
  const tex = new Texture(image);
  tex.colorSpace = SRGBColorSpace;
  tex.flipY = false;                      // v = 0 is the top row of the print
  tex.anisotropy = Math.min(8, renderer.capabilities.getMaxAnisotropy());
  tex.needsUpdate = true;
  return tex;
}
function printMaterial(tex) {
  return new MeshStandardMaterial({
    map: tex, transparent: true, roughness: CFG.PRINT.roughness, metalness: 0, side: FrontSide,
    depthWrite: false, polygonOffset: true, polygonOffsetFactor: -4, polygonOffsetUnits: -4,
    emissive: 0xffffff, emissiveMap: tex, emissiveIntensity: 0
  });
}

/* ---- uv → world ------------------------------------------------------- */

/* Finds the triangle of a print mesh that contains a UV and returns the
   world position and normal there. Meshopt quantisation moves scale into
   node transforms, so positions are always taken through matrixWorld. */
export function uvToWorld(mesh, u, v, outP, outN) {
  const g = mesh.geometry;
  const pos = g.attributes.position, uv = g.attributes.uv, nor = g.attributes.normal, idx = g.index;
  if (!uv) return false;
  const n = idx ? idx.count : pos.count;
  let best = null, bestErr = Infinity;
  for (let i = 0; i < n; i += 3) {
    const a = idx ? idx.getX(i) : i, b = idx ? idx.getX(i + 1) : i + 1, c = idx ? idx.getX(i + 2) : i + 2;
    const ax = uv.getX(a), ay = uv.getY(a), bx = uv.getX(b), by = uv.getY(b), cx = uv.getX(c), cy = uv.getY(c);
    const den = (by - cy) * (ax - cx) + (cx - bx) * (ay - cy);
    if (Math.abs(den) < 1e-12) continue;
    const wa = ((by - cy) * (u - cx) + (cx - bx) * (v - cy)) / den;
    const wb = ((cy - ay) * (u - cx) + (ax - cx) * (v - cy)) / den;
    const wc = 1 - wa - wb;
    /* how far outside the triangle (0 = inside); keep the nearest as a fallback */
    const err = Math.max(0, -wa, -wb, -wc);
    if (err < bestErr) { bestErr = err; best = [a, b, c, wa, wb, wc]; if (err === 0) break; }
  }
  if (!best) return false;
  const [a, b, c, wa, wb, wc] = best;
  mesh.updateWorldMatrix(true, false);
  outP.set(
    pos.getX(a) * wa + pos.getX(b) * wb + pos.getX(c) * wc,
    pos.getY(a) * wa + pos.getY(b) * wb + pos.getY(c) * wc,
    pos.getZ(a) * wa + pos.getZ(b) * wb + pos.getZ(c) * wc
  ).applyMatrix4(mesh.matrixWorld);
  if (outN) {
    if (nor) outN.set(
      nor.getX(a) * wa + nor.getX(b) * wb + nor.getX(c) * wc,
      nor.getY(a) * wa + nor.getY(b) * wb + nor.getY(c) * wc,
      nor.getZ(a) * wa + nor.getZ(b) * wb + nor.getZ(c) * wc
    ).transformDirection(mesh.matrixWorld);
    else outN.set(0, 0, -1);
  }
  return true;
}

/* A box of a print's texture (u0…u1, v0…v1, v from the top) as it lies on the
   cloth: its centre, and its width and height measured through that centre. */
function uvBox(mesh, b) {
  const uc = (b.u0 + b.u1) / 2, vc = (b.v0 + b.v1) / 2;
  const l = new Vector3(), r = new Vector3(), t = new Vector3(), d = new Vector3(), c = new Vector3();
  const ok = uvToWorld(mesh, b.u0, vc, l) && uvToWorld(mesh, b.u1, vc, r) && uvToWorld(mesh, uc, b.v0, t) && uvToWorld(mesh, uc, b.v1, d) && uvToWorld(mesh, uc, vc, c);
  if (!ok) throw new Error('model: the back print has no UVs');
  c.set((l.x + r.x) / 2, (t.y + d.y) / 2, c.z);
  return { c, w: l.distanceTo(r), h: t.distanceTo(d) };
}

/* ---- the red line ------------------------------------------------------ */

/* A ribbon that lies on the cloth under the caption of the back print: it
   is sampled along the print's own surface, so it follows the curve of the
   back and stays glued to it when the figure turns. `along` runs 0 → 1 from
   its left end (as seen from behind); the fragment shader cuts it off at
   uDraw, which is how the line draws. */
function buildLine(mesh, box, v) {
  const K = CFG.LINE, n = K.steps;
  const P = [], N = [];
  for (let i = 0; i <= n; i++) {
    const p = new Vector3(), nn = new Vector3();
    if (!uvToWorld(mesh, lerp(box.u0, box.u1, i / n), v, p, nn)) throw new Error('model: back print UVs do not cover the caption');
    P.push(p); N.push(nn.normalize());
  }
  const pos = new Float32Array((n + 1) * 6), along = new Float32Array((n + 1) * 2), index = [];
  const t = new Vector3(), up = new Vector3(), q = new Vector3();
  for (let i = 0; i <= n; i++) {
    t.subVectors(P[Math.min(n, i + 1)], P[Math.max(0, i - 1)]).normalize();
    up.crossVectors(N[i], t).normalize();
    q.copy(P[i]).addScaledVector(N[i], K.lift);
    world.content.worldToLocal(q);
    pos.set([q.x - up.x * K.height / 2, q.y - up.y * K.height / 2, q.z - up.z * K.height / 2,
      q.x + up.x * K.height / 2, q.y + up.y * K.height / 2, q.z + up.z * K.height / 2], i * 6);
    along[i * 2] = along[i * 2 + 1] = i / n;
    if (i < n) { const a = i * 2; index.push(a, a + 2, a + 1, a + 1, a + 2, a + 3); }
  }
  const geo = new BufferGeometry();
  geo.setAttribute('position', new BufferAttribute(pos, 3));
  geo.setAttribute('along', new BufferAttribute(along, 1));
  geo.setIndex(index);

  const mat = new MeshBasicMaterial({
    color: K.color, transparent: true, toneMapped: false, depthWrite: false, opacity: 0, side: DoubleSide,
    polygonOffset: true, polygonOffsetFactor: -8, polygonOffsetUnits: -8
  });
  const draw = mat.userData.draw = { value: 0 };
  mat.onBeforeCompile = shader => {
    shader.uniforms.uDraw = draw;
    shader.vertexShader = 'attribute float along;\nvarying float vAlong;\n' +
      shader.vertexShader.replace('#include <begin_vertex>', '#include <begin_vertex>\nvAlong = along;');
    shader.fragmentShader = 'uniform float uDraw;\nvarying float vAlong;\n' +
      shader.fragmentShader.replace('#include <clipping_planes_fragment>', 'if ( vAlong > uDraw ) discard;\n#include <clipping_planes_fragment>');
  };
  mat.customProgramCacheKey = () => 'line';
  const line = new Mesh(geo, mat);
  line.renderOrder = 4;
  line.visible = false;
  line.frustumCulled = false;
  return line;
}

/* ---- build ------------------------------------------------------------ */

function classOf(o) {
  const id = o.name + ' ' + ((o.material && o.material.name) || '') + ' ' + ((o.parent && o.parent.name) || '');
  const hit = CFG.CLASSES.find(c => c[1].test(o.name)) || CFG.CLASSES.find(c => c[1].test(id));
  return hit ? hit[0] : 'other';
}

export function buildScene(gltf, images, renderer, tier) {
  const scene = world.scene = new Scene();
  scene.environment = buildEnvironment(renderer);
  scene.environmentIntensity = CFG.LIGHT.env;

  /* lights */
  const L = CFG.LIGHT, rig = world.rig = new Group();
  const light = (hex, i, p) => { const l = new DirectionalLight(hex, i); l.position.set(p[0], p[1], p[2]); rig.add(l); return l; };
  world.key = light(L.key.color, L.key.tipas, L.key.pos);
  world.rimL = light(L.rimL.tipas[0], L.rimL.tipas[1], L.rimL.pos);
  world.rimR = light(L.rimR.tipas[0], L.rimR.tipas[1], L.rimR.pos);
  scene.add(rig);

  /* model: sort the meshes into classes the way the reference viewer does */
  const model = gltf.scene, G = world.groups;
  for (const k in G) G[k] = [];
  model.updateMatrixWorld(true);
  model.traverse(o => { if (o.isMesh) G[classOf(o)].push(o); });
  if (G.printFront.length !== 1 || G.printBack.length !== 1 || !G.tee.length) throw new Error('model: needs one PrintFront, one PrintBack and a tee mesh');
  world.printFront = G.printFront[0];
  world.printBack = G.printBack[0];

  /* measurements */
  const box = (list, out) => { out.makeEmpty(); list.forEach(m => out.expandByObject(m)); return out; };
  const F = world.F.setFromObject(model), T = box(G.tee, world.T), PF = box(G.printFront, world.PF), PB = box(G.printBack, world.PB);
  world.TOP.min.set(T.min.x, T.min.y - CFG.TOP_BELOW_HEM, T.min.z);
  world.TOP.max.set(T.max.x, F.max.y, T.max.z);
  world.TOP.getCenter(world.C);
  world.axis.set((F.min.x + F.max.x) / 2, 0, (F.min.z + F.max.z) / 2);
  world.Yr = F.max.y + CFG.RAIL.above;
  const c = new Vector3(), r = b => { b.getCenter(c); return Math.hypot(c.x - world.axis.x, c.z - world.axis.z); };
  world.printR = Math.max(0.05, r(PF), r(PB));
  fade.value.set(F.min.y + CFG.FADE[0], F.min.y + CFG.FADE[1]);

  /* materials: one replacement per class and source material */
  const old = new Set();
  const dress = (list, make) => {
    const made = new Map();
    for (const m of list) {
      const src = m.material;
      old.add(src);
      if (!made.has(src)) made.set(src, make(src));
      m.material = made.get(src);
    }
  };
  dress(G.tee, src => clothMaterial(src, tier, CFG.CLOTH, false));
  world.teeMats = [...new Set(G.tee.map(m => m.material))];
  dress(G.pants.concat(G.other), src => clothMaterial(src, tier, CFG.PANTS, true));
  dress(G.body, src => plasterMaterial(src, 0, true));
  dress(G.hair, src => plasterMaterial(src, CFG.PLASTER.hairDarker, false));
  dress(G.shoes, shoeMaterial);
  world.frontTex = printTexture(images.front, renderer);
  world.backTex = printTexture(images.back, renderer);
  dress(G.printFront, () => printMaterial(world.frontTex));
  dress(G.printBack, () => printMaterial(world.backTex));
  world.printFront.renderOrder = world.printBack.renderOrder = 2;
  old.forEach(src => { if (src && src.dispose) src.dispose(); });

  /* the map that stays lit: an unlit copy of the back print */
  const pb = world.printBack;
  const lit = world.printLit = new Mesh(pb.geometry, new MeshBasicMaterial({
    map: world.backTex, color: CFG.INK.lit, transparent: true, toneMapped: false, depthWrite: false,
    polygonOffset: true, polygonOffsetFactor: -6, polygonOffsetUnits: -6, opacity: 0
  }));
  lit.position.copy(pb.position);
  lit.quaternion.copy(pb.quaternion);
  lit.scale.copy(pb.scale);
  lit.renderOrder = 3;
  lit.visible = false;
  pb.parent.add(lit);

  /* yaw axis through the figure → content in model coordinates */
  const yaw = world.yaw = new Group(), content = world.content = new Group();
  yaw.position.copy(world.axis);
  content.position.copy(world.axis).negate();
  content.add(model);
  yaw.add(content);
  scene.add(yaw);
  scene.updateMatrixWorld(true);

  /* Where the back artwork lies on the cloth, from the boxes the build read from the art's metadata: the
     camera frames these, not the decal, whose canvas has an empty band under the caption. */
  const B = ART.back, cap = B.captionBox;
  const lineV = Math.min(0.995, cap.v1 + (cap.v1 - cap.v0) * CFG.LINE.gap);
  world.art = uvBox(pb, B.artBox);
  world.mapShot = uvBox(pb, { u0: B.artBox.u0, u1: B.artBox.u1, v0: B.artBox.v0, v1: lineV });

  /* the red line under the caption, as wide as the caption */
  world.lineRed = buildLine(pb, cap, lineV);
  content.add(world.lineRed);

  /* the hem, for the colour swatches: they only show while it is clear of them */
  world.hemR = Math.max(...[T.min.x, T.max.x].map(x => Math.max(...[T.min.z, T.max.z].map(z => Math.hypot(x - world.axis.x, z - world.axis.z)))));

  shirt.k = shirt.want = 0;
  shirt.name = 'black';
  applyShirt(0);

  return world;
}

/* ---- the colour of the tee -------------------------------------------- */

/* The tee comes in black and in white. A switch changes the cloth (colour
   and the two gains of its shader) and the ink of the back print, which is
   one-colour line art: bone on black cloth, near-black on white. Nothing
   else changes; the copy of the map that stays lit in the dark keeps its
   own bone colour. */
export const shirt = { name: 'black', k: 0, want: 0 };   // k: 0 black … 1 white, eased

const clothBlack = new Color(CFG.CLOTH.color), clothWhite = new Color(CFG.CLOTH_WHITE.color);
const inkOnBlack = new Color(CFG.INK.onBlack), inkOnWhite = new Color(CFG.INK.onWhite);

function applyShirt(k) {
  const A = CFG.CLOTH, B = CFG.CLOTH_WHITE;
  for (const m of world.teeMats) {
    m.color.lerpColors(clothBlack, clothWhite, k);
    m.userData.cloth.value.set(lerp(A.base, B.base, k), lerp(A.rim, B.rim, k), lerp(A.rimPow, B.rimPow, k));
  }
  const ink = world.printBack.material;
  ink.color.lerpColors(inkOnBlack, inkOnWhite, k);
  ink.emissive.copy(ink.color);
}

/* 'black' or 'white'; anything else is ignored. Returns true if the choice changed. */
export function chooseShirt(name) {
  if ((name !== 'black' && name !== 'white') || name === shirt.name) return false;
  shirt.name = name;
  shirt.want = name === 'white' ? 1 : 0;
  return true;
}

/* One frame of the ease between the two colours. Returns true while it runs. */
export function stepShirt(dt) {
  if (shirt.k === shirt.want) return false;
  const step = dt / (CFG.COLOR_MS / 1000);
  shirt.k = shirt.want > shirt.k ? Math.min(1, shirt.k + step) : Math.max(0, shirt.k - step);
  applyShirt(smoothstep(0, 1, shirt.k));
  return true;
}

/* ---- per-frame light state -------------------------------------------- */

/* m: 0 "Tipas" (bone rims) … 1 "Stendas" (purple and pink rims)
   dark: 0 lights on … 1 lights out
   rims, key: extra multipliers (the rack beat dims them)
   line: 0…1 how much of the red line under the caption is drawn
   az: the camera's azimuth in radians. The lamps and the environment turn
       with it, so the walk round the figure keeps key and rims where the
       hero has them and the back is lit like the front. Turning the figure
       by hand still moves it under fixed lamps. */
export function setLights(m, dark, rims, key, line, tier, az) {
  const L = CFG.LIGHT;
  world.rig.rotation.y = world.scene.environmentRotation.y = az * L.follow;
  world.key.intensity = lerp(L.key.tipas, L.key.stendas, m) * key * lerp(1, L.keyDark, dark);
  const rimDim = rims * lerp(1, L.rimDark, dark);
  world.rimL.color.lerpColors(tipasL, stendasL, m);
  world.rimL.intensity = lerp(L.rimL.tipas[1], L.rimL.stendas[1], m) * rimDim;
  world.rimR.color.lerpColors(tipasR, stendasR, m);
  world.rimR.intensity = tier >= 3 ? 0 : lerp(L.rimR.tipas[1], L.rimR.stendas[1], m) * rimDim;
  world.scene.environmentIntensity = lerp(L.env, L.envDark, dark);
  world.printFront.material.emissiveIntensity = world.printBack.material.emissiveIntensity = L.emissive * m * (1 - dark);

  const on = dark > 0.004;
  world.printLit.visible = on;
  world.printLit.material.opacity = dark;
  world.lineRed.visible = on && line > 0.001;
  world.lineRed.material.opacity = dark;
  world.lineRed.material.userData.draw.value = line;
}

export function disposeScene() {
  const s = world.scene;
  if (!s) return;
  s.traverse(o => {
    if (o.geometry) o.geometry.dispose();
    const m = o.material;
    if (m) for (const k in m) { const v = m[k]; if (v && v.isTexture) v.dispose(); }
    if (m && m.dispose) m.dispose();
  });
  if (s.environment) s.environment.dispose();
  world.scene = null;
}
