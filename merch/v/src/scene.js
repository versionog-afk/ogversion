/* Scene: environment, three lights, cloth and print materials, the lit-47
   overlay, the red line under the printed 47, and uvToWorld.

   Graph:
     scene (environment, no background)
     ├ key, rimL, rimR                fixed in the world
     └ teeSwing (pendulum pivot) ─ teeYaw (axis through C) ─ content
                                       └ model, printLit, line47
*/
import {
  Scene, Group, Box3, Vector3, Color, Matrix4, DirectionalLight, PMREMGenerator,
  Mesh, MeshBasicMaterial, MeshStandardMaterial, MeshPhysicalMaterial,
  BoxGeometry, PlaneGeometry, BackSide, FrontSide, DoubleSide,
  CanvasTexture, Texture, SRGBColorSpace, LinearFilter
} from 'three';
import { CFG, lerp } from './config.js';

export const world = {
  scene: null,
  teeSwing: null, teeYaw: null, content: null,
  key: null, rimL: null, rimR: null,
  fabric: [], print: null, printLit: null, line47: null, lineLength: 0,
  printTex: null,
  /* measured from the model at load, never hard-coded */
  C: new Vector3(),          // fabric bbox centre
  size: new Vector3(),       // fabric bbox size
  top: 0, bottom: 0,
  P: new Vector3(),          // print bbox centre
  printSize: new Vector3(),
  A47: new Vector3(),        // centre of the printed "47"
  Yr: 0,                     // rail height
  pivotY: 0
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

/* Black cotton. A matte black surface gives almost nothing back, so one
   shader patch adds a view-angle term to the diffuse light: edges and fold
   flanks pick up the rim lights and the shirt separates from the void. */
function clothMaterial(src, tier) {
  const C = CFG.CLOTH;
  const base = {
    color: C.color, roughness: C.roughness, metalness: 0,
    side: src && src.side !== undefined ? src.side : FrontSide,
    normalMap: (src && src.normalMap) || null,
    aoMap: (src && src.aoMap) || null
  };
  /* desktop adds physical sheen on top; the rim patch below is shared by every tier */
  const m = tier === 0
    ? new MeshPhysicalMaterial(Object.assign(base, { sheen: C.sheen, sheenRoughness: C.sheenRoughness, sheenColor: new Color(C.sheenColor) }))
    : new MeshStandardMaterial(base);
  /* x: gain on all diffuse light, y: extra gain at grazing angles, z: its falloff power */
  const u = m.userData.cloth = { value: new Vector3(C.base, C.rim, C.rimPow) };
  m.onBeforeCompile = shader => {
    shader.uniforms.uCloth = u;
    shader.fragmentShader = 'uniform vec3 uCloth;\n' + shader.fragmentShader.replace(
      'vec3 outgoingLight = totalDiffuse + totalSpecular + totalEmissiveRadiance;',
      'vec3 outgoingLight = totalDiffuse + totalSpecular + totalEmissiveRadiance;\n' +
      'outgoingLight += totalDiffuse * ( uCloth.x + uCloth.y * pow( 1.0 - saturate( dot( normal, normalize( vViewPosition ) ) ), uCloth.z ) );'
    );
  };
  if (src && src.normalMap && src.normalScale) m.normalScale.copy(src.normalScale);
  if (src && src.aoMap) m.aoMapIntensity = src.aoMapIntensity;
  return m;
}

/* White rectangle over the printed "47", black elsewhere: the alpha of the
   unlit copy of the print that stays visible when the lights go out. */
function maskTexture() {
  const M = CFG.MASK, U = CFG.UV47;
  const c = document.createElement('canvas');
  c.width = M.w; c.height = M.h;
  const g = c.getContext('2d');
  g.fillStyle = '#000';
  g.fillRect(0, 0, M.w, M.h);
  const x0 = (U.u0 - M.grow) * M.w, x1 = (U.u1 + M.grow) * M.w, y0 = (U.v0 - M.grow) * M.h, y1 = (U.v1 + M.grow) * M.h;
  /* feather: stacked translucent rects, the outermost one M.feather px out */
  const steps = 4;
  for (let i = 0; i < steps; i++) {
    const out = M.feather * (1 - i / (steps - 1));
    g.fillStyle = 'rgba(255,255,255,' + (1 / (steps - i)).toFixed(3) + ')';
    g.fillRect(x0 - out, y0 - out, x1 - x0 + 2 * out, y1 - y0 + 2 * out);
  }
  const t = new CanvasTexture(c);
  t.flipY = false;
  t.generateMipmaps = false;
  t.minFilter = t.magFilter = LinearFilter;
  return t;
}

/* ---- uv → world ------------------------------------------------------- */

/* Finds the Print triangle that contains a UV and returns the world
   position and normal there. Meshopt quantisation moves scale into node
   transforms, so positions are always taken through matrixWorld. */
export function uvToWorld(u, v, outP, outN) {
  const mesh = world.print, g = mesh.geometry;
  const pos = g.attributes.position, uv = g.attributes.uv, nor = g.attributes.normal, idx = g.index;
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
    else outN.set(0, 0, 1);
  }
  return true;
}

