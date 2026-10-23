from pathlib import Path
import gzip, shutil, base64
import streamlit as st
from src.nih_model import build_model
from src.nih_view import render_dashboard
from src.nih_detail_pages import render_milestones, render_variance

st.set_page_config(page_title='HELIX · NIH Hospital Dashboard',page_icon='🏥',layout='wide',initial_sidebar_state='collapsed')

def materialize(root:Path):
    runtime=Path('/tmp/helix_nih_data'); runtime.mkdir(parents=True,exist_ok=True)
    for n in range(38,101):
        raw=root/f'U{n}.xer'; gz=root/f'U{n}.xer.gz'; target=runtime/f'U{n}.xer'
        if target.exists(): target.unlink()
        if raw.exists():
            shutil.copy2(raw,target)
        elif gz.exists():
            with gzip.open(gz,'rb') as src, open(target,'wb') as dst:
                shutil.copyfileobj(src,dst)
        else:
            parts=sorted(root.glob(f'U{n}.xer.b64.part*'))
            if parts:
                encoded=''.join(p.read_text(encoding='ascii').strip() for p in parts)
                target.write_bytes(base64.b64decode(encoded))
    return runtime

root=Path(__file__).resolve().parent/'data'
data=materialize(root)
MODEL_VERSION='nih-pages-v0.6.2-2026-10-21'
@st.cache_resource(show_spinner='Reading NIH schedules…')
def load_model(path,version):return build_model(Path(path))
try:model=load_model(str(data),MODEL_VERSION)
except Exception as exc:
    st.error(f'NIH dashboard could not be built: {exc}'); st.stop()
if model.current_key == "U49":
    st.info("U50 XER has not been loaded. Showing the latest available schedule: U49.")
st.markdown("""
<style>
[data-testid="stSidebar"] {display:none}
.block-container {max-width:1550px;padding-top:1.35rem}
div[data-testid="stSegmentedControl"] {background:#0B2E52;padding:8px;border-radius:0 0 6px 6px}
div[data-testid="stSegmentedControl"] button {font-weight:700}
[data-testid="stHeader"] {background: #ffffff;}
[data-testid="stMainBlockContainer"] {padding-top: 1.35rem !important;}

.nih-header-row {display:grid;grid-template-columns:minmax(130px,1fr) minmax(0,7fr) minmax(130px,1fr);gap:12px;align-items:stretch;margin:0 0 14px}
.nih-logo-card {min-height:112px;height:auto;border:1px solid #cfdae7;border-radius:7px;background:#fff;display:flex;align-items:center;justify-content:center;padding:10px;box-sizing:border-box}
.nih-logo-card img {display:block;width:100%;max-height:110px;object-fit:contain}
.nih-header-main {min-width:0;min-height:112px;height:auto;border-radius:6px;background:#0B2E52;display:grid;grid-template-columns:minmax(0,1fr) auto;grid-template-areas:"copy tags" "meta meta";align-content:center;align-items:center;column-gap:16px;row-gap:10px;padding:15px 20px;color:white;box-sizing:border-box;overflow:visible}
.nih-header-copy {grid-area:copy;min-width:0}
.nih-header-title {font-size:clamp(17px,1.6vw,22px);font-weight:800;line-height:1.3;overflow-wrap:break-word}
.nih-header-sub {font-size:12px;margin-top:5px;line-height:1.4}
.nih-header-tags {grid-area:tags;display:flex;flex-wrap:wrap;gap:7px;justify-content:flex-end}
.nih-header-tags span {padding:8px;border:1px solid #819ab6;border-radius:5px;font-size:10px;font-weight:800;white-space:nowrap}
.nih-header-date {grid-area:meta;display:flex;flex-wrap:wrap;gap:5px 18px;justify-content:flex-end;font-size:11px;line-height:1.45;text-align:right;white-space:normal}
.nih-header-date > div {min-width:0}
.nih-tabs-wrap {height:0}
div[data-testid="stSegmentedControl"] {background:#fff!important;border:1px solid #cfd9e6;border-radius:8px;padding:14px!important;display:flex;justify-content:center;margin-bottom:15px}
@media(max-width:1100px){.nih-header-row{grid-template-columns:115px minmax(0,1fr) 115px}.nih-header-title{font-size:18px}.nih-header-main{padding:12px 14px}.nih-header-date{justify-content:flex-start;text-align:left}}
@media(max-width:720px){.nih-header-row{grid-template-columns:1fr 1fr}.nih-header-main{grid-column:1/-1;grid-row:1;grid-template-columns:minmax(0,1fr);grid-template-areas:"copy" "tags" "meta"}.nih-header-tags,.nih-header-date{justify-content:flex-start;text-align:left}.nih-logo-card{min-height:74px}.nih-logo-card img{max-height:70px}}
</style>
""",unsafe_allow_html=True)
logo_dir=Path(__file__).resolve().parent/"LOGOS"
def official_logo(filename):
    encoded=logo_dir/(filename+".b64")
    if encoded.exists():
        return base64.b64decode(encoded.read_text(encoding="ascii"))
    path=logo_dir/filename
    return str(path) if path.exists() else None

import html
import pandas as pd

logo_left=official_logo("Helix Electric Horizontral.jpg")
logo_right=official_logo("TORO PMC LOGO 4.png")
def logo_card(logo):
    if logo is None: return ""
    encoded=base64.b64encode(logo if isinstance(logo,bytes) else Path(logo).read_bytes()).decode("ascii")
    mimetype="image/jpeg" if logo is logo_left else "image/png"
    return f'<div class="nih-logo-card"><img src="data:{mimetype};base64,{encoded}" alt="Corporate logo"></div>'

stamp=model.data_date.strftime("%d-%b-%Y") if pd.notna(model.data_date) else "—"
st.markdown(f"""
<div class="nih-header-row">
 {logo_card(logo_left)}
 <div class="nih-header-main">
  <div class="nih-header-copy">
   <div class="nih-header-title">HELIX Project &amp; Portfolio Control Center</div>
   <div class="nih-header-sub">NIH Schedule Performance Dashboard</div>
  </div>
  <div class="nih-header-tags"><span>NIH PROJECT DETAIL</span><span>v0.6</span></div>
  <div class="nih-header-date"><b>Latest Data Date</b> {html.escape(stamp)}<div><b>Current Update</b> {html.escape(model.current_key)}</div><div>Baseline U38 · Previous {html.escape(model.previous_key)}</div></div>
 </div>
 {logo_card(logo_right)}
</div>
""",unsafe_allow_html=True)
st.markdown('<div class="nih-tabs-wrap">',unsafe_allow_html=True)
page=st.segmented_control("NIH Dashboard",["Project Overview","Milestones & Energization","Schedule Variance Analysis"],default="Project Overview",key="nih_page",label_visibility="collapsed") or "Project Overview"
st.markdown('</div>',unsafe_allow_html=True)
if page=="Project Overview":
    render_dashboard(model)
elif page=="Milestones & Energization":
    render_milestones(model)
else:
    render_variance(model)
