"""
Script 03 — SteelOrbis scraper (FIXED)
=======================================
Working URL confirmed: https://www.steelorbis.com/steel-prices/
Table format: Date | Avg. Price | Change (%)
Output: data/steelorbis_prices.csv
"""

import re, os, time
import requests
import pandas as pd
from bs4 import BeautifulSoup
from datetime import date

OUTPUT_PATH = "data/steelorbis_prices.csv"
HEADERS     = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

# Confirmed working URLs from debug session
PAGES = {
    "HRC Steel Price - SteelOrbis":   "https://www.steelorbis.com/steel-prices/",
    "CRC Steel Price - SteelOrbis":   "https://www.steelorbis.com/steel-prices/cold-rolled-coil/",
    "Rebar Steel Price - SteelOrbis": "https://www.steelorbis.com/steel-prices/rebar/",
}

def parse_price(text: str):
    cleaned = re.sub(r"[^\d.]", "", text.replace(",", ""))
    try:
        val = float(cleaned)
        return val if 50 < val < 5000 else None
    except ValueError:
        return None

def parse_date(text: str):
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%m/%d/%Y", "%d-%m-%Y"):
        try:
            return pd.to_datetime(text.strip(), format=fmt).strftime("%Y-%m-%d")
        except Exception:
            continue
    return None

def scrape_page(url: str, metric_name: str) -> list:
    resp = requests.get(url, headers=HEADERS, timeout=20)
    if resp.status_code == 404:
        print(f"  404: {url}")
        return []

    soup    = BeautifulSoup(resp.text, "lxml")
    tables  = soup.find_all("table")
    records = []

    for table in tables:
        rows = table.find_all("tr")
        if len(rows) < 2:
            continue
        # Header row
        hdrs      = [td.get_text(strip=True).lower() for td in rows[0].find_all(["th","td"])]
        date_col  = next((i for i,h in enumerate(hdrs) if "date" in h), None)
        price_col = next((i for i,h in enumerate(hdrs)
                          if any(k in h for k in ["price","avg","usd","value"])), None)
        if price_col is None:
            continue

        for row in rows[1:]:
            cells = row.find_all(["td","th"])
            if len(cells) <= price_col:
                continue
            val = parse_price(cells[price_col].get_text(strip=True))
            if val is None:
                continue
            rec_date = date.today().strftime("%Y-%m-%d")
            if date_col is not None and date_col < len(cells):
                parsed = parse_date(cells[date_col].get_text(strip=True))
                if parsed:
                    rec_date = parsed
            records.append({
                "date":             rec_date,
                "metric_name":      metric_name,
                "kpi_value":        val,
                "unit_of_measure":  "USD/t",
                "region_or_country":"Global",
                "source":           "SteelOrbis",
            })
    return records


def main():
    os.makedirs("data", exist_ok=True)
    all_records = []

    for metric_name, url in PAGES.items():
        print(f"Scraping {metric_name.split(' - ')[0]} -> {url}")
        try:
            rows = scrape_page(url, metric_name)
            print(f"  {len(rows)} rows")
            all_records.extend(rows)
        except Exception as e:
            print(f"  FAILED: {e}")
        time.sleep(1.5)

    df = pd.DataFrame(all_records).drop_duplicates()

    if df.empty:
        print("\nWARNING: No data scraped.")
    else:
        df.to_csv(OUTPUT_PATH, index=False)
        print(f"\nSaved {len(df):,} rows -> {OUTPUT_PATH}")
        print(df[["date","metric_name","kpi_value"]].head(10).to_string(index=False))

    return df

if __name__ == "__main__":
    main()
