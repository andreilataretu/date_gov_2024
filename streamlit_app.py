# streamlit_app.py

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
DOWNLOAD_URL = "https://docs.google.com/uc?export=download"

# Salvăm în folderul data/ de lângă script
LOCAL_LARGE_PATH = Path(__file__).parent / "data" / "web_uu_an2024_convertit.csv"

def get_confirm_token(response):
    for k, v in response.cookies.items():
        if k.startswith("download_warning"):
            return v
    return None

def download_file_from_google_drive(file_id: str, destination: Path):
    # creăm directorul (dacă nu există)
    destination.parent.mkdir(parents=True, exist_ok=True)

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
        st.info("🔄 Descarc fișierul mare de pe Drive (75 MB)…")
        download_file_from_google_drive(DRIVE_ID_LARGE, LOCAL_LARGE_PATH)
    return pd.read_csv(LOCAL_LARGE_PATH, dtype=str, low_memory=False)

# —————————————————————————————————————————————
# 2) Încarcă datele mari + datele mici
df_large = load_large_csv()
st.info(f"✔️ Fișier mare: {df_large.shape[0]} rânduri × {df_large.shape[1]} coloane")

DATA_DIR = Path(__file__).parent / "data"
SMALL = DATA_DIR / "web_bl_bs_sl_an2024_convertit.csv"
if SMALL.exists():
    df_small = pd.read_csv(SMALL, dtype=str, low_memory=False)
    st.info(f"✔️ Fișier mic:  {df_small.shape[0]} rânduri × {df_small.shape[1]} coloane")
    df = pd.concat([df_large, df_small], ignore_index=True)
else:
    st.warning(f"Fișierul mic nu există în {DATA_DIR}, folosesc doar cel mare.")
    df = df_large

st.success(f"✅ Total: {df.shape[0]} rânduri × {df.shape[1]} coloane")

# —————————————————————————————————————————————
# 3) Verifică coloana CUI
if "CUI" not in df.columns:
    st.error("Lip col. ‘CUI’ în date — verifică header-ele!")
    st.stop()

# —————————————————————————————————————————————
# 4) Căutare după CUI
cui   = st.text_input("🔍 Introdu CUI (sau fragment)", "")
exact = st.checkbox("Exact match", value=False)

if cui:
    # filtrare locală
    if exact:
        mask = df["CUI"].str.strip().eq(cui.strip(), na=False)
    else:
        mask = df["CUI"].str.contains(cui.strip(), na=False)

    res = df.loc[mask].copy()

    if res.empty:
        st.warning("Nicio firmă găsită local cu acest CUI.")
    else:
        # afișez întâi toate coloanele originale
        st.write(f"**{len(res)}** firme găsite:")
        st.dataframe(res.reset_index(drop=True))

        # ——— începe secțiunea de enrich și tabelul mic ———
        # pregătesc lista de (Denumire, FormaJur)
        rows = []
        for cui_val in res["CUI"].tolist():
            den, frm = lookup_company(cui_val)
            rows.append({
                "CUI": cui_val,
                "Denumire": den or "-",
                "FormaJur": frm or "-"
            })

        df_enriched = pd.DataFrame(rows)

        st.write("### 📋 Detalii îmbogățite (nume și formă juridică)")
        st.dataframe(
            df_enriched,
            use_container_width=True,
            height=200
        )
        # ——— sfârșit tabel enrich ———
else:
    st.info("Introdu un CUI pentru a căuta…")
