"""
Start Variance "Building Section" heat map.

Each level is drawn as a floor of a building (roof on top, basements below
ground, "Others" as a site annex) and each activity type as a bay/room.
Pure-Python: returns a Plotly figure *dict*, so it has no hard dependency.

Streamlit usage:
    import plotly.graph_objects as go
    from building_heatmap import build_building_heatmap
    fig = go.Figure(build_building_heatmap(df, level_col="Level",
                                           type_col="Activity Type",
                                           value_col="start_var_cd",
                                           title="START VARIANCE · U49 → U50"))
    st.plotly_chart(fig, use_container_width=True)

`df` can be a pandas DataFrame or a list of (level, type, value) tuples.
If several rows share the same (level, type), they are averaged.
"""

from __future__ import annotations

import re
from collections import defaultdict

# ---------------------------------------------------------------- palette
CMIN, CMAX = -30.0, 30.0
COLORSCALE = [
    [0.00, "#b8123a"],
    [0.17, "#e4543c"],
    [0.33, "#f09a6c"],
    [0.50, "#f5e6b8"],
    [0.67, "#c3de7c"],
    [0.83, "#5aae5c"],
    [1.00, "#17734a"],
]
SHELL = "#26303b"        # structure (slabs / columns show as gaps)
ROOF = "#1b222b"
EMPTY_ROOM = "#3d4752"   # bay with no activities
SKY = "#eef3f8"
SOIL = "#cdb89c"
GROUND = "#6b4f3a"
GRASS = "#6f9e4c"
INK = "#1f2933"
MUTED = "#6b7785"


def _hex_to_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def color_for(v):
    t = (max(CMIN, min(CMAX, v)) - CMIN) / (CMAX - CMIN)
    for (t0, c0), (t1, c1) in zip(COLORSCALE, COLORSCALE[1:]):
        if t <= t1:
            f = 0 if t1 == t0 else (t - t0) / (t1 - t0)
            a, b = _hex_to_rgb(c0), _hex_to_rgb(c1)
            return "rgb({},{},{})".format(*(round(a[i] + (b[i] - a[i]) * f) for i in range(3)))
    return COLORSCALE[-1][1]


def _records(data, level_col, type_col, value_col):
    if hasattr(data, "to_dict"):  # pandas DataFrame
        for r in data[[level_col, type_col, value_col]].itertuples(index=False):
            yield r[0], r[1], r[2]
    else:
        yield from data


def _level_key(lv):
    m = re.match(r"([A-Za-z]+)\s*0*(\d+)", str(lv))
    return (m.group(1).upper(), int(m.group(2))) if m else (str(lv), 0)


