import re
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from src.nih_model import forecast_finish
from src.north_elevation_heatmap import build_north_elevation

NAVY="#0B2E52"
LEVELS=["B2","B1"]+[f"L{i}" for i in range(1,10)]
MILESTONES=["EXS.130","P2.SUM.235","P2.SUM.245","P2.SUM.225","EXS.140"]
COLORS=["#3568A6","#E4572E","#159B77","#8064A2","#A47B23","#C64B68","#1D7990"]

def date_text(value):
    return pd.Timestamp(value).strftime("%d-%b-%Y") if pd.notna(value) else "—"

def frame(model,key):
    return model.raw_schedules[key].copy()

def scoped(model,key):
    # Stable HELIX IDs, including exports with incomplete activity-code dictionaries
    base_ids=set(model.schedules["U38"]["task_code"].astype(str))
    current_ids=set(model.current["task_code"].astype(str))
    ids=base_ids|current_ids|set(model.native_scopes[key]["task_code"].astype(str))
    df=frame(model,key)
    return df[df["task_code"].astype(str).isin(ids)].copy()

def finish_by_code(model,key,code):
    rows=frame(model,key)
    rows=rows[rows["task_code"].astype(str).eq(code)]
    return forecast_finish(rows).iloc[0] if not rows.empty else pd.NaT

def history_selection(model,prefix,default=None):
    options=model.available_updates
    defaults=[k for k in (default or ["U38","U45","U46","U47","U48","U49","U50"]) if k in options]
    return st.multiselect("Schedule updates",options,default=defaults,
        format_func=lambda k:k if k=="U38" else f"{pd.to_datetime(model.projects[k].get('last_recalc_date'),errors='coerce').strftime('%b %Y') if pd.notna(pd.to_datetime(model.projects[k].get('last_recalc_date'),errors='coerce')) else k} ({k})",
        key=prefix)

def title(text):
    st.markdown(f'<div style="background:#0B2E52;color:white;padding:12px 16px;font-weight:800;font-size:17px">{text}</div>',unsafe_allow_html=True)

from functools import lru_cache

@lru_cache(maxsize=12)
def _calendar_catalog(root,key):
    """Read the activity calendar and exceptions from its P6 XER snapshot."""
    import re
    from datetime import timedelta
    path=root/f"{key}.xer"
    if not path.exists():
        return None
    table=None
    columns=[]
    task_calendars={}
    calendars={}
    with path.open(encoding="cp1252",errors="ignore") as stream:
        for line in stream:
            parts=line.rstrip("\r\n").split("\t")
            if parts[0]=="%T":
                table=parts[1] if len(parts)>1 else None
            elif parts[0]=="%F":
                columns=parts[1:]
            elif parts[0]=="%R" and table in ("TASK","CALENDAR"):
                row=dict(zip(columns,parts[1:]))
                if table=="TASK":
                    task_calendars[row.get("task_code")]=row.get("clndr_id")
                if table=="CALENDAR":
                    calendars[row.get("clndr_id")]=row
    parsed={}
    for cal_id,c in calendars.items():
        parsed[cal_id]=_parse_calendar_data(c)
    return task_calendars,parsed

def _parse_calendar_data(c):
    raw=c.get("clndr_data","")
    days_section=raw.split("DaysOfWeek()",1)[-1].split("Exceptions()",1)[0]
    workdays=set()
    days=list(re.finditer(r"\(0\|\|([1-7])\(\)\(",days_section))
    for idx,match in enumerate(days):
        fragment=days_section[match.end():days[idx+1].start() if idx+1<len(days) else len(days_section)]
        if "s|" in fragment:
            workdays.add((int(match.group(1))+5)%7)  # P6: 1=Sunday, 2=Monday
    if not workdays:
        workdays=set(range(7)) if "7D" in c.get("clndr_name","") else set(range(5))
    exception_text=raw.split("Exceptions()",1)[-1]
    entries=list(re.finditer(r"\(0\|\|\d+\(d\|(\d+)\)",exception_text))
    overrides={}
    base=pd.Timestamp("1899-12-30")
    for idx,match in enumerate(entries):
        segment=exception_text[match.end():entries[idx+1].start() if idx+1<len(entries) else len(exception_text)]
        date=(base+pd.Timedelta(days=int(match.group(1)))).date()
        overrides[date]="s|" in segment
    return workdays,overrides

def _milestone_calendar(root,key,code):
    catalog=_calendar_catalog(root,key)
    if catalog is None:
        return None
    task_calendars,calendars=catalog
    return calendars.get(task_calendars.get(code))

def _workday_shift(baseline,current,calendar):
    if pd.isna(baseline) or pd.isna(current) or calendar is None:
        return None
    start=pd.Timestamp(baseline).normalize()
    finish=pd.Timestamp(current).normalize()
    if start==finish:
        return 0
    direction=-1 if finish>start else 1
    left,right=(start,finish) if finish>start else (finish,start)
    weekdays,overrides=calendar
    dates=pd.date_range(left+pd.Timedelta(days=1),right,freq="D")
    return direction*sum(overrides.get(day.date(),day.weekday() in weekdays) for day in dates)

