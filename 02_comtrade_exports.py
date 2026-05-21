"""
Script 02 — Steel production & trade data (FINAL)
==================================================
Free sources used (no API key, no subscription):

  A) USGS Minerals Yearbook — steel production by country (Excel, free)
  B) WSA monthly press releases — top-10 country production (scraped HTML)
  C) Eurostat COMEXT — EU steel trade value by HS code (JSON API)

Output: data/comtrade_steel_exports.csv
        data/comtrade_hhi.csv
"""

import os, re, time, io
import requests
import pandas as pd
from bs4 import BeautifulSoup

OUTPUT_EXPORTS = "data/comtrade_steel_exports.csv"
OUTPUT_HHI     = "data/comtrade_hhi.csv"
HEADERS        = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

# ─────────────────────────────────────────────────────────────────────────────
# SOURCE A: USGS Minerals Yearbook — Iron & Steel chapter
# URL pattern: https://minerals.usgs.gov/minerals/pubs/commodity/iron_&_steel/
# Free Excel tables with steel production by country
# ─────────────────────────────────────────────────────────────────────────────

USGS_URLS = [
    "https://minerals.usgs.gov/minerals/pubs/commodity/iron_&_steel/mcs-2024-femet.xlsx",
    "https://minerals.usgs.gov/minerals/pubs/commodity/iron_&_steel/mcs-2023-femet.xlsx",
    "https://minerals.usgs.gov/minerals/pubs/commodity/iron_&_steel/mcs-2022-femet.xlsx",
    # MCS = Mineral Commodity Summaries, published annually
]

def fetch_usgs_steel() -> pd.DataFrame:
    print("[A] USGS Mineral Commodity Summaries — steel production ...")
    for url in USGS_URLS:
        try:
            print(f"  Trying: {url}")
            resp = requests.get(url, headers=HEADERS, timeout=30)
            if resp.status_code != 200:
                print(f"  Status {resp.status_code}")
                continue
            xl = pd.ExcelFile(io.BytesIO(resp.content))
            print(f"  Sheets: {xl.sheet_names}")
            for sheet in xl.sheet_names:
                df = xl.parse(sheet, header=None)
                col0 = df.iloc[:, 0].astype(str).str.lower()
                if any("china" in v for v in col0) and any("india" in v for v in col0):
                    print(f"  Found country data in sheet '{sheet}'")
                    return parse_usgs_sheet(df, sheet)
        except Exception as e:
            print(f"  Failed: {e}")
    print("  WARNING: USGS data not available.")
    return pd.DataFrame()


def parse_usgs_sheet(raw: pd.DataFrame, sheet_name: str) -> pd.DataFrame:
    year_pat = re.compile(r"^20\d{2}$")
    # Find header row with years
    header_idx, year_cols = None, {}
    for i, row in raw.iterrows():
        for j, val in enumerate(row):
            if year_pat.match(str(val).strip()):
                if header_idx is None:
                    header_idx = i
                year_cols[j] = int(str(val).strip())
    if header_idx is None:
        return pd.DataFrame()

    records = []
    skip = {"nan","total","world","other","—",""}
    for i in range(header_idx + 1, len(raw)):
        country = str(raw.iloc[i, 0]).strip()
        if country.lower() in skip or not country:
            continue
        for col_j, year in year_cols.items():
            try:
                val = float(str(raw.iloc[i, col_j]).replace(",","").replace("e","").replace("W",""))
                if pd.isna(val) or val <= 0:
                    continue
                records.append({
                    "year": year, "date": f"{year}-01-01",
                    "hs_code": "CRUDE", "hs_desc": "Crude steel production",
                    "flow": "Production", "reporter": country,
                    "reporter_code": country[:10],
                    "trade_value_eur": None,
                    "qty_kg": val * 1e9,   # kt -> kg (USGS reports in 1000t)
                    "source": "USGS MCS",
                })
            except Exception:
                continue
    print(f"  Extracted {len(records)} country-year rows")
    return pd.DataFrame(records)


# ─────────────────────────────────────────────────────────────────────────────
# SOURCE B: WSA monthly press releases — top-10 countries (scraped)
# These are freely published HTML pages with structured tables
# ─────────────────────────────────────────────────────────────────────────────

WSA_PRESS_RELEASES = [
    ("2024", "https://worldsteel.org/media/press-releases/2025/december-2024-crude-steel-production-and-2024-global-totals/"),
    ("2023", "https://worldsteel.org/media/press-releases/2024/december-2023-crude-steel-production-and-2023-global-totals/"),
    ("2022", "https://worldsteel.org/media/press-releases/2023/december-2022-crude-steel-production-and-2022-global-totals/"),
    ("2021", "https://worldsteel.org/media/press-releases/2022/december-2021-crude-steel-production-and-2021-global-totals/"),
]

