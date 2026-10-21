import re
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from src.nih_model import forecast_finish

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

def render_milestones(model):
    title("KEY PROJECT MILESTONES")
    updates=history_selection(model,"milestone_versions")
    if not updates:
        st.info("Select at least one update.")
        return
    rows=[]
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
        row["Variance (calendar days)"]=int((base.normalize()-last.normalize()).days) if pd.notna(base) and pd.notna(last) else None
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
    panels=current[names.str.contains(r"panels? ready to energize|energiz(?:e|ation).*panel",case=False,regex=True)].copy()
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
        record["Variance (calendar days)"]=int((baseline.normalize()-current_date.normalize()).days) if pd.notna(baseline) and pd.notna(current_date) else None
        record["Status"]=activity.get("Status","")
        rows.append(record)
    st.dataframe(pd.DataFrame(rows),use_container_width=True,hide_index=True,height=550)

def level_of(name):
    text=str(name).upper()
    m=re.search(r"(?<![A-Z0-9])(B[12]|L[1-9])(?![A-Z0-9])",text)
    return m.group(1) if m else "Others"

def type_of(name):
    text=str(name).lower()
    for label,words in [
        ("Cans/Troughs/XFMRs",["transformer","xfmr","trough","can "]),
        ("Conduits",["conduit"]),
        ("Elev. Pri. Conduit",["elevator primary conduit"]),
        ("Pull Wire",["pull wire","wire pulling","pull cable"]),
        ("Risers + OH",["riser","overhead"])]:
        if any(w in text for w in words):
            return label
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
    c1,c2=st.columns(2)
    with c1:
        previous=st.selectbox("Previous Update",available,index=available.index(model.previous_key))
    with c2:
        current=st.selectbox("Current Update",available,index=available.index(model.current_key))
    if int(previous[1:])>=int(current[1:]):
        st.warning("Select a Current Update later than the Previous Update.")
        return
    categories=["Cans/Troughs/XFMRs","Conduits","Elev. Pri. Conduit","Other","Pull Wire","Risers + OH"]
    levels=["L9","L8","L7","L6","L5","L4","L3","L2","L1","B1","B2","Others"]
    for metric in ("Start","Finish"):
        details=variance_details(model,previous,current,metric)
        st.markdown(f"**{metric.upper()} VARIANCE HEAT MAP · {previous} → {current}**")
        if details.empty:
            st.info("No comparable activities with valid dates.")
            continue
        matrix=details.pivot_table(index="Level",columns="Activity Type",values="Variance",aggfunc="mean")
        matrix=matrix.reindex(index=levels,columns=categories)
        z=matrix.to_numpy()
        maxabs=max(1.0,float(abs(details["Variance"]).quantile(0.95)))
        labels=matrix.apply(lambda column:column.map(lambda value: "" if pd.isna(value) else f"{value:+.0f}"))
        heat=go.Figure(go.Heatmap(
            x=categories,y=levels,z=z,
            zmin=-maxabs,zmax=maxabs,zmid=0,
            colorscale=[[0.0,"#B50932"],[0.25,"#F36A43"],[0.5,"#F7E9B0"],[0.75,"#BDE36F"],[1,"#147E47"]],
            text=labels.to_numpy(),texttemplate="%{text}",
            textfont=dict(size=12,color="#162333"),
            xgap=2,ygap=2,
            hovertemplate="Level: %{y}<br>Type: %{x}<br>Mean variance: %{z:.1f} calendar days<extra></extra>",
            colorbar=dict(title="Calendar days")))
        heat.update_layout(height=550,margin=dict(l=60,r=35,t=20,b=80),
            xaxis_title="Activity Type",yaxis_title="Level",yaxis=dict(autorange="reversed"),
            plot_bgcolor="#D3D3D3")
        st.plotly_chart(heat,use_container_width=True)
    title("HISTORICAL START & FINISH VARIANCE BY LEVEL · VS U38")
    history=[k for k in ["U45","U46","U47","U48","U49","U50"] if k in available]
    chosen_history=st.multiselect("Historical updates",available,default=history,key="nih_variance_history")
    for metric in ("Start","Finish"):
        fig=go.Figure()
        summary={"Level":LEVELS}
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
