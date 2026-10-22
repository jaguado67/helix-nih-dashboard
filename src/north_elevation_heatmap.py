"""
Start Variance heat map drawn as BUILDING ELEVATION - NORTH (A-2201-PH2).

Architectural-sheet look: line work on paper, one material zone per activity
group (taken from the elevation's material legend), window openings coloured
by variance, real floor-to-floor heights, and level datums on the right that
carry the floor average.

Pure Python -> returns a Plotly figure dict.  In Streamlit:
    import plotly.graph_objects as go
    st.plotly_chart(go.Figure(build_north_elevation(df, "Level", "Group", "start_var",
                    title="START VARIANCE · U49 → U50")), use_container_width=True)
"""

from __future__ import annotations

import re
from collections import defaultdict

# --------------------------------------------------------------------- colour scale
CMIN, CMAX = -30.0, 30.0
COLORSCALE = [[0.00, "#b8123a"], [0.17, "#e4543c"], [0.33, "#f09a6c"], [0.50, "#f5e6b8"],
              [0.67, "#c3de7c"], [0.83, "#5aae5c"], [1.00, "#17734a"]]


def _rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def color_for(v):
    t = (max(CMIN, min(CMAX, v)) - CMIN) / (CMAX - CMIN)
    for (t0, c0), (t1, c1) in zip(COLORSCALE, COLORSCALE[1:]):
        if t <= t1:
            f = 0 if t1 == t0 else (t - t0) / (t1 - t0)
            a, b = _rgb(c0), _rgb(c1)
            return "rgb({},{},{})".format(*(round(a[i] + (b[i] - a[i]) * f) for i in range(3)))
    return COLORSCALE[-1][1]


def _records(data, level_col, type_col, value_col):
    if hasattr(data, "to_dict"):
        for r in data[[level_col, type_col, value_col]].itertuples(index=False):
            yield r[0], r[1], r[2]
    else:
        yield from data


def _lkey(lv):
    m = re.match(r"([A-Za-z]+)\s*0*(\d+)", str(lv))
    return (m.group(1).upper(), int(m.group(2))) if m else (str(lv), 0)


# --------------------------------------------------------------------- sheet palette
PAPER = "#f7f6f2"
LINE = "#2b2b2b"
HATCH = "rgba(43,43,43,0.28)"
FAINT = "rgba(43,43,43,0.14)"
GLASS = "#dbe7ec"
PRECAST = "#efede8"
METAL = "#e1e3e5"
EXIST = "#e4e4e1"
INK = "#1f2933"
MUTED = "#6b7785"

# Floor-to-floor heights (m) from A-2201-PH2 dimension string.
# L9 is placed in the penthouse (MAIN ROOF -> PENTHOUSE ROOF); basements are assumed.
DEFAULT_HEIGHTS = {"L1": 4.013, "L2": 3.640, "L3": 3.675, "L4": 3.962, "L5": 4.470, "L6": 4.470,
                   "L7": 4.470, "L8": 5.690, "L9": 5.182, "B1": 4.0, "B2": 4.0}
DATUM_NAMES = {"L9": "MAIN ROOF"}

# Material zone for each column, left to right, as on the north elevation.
ZONES = [("PCP-04", "terracotta grid"), ("GL-01", "curtain wall"), ("PCP-01", "thin brick"),
         ("PCP-03", "precast frame"), ("PCP-03", "precast frame"), ("PCP-03", "precast frame")]


