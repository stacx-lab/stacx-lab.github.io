"""Side-view Go2 + D1 illustration, proportioned from go2_d1_hole_aligned.urdf and the device profiles.

Planar forward kinematics in the robot's sagittal plane (x forward, z up, metres); drawn with the head
facing left. Shapes are simplified silhouettes around real joint positions and link lengths; this is an
illustration, not a calibrated render.
"""
from __future__ import annotations
import math
from PIL import Image, ImageDraw

# --- dimensions from the URDF / profiles (metres) ---
HIP_X = 0.1934                 # FR/FL/RR/RL hip joints at x = ±0.1934 on the trunk
THIGH = CALF = 0.213           # thigh -> calf and calf -> foot joint offsets
FOOT_R = 0.022
HIP_R = 0.046                  # hip collision cylinder radius
ARM_MOUNT = (-0.0193, 0.0855)  # arm/profile.yaml extrinsics.mount (base_link)
D1_BASE_H = 0.0738             # d1_link1_joint z
D1_SHOULDER_H = 0.0578         # d1_link2_joint z
D1_UPPER = 0.27                # d1_link3_joint z
D1_ELBOW = (0.05, 0.041325)    # d1_link4_joint x, z
D1_FOREARM = 0.15468           # d1_link5_joint x
D1_WRIST = 0.0777              # d1_link6_joint x
D435_MOUNT = (0.3771, 0.0012)  # d435/profile.yaml mount, relative to the arm base
D405_ON_FLANGE = (0.0435, 0.0501)  # d405/profile.yaml mount, relative to the flange

# Standing gait pose and a readable "ready" arm pose (radians).
STAND = {'near': (0.70, -1.40), 'far': (0.62, -1.28)}
ARM_POSE = (-1.25, 1.50, 0.55)  # folded carry pose, as used between pickups  # Joint2, Joint3, Joint5

def rot(v, q):
    """Rotate (x, z) about +y by q (URDF convention: +q tips +z toward +x)."""
    x, z = v
    return (x * math.cos(q) + z * math.sin(q), -x * math.sin(q) + z * math.cos(q))

def add(a, b): return (a[0] + b[0], a[1] + b[1])

def leg(hip, thigh_q, calf_q):
    knee = add(hip, rot((0, -THIGH), thigh_q))
    foot = add(knee, rot((0, -CALF), thigh_q + calf_q))
    return hip, knee, foot

def arm_chain():
    base = ARM_MOUNT
    shoulder = add(base, (0, D1_BASE_H + D1_SHOULDER_H))
    q2, q3, q5 = ARM_POSE
    elbow = add(shoulder, rot((0, D1_UPPER), q2))
    elbow2 = add(elbow, rot(D1_ELBOW, q2 + q3))
    wrist = add(elbow2, rot((D1_FOREARM, 0), q2 + q3))
    flange = add(wrist, rot((D1_WRIST, 0), q2 + q3 + q5))
    tip_dir = q2 + q3 + q5
    return base, shoulder, elbow, elbow2, wrist, flange, tip_dir

def stand_height():
    _, _, foot = leg((HIP_X, 0), *STAND['near'])
    return -foot[1] + FOOT_R

# ---------------------------------------------------------------- drawing
def _capsule(d, a, b, w0, w1, fill, outline, ow):
    """Tapered link from a (width w0) to b (width w1), rounded ends."""
    ang = math.atan2(b[1] - a[1], b[0] - a[0]); nx, ny = -math.sin(ang), math.cos(ang)
    poly = [(a[0] + nx * w0 / 2, a[1] + ny * w0 / 2), (b[0] + nx * w1 / 2, b[1] + ny * w1 / 2),
            (b[0] - nx * w1 / 2, b[1] - ny * w1 / 2), (a[0] - nx * w0 / 2, a[1] - ny * w0 / 2)]
    d.polygon(poly, fill=fill)
    for c, w in ((a, w0), (b, w1)): d.ellipse((c[0] - w / 2, c[1] - w / 2, c[0] + w / 2, c[1] + w / 2), fill=fill)
    if outline:
        d.line([poly[0], poly[1]], fill=outline, width=ow); d.line([poly[3], poly[2]], fill=outline, width=ow)
        for c, w, s in ((a, w0, ang + math.pi / 2), (b, w1, ang - math.pi / 2)):
            box = (c[0] - w / 2, c[1] - w / 2, c[0] + w / 2, c[1] + w / 2)
            d.arc(box, math.degrees(s), math.degrees(s) + 180, fill=outline, width=ow)

