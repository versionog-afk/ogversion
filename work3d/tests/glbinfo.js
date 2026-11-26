// node glbinfo.js <file.glb>: nodes, meshes, materials, triangles, textures
const fs = require('fs');
const f = process.argv[2];
const b = fs.readFileSync(f);
const len = b.readUInt32LE(12);
const j = JSON.parse(b.slice(20, 20 + len).toString('utf8'));
let tris = 0;
for (const [i, m] of (j.meshes || []).entries()) {
  let t = 0;
  for (const p of m.primitives) { const acc = j.accessors[p.indices !== undefined ? p.indices : p.attributes.POSITION]; t += acc.count / 3; }
  tris += t;
  const mats = m.primitives.map(p => p.material !== undefined ? j.materials[p.material].name : '-');
  const attrs = Object.keys(m.primitives[0].attributes).join(',');
  console.log('mesh', i, JSON.stringify(m.name), 'tris', Math.round(t), 'mat', mats.join('|'), attrs);
}
for (const [i, n] of (j.nodes || []).entries()) console.log('node', i, JSON.stringify(n.name), n.mesh !== undefined ? 'mesh ' + n.mesh : '', n.children ? 'children ' + n.children : '', n.translation ? 't ' + n.translation.map(x => x.toFixed(3)) : '', n.scale ? 's ' + n.scale.map(x => x.toFixed(4)) : '');
for (const [i, m] of (j.materials || []).entries()) console.log('material', i, JSON.stringify(m.name), m.doubleSided ? 'double' : '', m.normalTexture ? 'normal' : '', m.occlusionTexture ? 'ao' : '', m.pbrMetallicRoughness && m.pbrMetallicRoughness.baseColorTexture ? 'map' : '', m.alphaMode || '');
console.log('images', (j.images || []).map(i => i.mimeType + (i.name ? ' ' + i.name : '')).join('; '));
console.log('ext', (j.extensionsUsed || []).join(','), 'triangles', Math.round(tris), 'bytes', b.length);
