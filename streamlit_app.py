# streamlit_app.py

import os
import streamlit as st
import pandas as pd
import requests
from pathlib import Path

st.set_page_config(
    page_title="Căutare firme după CUI (Drive + local)",
    layout="wide",
)
st.title("🔎 Căutare firme după CUI")

# —————————————————————————————————————————————
# 1) Configurare Google Drive pentru fișierul mare
DRIVE_ID_LARGE = "1xfyW-Y8JhpGG2lTP6YcdC6kHuk7DBz3A"  # ← pune ID-ul tău aici
LOCAL_LARGE_PATH = Path("/mnt/data/web_uu_an2024_convertit.csv")
DOWNLOAD_URL = "https://docs.google.com/uc?export=download"

def get_confirm_token(response):
    for key, value in response.cookies.items():
        if key.startswith("download_warning"):
            return value
    return None

def download_file_from_google_drive(file_id: str, destination: Path):
    session = requests.Session()
    res = session.get(DOWNLOAD_URL, params={"id": file_id}, stream=True)
    token = get_confirm_token(res)
    if token:
        res = session.get(
            DOWNLOAD_URL,
            params={"id": file_id, "confirm": token},
            stream=True
        )
    with open(destination, "wb") as f:
        for chunk in res.iter_content(32768):
            if chunk:
                f.write(chunk)

@st.cache_data(show_spinner=True)
def load_large_csv() -> pd.DataFrame:
    if not LOCAL_LARGE_PATH.exists():
        st.info("🔄 Descarcă fișierul mare de pe Drive (75 MB)…")
        download_file_from_google_drive(DRIVE_ID_LARGE, LOCAL_LARGE_PATH)
    return pd.read_csv(LOCAL_LARGE_PATH, dtype=str, low_memory=False)

# —————————————————————————————————————————————
# 2) Încarcă CSV-ul mare + CSV-ul mic din folderul `data/`
df_large = load_large_csv()
st.info(f"✔️  Fișier mare încărcat: {df_large.shape[0]} rânduri × {df_large.shape[1]} coloane")

DATA_DIR = Path(__file__).parent / "data"
SMALL_CSV_NAME = "web_bl_bs_sl_an2024_convertit.csv"
small_path = DATA_DIR / SMALL_CSV_NAME

if small_path.exists():
    df_small = pd.read_csv(small_path, dtype=str, low_memory=False)
    st.info(f"✔️  Fișier mic încărcat:  {df_small.shape[0]} rânduri × {df_small.shape[1]} coloane")
    df = pd.concat([df_large, df_small], ignore_index=True)
else:
    st.warning(f"Fișierul mic `{SMALL_CSV_NAME}` nu a fost găsit în `{DATA_DIR}`; folosesc doar CSV-ul mare.")
    df = df_large

st.success(f"✅ Total date: {df.shape[0]} rânduri × {df.shape[1]} coloane")

# —————————————————————————————————————————————
# 3) Verifică existența coloanei CUI
if "CUI" not in df.columns:
    st.error("Coloana 'CUI' nu există în date. Asigură-te că ai coloana exact 'CUI'.")
    st.stop()

# —————————————————————————————————————————————
# 4) Căutare după CUI
cui_input = st.text_input("🔍 Introdu CUI (sau fragment de CUI)", "")
exact = st.checkbox("Căutare exactă", value=False)

if cui_input:
    s = cui_input.strip()
    if exact:
        mask = df["CUI"].str.strip().eq(s, na=False)
    else:
        mask = df["CUI"].str.contains(s, na=False)
    results = df[mask]
    if not results.empty:
        st.write(f"**{len(results)}** firme găsite:")
        st.dataframe(results.reset_index(drop=True))
    else:
        st.warning("Nicio firmă găsită cu acest CUI.")
else:
    st.info("Introdu un CUI în caseta de mai sus pentru a căuta.")
