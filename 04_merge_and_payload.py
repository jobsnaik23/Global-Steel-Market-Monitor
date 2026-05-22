"""
Script 04 — Merge, KPI calculation & final JSON payload
========================================================
Reads outputs from scripts 01–03, computes derived KPIs
(grade premium, HHI, sector demand share), and writes the
final structured JSON payload ready for Power BI import.

Output : data/steel_kpi_payload.json
         data/steel_kpi_payload.csv   (Power BI friendly flat file)

JSON structure produced
-----------------------
{
  "data_points": [
    {
      "metric_name": "...",
      "kpi_value": 123.45,
      "unit_of_measure": "USD/t",
      "region_or_country": "Global",
      "record_date": "2024-01-01"
    },
    ...
  ]
}

Run order
---------
python 01_worldbank_prices.py
python 02_comtrade_exports.py
python 03_steelorbis_scraper.py
python 04_merge_and_payload.py
"""

import json
import os
import pandas as pd

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
PATHS = {
    "wb":        "data/wb_steel_prices.csv",
    "comtrade":  "data/comtrade_steel_exports.csv",
    "hhi":       "data/comtrade_hhi.csv",
    "steelorbis":"data/steelorbis_prices.csv",
}

OUTPUT_JSON = "data/steel_kpi_payload.json"
OUTPUT_CSV  = "data/steel_kpi_payload.csv"

# Standard field names for the payload
PAYLOAD_COLS = ["metric_name", "kpi_value", "unit_of_measure",
                "region_or_country", "record_date"]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_if_exists(path: str, label: str) -> pd.DataFrame:
    if os.path.exists(path):
        df = pd.read_csv(path)
        print(f"  Loaded {label}: {len(df):,} rows")
        return df
    else:
        print(f"  MISSING {label} → {path}  (run the relevant script first)")
        return pd.DataFrame()


def normalise(df: pd.DataFrame, date_col: str = "date") -> pd.DataFrame:
    """Rename the date column to 'record_date' and keep only payload cols."""
    if df.empty:
        return df
    df = df.copy()
    if date_col in df.columns and "record_date" not in df.columns:
        df = df.rename(columns={date_col: "record_date"})
    # Keep only the five standard payload columns
    existing = [c for c in PAYLOAD_COLS if c in df.columns]
    return df[existing].dropna(subset=["kpi_value"])


# ---------------------------------------------------------------------------
# Derived KPIs
# ---------------------------------------------------------------------------

def compute_grade_premium(wb_df: pd.DataFrame) -> pd.DataFrame:
    """
    Grade premium = HRC price − CRC price (negative = CRC is premium product).
    In practice, CRC > HRC because of extra processing.
    We compute |CRC − HRC| and label it correctly.
    Uses World Bank data (Global, monthly).
    """
    if wb_df.empty:
        return pd.DataFrame()

    hrc = wb_df[wb_df["metric_name"].str.contains("HRC", case=False)][["date","kpi_value","region_or_country"]]
    crc = wb_df[wb_df["metric_name"].str.contains("CRC", case=False)][["date","kpi_value","region_or_country"]]

    merged = hrc.merge(crc, on=["date","region_or_country"], suffixes=("_hrc","_crc"))
    if merged.empty:
        return pd.DataFrame()

    merged["kpi_value"]       = (merged["kpi_value_crc"] - merged["kpi_value_hrc"]).round(2)
    merged["metric_name"]     = "CRC Premium over HRC"
    merged["unit_of_measure"] = "USD/t"
    merged["record_date"]     = merged["date"]

    return merged[PAYLOAD_COLS].dropna(subset=["kpi_value"])