def build_north_elevation(data, level_col="Level", type_col="Activity Type", value_col="Variance",
                          title="START VARIANCE HEAT MAP", type_order=None, others_label="Others",
                          level_heights=None, unit="calendar days", height=1000):
    H = dict(DEFAULT_HEIGHTS, **(level_heights or {}))

    # ---------------------------------------------------------------- aggregate
    acc = defaultdict(list)
    types_seen, levels_seen = [], []
    for lv, ty, v in _records(data, level_col, type_col, value_col):
        if v is None or v != v:
            continue
        lv, ty = str(lv), str(ty)
        acc[(lv, ty)].append(float(v))
        types_seen += [ty] if ty not in types_seen else []
        levels_seen += [lv] if lv not in levels_seen else []
    cell = {k: sum(v) / len(v) for k, v in acc.items()}
    types = list(type_order) if type_order else types_seen
    n = len(types)

    above = sorted([l for l in levels_seen if _lkey(l)[0] != "B" and l != others_label], key=lambda l: _lkey(l)[1])
    below = sorted([l for l in levels_seen if _lkey(l)[0] == "B"], key=lambda l: _lkey(l)[1])
    has_site = others_label in levels_seen

    # vertical datums (m): row = [base, top]
    rows = {}
    z = 0.0
    for lv in above:
        h = H.get(lv, 4.0)
        rows[lv] = (z, z + h)
        z += h
    roof = z
    z = 0.0
    for lv in below:
        h = H.get(lv, 4.0)
        rows[lv] = (z - h, z)
        z -= h
    base = z
    ph_level = above[-1] if (above and above[-1] in DATUM_NAMES) else None
    body_top = rows[ph_level][0] if ph_level else roof

    # ---------------------------------------------------------------- horizontal layout (m)
    ZW = 7.4
    gaps = {3: 1.7, 5: 0.9}                       # stair strip before col 3, glass slot before col 5
    X, x = [], 0.0
    for i in range(n):
        x += gaps.get(i, 0.0)
        X.append((x, x + ZW))
        x += ZW
    bx0, bx1 = 0.0, x
    site_y = (base if below else 0.0) - 4.6
    S, A = [], []

    def R(x0, y0, x1, y1, fill, line=LINE, w=1.0, layer="below", dash=None):
        d = dict(type="rect", x0=x0, y0=y0, x1=x1, y1=y1, fillcolor=fill,
                 line=dict(color=line, width=w), layer=layer)
        if dash:
            d["line"]["dash"] = dash
        S.append(d)

    def P(segs, color=HATCH, w=0.6, layer="below", dash=None):
        if not segs:
            return
        path = " ".join(f"M{a:.3f},{b:.3f} L{c:.3f},{d:.3f}" for a, b, c, d in segs)
        d = dict(type="path", path=path, line=dict(color=color, width=w), layer=layer)
        if dash:
            d["line"]["dash"] = dash
        S.append(d)

    def T(x, y, text, size=10, color=INK, **kw):
        A.append(dict(x=x, y=y, text=text, showarrow=False, font=dict(size=size, color=color), **kw))

    def frange(a, b, step):
        out, v = [], a + step
        while v < b - 1e-6:
            out.append(v)
            v += step
        return out

    # ---------------------------------------------------------------- ground + basement section
    gx0, gx1 = bx0 - 9.0, bx1 + 12.0
    if below:
        R(gx0, base - 1.2, gx1, 0, "#ebe6dc", line=PAPER, w=0)
        P([(xx, base - 1.2, xx + 1.2, 0) for xx in frange(gx0 - 1.2, gx1, 1.4)
           if xx + 1.2 <= gx1 and xx >= gx0], FAINT, 0.6)
        R(bx0, base - 0.6, bx1, 0, "#d9d7d1", w=1.4, dash="dash")
    P([(gx0, 0, gx1, 0)], LINE, 2.6)

    # ---------------------------------------------------------------- existing building beyond
    eh = rows[above[min(4, len(above) - 1)]][1] if above else 15
    R(bx0 - 7.5, 0, bx0, eh, EXIST, line=FAINT, w=1)
    P([(bx0 - 7.5, yy, bx0, yy) for yy in frange(0, eh, 0.35)], FAINT, 0.5)
    T(bx0 - 3.75, eh + 0.8, "EXISTING BUILDING<br>BEYOND", 8, MUTED)

    # ---------------------------------------------------------------- facade zones (above grade)
    for i, (x0, x1) in enumerate(X):
        code, _ = ZONES[i] if i < len(ZONES) else ("PCP-03", "")
        top_i = body_top
        if code == "PCP-04":
            R(x0, 0, x1, top_i, PRECAST)
            P([(xx, 0, xx, top_i) for xx in frange(x0, x1, 0.93)] +
              [(x0, yy, x1, yy) for yy in frange(0, top_i, 0.93)], FAINT, 0.6)
        elif code == "GL-01":
            R(x0, 0, x1, top_i, GLASS)
            xm = (x0 + x1) / 2
            P([(xm, 0, xm, top_i)], LINE, 1)
        elif code == "PCP-01":
            R(x0, 0, x1, top_i, "#ece6df")
            P([(x0, yy, x1, yy) for yy in frange(0, top_i, 0.32)], FAINT, 0.5)
        else:
            R(x0, 0, x1, top_i, PRECAST)
        R(x0, 0, x1, top_i, "rgba(0,0,0,0)", LINE, 1.4)
    # stair strip (alternating tread stair) and glass slot
    for gi, kind in ((3, "stair"), (5, "slot")):
        if gi < n:
            s0, s1 = X[gi - 1][1], X[gi][0]
            R(s0, 0, s1, body_top + (1.2 if kind == "stair" else 0), GLASS, LINE, 1.2)
            if kind == "stair":
                P([(s0, yy, s1, yy + 0.9) for yy in frange(-0.9, body_top, 1.1)], HATCH, 0.6)
    # spandrel bands at each level
    for lv in above:
        if lv == ph_level:
            continue
        y = rows[lv][1]
        P([(bx0, y, bx1, y)], LINE, 1.2)
        P([(bx0, y - 0.35, bx1, y - 0.35)], HATCH, 0.6)

    # ---------------------------------------------------------------- penthouse (metal panel MP-01)
    if ph_level:
        p0, p1 = rows[ph_level]
        px0, px1 = bx0 + 0.4, bx1 - 0.4
        R(bx0 - 0.25, p0 - 0.05, bx1 + 0.25, p0 + 0.35, "#d4d4cf", LINE, 1.2)   # roof parapet / coping
        R(px0, p0 + 0.35, px1, p1, METAL, LINE, 1.2)
        P([(xx, p0 + 0.35, xx, p1) for xx in frange(px0, px1, 0.32)], HATCH, 0.5)
        T(px0 + 0.3, p1 + 0.15, "MP-01", 8, MUTED, xanchor="left", yanchor="bottom")
        # upper penthouse over the right zone
        u0, u1 = X[-1][0] - 0.6, X[-1][1] - 0.2
        R(u0, p1, u1, p1 + 6.553, METAL, LINE, 1.2)
        P([(xx, p1, xx, p1 + 6.553) for xx in frange(u0, u1, 0.32)], HATCH, 0.5)
        roof_line = p1 + 6.553
    else:
        roof_line = roof

    # ---------------------------------------------------------------- site annex
    if has_site:
        R(bx0, site_y - 1.9, bx1, site_y + 1.9, "#e8e6e0", LINE, 1.2, dash="dot")
        T(bx0, site_y + 2.1, "<b>SITE / OUTSIDE BUILDING</b>", 9, MUTED, xanchor="left", yanchor="bottom")

    # ---------------------------------------------------------------- windows = data cells
    hx, hy, ht, hc = [], [], [], []
    worst = None
    order = above + below + ([others_label] if has_site else [])
    for lv in order:
        if lv == others_label:
            y0, y1 = site_y - 1.6, site_y + 1.6
        else:
            b, t = rows[lv]
            y0, y1 = (b + 0.75, t - 0.55) if lv not in below else (b + 0.5, t - 0.5)
            if lv == ph_level:
                y0, y1 = b + 0.9, t - 0.7
        for i, ty in enumerate(types):
            x0, x1 = X[i][0] + 0.55, X[i][1] - 0.55
            xc, yc = (x0 + x1) / 2, (y0 + y1) / 2
            v = cell.get((lv, ty))
            hx.append(xc); hy.append(yc)
            if v is None:
                R(x0, y0, x1, y1, "#ffffff" if lv != ph_level else METAL, LINE, 0.8)
                P([(x0, y0, x1, y1)], FAINT, 0.6)
                ht.append(f"<b>{lv} · {ty}</b><br>No activities"); hc.append(0)
                continue
            R(x0, y0, x1, y1, color_for(v), LINE, 1.6)
            P([(xc, y0, xc, y1)], "rgba(43,43,43,0.35)", 0.7)                 # mullion
            r = round(v)
            T(xc, yc, f"<b>{'+' if r >= 0 else ''}{r}</b>", 13, "white" if abs(v) >= 12 else INK)
            ht.append(f"<b>{lv} · {ty}</b><br>Mean variance: {v:+.1f} {unit}"
                      f"<br>Activities averaged: {len(acc[(lv, ty)])}")
            hc.append(v)
            if worst is None or v < worst[0]:
                worst = (v, x0, y0, x1, y1)
    if worst and worst[0] < 0:
        _, x0, y0, x1, y1 = worst
        R(x0 - 0.25, y0 - 0.25, x1 + 0.25, y1 + 0.25, "rgba(0,0,0,0)", "#111", 2.6, layer="above")
        A.append(dict(x=(x0 + x1) / 2, y=y1 + 0.25, yanchor="bottom", text="MAXIMUM DELAY", showarrow=False,
                      font=dict(size=8, color="white"), bgcolor="#111", borderpad=2))

    # ---------------------------------------------------------------- level datums + floor average
    dx0, dx1 = bx1 + 0.6, bx1 + 5.2
    bar_x = dx1 + 0.6
    T(bar_x, roof_line + 1.2, "<b>FLOOR AVG</b>", 9, MUTED, xanchor="left")
    datums = [(rows[lv][0], DATUM_NAMES.get(lv, f"LEVEL {_lkey(lv)[1]}") if lv not in below else lv)
              for lv in above + below]
    if ph_level:
        datums += [(rows[ph_level][1], "PENTHOUSE ROOF"), (roof_line, "UPPER PENTHOUSE ROOF")]
    else:
        datums += [(roof, "ROOF")]
    for y, name in datums:
        P([(dx0, y, dx1, y)], LINE, 0.8, dash="dashdot")
        S.append(dict(type="circle", x0=dx1 - 0.55, y0=y - 0.55, x1=dx1 + 0.55, y1=y + 0.55,
                      fillcolor=PAPER, line=dict(color=LINE, width=1), layer="above"))
        P([(dx1 - 0.55, y, dx1 + 0.55, y), (dx1, y - 0.55, dx1, y + 0.55)], LINE, 0.8, layer="above")
        T(dx1 - 0.7, y + 0.15, name, 8, INK, xanchor="right", yanchor="bottom")
    for lv in order:
        vals = [cell[(lv, t)] for t in types if (lv, t) in cell]
        if not vals:
            continue
        avg = sum(vals) / len(vals)
        yc = (site_y if lv == others_label else sum(rows[lv]) / 2)
        w = max(abs(avg) * 0.32, 0.12)
        R(bar_x, yc - 0.7, bar_x + w, yc + 0.7, color_for(avg), LINE, 0.8)
        T(bar_x + w + 0.3, yc, f"{avg:+.1f} d", 10, INK, xanchor="left")

    # ---------------------------------------------------------------- headers + sheet callout
    ylab = (site_y - 2.3) if has_site else (base - 1.8)
    for i, ty in enumerate(types):
        xc = (X[i][0] + X[i][1]) / 2
        T(xc, ylab, ty.replace("/", "/<br>"), 10, INK, yanchor="top")
        if i < len(ZONES):
            T(xc, ylab - 3.2, ZONES[i][0], 8, MUTED, yanchor="top")
    T(gx0 + 0.2, 0.15, "GRADE", 8, MUTED, xanchor="left", yanchor="bottom")
    cy = ylab - 6.2
    S.append(dict(type="circle", x0=gx0 + 0.2, y0=cy - 1.0, x1=gx0 + 2.2, y1=cy + 1.0,
                  fillcolor=PAPER, line=dict(color=LINE, width=1.2), layer="above"))
    T(gx0 + 1.2, cy, "1", 11, INK)
    P([(gx0 + 2.2, cy - 0.1, bx1 + 2, cy - 0.1)], LINE, 1.2)
    T(gx0 + 2.6, cy + 0.15, f"<b>{title} · BUILDING ELEVATION - NORTH</b>", 12, INK,
      xanchor="left", yanchor="bottom")
    T(gx0 + 2.6, cy - 0.35, "Each window = level × activity group · datums carry the floor average · "
                           "negative = delayed", 9, MUTED, xanchor="left", yanchor="top")

    traces = [dict(type="scatter", x=hx, y=hy, mode="markers", hoverinfo="text", hovertext=ht,
                   hoverlabel=dict(bgcolor="white", font=dict(color=INK)), showlegend=False,
                   marker=dict(symbol="square", size=44, opacity=0, color=hc, cmin=CMIN, cmax=CMAX,
                               colorscale=COLORSCALE, showscale=True,
                               colorbar=dict(title=dict(text=unit.capitalize(), side="top"), thickness=12,
                                             len=0.6, y=0.6, x=1.0, outlinewidth=0,
                                             tickvals=[-30, -20, -10, 0, 10, 20, 30],
                                             ticktext=["−30 late", "−20", "−10", "0", "+10", "+20",
                                                       "+30 early"])))]
    layout = dict(height=height, margin=dict(l=10, r=10, t=20, b=10), paper_bgcolor=PAPER, plot_bgcolor=PAPER,
                  xaxis=dict(visible=False, range=[gx0, gx1 + 2]),
                  yaxis=dict(visible=False, range=[cy - 2.2, roof_line + 3], scaleanchor="x", scaleratio=1),
                  shapes=S, annotations=A, hovermode="closest",
                  font=dict(family="Arial Narrow, Arial, sans-serif"))
    return dict(data=traces, layout=layout)


