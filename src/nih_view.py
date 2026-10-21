import pandas as pd
import plotly.graph_objects as go
import streamlit as st

NAVY="#0B2E52"; BLUE="#3568A6"; ORANGE="#E4572E"; GREEN="#1A9A75"; RED="#D93636"; GRID="#DCE4EC"

def fmt_date(x): return "—" if pd.isna(x) else pd.Timestamp(x).strftime("%d-%b-%Y")
def fmt_days(x): return "—" if x is None else f"{x:+d} d"

def _kpi(label,value,sub="",cls=""):
    return f'<div class="kpi {cls}"><div class="kl">{label}</div><div class="kv">{value}</div><div class="ks">{sub}</div></div>'

def render_dashboard(m):
    st.markdown("""
    <style>
    .block-container{max-width:1550px;padding-top:.55rem;padding-bottom:2rem}
    header[data-testid="stHeader"]{background:transparent}.stApp{background:#fff;color:#10233D}
    .hdr{background:#0B2E52;color:#fff;padding:12px 16px;display:grid;grid-template-columns:1.5fr .9fr .85fr;align-items:center;gap:12px}
    .brand{font-size:21px;font-weight:900;line-height:1.05}.sub{font-size:11px;margin-top:5px}.badges{text-align:center}.badge{display:inline-block;border:1px solid rgba(255,255,255,.55);padding:8px 11px;margin:2px;border-radius:4px;font-size:10px;font-weight:800}.right{text-align:right;font-size:10px;line-height:1.45}
    .view{background:#0B2E52;color:white;margin:10px 0 10px;padding:8px 12px;display:flex;justify-content:space-between;font-size:11px;font-weight:800}
    .section{font-size:16px;font-weight:900;margin:10px 0 6px;color:#111}.band{border:1px solid #b9d9d1;border-top:3px solid #159b77;border-radius:5px;background:#f7fbfa;padding:10px 0 0;margin-bottom:10px}.bandtitle{font-size:15px;font-weight:900;padding:0 12px 8px}.pill{background:#159b77;color:#fff;border-radius:14px;padding:5px 12px;margin-right:8px;font-size:10px}.hint{float:right;font-size:9px;color:#6b7a90;font-weight:400}
    .kgrid{display:grid;grid-template-columns:repeat(4,1fr);gap:8px}.kgrid8{display:grid;grid-template-columns:repeat(8,1fr);gap:8px}.kpi{background:#fff;border:1px solid #cfd9e6;border-radius:6px;padding:12px 8px;text-align:center;min-height:82px}.kl{font-size:9px;font-weight:800;color:#30425b}.kv{font-size:19px;font-weight:900;color:#071B33;margin-top:6px}.ks{font-size:8px;color:#7b899c;margin-top:4px}.good .kv{color:#159b77}.bad .kv{color:#d93636}.blue .kv{color:#2f80ed}
    </style>
    """,unsafe_allow_html=True)

    current=m.current_key; previous=m.previous_key
    cur=m.status_counts(); pct=m.status_percentages()
    previous_finish = m.milestone_previous() if hasattr(m, "milestone_previous") else None
    previous_shift = (m.current_finish.normalize()-previous_finish.normalize()).days if previous_finish is not None and pd.notna(previous_finish) and pd.notna(m.current_finish) else None
    previous_label = f"{previous_shift:+d} calendar days vs {previous}" if previous_shift is not None else f"vs {previous}"
    st.markdown(f'''<div class="hdr"><div><div class="brand">HELIX Project &amp; Portfolio Control Center</div><div class="sub">NIH Schedule Performance Dashboard</div></div><div class="badges"><span class="badge">BASELINE · U38</span><span class="badge">PREVIOUS · {previous}</span><span class="badge">CURRENT · {current}</span></div><div class="right"><b>Latest Data Date</b> {fmt_date(m.data_date)}<br><b>Current Update</b> {current}<br><b>Scope</b> HELIX Electrical + Fire Alarm</div></div>''',unsafe_allow_html=True)
    st.markdown(f'<div class="view"><span>NIH VIEW · v0.3.0</span><span>U38 Baseline · {previous} Previous · {current} Current</span></div>',unsafe_allow_html=True)

    st.markdown('<div class="section">PROJECT STATUS SUMMARY</div>',unsafe_allow_html=True)
    st.markdown('<div class="band"><div class="bandtitle"><span class="pill">TIME</span>SCHEDULE PERFORMANCE <span class="hint">Project completion milestone: EXS.130 · Date Shift convention = Baseline − Current</span></div>',unsafe_allow_html=True)
    st.markdown('<div class="kgrid">'+''.join([
        _kpi("Baseline Completion",fmt_date(m.baseline_finish),"U38 · Substantial Completion"),
        _kpi("Current Forecast Finish",fmt_date(m.current_finish),previous_label,"blue"),
        _kpi("Finish Date Shift",fmt_days(m.finish_shift),f"U38 − {current}","bad" if (m.finish_shift or 0)<0 else "good"),
        _kpi("Current Data Date",fmt_date(m.data_date),f"{current} P6 Data Date"),
    ])+'</div></div>',unsafe_allow_html=True)

    st.markdown('<div class="section">ACTIVITY PERFORMANCE</div>',unsafe_allow_html=True)
    st.markdown(f'<div class="band"><div class="bandtitle">OVERALL ACTIVITY STATUS <span class="hint">HELIX scope · {current} · activity-count metrics only</span></div>',unsafe_allow_html=True)
    open_acts=cur["In Progress"]+cur["Not Started"]
    st.markdown('<div class="kgrid8">'+''.join([
        _kpi("Total HELIX Activities",f"{cur['Total']:,}",f"{current} activity-count scope"),
        _kpi("Completed",f"{cur['Completed']:,}","Completed activities"),
        _kpi("In Progress",f"{cur['In Progress']:,}","Open / active activities"),
        _kpi("Not Started",f"{cur['Not Started']:,}","Open / not started"),
        _kpi("Completed Activities %",f"{pct['Completed %']:.1f}%",f"{cur['Completed']:,} of {cur['Total']:,}","good"),
        _kpi("In Progress Activities %",f"{pct['In Progress %']:.1f}%",f"{cur['In Progress']:,} of {cur['Total']:,}"),
        _kpi("Not Started Activities %",f"{pct['Not Started %']:.1f}%",f"{cur['Not Started']:,} of {cur['Total']:,}","bad"),
        _kpi("Open HELIX Activities",f"{open_acts:,}","In Progress + Not Started"),
    ])+'</div></div>',unsafe_allow_html=True)

    st.markdown(f'<div class="section">PROJECT PROGRESS S-CURVE · BASELINE VS PLANNING_{current} VS ACTUAL</div>',unsafe_allow_html=True)
    s=m.scurve()
    if not s.empty:
        s=s.loc[s["Date"]<=pd.Timestamp("2027-05-01")].copy()
        total=cur["Total"]
        actual=cur["Completed"]
        remaining=total-actual
        st.markdown('<div class="kgrid">'+''.join([
            _kpi(f"Total Plan · Planning_{current}",f"{total:,}","Current HELIX activity scope","blue"),
            _kpi("Total Actual",f"{actual:,}","Completed HELIX activities","good"),
            _kpi("Remaining",f"{remaining:,}","In Progress + Not Started","bad" if remaining else "good"),
            _kpi("Data Date",fmt_date(m.data_date),f"{current} schedule cut-off")
        ])+'</div>',unsafe_allow_html=True)
        st.markdown('<div class="section">CUMULATIVE S-CURVE · BASELINE VS CURRENT PLAN VS ACTUAL</div>',unsafe_allow_html=True)
        fig=go.Figure()
        for key,name,color,mode in [
            ("Baseline","Baseline (U38)",BLUE,"lines"),
            ("Planned",f"Planned / Forecast ({current})",ORANGE,"lines"),
            ("Actual","Actual",GREEN,"lines+markers")]:
            fig.add_trace(go.Scatter(x=s["Date"],y=s[key],name=name,mode=mode,
                                     line=dict(width=3,color=color),marker=dict(size=5 if key=="Actual" else 0),
                                     connectgaps=False))
        if pd.notna(m.data_date):
            observed=s.loc[s["Date"]<m.data_date,["Date","Actual"]].dropna()
            fig.data[2].x=list(observed["Date"])+[m.data_date]
            fig.data[2].y=list(observed["Actual"])+[actual]
            forecast=s.loc[s["Date"]>m.data_date,["Date","Planned"]].dropna()
            fig.data[1].x=[m.data_date]+list(forecast["Date"])
            fig.data[1].y=[actual]+list(forecast["Planned"])
            fig.add_vline(x=m.data_date,line_dash="dash",line_width=2,line_color="#3678CB")
            fig.add_annotation(x=m.data_date,y=1.08,yref="paper",text=f"Data Date · {fmt_date(m.data_date)}",
                               showarrow=False,font=dict(color=BLUE,size=11),bgcolor="white")
            fig.add_annotation(x=m.data_date,y=actual,text=f"Actual: {actual:,}",showarrow=True,ax=-35,ay=-30,
                               bgcolor="white",font=dict(color=GREEN))
        fig.update_layout(height=420,margin=dict(l=20,r=20,t=45,b=15),yaxis_title="Cumulative Activities",
                          legend=dict(orientation="h",y=1.17,x=.28),plot_bgcolor="white",hovermode="x unified")
        fig.update_yaxes(gridcolor=GRID,rangemode="tozero")
        fig.update_xaxes(gridcolor="#EEF1F5",tickformat="%b-%y",dtick="M2",
                         range=[s["Date"].min()-pd.Timedelta(days=15),pd.Timestamp("2027-05-31")])
        st.plotly_chart(fig,use_container_width=True,config={"displayModeBar":False})
        st.markdown('<div class="section">MONTHLY BASELINE VS PLANNED VS ACTUAL</div>',unsafe_allow_html=True)
        bars=go.Figure()
        for key,name,color in [("Monthly Baseline","Baseline",BLUE),
                               ("Monthly Planned","Planned",ORANGE),("Monthly Actual","Actual",GREEN)]:
            bars.add_trace(go.Bar(x=s["Date"],y=s[key],name=name,marker_color=color,
                                  text=s[key].where(s[key]>0),textposition="outside",textfont=dict(size=10)))
        if pd.notna(m.data_date):
            bars.add_vline(x=m.data_date,line_dash="dash",line_color="#3678CB")
        bars.update_layout(barmode="group",height=350,margin=dict(l=20,r=20,t=35,b=20),
                           yaxis_title="Monthly Activities",legend=dict(orientation="h",y=-.17,x=.32),
                           plot_bgcolor="white")
        bars.update_yaxes(gridcolor=GRID,rangemode="tozero")
        bars.update_xaxes(tickformat="%b-%y",dtick="M2",range=[s["Date"].min()-pd.Timedelta(days=15),pd.Timestamp("2027-05-31")])
        st.plotly_chart(bars,use_container_width=True,config={"displayModeBar":False})
        st.caption("Display horizon: Phase 2 through May 2027. Activities scheduled after this date remain in the source and overall scope totals but are excluded from the displayed monthly horizon.")
        st.caption(f"Planning_{current} is anchored to {actual:,} completed HELIX activities at the Data Date. "
                   "Actual progress stops at the Data Date; planned monthly bars count open activities by forecast month. "
                   "Activity-count metrics are not weighted by resources, costs or physical quantities.")

    prev=m.status_counts(previous)
    st.markdown(f'<div class="section">ACTIVITY STATUS COMPARISON · {previous} VS {current}</div>',unsafe_allow_html=True)
    d=pd.DataFrame({"Status":["Completed","In Progress","Not Started"],f"Previous {previous}":[prev["Completed"],prev["In Progress"],prev["Not Started"]],f"Current {current}":[cur["Completed"],cur["In Progress"],cur["Not Started"]]})
    fig2=go.Figure()
    fig2.add_trace(go.Bar(
        x=d["Status"],y=d[f"Previous {previous}"],name=f"Previous {previous}",
        marker_color=BLUE,text=d[f"Previous {previous}"],textposition="outside",
        textfont=dict(size=12),cliponaxis=False))
    fig2.add_trace(go.Bar(
        x=d["Status"],y=d[f"Current {current}"],name=f"Current {current}",
        marker_color=ORANGE,text=d[f"Current {current}"],textposition="outside",
        textfont=dict(size=12),cliponaxis=False))
    fig2.update_layout(
        barmode="group",height=390,
        margin=dict(l=30,r=30,t=35,b=40),plot_bgcolor="white",
        legend=dict(orientation="h",y=-0.17,x=0.35),
        yaxis_title="Number of HELIX Activities",
        xaxis_title=None,bargap=0.38,bargroupgap=0.08,
        font=dict(size=12,color=NAVY))
    fig2.update_yaxes(gridcolor=GRID,rangemode="tozero")
    fig2.update_xaxes(showgrid=False,categoryorder="array",
                      categoryarray=["Completed","In Progress","Not Started"])
    st.plotly_chart(fig2,use_container_width=True,config={"displayModeBar":False})

    with st.expander("Diagnostics · NIH HELIX Scope Audit",expanded=False):
        st.dataframe(pd.DataFrame([m.scope_diagnostics()]),use_container_width=True,hide_index=True)