def render_milestones(model):
    title("KEY PROJECT MILESTONES")
    updates=history_selection(model,"milestone_versions")
    if not updates:
        st.info("Select at least one update.")
        return
    rows=[]
    from pathlib import Path
    calendar_root=Path("/tmp/helix_nih_data")
    for code in MILESTONES:
        names=frame(model,model.current_key)
        hit=names[names["task_code"].astype(str).eq(code)]
        if hit.empty:
            continue
        row={"Activity ID":code,"Milestone":str(hit.iloc[0].get("task_name",""))}
        base=finish_by_code(model,"U38",code)
        for key in updates:
            row[key]=date_text(finish_by_code(model,key,code))
        last=finish_by_code(model,model.current_key,code)
        activity_calendar=_milestone_calendar(calendar_root,model.current_key,code)
        row["Variance (working days)"]=_workday_shift(base,last,activity_calendar)
        rows.append(row)
    if rows:
        df=pd.DataFrame(rows)
        st.dataframe(df,use_container_width=True,hide_index=True)
        fig=go.Figure()
        for i,r in enumerate(rows):
            ys=[finish_by_code(model,key,r["Activity ID"]) for key in updates]
            fig.add_trace(go.Scatter(x=updates,y=ys,name=r["Activity ID"],mode="lines+markers",
                line=dict(color=COLORS[i%len(COLORS)],width=2),connectgaps=False))
        fig.update_layout(height=440,plot_bgcolor="white",legend=dict(orientation="h",y=1.15),
            yaxis_title="Forecast Finish",xaxis_title="Schedule Update",margin=dict(l=20,r=20,t=60,b=25))
        fig.update_yaxes(gridcolor="#DCE4EC")
        st.plotly_chart(fig,use_container_width=True)
    title("HELIX PANEL ENERGIZATION DATES")
    current=scoped(model,model.current_key)
    names=current["task_name"].fillna("").astype(str)
    panels=current[names.str.contains(r"panels?\s+ready\s+to\s+energize\s*-\s*lock\s+doors\s+and\s+limit\s+access",case=False,regex=True)].copy()
    if panels.empty:
        st.info("No panel energization activities matched the configured names.")
        return
    panels["Level"]=panels["task_name"].fillna("").astype(str).apply(level_of)
    rows=[]
    for _,activity in panels.sort_values(["Level","task_code"]).iterrows():
        code=str(activity["task_code"])
        baseline=finish_by_code(model,"U38",code)
        current_date=finish_by_code(model,model.current_key,code)
        record={"Level":activity["Level"],"Activity ID":code,"Activity Name":activity["task_name"]}
        for key in updates:
            record[key]=date_text(finish_by_code(model,key,code))
        calendar=_milestone_calendar(Path("/tmp/helix_nih_data"),model.current_key,code)
        record["Variance (working days)"]=_workday_shift(baseline,current_date,calendar)
        record["Status"]=activity.get("Status","")
        rows.append(record)
    energization=pd.DataFrame(rows)
    latest_four=sorted([key for key in model.available_updates if key!="U38"],key=lambda x:int(x[1:]))[-4:]
    display_columns=["Level","Activity ID","Activity Name","U38"]+latest_four+["Variance (working days)","Status"]
    for col in display_columns:
        if col not in energization:
            energization[col]="—"
    energization=energization[display_columns]
    def status_color(value):
        return {"Completed":"background-color:#DDF3E5;color:#126A38;font-weight:700",
                "Not Started":"background-color:#FCE2E2;color:#AA2525;font-weight:700",
                "In Progress":"background-color:#FFF0D4;color:#936000;font-weight:700"}.get(str(value),"")
    def variance_color(value):
        if pd.isna(value): return ""
        return ("color:#BC2929;font-weight:700" if value<0 else
                "color:#157E43;font-weight:700" if value>0 else "color:#64748B")
    styled=(energization.style.map(status_color,subset=["Status"])
            .map(variance_color,subset=["Variance (working days)"]))
    st.dataframe(styled,use_container_width=True,hide_index=True,height=550,
        column_config={"Activity Name":st.column_config.TextColumn(width="large"),
                       "Activity ID":st.column_config.TextColumn(width="medium")})

def level_of(name):
    text=str(name).upper()
    m=re.search(r"(?<![A-Z0-9])(B[12]|L[1-9])(?![A-Z0-9])",text)
    return m.group(1) if m else "Others"

