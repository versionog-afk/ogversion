"""Shape (CC0 MakeHuman base mesh + targets) and pose (default rig, linear blend skinning) in numpy.
Units inside this module: decimetres (base mesh units) until `to_metres`."""
import os, sys, json
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *

def mix_targets(V, mix):
    out = V.copy()
    for path, w in mix:
        if abs(w) < 1e-6:
            continue
        out += w * load_target(path + '.target', len(V))
    return out

def default_mix(female=0.85, slim=0.45, lowmuscle=0.25, cup=-0.5):
    """gender / weight / muscle macro mix, an even blend of the three ethnic macros (generic face)"""
    mix = []
    for g, gw in (('female', female), ('male', 1 - female)):
        for mu, mw in (('minmuscle', lowmuscle), ('averagemuscle', 1 - lowmuscle)):
            for wt, ww in (('minweight', slim), ('averageweight', 1 - slim)):
                mix.append(('macrodetails/universal-%s-young-%s-%s' % (g, mu, wt), gw * mw * ww))
        for race in ('caucasian', 'asian', 'african'):
            mix.append(('macrodetails/%s-%s-young' % (race, g), gw / 3.0))
    if cup < 0:
        mix.append(('breast/female-young-averagemuscle-averageweight-mincup-averagefirmness', -cup * female))
    elif cup > 0:
        mix.append(('breast/female-young-averagemuscle-averageweight-maxcup-averagefirmness', cup * female))
    return mix

class Rig:
    def __init__(self, V):
        d = json.load(open(MH + '/rigs/default.mhskel'))
        self.bones = d['bones']; self.jv = d['joints']; self.planes = d['planes']
        self.J = {k: V[np.array(v)].mean(0) for k, v in self.jv.items()}
        self.order = []
        def add(b):
            if b in self.order: return
            p = self.bones[b]['parent']
            if p: add(p)
            self.order.append(b)
        for b in self.bones: add(b)
    def head(self, b): return self.J[self.bones[b]['head']]
    def tail(self, b): return self.J[self.bones[b]['tail']]
    def plane_normal(self, b):
        a, bb, c = [self.J[j] for j in self.planes[self.bones[b]['rotation_plane']]]
        n = np.cross(bb - a, c - bb); return n / np.linalg.norm(n)

def rot(axis, deg):
    axis = np.asarray(axis, float); axis /= np.linalg.norm(axis)
    a = np.radians(deg); c, s = np.cos(a), np.sin(a); x, y, z = axis
    return np.array([[c + x * x * (1 - c), x * y * (1 - c) - z * s, x * z * (1 - c) + y * s],
                     [y * x * (1 - c) + z * s, c + y * y * (1 - c), y * z * (1 - c) - x * s],
                     [z * x * (1 - c) - y * s, z * y * (1 - c) + x * s, c + z * z * (1 - c)]])

def skin(V, rig, pose, W):
    """pose: bone -> 3x3 world rotation about the bone's rest head. returns posed verts, posed joints fn, per-bone 4x4"""
    G = {}
    for b in rig.order:
        L = np.eye(4)
        if b in pose:
            R = pose[b]; h = rig.head(b)
            L[:3, :3] = R; L[:3, 3] = h - R @ h
        p = rig.bones[b]['parent']
        G[b] = (G[p] @ L) if p else L
    out = np.zeros_like(V); wsum = np.zeros(len(V))
    Vh = np.concatenate([V, np.ones((len(V), 1))], 1)
    for b, (idx, w) in W.items():
        if b not in G: continue
        out[idx] += w[:, None] * (Vh[idx] @ G[b].T)[:, :3]
        wsum[idx] += w
    has = wsum > 1e-6
    out[has] /= wsum[has, None]
    out[~has] = V[~has]
    def joint(b, which='head'):
        j = rig.head(b) if which == 'head' else rig.tail(b)
        return (G[b] @ np.append(j, 1))[:3]
    return out, joint, G, has
