/* Quality tiers.

   Q0  fine pointer    DPR ≤ 2     physical cloth (sheen)
   Q1  coarse pointer  DPR ≤ 1.5   standard cloth with the rim patch
   Q2  (governor)      DPR ≤ 1.25  reflections off
   Q3  (governor)      DPR 1.0     rimR off, idle sway off

   THIS STAGE picks the starting tier and honours ?q=0..3. The governor
   (cadence calibration while loading, stepping down between gestures) is the
   next stage: it should call setTier() and the onChange hook does the rest. */
export const quality = {
  tier: 1,
  forced: false,       // ?q= given: never change tier automatically
  lab: false,          // ?3d=1 given: software GL in tests, so never judge the frame rate
                       // (no automatic tier drops, no fps-based goStatic)
  onChange: null
};

export function startTier(params) {
  const q = params.get('q');
  quality.lab = params.get('3d') === '1';
  if (q !== null && /^[0-3]$/.test(q)) { quality.tier = +q; quality.forced = true; }
  else quality.tier = matchMedia('(pointer:coarse)').matches ? 1 : 0;
  return quality.tier;
}

export function setTier(t) {
  if (quality.forced || quality.lab || t === quality.tier) return;
  quality.tier = t;
  quality.onChange && quality.onChange(t);
}
