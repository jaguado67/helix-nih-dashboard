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
.block-container {max-width:1550px;padding-top:3.3rem}
div[data-testid="stSegmentedControl"] {background:#0B2E52;padding:8px;border-radius:0 0 6px 6px}
div[data-testid="stSegmentedControl"] button {font-weight:700}
[data-testid="stHeader"] {background: #ffffff;}
[data-testid="stMainBlockContainer"] {padding-top: 3.3rem !important;}
</style>
""",unsafe_allow_html=True)
logo_dir=Path(__file__).resolve().parent/"LOGOS"
def official_logo(filename):
    encoded=logo_dir/(filename+".b64")
    if encoded.exists():
        return base64.b64decode(encoded.read_text(encoding="ascii"))
    path=logo_dir/filename
    return str(path) if path.exists() else None

left,center,right=st.columns([1.15,5,1.15],vertical_alignment="center")
with left:
    logo=official_logo("Helix Electric Horizontral.jpg")
    if logo: st.image(logo,use_container_width=True)
with center:
    st.markdown("""<div style="background:#0B2E52;color:white;padding:27px 24px;min-height:115px;box-sizing:border-box;border-radius:5px">
       <div style="font-size:21px;line-height:1.4;font-weight:800">HELIX Project &amp; Portfolio Control Center</div>
       <div style="font-size:12px;margin-top:4px">NIH Schedule Performance Dashboard</div>
    </div>""",unsafe_allow_html=True)
with right:
    logo=official_logo("TORO PMC LOGO 4.png")
    if logo: st.image(logo,use_container_width=True)
st.markdown(f"""<div style="background:#eef3f8;color:#163b60;padding:9px 14px;font-weight:700;font-size:12px">
BASELINE · U38 &nbsp;&nbsp; | &nbsp;&nbsp; PREVIOUS · {model.previous_key}
&nbsp;&nbsp; | &nbsp;&nbsp; CURRENT · {model.current_key}
&nbsp;&nbsp; | &nbsp;&nbsp; DATA DATE · {model.data_date.strftime('%d-%b-%Y') if model.data_date is not None and not __import__('pandas').isna(model.data_date) else '—'}
</div>""",unsafe_allow_html=True)
page=st.segmented_control("NIH Dashboard",["Project Overview","Milestones & Energization","Schedule Variance Analysis"],default="Project Overview",key="nih_page",label_visibility="collapsed") or "Project Overview"
if page=="Project Overview":
    render_dashboard(model)
elif page=="Milestones & Energization":
    render_milestones(model)
else:
    render_variance(model)
