import os, datetime as dt
from pathlib import Path
import streamlit as st

st.set_page_config(page_title='Aegis Status', layout='wide')
st.title('Aegis Trading — System Status')

with st.expander('Environment'):
    st.write({k: os.getenv(k) for k in ['ETRADE_ENV','ETRADE_API_KEY','ETRADE_ACCESS_TOKEN','ETRADE_ACCOUNT_ID']})

try:
    import torch
    gpu_ok = torch.cuda.is_available()
    dev = torch.cuda.get_device_name(0) if gpu_ok else 'CPU-only'
    st.success(f'PyTorch: {torch.__version__} | CUDA: {gpu_ok} | Device: {dev}')
except Exception as e:
    st.error(f'Torch check failed: {e}')

# Last backup status
bdir = Path(r'C:\AITrader\backups')
if bdir.exists():
    zips = sorted(bdir.glob('backup_*.zip'))
    if zips:
        latest = zips[-1]
        ts = dt.datetime.fromtimestamp(latest.stat().st_mtime)
        st.success(f'Last backup: {ts:%Y-%m-%d %H:%M}  —  {latest.name}')
    else:
        st.warning('No backups found yet.')
else:
    st.warning('Backups folder not found.')

st.info('E*TRADE OAuth authorize is currently returning 500 on provider side. App logic, configs, and backups are active.')
