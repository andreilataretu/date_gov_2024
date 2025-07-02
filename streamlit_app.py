# streamlit_app.py

import os
import streamlit as st
import pandas as pd
import gdown

st.set_page_config(
    page_title="Căutare firme după CUI (Drive + local)",
    layout="wide",
)
st.title("🔎 Căutare firme după CUI")

# —————————————————————————————————————————————
# 1) Configurare Google Drive pentru fișierul mare
DRIVE_ID_LARGE = "1xfyW-Y8JhpGG2lTP6YcdC6kHuk7DBz3A"  # ← pune ID-ul tău aici
DRIVE_URL_LARGE = f"https://drive.google.com/uc?export=download&id={DRIVE_ID_LARGE}"
LOCAL_LARGE_PATH = "/mnt/data/web_uu_an2024_convertit.csv"

@st.cache_data(show_spinner=True)
def load_large_csv() -> pd.DataFrame:
    """
    Descarcă CSV-ul mare din Google Drive (o singură dată)
    și îl încarcă într-un DataFrame.
    """
    if not os.path.exists(LOCAL_LARGE_PATH):
        gdown.download(DRIVE_URL_LARGE, LOCAL_LARGE_PATH, quiet=False)
    return pd.read_csv(LOCAL_LARGE_PATH, dtype=str, low_memory=False)

# —————————————————————————————————————————————
# 2) Încarcă CSV-ul mare + CSV-ul mic din folderul `data/`

# A) DataFrame din Drive
df_large = load_large_csv()
st.info(f"🔄 Fișier mare încărcat: {df_large.shape[0]} rânduri × {df_large.shape[1]} coloane")

# B) DataFrame din fișierul mic (îl poți urca direct în repo sub data/)
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
SMALL_CSV_NAME = "web_bl_bs_sl_an2024_convertit.csv"
small_path = os.path.join(DATA_DIR, SMALL_CSV_NAME)

if os.path.exists(small_path):
    df_small = pd.read_csv(small_path, dtype=str, low_memory=False)
    st.info(f"🔄 Fișier mic încărcat:  {df_small.shape[0]} rânduri × {df_small.shape[1]} coloane")
    # Concatenează ambele seturi de date
    df = pd.concat([df_large, df_small], ignore_index=True)
else:
    st.warning(f"Fișierul mic `{SMALL_CSV_NAME}` nu a fost găsit în `{DATA_DIR}`. Lucrez doar cu CSV-ul mare.")
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