def build_building_heatmap(data, level_col="Level", type_col="Activity Type",
                           value_col="Variance", title="START VARIANCE",
                           type_order=None, others_label="Others",
                           unit="calendar days", height=860):
    # ------------------------------------------------ aggregate (mean)
    acc = defaultdict(list)
    types_seen, levels_seen = [], []
    for lv, ty, v in _records(data, level_col, type_col, value_col):
        if v is None or v != v:  # None / NaN
            continue
        lv, ty = str(lv), str(ty)
        acc[(lv, ty)].append(float(v))
        if ty not in types_seen:
            types_seen.append(ty)
        if lv not in levels_seen:
            levels_seen.append(lv)
    cell = {k: sum(v) / len(v) for k, v in acc.items()}
    types = list(type_order) if type_order else types_seen

    above = sorted([l for l in levels_seen if _level_key(l)[0] not in ("B",) and l != others_label],
                   key=lambda l: _level_key(l)[1], reverse=True)
    below = sorted([l for l in levels_seen if _level_key(l)[0] == "B"],
                   key=lambda l: _level_key(l)[1])
    has_others = others_label in levels_seen

    # y positions: above-ground floors 1..N, ground at 0.5, basements 0,-1,...
    ypos = {lv: len(above) - i for i, lv in enumerate(above)}
    for j, lv in enumerate(below):
        ypos[lv] = -j
    y_bottom_bldg = -len(below) + 0.45 if below else 0.55
    y_top = len(above) + 0.45
    y_others = y_bottom_bldg - 1.35
    if has_others:
        ypos[others_label] = y_others

    n = len(types)
    x0, x1 = -0.55, n - 0.45
    gauge_x0 = n + 0.25
    shapes, annotations = [], []

    def rect(xa, ya, xb, yb, fill, line=None, width=0, layer="below", dash=None, opacity=1):
        s = dict(type="rect", x0=xa, y0=ya, x1=xb, y1=yb, fillcolor=fill,
                 line=dict(color=line or fill, width=width), layer=layer, opacity=opacity)
        if dash:
            s["line"]["dash"] = dash
        shapes.append(s)

    def seg(xa, ya, xb, yb, color, width, dash=None):
        s = dict(type="line", x0=xa, y0=ya, x1=xb, y1=yb, line=dict(color=color, width=width), layer="below")
        if dash:
            s["line"]["dash"] = dash
        shapes.append(s)

    # ------------------------------------------------ site & ground
    soil_bottom = y_bottom_bldg - 0.5
    rect(-1.7, soil_bottom, gauge_x0 + 1.9, 0.5, SOIL, opacity=0.45)
    seg(-1.7, 0.5, gauge_x0 + 1.9, 0.5, GROUND, 3)
    seg(-1.7, 0.53, x0 - 0.05, 0.53, GRASS, 5)
    seg(x1 + 0.05, 0.53, gauge_x0 + 1.9, 0.53, GRASS, 5)

    # ------------------------------------------------ building shell + roof
    rect(x0, y_bottom_bldg - 0.1, x1, y_top, SHELL)
    rect(x0 - 0.1, y_top, x1 + 0.1, y_top + 0.18, ROOF)                     # parapet
    mid = (n - 1) / 2
    rect(mid - 0.9, y_top + 0.18, mid + 0.9, y_top + 0.75, SHELL)          # penthouse
    rect(mid - 0.75, y_top + 0.3, mid - 0.15, y_top + 0.62, "#55606c")     # louver
    rect(mid + 0.15, y_top + 0.3, mid + 0.75, y_top + 0.62, "#55606c")
    seg(mid + 1.3, y_top + 0.18, mid + 1.3, y_top + 1.25, ROOF, 2)        # antenna
    shapes.append(dict(type="circle", x0=mid + 1.25, y0=y_top + 1.2, x1=mid + 1.35, y1=y_top + 1.3,
                       fillcolor="#e4543c", line=dict(width=0), layer="above"))

    # annex for "Others"
    if has_others:
        rect(x0, y_others - 0.5, x1, y_others + 0.5, "#4a5561", line="#26303b", width=1)
        annotations.append(dict(x=x0, y=y_others + 0.62, xanchor="left", yanchor="bottom",
                                text="<b>SITE / OUTSIDE BUILDING</b>", showarrow=False,
                                font=dict(size=10, color=MUTED)))

    # ------------------------------------------------ rooms
    hx, hy, hc, htext = [], [], [], []
    worst = None
    rows = above + below + ([others_label] if has_others else [])
    for lv in rows:
        y = ypos[lv]
        for i, ty in enumerate(types):
            v = cell.get((lv, ty))
            xa, xb, ya, yb = i - 0.44, i + 0.44, y - 0.4, y + 0.4
            if v is None:
                rect(xa, ya, xb, yb, EMPTY_ROOM)
                hx.append(i); hy.append(y); hc.append(None)
                htext.append(f"<b>{lv} · {ty}</b><br>No activities")
                continue
            rect(xa, ya, xb, yb, color_for(v), layer="below")
            # "window" glint on top edge
            rect(xa + 0.04, yb - 0.07, xb - 0.04, yb - 0.035, "rgba(255,255,255,0.35)")
            r = round(v)
            label = f"+{r}" if r >= 0 else f"{r}"
            annotations.append(dict(x=i, y=y, text=f"<b>{label}</b>", showarrow=False,
                                    font=dict(size=14, color="white" if abs(v) >= 12 else INK)))
            hx.append(i); hy.append(y); hc.append(v)
            htext.append(f"<b>{lv} · {ty}</b><br>Mean variance: {v:+.1f} {unit}"
                         f"<br>Activities averaged: {len(acc[(lv, ty)])}")
            if worst is None or v < worst[0]:
                worst = (v, i, y)

    if worst and worst[0] < 0:
        _, wi, wy = worst
        rect(wi - 0.47, wy - 0.43, wi + 0.47, wy + 0.43, "rgba(0,0,0,0)", line="#111", width=3, layer="above")
        annotations.append(dict(x=wi + 0.47, y=wy + 0.43, xanchor="right", yanchor="bottom",
                                text="MAXIMUM DELAY", showarrow=False,
                                font=dict(size=9, color="white"), bgcolor="#111", borderpad=2))

    # ------------------------------------------------ floor indicator (left)
    fx, fy, ft = [], [], []
    for lv in rows:
        fx.append(-1.05); fy.append(ypos[lv]); ft.append(lv if lv != others_label else "SITE")

    # ------------------------------------------------ floor average gauge (right)
    scale = 1.4 / 20.0   # 20 days of slip = 1.4 x-units
    annotations.append(dict(x=gauge_x0, y=y_top + 0.35, xanchor="left", text="<b>FLOOR AVG</b>",
                            showarrow=False, font=dict(size=11, color=MUTED)))
    seg(gauge_x0, y_others - 0.5 if has_others else y_bottom_bldg, gauge_x0, y_top, "#9aa5b1", 1)
    for lv in rows:
        vals = [cell[(lv, t)] for t in types if (lv, t) in cell]
        if not vals:
            continue
        avg = sum(vals) / len(vals)
        y = ypos[lv]
        w = max(abs(avg) * scale, 0.03)
        rect(gauge_x0, y - 0.22, gauge_x0 + w, y + 0.22, color_for(avg))
        annotations.append(dict(x=gauge_x0 + w + 0.08, y=y, xanchor="left", showarrow=False,
                                text=f"{avg:+.1f} d", font=dict(size=11, color=INK)))

    # ------------------------------------------------ column headers
    for i, ty in enumerate(types):
        annotations.append(dict(x=i, y=(y_others - 0.65) if has_others else (y_bottom_bldg - 0.6),
                                yanchor="top", text=ty.replace(" + ", " +<br>").replace("/", "/<br>"),
                                showarrow=False, font=dict(size=11, color=INK)))
    annotations.append(dict(x=-1.05, y=0.5, text="GL", showarrow=False, xanchor="center", yanchor="bottom",
                            font=dict(size=9, color=GROUND)))

    traces = [
        # hover targets + colorbar
        dict(type="scatter", x=hx, y=hy, mode="markers", hoverinfo="text", hovertext=htext,
             hoverlabel=dict(bgcolor="white", font=dict(color=INK)),
             marker=dict(symbol="square", size=60, opacity=0,
                         color=[c if c is not None else 0 for c in hc],
                         cmin=CMIN, cmax=CMAX, colorscale=COLORSCALE, showscale=True,
                         colorbar=dict(title=dict(text=unit.capitalize(), side="top"), thickness=14,
                                       len=0.7, y=0.55, x=1.01, outlinewidth=0,
                                       tickvals=[-30, -20, -10, 0, 10, 20, 30],
                                       ticktext=["−30 late", "−20", "−10", "0", "+10", "+20", "+30 early"])),
             showlegend=False),
        # floor indicator buttons
        dict(type="scatter", x=fx, y=fy, mode="markers+text", text=ft, hoverinfo="skip",
             textfont=dict(color="white", size=11), showlegend=False,
             marker=dict(symbol="circle", size=34, color=SHELL, line=dict(color="#9aa5b1", width=2))),
    ]

    layout = dict(
        title=dict(text=f"<b>{title}</b><br><span style='font-size:12px;color:{MUTED}'>"
                        f"Building section view · each floor = level, each bay = activity type · "
                        f"negative = delayed · positive = earlier</span>", x=0.01, font=dict(size=18, color=INK)),
        height=height, margin=dict(l=20, r=20, t=80, b=20),
        plot_bgcolor=SKY, paper_bgcolor="white",
        xaxis=dict(visible=False, range=[-1.6, gauge_x0 + 1.9], fixedrange=False),
        yaxis=dict(visible=False, range=[(y_others - 1.3) if has_others else soil_bottom - 0.8, y_top + 1.45]),
        shapes=shapes, annotations=annotations, hovermode="closest",
        font=dict(family="Inter, Segoe UI, Arial, sans-serif"),
    )
    return dict(data=traces, layout=layout)


