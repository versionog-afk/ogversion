"""Sewing pattern of the tee with GarmentCode (pygarment, MIT): panels and stitches are built with its classes
(Panel, Edge, CurveEdge, Interface, Stitches, Component) and written with its serializer; the result is then translated
into this project's pattern.json (metres, named seams) and drawn as pattern.png.

Run with a Python that has pygarment's pattern dependencies (numpy<2, scipy, svgpathtools, svgwrite, cairosvg, matplotlib,
pyyaml, psutil) and the GarmentCode repository on PYTHONPATH (build.sh does that):
    venv/bin/python pattern_gc.py [spec.json]
Only pygarment.garmentcode and pygarment.pattern are imported - never its meshgen / simulation part."""
import os, sys, json, math
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from na2cfg import *
import teegeom as tg


def build_with_pygarment(M, gc_dir):
    import pygarment as pyg
    specs, D = tg.panels(M)
    cm = 100.0

    class TeePanel(pyg.Panel):
        def __init__(self, name, spec):
            super().__init__(name)
            verts = [[float(v[0] * cm), float(v[1] * cm)] for v in spec['vertices']]
            self.named = {}
            edges = []
            for ename, a, b, ctrl in spec['edges']:
                if ctrl is None:
                    e = pyg.Edge(verts[a], verts[b], label=ename)
                else:
                    e = pyg.CurveEdge(verts[a], verts[b], control_points=[[float(c[0] * cm), float(c[1] * cm)] for c in ctrl], relative=False, label=ename)
                edges.append(e); self.named[ename] = e
            self.edges = pyg.EdgeSequence(*edges)

        def iface(self, ename):
            return pyg.Interface(self, self.named[ename])

    class Tee(pyg.Component):
        def __init__(self):
            super().__init__('tee_' + M['name'])
            # 3D placement only arranges the panels for GarmentCode's own drawing; the drape uses its own arrangement
            place = dict(front=(-38, 0, 25), back=(38, 0, -25), sleeve_L=(-95, 55, 0), sleeve_R=(95, 55, 0), collar=(-25, -12, 0))
            self.p = {}
            for name, spec in specs.items():
                pn = TeePanel(name, spec); pn.translate_by(list(place[name])); self.p[name] = pn
            self.subs = list(self.p.values())
            rules = []
            for sname, a, b in tg.seams():
                ia = self.p[a[0]].iface(a[1])
                ib = pyg.Interface.from_multiple(*[self.p[x[0]].iface(x[1]) for x in b]) if isinstance(b, list) else self.p[b[0]].iface(b[1])
                rules.append((ia, ib))
            self.stitching_rules = pyg.Stitches(*rules)

    tee = Tee()
    pat = tee.assembly()
    os.makedirs(gc_dir, exist_ok=True)
    pat.serialize(gc_dir, to_subfolder=False, with_3d=False, with_text=True, view_ids=True)
    return os.path.join(gc_dir, pat.name + '_specification.json'), pyg.__file__


def rel_to_abs(a, b, rel):
    a, b = np.asarray(a, float), np.asarray(b, float); e = b - a; perp = np.array([-e[1], e[0]])
    return a + rel[0] * e + rel[1] * perp