def type_of(name):
    text=str(name).lower()
    # Categories are mutually exclusive; prioritize recognizable disciplines.
    if "fire alarm" in text or "fa device" in text:
        return "Fire Alarm"
    if "panel" in text or "switchboard" in text:
        return "Panels"
    if any(w in text for w in ("transformer","xfmr","trough","can ")):
        return "Cans/Troughs/XFMRs"
    if "conduit" in text:
        return "Conduits"
    if any(w in text for w in ("pull wire","wire pulling","pull cable")):
        return "Pull Wire"
    return "Other"

def variance_details(model,previous_key,current_key,field):
    prior=scoped(model,previous_key).drop_duplicates("task_code").set_index("task_code")
    current=scoped(model,current_key).drop_duplicates("task_code").set_index("task_code")
    ids=prior.index.intersection(current.index)
    prior=prior.loc[ids]
    current=current.loc[ids]
    columns=(["act_start_date","early_start_date","target_start_date"] if field=="Start"
             else ["act_end_date","reend_date","early_end_date","target_end_date"])
    def choose(df):
        series=pd.Series(pd.NaT,index=df.index,dtype="datetime64[ns]")
        for column in columns:
            if column in df:
                values=pd.to_datetime(df[column],errors="coerce")
                if column=="act_end_date":
                    values=values.where(df["Status"].eq("Completed"))
                if column=="act_start_date":
                    values=values.where(df["Status"].isin(["Completed","In Progress"]))
                series=series.where(series.notna(),values)
        return series
    before=choose(prior)
    after=choose(current)
    days=(before-after).dt.total_seconds()/86400
    return pd.DataFrame({"Activity ID":ids,
        "Level":prior["task_name"].map(level_of).values,
        "Activity Type":prior["task_name"].map(type_of).values,
        "Variance":days.values}).dropna(subset=["Variance"])

def render_variance(model):
    title("SCHEDULE VARIANCE ANALYSIS")
    available=[k for k in model.available_updates if k!="U38"]
    # Allow the original U38 baseline as the reference for any later update.
    previous_options=["U38"]+available
    c1,c2=st.columns(2)
    with c1:
        previous=st.selectbox("Previous Update",previous_options,
                              index=previous_options.index(model.previous_key))
    with c2:
        current=st.selectbox("Current Update",available,index=available.index(model.current_key))
    if int(previous[1:])>=int(current[1:]):
        st.warning("Select a Current Update later than the Previous Update.")
        return
    categories=["Cans/Troughs/XFMRs","Conduits","Fire Alarm","Other","Pull Wire","Panels"]
    for metric in ("Start","Finish"):
        details=variance_details(model,previous,current,metric)
        if details.empty:
            st.info(f"No comparable {metric.lower()} dates.")
            continue
        figure=go.Figure(build_north_elevation(
            details,level_col="Level",type_col="Activity Type",
            value_col="Variance",
            title=f"{metric.upper()} VARIANCE · {previous} → {current}",
            type_order=categories,unit="calendar days",height=1000))
        st.plotly_chart(figure,use_container_width=True,config={"displayModeBar":False})
    title("HISTORICAL START & FINISH VARIANCE BY LEVEL · VS U38")
    history=[k for k in ["U45","U46","U47","U48","U49","U50"] if k in available]
    chosen_history=st.multiselect("Historical updates",available,default=history,key="nih_variance_history")
    for metric in ("Start","Finish"):
        fig=go.Figure()
        summary={"Level":LEVELS,"U38":[0]*len(LEVELS)}
        fig.add_trace(go.Scatter(x=LEVELS,y=[0]*len(LEVELS),name="U38",mode="lines+markers",
            line=dict(width=3,color="#1F2937"),marker=dict(size=6,color="#1F2937")))
        for i,key in enumerate(chosen_history):
            data=variance_details(model,"U38",key,metric)
            means=data.groupby("Level")["Variance"].mean()
            values=[round(float(means.get(level)),1) if pd.notna(means.get(level)) else None for level in LEVELS]
            summary[key]=values
            fig.add_trace(go.Scatter(x=LEVELS,y=values,name=key,mode="lines+markers",
                line=dict(width=2.5,color=COLORS[i%len(COLORS)])))
        fig.update_layout(title=f"{metric.upper()} VARIANCE BY LEVEL · U38 BASELINE",
            height=420,plot_bgcolor="white",yaxis_title="Calendar Days · negative means later",
            legend=dict(orientation="h",y=1.04,x=0,yanchor="bottom"),margin=dict(l=45,r=25,t=115,b=35))
        fig.update_yaxes(gridcolor="#DCE4EC",zeroline=True,zerolinecolor="#7C8797")
        st.plotly_chart(fig,use_container_width=True)
        st.dataframe(pd.DataFrame(summary),use_container_width=True,hide_index=True)
    with st.expander("Activity Variance Details",expanded=False):
        detail=variance_details(model,previous,current,"Finish")
        st.dataframe(detail.sort_values("Variance"),use_container_width=True,hide_index=True)
