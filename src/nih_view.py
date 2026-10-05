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

    cur=m.status_counts("U49"); pct=m.status_percentages("U49")
    st.markdown(f'''<div class="hdr"><div><div class="brand">HELIX Project &amp; Portfolio Control Center</div><div class="sub">NIH Schedule Performance Dashboard</div></div><div class="badges"><span class="badge">BASELINE · U38</span><span class="badge">PREVIOUS · U39–U48</span><span class="badge">CURRENT · U49</span></div><div class="right"><b>Latest Data Date</b> {fmt_date(m.data_date)}<br><b>Current Update</b> U49<br><b>Scope</b> HELIX Electrical + Fire Alarm</div></div>''',unsafe_allow_html=True)
    st.markdown('<div class="view"><span>NIH VIEW · v0.2.8</span><span>U38 Baseline · U39–U48 Previous History · U49 Current</span></div>',unsafe_allow_html=True)

    st.markdown('<div class="section">PROJECT STATUS SUMMARY</div>',unsafe_allow_html=True)
    st.markdown('<div class="band"><div class="bandtitle"><span class="pill">TIME</span>SCHEDULE PERFORMANCE <span class="hint">Project completion milestone: EXS.130 · Date Shift convention = Baseline − Current</span></div>',unsafe_allow_html=True)
    st.markdown('<div class="kgrid">'+''.join([
        _kpi("Baseline Completion",fmt_date(m.baseline_finish),"U38 · Substantial Completion"),
        _kpi("Current Forecast Finish",fmt_date(m.current_finish),"0 d vs U48","blue"),
        _kpi("Finish Date Shift",fmt_days(m.finish_shift),"U38 − U49","bad" if (m.finish_shift or 0)<0 else "good"),
        _kpi("Current Data Date",fmt_date(m.data_date),"U49 P6 Data Date"),
    ])+'</div></div>',unsafe_allow_html=True)

    st.markdown('<div class="section">ACTIVITY PERFORMANCE</div>',unsafe_allow_html=True)
    st.markdown('<div class="band"><div class="bandtitle">OVERALL ACTIVITY STATUS <span class="hint">HELIX scope · U49 · activity-count metrics only</span></div>',unsafe_allow_html=True)
    open_acts=cur["In Progress"]+cur["Not Started"]
    st.markdown('<div class="kgrid8">'+''.join([
        _kpi("Total HELIX Activities",f"{cur['Total']:,}","U49 activity-count scope"),
        _kpi("Completed",f"{cur['Completed']:,}","Completed activities"),
        _kpi("In Progress",f"{cur['In Progress']:,}","Open / active activities"),
        _kpi("Not Started",f"{cur['Not Started']:,}","Open / not started"),
        _kpi("Completed Activities %",f"{pct['Completed %']:.1f}%",f"{cur['Completed']:,} of {cur['Total']:,}","good"),
        _kpi("In Progress Activities %",f"{pct['In Progress %']:.1f}%",f"{cur['In Progress']:,} of {cur['Total']:,}"),
        _kpi("Not Started Activities %",f"{pct['Not Started %']:.1f}%",f"{cur['Not Started']:,} of {cur['Total']:,}","bad"),
        _kpi("Open HELIX Activities",f"{open_acts:,}","In Progress + Not Started"),
    ])+'</div></div>',unsafe_allow_html=True)

    st.markdown('<div class="section">ACTIVITY S-CURVE · HELIX SCOPE</div>',unsafe_allow_html=True)
    st.caption("Cumulative activity count above · monthly activity quantities below")
    s=m.scurve()
    if not s.empty:
        fig=go.Figure()
        fig.add_trace(go.Scatter(x=s["Date"],y=s["Baseline (U38)"],name="Baseline (U38)",mode="lines",line=dict(width=3,color=BLUE)))
        fig.add_trace(go.Scatter(x=s["Date"],y=s["Planned / Forecast (U49)"],name="Planned / Forecast (U49)",mode="lines",line=dict(width=3,color=ORANGE)))
        fig.add_trace(go.Scatter(x=s["Date"],y=s["Actual"],name="Actual",mode="lines+markers",line=dict(width=3,color=GREEN),marker=dict(size=5)))
        if pd.notna(m.data_date):
            ymax=max(s["Baseline (U38)"].max(),s["Planned / Forecast (U49)"].max())
            fig.add_vline(x=m.data_date,line_dash="dash",line_width=2,line_color="#607d9b")
            fig.add_annotation(x=m.data_date,y=ymax,text=f"Data Date · {fmt_date(m.data_date)}",showarrow=False,xanchor="left",bgcolor="white")
            fig.add_annotation(x=m.data_date,y=cur["Completed"],text=f'Actual at Data Date: {cur["Completed"]:,}',showarrow=False,xanchor="left",bgcolor="#eaf7f2",font=dict(color=GREEN))
        fig.update_layout(height=450,margin=dict(l=15,r=15,t=30,b=20),yaxis_title="Cumulative Activities",legend=dict(orientation="h",y=1.08,x=.35),plot_bgcolor="white",hovermode="x unified")
        fig.update_yaxes(gridcolor=GRID); fig.update_xaxes(showgrid=False)
        st.plotly_chart(fig,use_container_width=True,config={"displayModeBar":False})

    prev=m.status_counts("U48")
    st.markdown('<div class="section">ACTIVITY PLAN VS ACTUAL · U48 VS U49</div>',unsafe_allow_html=True)
    d=pd.DataFrame({"Status":["Completed","In Progress","Not Started"],"Previous U48":[prev["Completed"],prev["In Progress"],prev["Not Started"]],"Current U49":[cur["Completed"],cur["In Progress"],cur["Not Started"]]})
    fig2=go.Figure()
    fig2.add_trace(go.Bar(y=d["Status"],x=d["Previous U48"],name="Previous U48",orientation="h"))
    fig2.add_trace(go.Bar(y=d["Status"],x=d["Current U49"],name="Current U49",orientation="h"))
    fig2.update_layout(barmode="group",height=330,margin=dict(l=20,r=20,t=20,b=20),legend=dict(orientation="h"),plot_bgcolor="white")
    fig2.update_xaxes(gridcolor=GRID)
    st.plotly_chart(fig2,use_container_width=True,config={"displayModeBar":False})

    with st.expander("Diagnostics · NIH HELIX Scope Audit",expanded=False):
        st.dataframe(pd.DataFrame([m.scope_diagnostics()]),use_container_width=True,hide_index=True)
