"""
Script 01 — Steel price ingestion (FINAL v6)
=============================================
Sources:
  1. World Bank Pink Sheet  -> Iron ore CFR spot (confirmed working)
  2. Eurostat API           -> EU steel producer price index (C241, EU27)
  3. SteelOrbis             -> HRC / CRC / Rebar daily spot prices

Output: data/wb_steel_prices.csv
"""

import io, re, os, time
import requests
import pandas as pd
from bs4 import BeautifulSoup
from datetime import date

OUTPUT_PATH = "data/wb_steel_prices.csv"
PERIOD_PAT  = re.compile(r"^\d{4}M\d{2}$")

# ─────────────────────────────────────────────────────────────────────────────
# SOURCE 1: World Bank Pink Sheet — Iron ore
# ─────────────────────────────────────────────────────────────────────────────
WB_URL = (
    "https://thedocs.worldbank.org/en/doc/"
    "5d903e848db1d1b83e0ec8f744e55570-0350012021/related/"
    "CMO-Historical-Data-Monthly.xlsx"
)

def fetch_iron_ore_wb() -> pd.DataFrame:
    print("[1/3] World Bank Pink Sheet — Iron ore ...")
    resp = requests.get(WB_URL, timeout=60)
    resp.raise_for_status()
    xl       = pd.ExcelFile(io.BytesIO(resp.content))
    raw      = xl.parse("Monthly Prices", header=None)
    name_row = raw.iloc[4]
    iron_col = next((i for i, v in enumerate(name_row) if "iron ore" in str(v).lower()), None)
    if iron_col is None:
        print("  WARNING: Iron ore column not found.")
        return pd.DataFrame()
    print(f"  Iron ore -> col {iron_col}: '{name_row.iloc[iron_col]}'")
    records = []
    for i in range(6, len(raw)):
        period = str(raw.iloc[i, 0]).strip()
        if not PERIOD_PAT.match(period):
            continue
        try:
            value = float(raw.iloc[i, iron_col])
            if pd.isna(value):
                continue
            records.append({
                "date": pd.to_datetime(period, format="%YM%m").strftime("%Y-%m-%d"),
                "metric_name": "Iron Ore Price CFR China - World Bank",
                "kpi_value": round(value, 2),
                "unit_of_measure": "USD/t",
                "region_or_country": "Global",
                "source": "World Bank Pink Sheet",
            })
        except Exception:
            continue
    print(f"  Extracted {len(records)} rows")
    return pd.DataFrame(records)


# ─────────────────────────────────────────────────────────────────────────────
# SOURCE 2: Eurostat — EU steel producer price index
# NACE C241 = Basic iron and steel, EU27, monthly, index 2015=100
# ─────────────────────────────────────────────────────────────────────────────
EUROSTAT_COMBOS = [
    ("C241",  "EU27_2020", "EU Steel Producer Price Index (2015=100) - Eurostat", "EU"),
    ("C2431", "EU27_2020", "EU Cold-Drawn Steel Price Index (2015=100) - Eurostat", "EU"),
]

def fetch_eurostat_steel() -> pd.DataFrame:
    print("\n[2/3] Eurostat — EU steel producer price index ...")
    base = (
        "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/"
        "sts_inppd_m?format=JSON&lang=EN&s_adj=NSA&unit=I15"
    )
    records = []
    for nace, geo, metric_name, region in EUROSTAT_COMBOS:
        url = f"{base}&nace_r2={nace}&geo={geo}"
        try:
            resp = requests.get(url, timeout=20)
            resp.raise_for_status()
            data = resp.json()

            values  = data.get("value", {})
            periods = list(
                data["dimension"]["time"]["category"]["index"].keys()
            )
            idx_to_period = {str(i): p for i, p in enumerate(periods)}

            count = 0
            for idx_str, value in values.items():
                period = idx_to_period.get(str(idx_str))
                if not period or value is None:
                    continue
                try:
                    dt = pd.to_datetime(period)   # "2015-01" -> datetime
                    records.append({
                        "date": dt.strftime("%Y-%m-%d"),
                        "metric_name": metric_name,
                        "kpi_value": round(float(value), 2),
                        "unit_of_measure": "Percentage",
                        "region_or_country": region,
                        "source": "Eurostat",
                    })
                    count += 1
                except Exception:
                    continue
            print(f"  {nace} / {geo}: {count} rows")
        except Exception as e:
            print(f"  {nace} FAILED: {e}")
        time.sleep(0.5)

    return pd.DataFrame(records)