# -------------------------------------------------------------- demo data
DEMO = [  # values read from the U49 → U50 screenshot
    ("L9", "Conduits", 1), ("L9", "Other", -6), ("L9", "Pull Wire", 0),
    ("L8", "Cans/Troughs/XFMRs", -12), ("L8", "Conduits", -1), ("L8", "Other", -13), ("L8", "Pull Wire", -11),
    ("L7", "Cans/Troughs/XFMRs", -12), ("L7", "Conduits", -6), ("L7", "Other", -16), ("L7", "Pull Wire", -17),
    ("L6", "Cans/Troughs/XFMRs", -10), ("L6", "Conduits", 0), ("L6", "Other", -10), ("L6", "Pull Wire", -8),
    ("L5", "Cans/Troughs/XFMRs", -10), ("L5", "Conduits", 0), ("L5", "Other", -6), ("L5", "Pull Wire", 0),
    ("L4", "Cans/Troughs/XFMRs", -10), ("L4", "Conduits", 0), ("L4", "Other", -6), ("L4", "Pull Wire", -4),
    ("L3", "Cans/Troughs/XFMRs", -9), ("L3", "Conduits", 0), ("L3", "Other", -13), ("L3", "Pull Wire", -13),
    ("L2", "Cans/Troughs/XFMRs", -10), ("L2", "Conduits", -1), ("L2", "Other", -7), ("L2", "Pull Wire", -5),
    ("L1", "Cans/Troughs/XFMRs", -9), ("L1", "Conduits", 0), ("L1", "Other", -11), ("L1", "Pull Wire", -11),
    ("B1", "Other", 0),
    ("B2", "Cans/Troughs/XFMRs", 0), ("B2", "Conduits", 0), ("B2", "Other", -6), ("B2", "Pull Wire", -5),
    ("Others", "Cans/Troughs/XFMRs", 0), ("Others", "Conduits", 0), ("Others", "Other", -8),
    ("Others", "Pull Wire", 0), ("Others", "Risers + OH", 0),
]
TYPES = ["Cans/Troughs/XFMRs", "Conduits", "Elev. Pri. Conduit", "Other", "Pull Wire", "Risers + OH"]

if __name__ == "__main__":
    import json, sys
    fig = build_building_heatmap(DEMO, title="START VARIANCE HEAT MAP · U49 → U50", type_order=TYPES)
    out = sys.argv[1] if len(sys.argv) > 1 else "building_heatmap.json"
    with open(out, "w") as f:
        json.dump(fig, f)
    print("wrote", out)