/* ---- build ------------------------------------------------------------ */

export function buildScene(gltf, printImage, renderer, tier) {
  const scene = world.scene = new Scene();
  scene.environment = buildEnvironment(renderer);
  scene.environmentIntensity = CFG.LIGHT.env;

  /* lights */
  const L = CFG.LIGHT;
  const light = (hex, i, p) => { const l = new DirectionalLight(hex, i); l.position.set(p[0], p[1], p[2]); scene.add(l); return l; };
  world.key = light(L.key.color, L.key.tipas, L.key.pos);
  world.rimL = light(L.rimL.tipas[0], L.rimL.tipas[1], L.rimL.pos);
  world.rimR = light(L.rimR.tipas[0], L.rimR.tipas[1], L.rimR.pos);

  /* model: split into fabric and print the way the reference viewer does */
  const model = gltf.scene;
  model.updateMatrixWorld(true);
  const prints = [];
  model.traverse(o => {
    if (!o.isMesh) return;
    const isPrint = /print/i.test(o.name) || /print/i.test((o.material && o.material.name) || '');
    (isPrint ? prints : world.fabric).push(o);
  });
  if (!prints.length || !world.fabric.length) throw new Error('model: fabric or Print mesh missing');
  world.print = prints[0];

  /* measurements */
  const fb = new Box3(), pb = new Box3();
  world.fabric.forEach(m => fb.expandByObject(m));
  prints.forEach(m => pb.expandByObject(m));
  fb.getCenter(world.C); fb.getSize(world.size);
  pb.getCenter(world.P); pb.getSize(world.printSize);
  world.top = fb.max.y; world.bottom = fb.min.y;
  world.Yr = world.top + CFG.RAIL.above;
  world.pivotY = world.top + CFG.SWING.pivot;

  /* print texture: sRGB, v = 0 at the top */
  const tex = world.printTex = new Texture(printImage);
  tex.colorSpace = SRGBColorSpace;
  tex.flipY = false;
  tex.anisotropy = Math.min(8, renderer.capabilities.getMaxAnisotropy());
  tex.needsUpdate = true;

  /* materials */
  const cloth = new Map();
  for (const m of world.fabric) {
    const src = m.material;
    if (!cloth.has(src)) cloth.set(src, clothMaterial(src, tier));
    m.material = cloth.get(src);
    if (src && src.dispose) src.dispose();
  }
  const srcPrint = world.print.material;
  const printMat = new MeshStandardMaterial({
    map: tex, transparent: true, roughness: CFG.PRINT.roughness, metalness: 0, side: FrontSide,
    depthWrite: false, polygonOffset: true, polygonOffsetFactor: -4, polygonOffsetUnits: -4,
    emissive: 0xffffff, emissiveMap: tex, emissiveIntensity: 0,
    normalMap: (srcPrint && srcPrint.normalMap) || null
  });
  for (const m of prints) { m.material = printMat; m.renderOrder = 2; }
  if (srcPrint && srcPrint.dispose) srcPrint.dispose();

  /* the 47 that stays lit: an unlit copy of the print, masked to the digits */
  const lit = world.printLit = new Mesh(world.print.geometry, new MeshBasicMaterial({
    map: tex, alphaMap: maskTexture(), transparent: true, toneMapped: false, depthWrite: false,
    polygonOffset: true, polygonOffsetFactor: -6, polygonOffsetUnits: -6, opacity: 0
  }));
  lit.position.copy(world.print.position);
  lit.quaternion.copy(world.print.quaternion);
  lit.scale.copy(world.print.scale);
  lit.renderOrder = 3;
  lit.visible = false;
  world.print.parent.add(lit);

  /* the red line under the printed 47 */
  const U = CFG.UV47, K = CFG.LINE47;
  const a = new Vector3(), b = new Vector3(), na = new Vector3(), nb = new Vector3();
  if (!uvToWorld(U.u0, K.v, a, na) || !uvToWorld(U.u1, K.v, b, nb)) throw new Error('model: print UVs do not cover the 47');
  uvToWorld((U.u0 + U.u1) / 2, (U.v0 + U.v1) / 2, world.A47, null);
  const x = new Vector3().subVectors(b, a);
  world.lineLength = x.length();
  x.normalize();
  const n = na.add(nb).normalize();
  const y = new Vector3().crossVectors(n, x).normalize();
  n.crossVectors(x, y).normalize();
  const line = world.line47 = new Mesh(
    new PlaneGeometry(1, 1).translate(0.5, 0, 0),           // origin at its left end
    new MeshBasicMaterial({ color: CFG.RAIL.color, transparent: true, toneMapped: false, depthWrite: false, opacity: 0, polygonOffset: true, polygonOffsetFactor: -8, polygonOffsetUnits: -8 })
  );
  line.quaternion.setFromRotationMatrix(new Matrix4().makeBasis(x, y, n));
  line.position.copy(a).addScaledVector(n, K.lift);
  line.scale.set(0.0001, K.height, 1);
  line.renderOrder = 4;
  line.visible = false;

  /* pendulum pivot → yaw axis through C → content in model coordinates */
  const swing = world.teeSwing = new Group(), yaw = world.teeYaw = new Group(), content = world.content = new Group();
  swing.position.set(world.C.x, world.pivotY, world.C.z);
  content.position.set(-world.C.x, -world.pivotY, -world.C.z);
  content.add(model, line);
  yaw.add(content);
  swing.add(yaw);
  scene.add(swing);

  return world;
}