def translate(M, gc_json, source):
    """GarmentCode specification -> pattern.json of this project (metres; the frames of teegeom.py restored)"""
    G = json.load(open(gc_json))['pattern']
    specs, D = tg.panels(M)
    P = {}
    for name, gp in G['panels'].items():
        v = np.array(gp['vertices'], float) / 100.0
        v += specs[name]['vertices'][0] - v[0]          # GarmentCode moves the first vertex to (about) the origin on assembly
        edges = []
        for ge in gp['edges']:
            a, b = ge['endpoints']; e = dict(v=[int(a), int(b)], label=ge.get('label', ''))
            cv = ge.get('curvature')
            if cv:
                if cv['type'] != 'cubic': raise SystemExit('unexpected curve type ' + cv['type'])
                e['bezier'] = [rel_to_abs(v[a], v[b], p).round(6).tolist() for p in cv['params']]
            edges.append(e)
        # edges that GarmentCode subdivided to match a stitch lose their label: take it from the designed straight edge they lie on
        for e in edges:
            if e['label']: continue
            a, b = v[e['v'][0]], v[e['v'][1]]
            for ename, i, j, ctrl in specs[name]['edges']:
                if ctrl is not None: continue
                p0, p1 = specs[name]['vertices'][i], specs[name]['vertices'][j]; d = (p1 - p0) / np.linalg.norm(p1 - p0)
                if all(abs(np.cross(d, q - p0)) < 1e-6 and -1e-6 <= (q - p0) @ d <= np.linalg.norm(p1 - p0) + 1e-6 for q in (a, b)):
                    e['label'] = ename; break
        P[name] = dict(role=specs[name]['role'], vertices=v.round(6).tolist(), edges=edges)
        if 'side' in specs[name]: P[name]['side'] = specs[name]['side']
    # check against the design: every designed vertex must be present
    err = 0.0
    for name, sp in specs.items():
        pv = np.array(P[name]['vertices'])
        for q in sp['vertices']:
            err = max(err, float(np.linalg.norm(pv - q, axis=1).min()))
    # seams: GarmentCode stitches pair edges; names and sewing directions are attached here
    want = {}
    for sname, a, b in tg.seams():
        for x in (b if isinstance(b, list) else [b]):
            want[(a[0], a[1], x[0], x[1])] = sname
    def lab(pe): return P[pe['panel']]['edges'][pe['edge']]['label']
    seams = []
    for st in G['stitches']:
        a, b = st[0], st[1]
        key = (a['panel'], lab(a), b['panel'], lab(b)); key2 = (b['panel'], lab(b), a['panel'], lab(a))
        if key2 in want: a, b, key = b, a, key2
        if key not in want: raise SystemExit('stitch not in the design: %r' % (key,))
        seams.append(dict(name=want[key], a=dict(panel=a['panel'], edge=int(a['edge'])), b=dict(panel=b['panel'], edge=int(b['edge']))))
    # sewing direction: both edges are mapped into the flat-lay (or, for the collar band, walked along the neck loop)
    def flat(panel, pt):
        pt = np.asarray(pt, float)
        if P[panel]['role'] == 'sleeve':
            p, q = -pt[1], pt[0]; X = D['S'] + p * D['ds'] + abs(q) * D['dh']
            return X * (np.array([-1.0, 1.0]) if P[panel].get('side') == 'R' else 1.0)
        return pt
    def ends(pe):
        pn = P[pe['panel']]; e = pn['edges'][pe['edge']]
        return np.array(pn['vertices'][e['v'][0]]), np.array(pn['vertices'][e['v'][1]])
    def elen(pe):
        pn = P[pe['panel']]; e = pn['edges'][pe['edge']]; a, b = ends(pe)
        return tg.polylen(tg.bez(a, e['bezier'][0], e['bezier'][1], b)) if 'bezier' in e else float(np.linalg.norm(b - a))
    # the collar band (x from 0 to its cut length) runs from the wearer's left shoulder seam along the back neck to the right
    # shoulder and returns along the front neck
    cur = np.array([D['nh'], D['L']]); order = ['back', 'front']
    cs = sorted([s for s in seams if s['name'] == 'collar'], key=lambda s: (order.index(s['b']['panel']), 0))
    for panel in order:
        todo = [s for s in cs if s['b']['panel'] == panel]
        while todo:
            for s in todo:
                b0, b1 = ends(s['b'])
                if min(np.linalg.norm(b0 - cur), np.linalg.norm(b1 - cur)) < 1e-5: break
            else: raise SystemExit('collar seam does not form a loop')
            fwd_b = np.linalg.norm(b0 - cur) < 1e-5; cur = b1 if fwd_b else b0
            a0, a1 = ends(s['a']); fwd_a = a1[0] > a0[0]
            s['reversed'] = bool(fwd_a != fwd_b); s['band_from'] = round(float(min(a0[0], a1[0])), 6); todo.remove(s)
    for s in seams:
        if s['name'] == 'collar':
            pass
        elif s['name'] == 'collar_close':
            a0, a1 = ends(s['a']); b0, b1 = ends(s['b']); s['reversed'] = bool(abs(a0[1] - b1[1]) < abs(a0[1] - b0[1]))
        else:
            a0, a1 = ends(s['a']); b0, b1 = ends(s['b'])
            fa0, fa1, fb0, fb1 = flat(s['a']['panel'], a0), flat(s['a']['panel'], a1), flat(s['b']['panel'], b0), flat(s['b']['panel'], b1)
            same = np.linalg.norm(fa0 - fb0) + np.linalg.norm(fa1 - fb1); opp = np.linalg.norm(fa0 - fb1) + np.linalg.norm(fa1 - fb0)
            s['reversed'] = bool(opp < same)
            if min(same, opp) > 1e-4: raise SystemExit('seam %s does not close in the flat-lay (%.4f m)' % (s['name'], min(same, opp)))
        s['length_a'] = round(elen(s['a']), 5); s['length_b'] = round(elen(s['b']), 5)
    n = M['neck']
    out = dict(units='metres', spec=M['name'], source=source,
               frames='front/back: flat-lay (x to the wearer\'s left, y up from the hem). sleeves: x = q across (q > 0 front half), y = -p along the fold line from the shoulder point. collar: straight strip, cut length x 2 * rib width, folded double along its length; edge "seam_fold" is folded onto edge "seam" and caught in the same seam.',
               flat_lay=dict(S=D['S'].tolist(), ds=D['ds'].tolist(), dh=D['dh'].tolist(), note='a sleeve point (p, q) lies at S + p * ds + |q| * dh (x mirrored for the wearer\'s right sleeve) when the shirt lies flat'),
               collar=dict(rib_width=n['rib_width'], cut_length=round(D['collar_len'], 5), neckline_length=round(D['neck_len'], 5),
                           note='the band is shorter than the neckline (rib_length_ratio) and is stretched onto it'),
               derived={k: round(v, 5) for k, v in tg.report(M).items()},
               panels=P, seams=seams)
    return out, err


