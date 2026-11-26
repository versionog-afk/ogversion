"""All design parameters of the tee, the mannequin and the simulation.
Garment frame: x right (viewer's right when looking at the front), y up, z towards the viewer (front).
Units: metres. y = 0 is the designed hem level, y_hps the high point shoulder (collar seam at the shoulder)."""
import math
from types import SimpleNamespace as NS

P = NS(
    # ---- topology -------------------------------------------------------------------
    N=128,        # columns around the body (and around the neckline)
    S=6,          # columns removed for the armhole (width of the hole)
    NR=3,         # rows of the collar rib (simulated with the cloth, pinned at its top edge)
    J0S=10,       # rows from the neckline to the top of the armhole (along the shoulder)
    R=20,         # rows along the armhole
    JB=46,        # rows from the armpit to the hem
    K=20,         # rings along a sleeve
    # ---- body tube (boxy) -------------------------------------------------------------
    body_a=0.250,   # half width of the (super)elliptical body cross-section
    body_b=0.125,   # half depth
    body_n=2.5,     # superellipse exponent (2 = ellipse, larger = boxier)
    body_zc=0.006,  # z centre of the tube
    y_hps=0.745,
    # ---- shoulder roof ----------------------------------------------------------------
    sigma=math.radians(20.0),    # shoulder slope
    gamma_f=math.radians(46.0),  # front roof pitch over the shoulders
    gamma_fc=math.radians(56.0), # front roof pitch at the centre (upper chest below the collar)
    gamma_b=math.radians(50.0),  # back roof pitch (upper back)
    z_ridge=-0.012,
    c_roof=0.03, k_tube=0.07, eps_x=0.03, funnel_r=0.05,
    # ---- neckline (seam between body and rib), designed directly in the worn shape -----
    neck_w=0.086,      # half width (x) at the shoulder
    neck_front=0.080,   # z extent in front of the ridge
    neck_back=0.047,    # z extent behind the ridge
    neck_drop_f=0.070,  # how much lower than the HPS the front neck point is
    neck_drop_b=-0.012,  # negative: the back of the collar seam sits higher than the shoulder point
    rib_w=0.022,        # rib width
    rib_elev=(40.0, 55.0, 70.0),   # elevation of the rib above horizontal at front / side / back (degrees)
    # ---- sleeves ------------------------------------------------------------------------
    beta_rest=math.radians(38.0),   # sleeve axis angle below horizontal in the rest shape
    r_seam=0.070, r_hem=0.064,      # sleeve tube radius at the armhole seam / at the hem
    ridge_len=0.240,                # shoulder seam length HPS -> armhole seam (dropped shoulder)
    sleeve_len=0.225,               # along the top of the sleeve
    k_arm=0.035,
    # ---- mannequin (collision only) ----------------------------------------------------
    jx=0.225, jy=0.628, jz=-0.002,  # shoulder joint
    arm_r=0.055, arm_clear=0.006,
    alpha_L=math.radians(30.5), alpha_R=math.radians(29.0),   # final arm angle from vertical (+x arm, -x arm)
    fwd_L=math.radians(4.0), fwd_R=math.radians(6.5),         # slight forward swing of the arms
    # ---- cloth ---------------------------------------------------------------------------
    thickness=0.0022,
    smooth_iters=4,
    # ---- textures / print ----------------------------------------------------------------
    atlas=2048, normal_quality=90, grain=0.000045, wrinkle=0.00007, ao_rays=48,
    print_gap=0.085, print_nu=56, print_nv=46, print_offset=0.0012,
    sim=NS(
        f_settle0=10, f_move=55, f_settle1=75,       # frames: settle, arms come down, settle
        quality=9, mass=0.25, air_damping=2.5,
        tension=40.0, compression=8.0, shear=8.0, bending=2.8,
        tension_damp=10.0, compression_damp=10.0, shear_damp=6.0, bending_damp=1.0,
        stiff_bending=60.0, stiff_tension=90.0,
        dist=0.004, self_dist=0.0025, coll_quality=4, friction=12.0, self_friction=4.0,
        collider_outer=0.003,
        print_stiff=0.60,      # extra stiffness weight inside the print area (ink film)
    ),
)
P.J0 = P.NR + P.J0S
P.J1 = P.J0 + P.R
P.M = P.J1 + P.JB
P.C = 2 * P.S + 2 * P.R
