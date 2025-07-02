# streamlit_app.py

import streamlit as st
import pandas as pd
import requests
from pathlib import Path

# ─────────── Adaugă după celelalte importuri ───────────
@st.cache_data(show_spinner=False)
def get_registry_csv_url() -> str:
    """Returnează URL-ul CSV-ului mare din CKAN."""
    pkg_id   = "a03a00da-2fed-4607-97f1-5147c3ff32a6"
    res_id   = "8a535477-4b41-413e-845f-8b6afdb2d664"
    meta_url = "https://data.gov.ro/api/3/action/package_show"
    r = requests.get(meta_url, params={"id": pkg_id}).json()["result"]
    return next(rsrc["url"] for rsrc in r["resources"] if rsrc["id"] == res_id)

@st.cache_data(show_spinner=False)
def lookup_company(cui: str) -> tuple[str | None, str | None]:
    """
    Parcurge CSV-ul oficial pe bucăți și returnează
    (Denumire, FormaJur) pentru CUI-ul dat, sau (None,None).
    """
    url  = get_registry_csv_url()
    cols = ["CUI", "DENUMIRE", "FORMA_JURIDICA"]
    for chunk in pd.read_csv(
        url,
        usecols=cols,
        dtype=str,
        chunksize=100_000,
        low_memory=False
    ):
        hit = chunk.loc[chunk["CUI"].str.strip() == cui.strip()]
        if not hit.empty:
            return hit.iloc[0]["DENUMIRE"], hit.iloc[0]["FORMA_JURIDICA"]
    return None, None
# ───────────────────────────────────────────────────────


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
cui = st.text_input("🔍 Introdu CUI (sau fragment)", "")
exact = st.checkbox("Exact match", value=False)
if cui:
    if exact:
        mask = df["CUI"].str.strip().eq(cui.strip(), na=False)
    else:
        mask = df["CUI"].str.contains(cui.strip(), na=False)
    res = df[mask]
    if not res.empty:
    # ─── îmbogăţire pentru fiecare CUI găsit ───
    res = res.copy()
    res["Denumire"] = "-"
    res["FormaJur"]  = "-"
    for idx, row in res.iterrows():
        den, form = lookup_company(row["CUI"])
        if den:  res.at[idx, "Denumire"] = den
        if form: res.at[idx, "FormaJur"] = form

    st.write(f"**{len(res)}** firme găsite și îmbogățite:")
    st.dataframe(res.reset_index(drop=True))

    else:
        st.warning("Niciuna nu corespunde.")
else:
    st.info("Introdu un CUI pentru a căuta…")
