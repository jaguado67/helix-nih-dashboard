import pandas as pd
import plotly.graph_objects as go
import streamlit as st

NAVY="#0C2D50"; TEXT="#10233D"; GRID="#DCE4EC"

def fmt_date(x): return "—" if pd.isna(x) else pd.Timestamp(x).strftime("%d-%b-%Y")
def fmt_days(x): return "—" if x is None else f"{x:+d} days"

def render_dashboard(m):
    st.markdown("""
    <style>
    .block-container{max-width:1700px;padding-top:.7rem;padding-bottom:2rem}
    .hdr{background:#0C2D50;color:white;padding:14px 18px;border-radius:4px;margin-bottom:12px}
    .title{font-size:24px;font-weight:800}.sub{font-size:13px;opacity:.9}
    .section{font-size:17px;font-weight:800;color:#111;margin:14px 0 6px}
    .kpi{border:1px solid #cfd8e3;border-radius:8px;padding:12px 14px;background:#fff;min-height:102px}
    .kl{font-size:12px;font-weight:700;color:#506070}.kv{font-size:24px;font-weight:800;color:#0C2D50}
    </style>
    """,unsafe_allow_html=True)
    st.markdown('<div class="hdr"><div class="title">HELIX NIH · Schedule Performance Dashboard</div><div class="sub">Hospital Project · Baseline U38 · Current U49 · Previous U48</div></div>',unsafe_allow_html=True)

    cur=m.status_counts("U49")
    cols=st.columns(7)
    vals=[
        ("Baseline Completion",fmt_date(m.baseline_finish)),
        ("Current Forecast Finish",fmt_date(m.current_finish)),
        ("Finish Date Shift",fmt_days(m.finish_shift)),
        ("Completed Activities",f"{cur['Completed']:,}"),
        ("In Progress Activities",f"{cur['In Progress']:,}"),
        ("Not Started Activities",f"{cur['Not Started']:,}"),
        ("Current Data Date",fmt_date(m.data_date)),
    ]
    for c,(lab,val) in zip(cols,vals):
        c.markdown(f'<div class="kpi"><div class="kl">{lab}</div><div class="kv">{val}</div></div>',unsafe_allow_html=True)

    st.markdown('<div class="section">S-CURVE · CUMULATIVE ACTIVITY COUNT</div>',unsafe_allow_html=True)
    s=m.scurve()
    if not s.empty:
        fig=go.Figure()
        fig.add_trace(go.Scatter(x=s["Date"],y=s["Baseline U38"],name="Baseline U38",mode="lines",line=dict(width=3)))
        fig.add_trace(go.Scatter(x=s["Date"],y=s["Current U49"],name="Current U49",mode="lines",line=dict(width=3)))
        fig.update_layout(height=390,margin=dict(l=20,r=20,t=20,b=20),yaxis_title="Cumulative Activities",legend=dict(orientation="h"),plot_bgcolor="white")
        fig.update_yaxes(gridcolor=GRID)
        st.plotly_chart(fig,use_container_width=True,config={"displayModeBar":False})

    st.markdown('<div class="section">OVERALL ACTIVITY STATUS · U48 VS U49</div>',unsafe_allow_html=True)
    p=m.status_counts("U48")
    df=pd.DataFrame({"Status":["Completed","In Progress","Not Started"],"Previous U48":[p["Completed"],p["In Progress"],p["Not Started"]],"Current U49":[cur["Completed"],cur["In Progress"],cur["Not Started"]]})
    fig=go.Figure()
    fig.add_trace(go.Bar(y=df["Status"],x=df["Previous U48"],name="Previous U48",orientation="h"))
    fig.add_trace(go.Bar(y=df["Status"],x=df["Current U49"],name="Current U49",orientation="h"))
    fig.update_layout(barmode="group",height=330,margin=dict(l=20,r=20,t=20,b=20),legend=dict(orientation="h"),plot_bgcolor="white")
    fig.update_xaxes(gridcolor=GRID)
    st.plotly_chart(fig,use_container_width=True,config={"displayModeBar":False})

    st.markdown('<div class="section">MONTHLY UPDATE TREND · U38–U49</div>',unsafe_allow_html=True)
    tr=m.update_trend()
    fig=go.Figure()
    fig.add_trace(go.Scatter(x=tr["Update"],y=tr["Completed"],name="Completed",mode="lines+markers"))
    fig.add_trace(go.Scatter(x=tr["Update"],y=tr["In Progress"],name="In Progress",mode="lines+markers"))
    fig.add_trace(go.Scatter(x=tr["Update"],y=tr["Not Started"],name="Not Started",mode="lines+markers"))
    fig.update_layout(height=360,margin=dict(l=20,r=20,t=20,b=20),yaxis_title="Activities",legend=dict(orientation="h"),plot_bgcolor="white")
    fig.update_yaxes(gridcolor=GRID)
    st.plotly_chart(fig,use_container_width=True,config={"displayModeBar":False})
    st.dataframe(tr,use_container_width=True,hide_index=True)

    with st.expander("Diagnostics · NIH XER Audit",expanded=False):
        st.dataframe(pd.DataFrame([m.scope_diagnostics()]),use_container_width=True,hide_index=True)