def draw(pat, path, M):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.path import Path
    from matplotlib.patches import PathPatch
    P = pat['panels']; D = pat['derived']
    b = M['body']; W = b['chest_width_flat']
    place = dict(front=(0.0, 0.0), back=(W + 0.12, 0.0), sleeve_L=(-W / 2 - 0.34, b['length_hps_to_hem'] - 0.02), sleeve_R=(1.5 * W + 0.12 + 0.34, b['length_hps_to_hem'] - 0.02), collar=(W / 2 + 0.06 - pat['collar']['cut_length'] / 2, -0.14))
    fig, ax = plt.subplots(figsize=(15, 8.2), dpi=120)
    cols = plt.get_cmap('tab20')
    seam_names = sorted(set(s['name'] for s in pat['seams']))
    scol = {n: cols(i % 20) for i, n in enumerate(seam_names)}
    ecol = {}
    for s in pat['seams']:
        for side in ('a', 'b'): ecol[(s[side]['panel'], s[side]['edge'])] = (scol[s['name']], s['name'])
    def epts(pn, e):
        v = np.array(pn['vertices']); a, c = v[e['v'][0]], v[e['v'][1]]
        return tg.bez(a, e['bezier'][0], e['bezier'][1], c, 60) if 'bezier' in e else np.array([a, c])
    for name, pn in P.items():
        off = np.array(place[name]); loop = np.concatenate([epts(pn, e)[:-1] for e in pn['edges']]) + off
        ax.add_patch(PathPatch(Path(np.vstack([loop, loop[:1]])), facecolor='#eef0f3', edgecolor='none'))
        for i, e in enumerate(pn['edges']):
            pts = epts(pn, e) + off
            c, sn = ecol.get((name, i), ('#555555', None))
            ax.plot(pts[:, 0], pts[:, 1], color=c, lw=3.2 if sn else 1.2, solid_capstyle='round')
            m = pts[len(pts) // 2]
            ln = tg.polylen(pts)
            ax.annotate('%s\n%.1f cm' % (sn or e['label'], ln * 100), m, fontsize=6.3, ha='center', va='center', color='#111', bbox=dict(boxstyle='round,pad=0.15', fc='white', ec='none', alpha=0.8))
        c = loop.mean(0)
        if name == 'collar': c = c + np.array([0, -0.045])
        ax.text(c[0], c[1], {'front': 'FRONT', 'back': 'BACK', 'sleeve_L': 'SLEEVE\n(wearer\'s left)', 'sleeve_R': 'SLEEVE\n(wearer\'s right)', 'collar': 'COLLAR BAND, 1x1 rib (cut %.1f x %.1f cm, folded double, stretched onto a %.1f cm neckline)' % (pat['collar']['cut_length'] * 100, 2 * pat['collar']['rib_width'] * 100, pat['collar']['neckline_length'] * 100)}[name], ha='center', va='center', fontsize=9, color='#333', weight='bold')
        if name in ('front', 'back'):      # hem allowance and print canvases
            ha = b['hem_allowance']; ax.plot([off[0] - b['hem_width_flat'] / 2, off[0] + b['hem_width_flat'] / 2], [ha, ha], color='#888', lw=0.8, ls='--')
            pr = M['print_front'] if name == 'front' else M['print_back']
            if name == 'front':
                cy = b['length_hps_to_hem'] - M['neck']['front_drop'] - pr['center_below_front_collar_seam']; x0 = pr['center_x'] - pr['canvas_width'] / 2; y1 = cy + pr['canvas_height'] / 2
            else:
                y1 = b['length_hps_to_hem'] - M['neck']['back_drop'] - pr['art_top_below_back_collar_seam'] + pr['art_top_v'] * pr['canvas_height']; x0 = -pr['center_x'] - pr['canvas_width'] / 2
            ax.add_patch(plt.Rectangle((off[0] + x0, y1 - pr['canvas_height']), pr['canvas_width'], pr['canvas_height'], fill=False, ec='#c0392b', lw=1.0, ls=':'))
            ax.text(off[0] + x0 + pr['canvas_width'] / 2, y1 - pr['canvas_height'] / 2, 'print canvas\n%.1f x %.1f cm' % (pr['canvas_width'] * 100, pr['canvas_height'] * 100), ha='center', va='center', fontsize=6.5, color='#c0392b')
    ax.set_aspect('equal'); ax.autoscale(); ax.margins(0.03); ax.axis('off')
    ax.set_title('%s  -  sewing pattern (finished measurements, no seam allowance; same colour = sewn together)\n'
                 'chest %.1f cm flat, length %.1f cm, shoulder to shoulder %.1f cm, sleeve %.1f cm, sleeve opening %.1f cm flat, collar rib %.1f cm.  Source: %s'
                 % (M['title'], W * 100, b['length_hps_to_hem'] * 100, b['shoulder_to_shoulder'] * 100, M['sleeve']['length_from_shoulder_seam'] * 100, M['sleeve']['opening_flat'] * 100, M['neck']['rib_width'] * 100, pat['source']), fontsize=9)
    fig.savefig(path, bbox_inches='tight', facecolor='white'); plt.close(fig)


if __name__ == '__main__':
    M = load_spec(); out = out_dir(M)
    gc_json, where = build_with_pygarment(M, os.path.join(out, 'garmentcode'))
    pat, err = translate(M, gc_json, 'GarmentCode / pygarment (pattern classes and serializer)')
    json.dump(pat, open(os.path.join(out, 'pattern.json'), 'w'), indent=1)
    draw(pat, os.path.join(out, 'pattern.png'), M)
    log('pygarment from', os.path.dirname(where))
    log('pattern.json: %d panels, %d seams, max distance design vertex -> GarmentCode vertex %.2e m' % (len(pat['panels']), len(pat['seams']), err))
    for k, v in pat['derived'].items(): log('  %-32s %.1f cm' % (k, v * 100))
    for s in pat['seams']:
        if abs(s['length_a'] - s['length_b']) > 5e-4: log('  seam %-18s lengths differ: %.1f / %.1f cm' % (s['name'], s['length_a'] * 100, s['length_b'] * 100))