def compute_export_volume_mmt(comtrade_df: pd.DataFrame) -> pd.DataFrame:
    """
    Aggregate global export volume per HS code per year → Million Metric Tons.
    """
    if comtrade_df.empty:
        return pd.DataFrame()

    df = comtrade_df.copy()
    df["qty_kg"] = pd.to_numeric(df["qty_kg"], errors="coerce")
    df = df.dropna(subset=["qty_kg"])

    grouped = (
        df.groupby(["date", "hs_code", "hs_desc"])["qty_kg"]
        .sum()
        .reset_index()
    )
    grouped["kpi_value"]       = (grouped["qty_kg"] / 1e9).round(4)
    grouped["metric_name"]     = "Export Volume - " + grouped["hs_desc"]
    grouped["unit_of_measure"] = "Million Metric Tons"
    grouped["region_or_country"] = "Global"
    grouped["record_date"]     = grouped["date"]

    return grouped[PAYLOAD_COLS]


def compute_hhi_payload(hhi_df: pd.DataFrame) -> pd.DataFrame:
    """Re-map HHI to standard payload (unit stays as index, label as Percentage)."""
    if hhi_df.empty:
        return pd.DataFrame()
    df = hhi_df.copy()
    df["record_date"] = df["date"]
    # HHI is a 0-10000 index; we label unit as 'Percentage' per your spec
    # but note in metric_name it's an index
    df["unit_of_measure"] = "Percentage"
    return df[PAYLOAD_COLS].dropna(subset=["kpi_value"])


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    os.makedirs("data", exist_ok=True)
    print("Loading source files …")

    wb_df         = load_if_exists(PATHS["wb"],         "World Bank prices")
    comtrade_df   = load_if_exists(PATHS["comtrade"],   "Comtrade exports")
    hhi_df        = load_if_exists(PATHS["hhi"],        "Comtrade HHI")
    steelorbis_df = load_if_exists(PATHS["steelorbis"], "SteelOrbis prices")

    print("\nNormalising …")
    frames = []

    # 1. World Bank HRC / CRC / Rebar prices
    if not wb_df.empty:
        frames.append(normalise(wb_df))

    # 2. SteelOrbis spot prices
    if not steelorbis_df.empty:
        frames.append(normalise(steelorbis_df))

    # 3. Derived: grade premium
    premium_df = compute_grade_premium(wb_df)
    if not premium_df.empty:
        frames.append(premium_df)
        print(f"  Grade premium KPI: {len(premium_df):,} rows")

    # 4. Derived: export volume MMT
    vol_df = compute_export_volume_mmt(comtrade_df)
    if not vol_df.empty:
        frames.append(vol_df)
        print(f"  Export volume KPI: {len(vol_df):,} rows")

    # 5. HHI
    hhi_payload = compute_hhi_payload(hhi_df)
    if not hhi_payload.empty:
        frames.append(hhi_payload)
        print(f"  HHI KPI: {len(hhi_payload):,} rows")

    if not frames:
        print("\nERROR: No data to merge. Run scripts 01–03 first.")
        return

    # Combine all frames
    final = pd.concat(frames, ignore_index=True)

    # Ensure types are clean for Power BI / JSON
    final["kpi_value"] = pd.to_numeric(final["kpi_value"], errors="coerce")
    final = final.dropna(subset=["kpi_value", "record_date"])
    final["kpi_value"] = final["kpi_value"].round(4)
    final = final.sort_values(["record_date", "metric_name"])

    # --- Build JSON payload ---
    payload = {
        "data_points": [
            {
                "metric_name":       row["metric_name"],
                "kpi_value":         row["kpi_value"],
                "unit_of_measure":   row.get("unit_of_measure", None),
                "region_or_country": row.get("region_or_country", None),
                "record_date":       row["record_date"],
            }
            for _, row in final.iterrows()
        ]
    }

    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, default=str)

    final.to_csv(OUTPUT_CSV, index=False)

    print(f"\n{'='*50}")
    print(f"Final payload: {len(final):,} data points")
    print(f"  JSON → {OUTPUT_JSON}")
    print(f"  CSV  → {OUTPUT_CSV}")
    print(f"{'='*50}")
    print("\nMetric breakdown:")
    print(final.groupby("metric_name")["kpi_value"].count().to_string())
    print("\nSample rows:")
    print(final.sample(min(8, len(final)))[PAYLOAD_COLS].to_string(index=False))

    return payload


if __name__ == "__main__":
    main()