# ─────────────────────────────────────────────────────────────────────────────
# SOURCE 3: SteelOrbis — HRC / CRC / Rebar daily spot prices
# Working URL confirmed: https://www.steelorbis.com/steel-prices/
# Table format: Date | Avg. Price | Change (%)
# ─────────────────────────────────────────────────────────────────────────────
STEELORBIS_PAGES = {
    "HRC Steel Price - SteelOrbis":   "https://www.steelorbis.com/steel-prices/",
    "CRC Steel Price - SteelOrbis":   "https://www.steelorbis.com/steel-prices/cold-rolled-coil/",
    "Rebar Steel Price - SteelOrbis": "https://www.steelorbis.com/steel-prices/rebar/",
}
SO_HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

def parse_steelorbis_price(text: str) -> float | None:
    """Extract numeric USD value from strings like '398.50\xa0USD' or '398.50 USD'."""
    cleaned = re.sub(r"[^\d.]", "", text.replace(",", ""))
    try:
        val = float(cleaned)
        return val if 50 < val < 5000 else None
    except ValueError:
        return None

def parse_steelorbis_date(text: str) -> str | None:
    """Parse dates like '18/04/2026' -> '2026-04-18'."""
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%m/%d/%Y", "%d-%m-%Y"):
        try:
            return pd.to_datetime(text.strip(), format=fmt).strftime("%Y-%m-%d")
        except Exception:
            continue
    return None

def fetch_steelorbis() -> pd.DataFrame:
    print("\n[3/3] SteelOrbis — spot prices ...")
    records = []

    for metric_name, url in STEELORBIS_PAGES.items():
        try:
            resp = requests.get(url, headers=SO_HEADERS, timeout=20)
            if resp.status_code == 404:
                print(f"  404: {url} — skipping")
                continue

            soup   = BeautifulSoup(resp.text, "lxml")
            tables = soup.find_all("table")
            found  = 0

            for table in tables:
                rows = table.find_all("tr")
                if len(rows) < 2:
                    continue

                # Identify columns from header row
                hdrs = [td.get_text(strip=True).lower()
                        for td in rows[0].find_all(["th", "td"])]
                date_col  = next((i for i, h in enumerate(hdrs) if "date" in h), None)
                price_col = next((i for i, h in enumerate(hdrs)
                                  if any(k in h for k in ["price","usd","avg","value"])), None)

                if price_col is None:
                    continue

                for row in rows[1:]:
                    cells = row.find_all(["td", "th"])
                    if len(cells) <= price_col:
                        continue

                    price_val = parse_steelorbis_price(cells[price_col].get_text(strip=True))
                    if price_val is None:
                        continue

                    record_date = date.today().strftime("%Y-%m-%d")
                    if date_col is not None and date_col < len(cells):
                        parsed = parse_steelorbis_date(cells[date_col].get_text(strip=True))
                        if parsed:
                            record_date = parsed

                    records.append({
                        "date": record_date,
                        "metric_name": metric_name,
                        "kpi_value": price_val,
                        "unit_of_measure": "USD/t",
                        "region_or_country": "Global",
                        "source": "SteelOrbis",
                    })
                    found += 1

            print(f"  {metric_name.split(' - ')[0]}: {found} rows")
            time.sleep(1.0)

        except Exception as e:
            print(f"  FAILED {url}: {e}")

    return pd.DataFrame(records)


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────
def main():
    os.makedirs("data", exist_ok=True)
    frames = []
    for fn in [fetch_iron_ore_wb, fetch_eurostat_steel, fetch_steelorbis]:
        try:
            df = fn()
            if not df.empty:
                frames.append(df)
        except Exception as e:
            print(f"  Source failed entirely: {e}")

    if not frames:
        print("\nERROR: All sources failed.")
        return pd.DataFrame()

    final = pd.concat(frames, ignore_index=True)
    final.to_csv(OUTPUT_PATH, index=False)

    print(f"\n{'='*55}")
    print(f"Saved {len(final):,} rows -> {OUTPUT_PATH}")
    print("\nMetrics extracted:")
    print(final.groupby("metric_name")["kpi_value"].count().to_string())
    print("\nMost recent value per metric:")
    print(
        final.sort_values("date")
             .groupby("metric_name")
             .last()[["date", "kpi_value", "unit_of_measure"]]
             .to_string()
    )
    return final

if __name__ == "__main__":
    main()