# --------------------------------------------------------------------- demo (read from screenshot)
GROUPS = ["Cans/Troughs/XFMRs", "Conduits", "Fire Alarm", "Other", "Pull Wire", "Panels"]
_M = {"L9": [None, 1, -6, -6, 0, 0], "L8": [0, -1, -19, -10, -10, -10], "L7": [0, -8, -23, -15, -19, -9],
      "L6": [0, 0, -12, -7, -11, -10], "L5": [0, 0, -7, -5, 0, -3], "L4": [0, 0, -8, -5, -6, -6],
      "L3": [0, 0, -19, -13, -16, -4], "L2": [0, 0, -10, -6, -6, -6], "L1": [0, 0, -14, -11, -12, -4],
      "B1": [None, None, None, 0, None, None], "B2": [0, 0, -10, -6, -3, 0], "Others": [0, 0, -12, -8, 0, 0]}
DEMO = [(lv, GROUPS[i], v) for lv, row in _M.items() for i, v in enumerate(row) if v is not None]

if __name__ == "__main__":
    import json, sys
    fig = build_north_elevation(DEMO, title="START VARIANCE · U49 → U50", type_order=GROUPS)
    json.dump(fig, open(sys.argv[1] if len(sys.argv) > 1 else "north_elevation.json", "w"))