def render(size, scale, active, colors, idle, card, k=3):
    """Return (RGBA image of `size`, anchors in image px). `active` = set of device ids."""
    W, H = size; S = scale * k
    im = Image.new('RGBA', (W * k, H * k), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    ground = H * k - 6 * k
    cx = W * k / 2 + 0.03 * S
    def P(p): return (cx - p[0] * S, ground - (p[1] + stand_height()) * S)
    def on(dev): return dev in active
    def line_col(dev): return colors[dev] if on(dev) else '#8F897D'
    def tint(dev, light, dark='#E9E5DC'): return light if on(dev) else dark
    OW = max(2, int(1.6 * k))

    # Ground shadow
    a, b = P((0.34, -stand_height())), P((-0.30, -stand_height()))
    d.ellipse((min(a[0], b[0]), a[1] - 5 * k, max(a[0], b[0]), a[1] + 5 * k), fill=(0, 0, 0, 22))

    # Far-side legs (lighter, slightly different phase)
    far = '#D8D3C8' if not on('base') else '#BFD3EE'
    for hx in (HIP_X, -HIP_X):
        hip, knee, foot = leg((hx, 0), *STAND['far'])
        _capsule(d, P(hip), P(knee), 0.084 * S, 0.050 * S, far, None, OW)
        _capsule(d, P(knee), P(foot), 0.040 * S, 0.022 * S, far, None, OW)
        f = P(foot); r = FOOT_R * S; d.ellipse((f[0] - r, f[1] - r, f[0] + r, f[1] + r), fill='#9C968A' if not on('base') else '#8EAAD3')

    # Trunk: Go2 silhouette with sloped head and chin LiDAR
    body = [(-0.210, -0.030), (-0.205, 0.045), (-0.180, 0.066), (0.180, 0.066), (0.238, 0.052), (0.288, 0.014),
            (0.308, -0.030), (0.292, -0.060), (0.200, -0.070), (-0.170, -0.066), (-0.205, -0.052)]
    d.polygon([P(p) for p in body], fill=tint('base', '#E4ECF8', '#F2EFE8'), outline=line_col('base'), width=OW)
    d.polygon([P(p) for p in [(-0.200, -0.030), (0.300, -0.030), (0.290, -0.058), (0.200, -0.066), (-0.170, -0.062), (-0.200, -0.050)]],
              fill=tint('base', '#C9DAF1', '#DCD7CC'))  # darker belly
    d.polygon([P(p) for p in body], outline=line_col('base'), width=OW)
    d.line([P((-0.15, 0.040)), P((0.17, 0.040))], fill=tint('base', '#F4F8FD', '#FBFAF7'), width=OW * 2)  # top highlight
    d.polygon([P(p) for p in [(0.250, 0.040), (0.288, 0.008), (0.300, -0.028), (0.262, -0.030), (0.238, 0.010)]],
              fill='#3B3A37')  # dark face plate
    lc = P((0.282, -0.064)); r = 0.020 * S
    d.pieslice((lc[0] - r, lc[1] - r, lc[0] + r, lc[1] + r), 0, 180, fill='#55534E')  # LiDAR under the chin
    # Computer dock on the back
    d.rounded_rectangle((*P((0.10, 0.088)), *P((-0.10, 0.060))), radius=int(0.008 * S), fill=tint('host', '#ECEAE5', '#E6E1D7'),
                        outline=line_col('host'), width=OW)

    # D435 head camera on its bracket
    cam = add(ARM_MOUNT, D435_MOUNT)
    d.line([P((cam[0] - 0.02, 0.058)), P((cam[0] - 0.02, cam[1] - 0.012))], fill='#6A665F', width=OW * 2)
    d.rounded_rectangle((*P((cam[0] + 0.012, cam[1] + 0.014)), *P((cam[0] - 0.075, cam[1] - 0.014))), radius=int(0.006 * S),
                        fill=tint('d435', '#D7F0F2', '#4A4844'), outline=line_col('d435'), width=OW)
    for lx in (0.0, 0.05):
        c = P((cam[0] - 0.006 - lx, cam[1])); r = 0.007 * S
        d.ellipse((c[0] - r, c[1] - r, c[0] + r, c[1] + r), fill=colors['d435'] if on('d435') else '#9E9A92')

    # Near-side legs: hip motor, thick thigh, thin calf, rubber foot
    for hx in (HIP_X, -HIP_X):
        hip, knee, foot = leg((hx, 0), *STAND['near'])
        _capsule(d, P(hip), P(knee), 0.090 * S, 0.052 * S, tint('base', '#DCE7F7', '#EDEAE3'), line_col('base'), OW)
        _capsule(d, P(knee), P(foot), 0.042 * S, 0.022 * S, tint('base', '#C9DAF1', '#D6D1C6'), line_col('base'), OW)
        kn = P(knee); r = 0.026 * S
        d.ellipse((kn[0] - r, kn[1] - r, kn[0] + r, kn[1] + r), fill=tint('base', '#C9DAF1', '#D6D1C6'), outline=line_col('base'), width=OW)
        f = P(foot); r = FOOT_R * S; d.ellipse((f[0] - r, f[1] - r, f[0] + r, f[1] + r), fill='#4A4844')
        h = P(hip); r = HIP_R * S
        d.ellipse((h[0] - r, h[1] - r, h[0] + r, h[1] + r), fill=tint('base', '#F4F8FD', '#FBFAF7'), outline=line_col('base'), width=OW)
        r2 = 0.018 * S; d.ellipse((h[0] - r2, h[1] - r2, h[0] + r2, h[1] + r2), fill=tint('base', '#C9DAF1', '#E2DED4'))

    # D1 arm
    base, shoulder, elbow, elbow2, wrist, flange, tip_dir = arm_chain()
    arm_fill, arm_dark = tint('arm', '#5F58C9', '#3E3C38'), tint('arm', '#4A43B0', '#2C2B28')
    d.rounded_rectangle((*P((base[0] + 0.040, base[1] + D1_BASE_H + 0.015)), *P((base[0] - 0.040, base[1]))),
                        radius=int(0.012 * S), fill=arm_dark)
    _capsule(d, P(shoulder), P(elbow), 0.046 * S, 0.040 * S, arm_fill, None, OW)
    _capsule(d, P(elbow2), P(wrist), 0.040 * S, 0.034 * S, arm_fill, None, OW)
    _capsule(d, P(elbow), P(elbow2), 0.050 * S, 0.044 * S, arm_dark, None, OW)
    _capsule(d, P(wrist), P(flange), 0.036 * S, 0.034 * S, arm_dark, None, OW)
    for j in (shoulder, elbow, wrist):
        c = P(j); r = 0.022 * S
        d.ellipse((c[0] - r, c[1] - r, c[0] + r, c[1] + r), fill=arm_dark, outline=tint('arm', '#B9B4F3', '#6E6A62'), width=OW)

    # Gripper: two parallel fingers past the flange
    fl = flange; gdir = tip_dir
    finger = '#E8612C' if on('gripper') else '#2C2B28'
    palm_a, palm_b = add(fl, rot((0, 0.028), gdir)), add(fl, rot((0, -0.028), gdir))
    d.line([P(palm_a), P(palm_b)], fill=finger, width=int(0.016 * S))
    for off in (0.022, -0.022):
        a0 = add(fl, rot((0.004, off), gdir)); a1 = add(a0, rot((0.070, -off * 0.25), gdir))
        _capsule(d, P(a0), P(a1), 0.016 * S, 0.012 * S, finger, None, OW)

    # D405 wrist camera above the flange
    cam5 = add(fl, rot(D405_ON_FLANGE, gdir))
    corners = []
    for dx, dz in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
        x, z = dx * 0.021, dz * 0.010
        corners.append(P(add(cam5, rot((x, z), gdir))))
    d.polygon(corners, fill=tint('d405', '#D7F0F2', '#4A4844'), outline=line_col('d405'), width=OW)
    for lx in (-0.009, 0.009):
        q = P(add(cam5, rot((lx, -0.0105), gdir))); r = 0.0045 * S
        d.ellipse((q[0] - r, q[1] - r, q[0] + r, q[1] + r), fill=colors['d405'] if on('d405') else '#9E9A92')

    im = im.resize((W, H), Image.Resampling.LANCZOS)
    def A(p): x, y = P(p); return (x / k, y / k)
    anchors = {
        'gripper': A(add(flange, rot((0.06, 0), gdir))),
        'd405': A(cam5),
        'd435': A((cam[0] - 0.03, cam[1] + 0.014)),
        'arm': A(add(shoulder, rot((0, D1_UPPER * 0.55), ARM_POSE[0]))),
        'base': A((-0.12, -0.03)),
        'host': A((-0.06, 0.088)),
    }
    return im, anchors
