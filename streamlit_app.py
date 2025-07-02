# streamlit_app.py

import streamlit as st
import pandas as pd
import requests
from pathlib import Path

# ───────── Config Streamlit ─────────
st.set_page_config(
    page_title="Căutare firme după CUI (Drive + local + enrich)",
    layout="wide",
)
st.title("🔎 Căutare firme după CUI + denumire & forma juridică")

# ───────── Funcții de lookup CKAN ─────────
@st.cache_data(show_spinner=False)
def get_registry_csv_url() -> str:
    pkg_id   = "a03a00da-2fed-4607-97f1-5147c3ff32a6"
    res_id   = "8a535477-4b41-413e-845f-8b6afdb2d664"
    meta_url = "https://data.gov.ro/api/3/action/package_show"
    res = requests.get(meta_url, params={"id": pkg_id}).json()["result"]
    return next(r["url"] for r in res["resources"] if r["id"] == res_id)

@st.cache_data(show_spinner=False)
def lookup_company(cui: str) -> tuple[str | None, str | None]:
    """
    Parcurge CSV-ul registrului pe chunks și returnează
    (Denumire, FormaJur) pentru CUI. Dacă nu găsește, returnează (None,None).
    """
    url  = get_registry_csv_url()
    cols = ["CUI", "DENUMIRE", "FORMA_JURIDICA"]
    for chunk in pd.read_csv(
        url, usecols=cols, dtype=str, chunksize=100_000, low_memory=False
    ):
        hit = chunk.loc[chunk["CUI"].str.strip() == cui.strip()]
        if not hit.empty:
            return hit.iloc[0]["DENUMIRE"], hit.iloc[0]["FORMA_JURIDICA"]
    return None, None

# ───────── Descărcare & încărcare CSV mare din Drive ─────────
DRIVE_ID_LARGE   = "1xfyW-Y8JhpGG2lTP6YcdC6kHuk7DBz3A"
DOWNLOAD_URL     = "https://docs.google.com/uc?export=download"
LOCAL_LARGE_PATH = Path(__file__).parent / "data" / "web_uu_an2024_convertit.csv"

def get_confirm_token(response):
    for k,v in response.cookies.items():
        if k.startswith("download_warning"):
            return v
    return None

def download_file_from_google_drive(file_id: str, destination: Path):
    destination.parent.mkdir(parents=True, exist_ok=True)
    sess = requests.Session()
    res  = sess.get(DOWNLOAD_URL, params={"id": file_id}, stream=True)
    token = get_confirm_token(res)
    if token:
        res = sess.get(DOWNLOAD_URL, params={"id": file_id, "confirm": token}, stream=True)
    with open(destination, "wb") as f:
        for chunk in res.iter_content(32768):
            if chunk:
                f.write(chunk)

@st.cache_data(show_spinner=True)
def load_large_csv() -> pd.DataFrame:
    if not LOCAL_LARGE_PATH.exists():
        st.info("🔄 Descarc fișierul mare de pe Drive…")
        download_file_from_google_drive(DRIVE_ID_LARGE, LOCAL_LARGE_PATH)
    return pd.read_csv(LOCAL_LARGE_PATH, dtype=str, low_memory=False)

# ───────── Încarcare date locale ─────────
df_large = load_large_csv()
st.info(f"✔️ Mare: {df_large.shape[0]} rânduri × {df_large.shape[1]} coloane")

DATA_DIR = Path(__file__).parent / "data"
small_fp = DATA_DIR / "web_bl_bs_sl_an2024_convertit.csv"
if small_fp.exists():
    df_small = pd.read_csv(small_fp, dtype=str, low_memory=False)
    st.info(f"✔️ Mic:  {df_small.shape[0]} rânduri × {df_small.shape[1]} coloane")
    df = pd.concat([df_large, df_small], ignore_index=True)
else:
    st.warning("Fișierul mic lipsește, lucrez doar cu cel mare.")
    df = df_large

st.success(f"✅ Total local: {df.shape[0]} rânduri × {df.shape[1]} coloane")

# ───────── Verific CUI ─────────
if "CUI" not in df.columns:
    st.error("Nu există coloana 'CUI' în date. Verifică header-ele!")
    st.stop()

# ───────── Căutare + enrich ─────────
cui   = st.text_input("🔍 Introdu CUI (sau fragment)", "")
exact = st.checkbox("Exact match", value=False)

if cui:
    # filtrare locală
    if exact:
        mask = df["CUI"].str.strip().eq(cui.strip(), na=False)
    else:
        mask = df["CUI"].str.contains(cui.strip(), na=False)

    # extrag rezultate și pregătesc îmbogățirea
    res = df.loc[mask].copy()

    if res.empty:
        st.warning("Nicio firmă găsită local cu acest CUI.")
    else:
        # inițializez coloanele noi
        res["Denumire"] = "-"
        res["FormaJur"] = "-"
        # pentru fiecare rând găsit, fac lookup în registru
        for idx, row in res.iterrows():
            den, frm = lookup_company(row["CUI"])
            if den:
                res.at[idx, "Denumire"] = den
            if frm:
                res.at[idx, "FormaJur"] = frm

        # afișez rezultatul îmbogățit
        st.write(f"**{len(res)}** firme găsite și îmbogățite:")
        st.dataframe(res.reset_index(drop=True))
else:
    st.info("Introdu un CUI pentru a căuta…")
