import pandas as pd
import plotly.graph_objects as go
import streamlit as st

NAVY="#0B2E52"; BLUE="#3568A6"; ORANGE="#E4572E"; GREEN="#1A9A75"; RED="#D93636"; GRID="#DCE4EC"

def fmt_date(x): return "—" if pd.isna(x) else pd.Timestamp(x).strftime("%d-%b-%Y")
def fmt_days(x): return "—" if x is None else f"{x:+d} d"

def _kpi(label,value,sub="",cls=""):
    return f'<div class="kpi {cls}"><div class="kl">{label}</div><div class="kv">{value}</div><div class="ks">{sub}</div></div>'

def update_label(m,key):
    project=m.projects[key]
    for field in ("last_recalc_date","data_date","last_schedule_date"):
        date=pd.to_datetime(project.get(field),errors="coerce")
        if pd.notna(date):
            return f"{date.strftime('%B %Y')} ({key})"
    return key

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

    st.markdown('<div class="section">HISTORICAL SCHEDULE COMPARISON</div>',unsafe_allow_html=True)
    available=[k for k in m.available_updates if k!="U38"]
    expected=[f"U{i}" for i in range(39,int(m.current_key[1:])+1)]
    missing=[key for key in expected if key not in available]
    st.caption(f"Loaded: U38 baseline + {len(available)} update(s).")
    if missing:
        st.warning("Missing historical XER files in the deployed GitHub data folder: "
                   + ", ".join(missing)
                   + ". Upload each file as Uxx.xer or Uxx.xer.gz to enable selection.")
    default=[k for k in ("U40","U44","U49","U50") if k in available]
    if not default:
        default=available[-4:]
    selected=st.multiselect("Compare updates against the fixed U38 baseline",available,
                            default=default,format_func=lambda k: f"{update_label(m,k)}",
                            key="nih_historical_selection")
    if selected:
        cohort=None
        hist_fig=go.Figure()
        baseline=m.schedules["U38"].copy()  # HELIX-only via verified current HELIX code set
        if cohort is not None:
            baseline=baseline[baseline["task_code"].astype(str).isin(cohort)]
        current_helix_count=len(m.current)
        if len(baseline)>current_helix_count+100:
            st.error(f"Baseline scope invalid: {len(baseline):,} vs {current_helix_count:,} current HELIX activities.")
            st.stop()
        dates=pd.to_datetime(baseline["target_end_date"],errors="coerce").fillna(pd.to_datetime(baseline["early_end_date"],errors="coerce"))
        months=pd.date_range("2023-03-01","2027-05-01",freq="MS")
        base=pd.DataFrame({"Date":months,"Baseline":[int(dates.le(month+pd.offsets.MonthEnd(0)).sum()) for month in months]})
        hist_fig.add_trace(go.Scatter(x=base["Date"],y=base["Baseline"],name="Baseline (U38)",
                                      mode="lines",line=dict(color=BLUE,width=4)))
        palette=["#E4572E","#7654A3","#159B77","#C08D23","#A83B69","#444F88","#008E9A"]
        for i,key in enumerate(selected):
            history,cutoff=m.historical_curve(key,activity_ids=cohort)
            if history.empty:
                continue
            forecast=history[["Date","Forecast"]].dropna()
            if pd.notna(cutoff):
                completed=int((m.raw_schedules[key][m.raw_schedules[key]["task_code"].astype(str).isin(cohort)] if cohort is not None else m.native_scopes[key])["Status"].eq("Completed").sum())
                forecast=pd.concat([pd.DataFrame({"Date":[cutoff],"Forecast":[completed]}),forecast.loc[forecast["Date"]>cutoff]],ignore_index=True)
            if key=="U39" and cohort is None and pd.notna(cutoff) and not forecast.empty:
                forecast.loc[forecast["Date"].eq(cutoff),"Forecast"]=348
            color=palette[i%len(palette)]
            # Dashed = observed historical progress; solid = remaining forecast.
            actual_rows=m.schedules[key]
            if key=="U39" and m.native_scopes[key].empty:
                ids=set(m.schedules["U38"]["task_code"].astype(str))
                actual_rows=m.raw_schedules[key][m.raw_schedules[key]["task_code"].astype(str).isin(ids)]
            actual_dates=pd.to_datetime(actual_rows["act_end_date"],errors="coerce")
            actual_dates=actual_dates.where(actual_rows["Status"].eq("Completed"))
            if pd.notna(cutoff) and not actual_dates.dropna().empty:
                history_months=pd.date_range(
                    min(base["Date"].min(),actual_dates.min().to_period("M").to_timestamp()),
                    cutoff.to_period("M").to_timestamp(),freq="MS")
                past=pd.DataFrame({"Date":list(history_months)+[cutoff]})
                past["Count"]=[int(actual_dates.le(d+pd.offsets.MonthEnd(0)).sum())
                               for d in history_months]+[int(actual_dates.le(cutoff).sum())]
                hist_fig.add_trace(go.Scatter(x=past["Date"],y=past["Count"],
                    name=update_label(m,key)+" · actual",mode="lines",
                    line=dict(width=1.8,color=color,dash="dash"),
                    showlegend=False,hovertemplate="%{x|%b-%Y}: %{y} actual<extra></extra>"))
            hist_fig.add_trace(go.Scatter(x=forecast["Date"],y=forecast["Forecast"],
                                          name=update_label(m,key),mode="lines",
                                          line=dict(width=2.5,color=color)))
        hist_fig.update_layout(height=430,plot_bgcolor="white",hovermode="x unified",
                               margin=dict(l=15,r=15,t=40,b=15),yaxis_title="Cumulative Activities",
                               legend=dict(orientation="h",y=1.16,x=0))
        hist_fig.update_yaxes(gridcolor=GRID,rangemode="tozero")
        hist_fig.update_xaxes(tickformat="%b-%y",dtick="M2",range=[base["Date"].min(),pd.Timestamp("2027-05-31")])
        st.plotly_chart(hist_fig,use_container_width=True,config={"displayModeBar":False})
        st.caption("Dashed lines: reported actual progress up to each Data Date. Solid lines: forecast after the Data Date. U38: baseline.")
        st.dataframe(m.historical_diagnostics(selected,activity_ids=cohort).sort_values("Data Date",ascending=False,kind="stable"),use_container_width=True,hide_index=True)

    else:
        st.info("Select one or more updates to view historical forecast curves.")

    prev=m.status_counts(previous)
    def update_month(key):
        project=m.projects[key]
        date=pd.NaT
        for field in ("last_recalc_date","data_date","last_schedule_date"):
            candidate=pd.to_datetime(project.get(field),errors="coerce")
            if pd.notna(candidate):
                date=candidate
                break
        return f"{date.strftime('%B %Y')} ({key})" if pd.notna(date) else key
    previous_label=update_month(previous)
    current_label=update_month(current)
    st.markdown(f'<div class="section">ACTIVITY STATUS COMPARISON · {previous_label} VS {current_label}</div>',unsafe_allow_html=True)
    d=pd.DataFrame({"Status":["Completed","In Progress","Not Started"],f"Previous {previous}":[prev["Completed"],prev["In Progress"],prev["Not Started"]],f"Current {current}":[cur["Completed"],cur["In Progress"],cur["Not Started"]]})
    fig2=go.Figure()
    fig2.add_trace(go.Bar(
        x=d["Status"],y=d[f"Previous {previous}"],name=previous_label,
        marker_color=BLUE,text=d[f"Previous {previous}"],textposition="outside",
        textfont=dict(size=12),cliponaxis=False))
    fig2.add_trace(go.Bar(
        x=d["Status"],y=d[f"Current {current}"],name=current_label,
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
    status_col,monthly_col=st.columns(2,gap="large")
    with status_col:
        st.markdown("<div style=\"text-align:center;font-weight:800;margin-bottom:12px\">ACTIVITY STATUS · PREVIOUS VS CURRENT</div>",unsafe_allow_html=True)
        fig2.update_layout(height=370,legend=dict(orientation="h",y=-0.24,x=0))
        st.plotly_chart(fig2,use_container_width=True,config={"displayModeBar":False})
    with monthly_col:
        st.markdown("<div style=\"text-align:center;font-weight:800;margin-bottom:12px\">MONTHLY PROGRESS · PLANNED VS COMPLETED</div>",unsafe_allow_html=True)
        monthly=[]
        available_hist=sorted([k for k in m.available_updates if k!="U38"],key=lambda k:int(k[1:]))
        for newer in [previous,current]:
            older_candidates=[k for k in available_hist if int(k[1:])<int(newer[1:])]
            if not older_candidates:
                continue
            older=older_candidates[-1]
            beginning=pd.to_datetime(m.projects[older].get("last_recalc_date"),errors="coerce")
            ending=pd.to_datetime(m.projects[newer].get("last_recalc_date"),errors="coerce")
            if pd.isna(beginning) or pd.isna(ending):
                continue
            old_df=m.schedules[older]
            new_df=m.schedules[newer]
            from src.nih_model import forecast_finish
            due=forecast_finish(old_df)
            old_done=old_df["Status"].eq("Completed")
            planned=int((~old_done & due.gt(beginning) & due.le(ending)).sum())
            old_ids=set(old_df.loc[old_done,"task_code"].astype(str))
            newly_done=new_df.loc[new_df["Status"].eq("Completed"),"task_code"].astype(str)
            completed=int((~newly_done.isin(old_ids)).sum())
            monthly.append({"Period":beginning.strftime("%b %Y")+" → "+ending.strftime("%b %Y"),
                            "Planned":planned,"Completed":completed})
        if monthly:
            progress=pd.DataFrame(monthly)
            bars=go.Figure()
            for field,color in [("Planned",BLUE),("Completed",ORANGE)]:
                bars.add_trace(go.Bar(x=progress["Period"],y=progress[field],name=field,
                    marker_color=color,text=progress[field],textposition="outside",cliponaxis=False))
            bars.update_layout(barmode="group",height=370,plot_bgcolor="white",
                margin=dict(l=25,r=15,t=30,b=55),yaxis_title="HELIX Activities",
                legend=dict(orientation="h",y=-0.28,x=0))
            bars.update_yaxes(gridcolor=GRID,rangemode="tozero")
            st.plotly_chart(bars,use_container_width=True,config={"displayModeBar":False})

    with st.expander("Diagnostics · NIH HELIX Scope Audit",expanded=False):
        st.dataframe(pd.DataFrame([m.scope_diagnostics()]),use_container_width=True,hide_index=True)

