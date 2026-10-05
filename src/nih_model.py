from pathlib import Path
from dataclasses import dataclass
import pandas as pd
import numpy as np

WANTED={"PROJECT","TASK","ACTVTYPE","ACTVCODE","TASKACTV"}
HELIX_CODE_TYPE="Resp | SRLM"
KEY_MILESTONE="EXS.130"


def parse_xer(path:Path):
    tables={k:[] for k in WANTED}; cur=None; fields={}
    with open(path,"r",encoding="cp1252",errors="ignore") as f:
        for line in f:
            p=line.rstrip("\r\n").split("\t")
            if not p: continue
            if p[0]=="%T":
                cur=p[1] if len(p)>1 else None
            elif p[0]=="%F" and cur in WANTED:
                fields[cur]=p[1:]
            elif p[0]=="%R" and cur in WANTED and cur in fields:
                vals=p[1:]; cols=fields[cur]
                if len(vals)<len(cols): vals += [""]*(len(cols)-len(vals))
                tables[cur].append(vals[:len(cols)])
    return {k:pd.DataFrame(v,columns=fields.get(k,[])) for k,v in tables.items()}


def task_frame(df):
    df=df.copy()
    for c in ["target_start_date","target_end_date","early_start_date","early_end_date","act_start_date","act_end_date","reend_date"]:
        if c in df: df[c]=pd.to_datetime(df[c],errors="coerce")
    for c in ["target_drtn_hr_cnt","remain_drtn_hr_cnt","phys_complete_pct","total_float_hr_cnt"]:
        if c in df: df[c]=pd.to_numeric(df[c],errors="coerce")
    mp={"TK_Complete":"Completed","TK_Active":"In Progress","TK_NotStart":"Not Started"}
    df["Status"]=df.get("status_code",pd.Series("",index=df.index)).map(mp).fillna("Unknown")
    return df


def _normal(x): return str(x or "").strip().casefold()


def helix_task_codes(tables):
    at=tables.get("ACTVTYPE",pd.DataFrame()); ac=tables.get("ACTVCODE",pd.DataFrame())
    ta=tables.get("TASKACTV",pd.DataFrame()); task=tables.get("TASK",pd.DataFrame())
    if any(x.empty for x in [at,ac,ta,task]): return set()
    types=at[at.get("actv_code_type",pd.Series(index=at.index,dtype=object)).astype(str).str.strip().str.casefold().eq(_normal(HELIX_CODE_TYPE))]
    type_ids=set(types.get("actv_code_type_id",pd.Series(dtype=object)).astype(str))
    if not type_ids: return set()
    codes=ac.copy()
    codes["actv_code_id"]=codes["actv_code_id"].astype(str)
    codes["parent_actv_code_id"]=codes.get("parent_actv_code_id",pd.Series(index=codes.index,dtype=object)).astype(str)
    codes["actv_code_type_id"]=codes["actv_code_type_id"].astype(str)
    codes=codes[codes["actv_code_type_id"].isin(type_ids)].copy()
    helix=set(codes[codes.get("actv_code_name",pd.Series(index=codes.index,dtype=object)).astype(str).str.contains(r"\bHelix\b",case=False,na=False,regex=True)]["actv_code_id"].astype(str))
    while helix:
        children=set(codes[codes["parent_actv_code_id"].isin(helix)]["actv_code_id"].astype(str))-helix
        if not children: break
        helix|=children
    task_ids=set(ta[ta.get("actv_code_id",pd.Series(index=ta.index,dtype=object)).astype(str).isin(helix)].get("task_id",pd.Series(dtype=object)).astype(str))
    return set(task[task.get("task_id",pd.Series(index=task.index,dtype=object)).astype(str).isin(task_ids)].get("task_code",pd.Series(dtype=object)).astype(str))


def pdate(row,*cols):
    for c in cols:
        x=pd.to_datetime(row.get(c),errors="coerce")
        if pd.notna(x): return pd.Timestamp(x)
    return pd.NaT


