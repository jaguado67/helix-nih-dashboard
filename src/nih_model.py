from pathlib import Path
from dataclasses import dataclass
import pandas as pd
import numpy as np

WANTED={"PROJECT","TASK"}

def parse_xer(path:Path):
    tables={k:[] for k in WANTED}; cur=None; fields=[]
    with open(path,"r",encoding="cp1252",errors="ignore") as f:
        for line in f:
            p=line.rstrip("\r\n").split("\t")
            if not p: continue
            if p[0]=="%T":
                cur=p[1]; fields=[]
            elif p[0]=="%F" and cur in WANTED:
                fields=p[1:]
            elif p[0]=="%R" and cur in WANTED:
                tables[cur].append(dict(zip(fields,p[1:])))
    return tables

def task_frame(rows):
    df=pd.DataFrame(rows)
    for c in ["target_start_date","target_end_date","early_start_date","early_end_date","act_start_date","act_end_date","reend_date"]:
        if c in df: df[c]=pd.to_datetime(df[c],errors="coerce")
    for c in ["target_drtn_hr_cnt","remain_drtn_hr_cnt","phys_complete_pct","total_float_hr_cnt"]:
        if c in df: df[c]=pd.to_numeric(df[c],errors="coerce")
    mp={"TK_Complete":"Completed","TK_Active":"In Progress","TK_NotStart":"Not Started"}
    df["Status"]=df.get("status_code",pd.Series("",index=df.index)).map(mp).fillna("Unknown")
    return df

def pdate(row,*cols):
    for c in cols:
        x=pd.to_datetime(row.get(c),errors="coerce")
        if pd.notna(x): return pd.Timestamp(x)
    return pd.NaT

def finish_series(df):
    out=pd.Series(pd.NaT,index=df.index,dtype="datetime64[ns]")
    for c in ["act_end_date","reend_date","early_end_date","target_end_date"]:
        if c in df:
            s=pd.to_datetime(df[c],errors="coerce")
            out=out.where(out.notna(),s)
    return out

@dataclass
class NIHModel:
    schedules:dict
    projects:dict

    @property
    def baseline(self): return self.schedules["U38"]
    @property
    def previous(self): return self.schedules["U48"]
    @property
    def current(self): return self.schedules["U49"]
    @property
    def baseline_project(self): return self.projects["U38"]
    @property
    def current_project(self): return self.projects["U49"]

    @property
    def baseline_finish(self): return pdate(self.baseline_project,"scd_end_date","plan_end_date")
    @property
    def current_finish(self): return pdate(self.current_project,"scd_end_date","plan_end_date")
    @property
    def data_date(self): return pdate(self.current_project,"last_recalc_date","data_date","last_schedule_date")
    @property
    def finish_shift(self):
        if pd.notna(self.baseline_finish) and pd.notna(self.current_finish):
            return int((self.baseline_finish.normalize()-self.current_finish.normalize()).days)
        return None

    def status_counts(self,key="U49"):
        df=self.schedules[key]; vc=df["Status"].value_counts()
        return {"Total":len(df),"Completed":int(vc.get("Completed",0)),"In Progress":int(vc.get("In Progress",0)),"Not Started":int(vc.get("Not Started",0))}

    def scurve(self):
        b=finish_series(self.baseline); c=finish_series(self.current)
        vals=pd.concat([b.dropna(),c.dropna()])
        if vals.empty:return pd.DataFrame()
        idx=pd.date_range(vals.min().normalize(),vals.max().normalize(),freq="MS")
        rows=[]
        for d in idx:
            e=d+pd.offsets.MonthEnd(0)
            rows.append({"Date":d,"Baseline U38":int((b<=e).sum()),"Current U49":int((c<=e).sum())})
        return pd.DataFrame(rows)

    def update_trend(self):
        rows=[]
        for k in sorted(self.schedules,key=lambda x:int(x[1:])):
            df=self.schedules[k]; pr=self.projects[k]; vc=df["Status"].value_counts()
            finish=pdate(pr,"scd_end_date","plan_end_date")
            dd=pdate(pr,"last_recalc_date","data_date","last_schedule_date")
            rows.append({"Update":k,"Data Date":dd,"Forecast Finish":finish,"Total":len(df),"Completed":int(vc.get("Completed",0)),"In Progress":int(vc.get("In Progress",0)),"Not Started":int(vc.get("Not Started",0))})
        return pd.DataFrame(rows)

    def scope_diagnostics(self):
        b=set(self.baseline.get("task_code",pd.Series(dtype=str)).astype(str))
        c=set(self.current.get("task_code",pd.Series(dtype=str)).astype(str))
        return {"Baseline Activities":len(self.baseline),"Current Activities":len(self.current),"Matched Activity IDs":len(b&c),"Current-only IDs":len(c-b),"Baseline-only IDs":len(b-c)}

def build_model(data_dir:Path):
    schedules={}; projects={}
    for n in range(38,50):
        key=f"U{n}"; p=data_dir/f"{key}.xer"
        if not p.exists(): continue
        t=parse_xer(p)
        schedules[key]=task_frame(t["TASK"])
        projects[key]=pd.Series(t["PROJECT"][0]) if t["PROJECT"] else pd.Series(dtype=object)
    missing=[k for k in ("U38","U48","U49") if k not in schedules]
    if missing: raise ValueError("Missing required schedules: "+", ".join(missing))
    return NIHModel(schedules,projects)
