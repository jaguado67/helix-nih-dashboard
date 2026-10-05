from pathlib import Path
import gzip, shutil
import streamlit as st
from src.nih_model import build_model
from src.nih_view import render_dashboard

st.set_page_config(page_title='HELIX · NIH Hospital Dashboard',page_icon='🏥',layout='wide',initial_sidebar_state='collapsed')

def materialize(root:Path):
    runtime=Path('/tmp/helix_nih_data'); runtime.mkdir(parents=True,exist_ok=True)
    for n in range(38,50):
        raw=root/f'U{n}.xer'; gz=root/f'U{n}.xer.gz'; target=runtime/f'U{n}.xer.gz'
        if target.exists():continue
        if gz.exists(): shutil.copy2(gz,target)
        elif raw.exists():
            with open(raw,'rb') as src,gzip.open(target,'wb',compresslevel=6) as dst: shutil.copyfileobj(src,dst)
    return runtime

root=Path(__file__).resolve().parent/'data'
data=materialize(root)
MODEL_VERSION='nih-u38-u49-2026-10-05-v1'
@st.cache_resource(show_spinner='Reading NIH U38–U49 schedules…')
def load_model(path,version):return build_model(Path(path))
try:model=load_model(str(data),MODEL_VERSION)
except Exception as exc:
    st.error(f'NIH dashboard could not be built: {exc}'); st.stop()
render_dashboard(model)