def forecast_finish(df):
    out=pd.Series(pd.NaT,index=df.index,dtype="datetime64[ns]")
    for c in ["act_end_date","reend_date","early_end_date","target_end_date"]:
        if c in df:
            s=pd.to_datetime(df[c],errors="coerce")
            out=out.where(out.notna(),s)
    return out


def milestone_date(df,code):
    r=df[df.get("task_code",pd.Series(index=df.index,dtype=object)).astype(str).str.strip().eq(code)]
    if r.empty: return pd.NaT
    return forecast_finish(r).iloc[0]


@dataclass
class NIHModel:
    schedules:dict
    raw_schedules:dict
    projects:dict
    scope_codes:set

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
    def data_date(self): return pdate(self.current_project,"last_recalc_date","data_date","last_schedule_date")
    @property
    def baseline_finish(self): return milestone_date(self.raw_schedules["U38"],KEY_MILESTONE)
    @property
    def current_finish(self): return milestone_date(self.raw_schedules["U49"],KEY_MILESTONE)
    @property
    def finish_shift(self):
        if pd.notna(self.baseline_finish) and pd.notna(self.current_finish):
            return int((self.baseline_finish.normalize()-self.current_finish.normalize()).days)
        return None

    def status_counts(self,key="U49"):
        df=self.schedules[key]; vc=df["Status"].value_counts()
        return {"Total":len(df),"Completed":int(vc.get("Completed",0)),"In Progress":int(vc.get("In Progress",0)),"Not Started":int(vc.get("Not Started",0))}

    def status_percentages(self,key="U49"):
        c=self.status_counts(key); n=c["Total"] or 1
        return {k+" %":100*c[k]/n for k in ["Completed","In Progress","Not Started"]}

    def scurve(self):
        b=self.baseline.copy(); c=self.current.copy(); dd=self.data_date
        bfin=pd.to_datetime(b.get("target_end_date"),errors="coerce")
        cfin=forecast_finish(c)
        afin=pd.to_datetime(c.get("act_end_date"),errors="coerce")
        vals=pd.concat([bfin.dropna(),cfin.dropna()])
        if vals.empty:return pd.DataFrame()
        start=vals.min().to_period("M").to_timestamp(); end=vals.max().to_period("M").to_timestamp()
        idx=pd.date_range(start,end,freq="MS")
        rows=[]
        for d in idx:
            e=d+pd.offsets.MonthEnd(0)
            rows.append({
                "Date":d,
                "Baseline (U38)":int((bfin<=e).sum()),
                "Planned / Forecast (U49)":int((cfin<=e).sum()),
                "Actual":int((afin<=min(e,dd)).sum()) if pd.notna(dd) else int((afin<=e).sum()),
            })
        return pd.DataFrame(rows)

    def scope_diagnostics(self):
        return {
            "HELIX Filter":"Resp | SRLM → Helix | Electrical / Helix | Fire Alarm",
            "U49 HELIX Activities":len(self.current),
            "U49 Raw Activities":len(self.raw_schedules["U49"]),
            "HELIX Activity IDs":len(self.scope_codes),
            "Baseline U38 Matches":len(self.baseline),
            "Previous U48 Matches":len(self.previous),
        }


def build_model(data_dir:Path):
    tables={}; projects={}; raw={}
    for n in range(38,50):
        key=f"U{n}"; p=data_dir/f"{key}.xer"
        if not p.exists(): continue
        t=parse_xer(p); tables[key]=t
        raw[key]=task_frame(t["TASK"])
        projects[key]=pd.Series(t["PROJECT"].iloc[0]) if not t["PROJECT"].empty else pd.Series(dtype=object)
    missing=[k for k in ("U38","U48","U49") if k not in tables]
    if missing: raise ValueError("Missing required schedules: "+", ".join(missing))

    scope=helix_task_codes(tables["U49"])
    if not scope: raise ValueError("HELIX scope was not found under Resp | SRLM in U49.")
    schedules={}
    for key,df in raw.items():
        schedules[key]=df[df.get("task_code",pd.Series(index=df.index,dtype=object)).astype(str).isin(scope)].copy()
    return NIHModel(schedules,raw,projects,scope)
