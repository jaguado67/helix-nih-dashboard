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

def variance_details(model,key,field):
    baseline=scoped(model,"U38")[["task_code","task_name","target_start_date","target_end_date"]].copy()
    if field=="Start":
        bcol="target_start_date"
        choices=["act_start_date","early_start_date","target_start_date"]
    else:
        bcol="target_end_date"
        choices=["act_end_date","reend_date","early_end_date","target_end_date"]
    current=scoped(model,key)
    current=current.drop_duplicates("task_code").set_index("task_code")
    baseline=baseline.drop_duplicates("task_code").set_index("task_code")
    common=baseline.index.intersection(current.index)
    baseline=baseline.loc[common]
    current=current.loc[common]
    planned=pd.to_datetime(baseline[bcol],errors="coerce")
    actual=pd.Series(pd.NaT,index=current.index,dtype="datetime64[ns]")
    if field=="Start":
        complete=current["Status"].isin(["Completed","In Progress"])
        first=pd.to_datetime(current["act_start_date"],errors="coerce")
        actual=actual.where(actual.notna(),first.where(complete))
        for c in choices[1:]:
            actual=actual.where(actual.notna(),pd.to_datetime(current[c],errors="coerce"))
    else:
        if "act_end_date" in current:
            actual=actual.where(actual.notna(),pd.to_datetime(current["act_end_date"],errors="coerce").where(current["Status"].eq("Completed")))
        for c in choices[1:]:
            actual=actual.where(actual.notna(),pd.to_datetime(current[c],errors="coerce"))
    delta=(planned-actual).dt.total_seconds()/86400
    return pd.DataFrame({"Activity ID":common,"Level":baseline["task_name"].map(level_of).values,
        "Activity Type":baseline["task_name"].map(type_of).values,
        "Variance":delta.values}).dropna(subset=["Variance"])

def render_variance(model):
    title("SCHEDULE VARIANCE ANALYSIS")
    updates=history_selection(model,"variance_versions")
    updates=[k for k in updates if k!="U38"]
    if not updates:
        st.info("Select at least one update.")
        return
    chosen=st.selectbox("Heat map update",updates,index=len(updates)-1)
    for mode in ("Start","Finish"):
        details=variance_details(model,chosen,mode)
        if details.empty:
            st.warning(f"No comparable dated activities for {mode}.")
            continue
        st.markdown(f"**{mode.upper()} VARIANCE HEAT MAP · {chosen} VS U38**")
        matrix=details.pivot_table(index="Level",columns="Activity Type",values="Variance",aggfunc="mean")
        order=[x for x in LEVELS+["Others"] if x in matrix.index]
        matrix=matrix.reindex(order)
        fig=go.Figure(go.Heatmap(z=matrix.to_numpy(),x=list(matrix.columns),y=list(matrix.index),
            colorscale=[[0,"#BA1238"],[0.5,"#F6F2CD"],[1,"#12905C"]],zmid=0,
            text=matrix.round(0).astype("Int64").astype(str).replace("<NA>",""),texttemplate="%{text}",
            colorbar=dict(title="Days")))
        fig.update_layout(height=480,margin=dict(l=20,r=30,t=25,b=90),xaxis_title="Activity Type",yaxis_title="Level")
        st.plotly_chart(fig,use_container_width=True)
    st.markdown("**START & FINISH VARIANCE BY LEVEL · HISTORICAL MOVEMENT**")
    for metric in ("Start","Finish"):
        plot=go.Figure()
        for i,key in enumerate(updates):
            data=variance_details(model,key,metric)
            grouped=data.groupby("Level")["Variance"].mean()
            plot.add_trace(go.Scatter(x=LEVELS,y=[grouped.get(level,None) for level in LEVELS],
                name=key,mode="lines+markers",line=dict(color=COLORS[i%len(COLORS)])))
        plot.update_layout(title=f"{metric} Variance vs U38",height=310,plot_bgcolor="white",
            yaxis_title="Calendar Days (negative = later)",legend=dict(orientation="h",y=1.17),
            margin=dict(l=25,r=20,t=65,b=20))
        plot.update_yaxes(gridcolor="#DCE4EC",zeroline=True,zerolinecolor="#999")
        st.plotly_chart(plot,use_container_width=True)
    st.dataframe(variance_details(model,chosen,"Finish").sort_values("Variance"),use_container_width=True,hide_index=True)