def fetch_wsa_press_releases() -> pd.DataFrame:
    print("\n[B] WSA press releases — top-10 country production ...")
    records = []

    for year_str, url in WSA_PRESS_RELEASES:
        try:
            resp = requests.get(url, headers=HEADERS, timeout=20)
            if resp.status_code != 200:
                print(f"  {year_str}: status {resp.status_code}")
                continue
            soup   = BeautifulSoup(resp.text, "lxml")
            tables = soup.find_all("table")
            found  = 0
            for table in tables:
                rows = table.find_all("tr")
                for row in rows:
                    cells = [td.get_text(strip=True) for td in row.find_all(["td","th"])]
                    if len(cells) < 2:
                        continue
                    country = cells[0].strip()
                    # Skip header rows
                    if not country or country.lower() in ("country","rank","#",""):
                        continue
                    # Find a numeric production value (Mt range 0.1–1200)
                    for cell in cells[1:]:
                        num_str = re.sub(r"[^\d.]", "", cell)
                        try:
                            val = float(num_str)
                            if 0.1 <= val <= 1200:
                                records.append({
                                    "year": int(year_str),
                                    "date": f"{year_str}-01-01",
                                    "hs_code": "CRUDE",
                                    "hs_desc": "Crude steel production",
                                    "flow": "Production",
                                    "reporter": country,
                                    "reporter_code": country[:10],
                                    "trade_value_eur": None,
                                    "qty_kg": val * 1e9,   # Mt -> kg
                                    "source": "WSA press release",
                                })
                                found += 1
                                break
                        except ValueError:
                            continue
            print(f"  {year_str}: {found} country rows")
            time.sleep(0.5)
        except Exception as e:
            print(f"  {year_str}: FAILED — {e}")

    return pd.DataFrame(records)


# ─────────────────────────────────────────────────────────────────────────────
# SOURCE C: Eurostat COMEXT — EU steel trade by HS code
# ─────────────────────────────────────────────────────────────────────────────

DS_URL = (
    "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/"
    "DS-045409?format=JSON&lang=EN"
    "&REPORTER=EU27_2020&PARTNER=WRL_WORLD"
    "&FLOW={flow}&PRODUCT={product}&PERIOD={period}"
)
HS_PRODUCTS = {"7208": "HRC", "7209": "CRC", "7214": "Rebar"}
YEARS_EU    = list(range(2019, 2024))

def fetch_eurostat_trade() -> pd.DataFrame:
    print("\n[C] Eurostat COMEXT — EU steel trade ...")
    records = []
    for flow_code, flow_name in [("1","Import"),("2","Export")]:
        for hs, desc in HS_PRODUCTS.items():
            for year in YEARS_EU:
                url = DS_URL.format(flow=flow_code, product=hs, period=year)
                try:
                    resp = requests.get(url, timeout=15)
                    if resp.status_code in (404, 400):
                        continue
                    data   = resp.json()
                    values = data.get("value", {})
                    if not values:
                        continue
                    # Sum all values for this product/year/flow
                    total = sum(v for v in values.values() if v is not None)
                    records.append({
                        "year": year, "date": f"{year}-01-01",
                        "hs_code": hs, "hs_desc": f"{desc} - flat steel",
                        "flow": flow_name, "reporter": "EU27",
                        "reporter_code": "EU27_2020",
                        "trade_value_eur": round(total, 0),
                        "qty_kg": None,
                        "source": "Eurostat COMEXT",
                    })
                except Exception:
                    pass
                time.sleep(0.2)
    print(f"  Extracted {len(records)} EU trade records")
    return pd.DataFrame(records)


# ─────────────────────────────────────────────────────────────────────────────
# HHI — computed from production data
# ─────────────────────────────────────────────────────────────────────────────

def compute_hhi(df: pd.DataFrame) -> pd.DataFrame:
    records = []
    prod_df = df[df["flow"] == "Production"].dropna(subset=["qty_kg"])
    for year, grp in prod_df.groupby("year"):
        total = grp["qty_kg"].sum()
        if total <= 0:
            continue
        hhi = round(((grp["qty_kg"] / total) ** 2).sum() * 10_000, 1)
        records.append({
            "date":             f"{year}-01-01",
            "metric_name":      "HHI Steel Producer Concentration - Global",
            "kpi_value":        hhi,
            "unit_of_measure":  "Percentage",
            "region_or_country":"Global",
            "hs_code":          "CRUDE",
            "source":           "Computed",
        })
    return pd.DataFrame(records)


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def main():
    os.makedirs("data", exist_ok=True)

    usgs_df    = fetch_usgs_steel()
    wsa_df     = fetch_wsa_press_releases()
    eu_trade_df= fetch_eurostat_trade()

    # Combine production sources
    prod_frames = [f for f in [usgs_df, wsa_df] if not f.empty]
    all_frames  = prod_frames + ([eu_trade_df] if not eu_trade_df.empty else [])

    if not all_frames:
        print("\nERROR: No data collected from any source.")
        return pd.DataFrame()

    exports_df = pd.concat(all_frames, ignore_index=True)
    exports_df.to_csv(OUTPUT_EXPORTS, index=False)
    print(f"\nSaved {len(exports_df):,} rows -> {OUTPUT_EXPORTS}")

    # HHI
    prod_df = pd.concat(prod_frames, ignore_index=True) if prod_frames else pd.DataFrame()
    if not prod_df.empty:
        hhi_df = compute_hhi(prod_df)
        if not hhi_df.empty:
            hhi_df.to_csv(OUTPUT_HHI, index=False)
            print(f"Saved {len(hhi_df):,} HHI rows -> {OUTPUT_HHI}")
            print("\nHHI by year:")
            print(hhi_df[["date","kpi_value"]].to_string(index=False))
        else:
            print("HHI: no data computed.")
    else:
        print("No production data for HHI.")

    print(f"\nSources summary:")
    print(exports_df.groupby("source")["reporter"].count().to_string())
    return exports_df


if __name__ == "__main__":
    main()
