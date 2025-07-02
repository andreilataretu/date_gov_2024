# streamlit_app.py

import streamlit as st
import pandas as pd
import requests
from pathlib import Path

@st.cache_data(show_spinner=False)
def get_registry_csv_url() -> str:
    pkg_id   = "a03a00da-2fed-4607-97f1-5147c3ff32a6"
    res_id   = "8a535477-4b41-413e-845f-8b6afdb2d664"
    r = requests.get(
        "https://data.gov.ro/api/3/action/package_show",
        params={"id": pkg_id}
    ).json()["result"]
    return next(rs["url"] for rs in r["resources"] if rs["id"] == res_id)

 @st.cache_data(show_spinner=False)
     def lookup_company(cui: str) -> tuple[str|None, str|None]:
    -    url  = get_registry_csv_url()
    -    cols = ["CUI", "DENUMIRE", "FORMA_JURIDICA"]
    -    for chunk in pd.read_csv(
    -        url, usecols=cols, dtype=str, chunksize=100_000, low_memory=False
    -    ):
    +    url   = get_registry_csv_url()
    +    cols  = ["CUI", "DENUMIRE", "FORMA_JURIDICA"]
    +    try:
    +        reader = pd.read_csv(
    +            url,
    +            sep=";",               # multe CSV-uri de la ONRC sunt delimitate cu “;”
    +            engine="python",
    +            usecols=cols,
    +            dtype=str,
    +            chunksize=100_000,
    +            low_memory=False
    +        )
    +    except Exception as e:
    +        # Afișăm eroarea în UI o singură dată și ieșim silențios
    +        st.error(f"Eroare la încărcarea registrului: {e}")
    +        return None, None
    +
    +    # dacă am ajuns aici, reader e un TextFileReader valid
    +    for chunk in reader:
             hit = chunk.loc[chunk["CUI"].str.strip() == cui.strip()]
             if not hit.empty:
                 return hit.iloc[0]["DENUMIRE"], hit.iloc[0]["FORMA_JURIDICA"]
         return None, None



# ───────── Config Streamlit ─────────
st.set_page_config(
    page_title="Căutare firme după CUI + denumire & forma juridică",
    layout="wide",
)
st.title("🔎 Căutare firme după CUI + enrich CKAN")

# ───────── Drive download + load ─────────
DRIVE_ID_LARGE   = "1xfyW-Y8JhpGG2lTP6YcdC6kHuk7DBz3A"
DOWNLOAD_URL     = "https://docs.google.com/uc?export=download"
LOCAL_LARGE_PATH = Path(__file__).parent/"data"/"web_uu_an2024_convertit.csv"

def _get_token(resp):
    for k,v in resp.cookies.items():
        if k.startswith("download_warning"):
            return v
    return None

def download_drive(f_id: str, dst: Path):
    dst.parent.mkdir(exist_ok=True, parents=True)
    s = requests.Session()
    r = s.get(DOWNLOAD_URL, params={"id":f_id}, stream=True)
    tok = _get_token(r)
    if tok:
        r = s.get(DOWNLOAD_URL, params={"id":f_id,"confirm":tok}, stream=True)
    with open(dst, "wb") as f:
        for chunk in r.iter_content(32768):
            if chunk:
                f.write(chunk)

@st.cache_data(show_spinner=True)
def load_large_csv() -> pd.DataFrame:
    if not LOCAL_LARGE_PATH.exists():
        st.info("🔄 Descarc fișier mare de pe Drive…")
        download_drive(DRIVE_ID_LARGE, LOCAL_LARGE_PATH)
    return pd.read_csv(LOCAL_LARGE_PATH, dtype=str, low_memory=False)

# ───────── Load local data ─────────
df_large = load_large_csv()
st.info(f"✔️ Mare: {df_large.shape[0]}×{df_large.shape[1]}")

data_dir = Path(__file__).parent/"data"
small_fp = data_dir/"web_bl_bs_sl_an2024_convertit.csv"
if small_fp.exists():
    df_small = pd.read_csv(small_fp, dtype=str, low_memory=False)
    st.info(f"✔️ Mic:  {df_small.shape[0]}×{df_small.shape[1]}")
    df = pd.concat([df_large, df_small], ignore_index=True)
else:
    st.warning("⚠️ Fișier mic lipsește, lucrez doar cu cel mare.")
    df = df_large

st.success(f"✅ Total local: {df.shape[0]}×{df.shape[1]}")

# ───────── Verific că există CUI ─────────
if "CUI" not in df.columns:
    st.error("❗ Coloana 'CUI' nu există în date.")
    st.stop()

# ───────── Căutare + enrich ─────────
cui = st.text_input("🔍 Introdu CUI (sau fragment)", "")
exact = st.checkbox("Exact match", value=False)

if cui:
    # 1) filtrare locală
    if exact:
        mask = df["CUI"].str.strip().eq(cui.strip(), na=False)
    else:
        mask = df["CUI"].str.contains(cui.strip(), na=False)

    # 2) extrag și clonez subsetul
    res = df.loc[mask].copy()

    if res.empty:
        st.warning("Nicio firmă găsită local cu acest CUI.")
    else:
        # 3) adaug coloanele noi cu valori implicite
        res["Denumire"] = "-"
        res["FormaJur"]  = "-"
        # 4) pentru fiecare rând, completez denumire și forma
        for idx, row in res.iterrows():
            den, frm = lookup_company(row["CUI"])
            if den:
                res.at[idx, "Denumire"] = den
            if frm:
                res.at[idx, "FormaJur"] = frm

        # 5) afișez rezultatul îmbogățit
        st.write(f"**{len(res)}** firme găsite și îmbogățite:")
        st.dataframe(res.reset_index(drop=True))
else:
    st.info("Introdu un CUI pentru a căuta…")