/* ---- per-frame light state -------------------------------------------- */

/* m: 0 "Tipas" (bone rims) … 1 "Stendas" (purple and pink rims)
   dark: 0 lights on … 1 lights out
   rims, key: extra multipliers (the rack beat dims them)
   line: 0…1 how much of the red line under the printed 47 is drawn */
export function setLights(m, dark, rims, key, line, tier) {
  const L = CFG.LIGHT;
  world.key.intensity = lerp(L.key.tipas, L.key.stendas, m) * key * lerp(1, L.keyDark, dark);
  const rimDim = rims * lerp(1, L.rimDark, dark);
  world.rimL.color.lerpColors(tipasL, stendasL, m);
  world.rimL.intensity = lerp(L.rimL.tipas[1], L.rimL.stendas[1], m) * rimDim;
  world.rimR.color.lerpColors(tipasR, stendasR, m);
  world.rimR.intensity = tier >= 3 ? 0 : lerp(L.rimR.tipas[1], L.rimR.stendas[1], m) * rimDim;
  world.scene.environmentIntensity = lerp(L.env, L.envDark, dark);
  world.print.material.emissiveIntensity = L.emissive * m * (1 - dark);

  const on = dark > 0.004;
  world.printLit.visible = on;
  world.printLit.material.opacity = dark;
  world.line47.visible = on && line > 0.001;
  world.line47.material.opacity = dark;
  world.line47.scale.x = Math.max(0.0001, world.lineLength * line);
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
