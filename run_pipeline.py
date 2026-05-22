"""
ArcelorMittal BI Bootcamp — Master Pipeline Runner
===================================================
Runs all six scripts in order and produces a unified
Power BI ready dataset.

Usage:
    python run_pipeline.py

Optional flags:
    python run_pipeline.py --skip 2,3    # skip scripts 02 and 03
    python run_pipeline.py --only 1,4    # run only scripts 01 and 04
"""

import os
import sys
import time
import json
import argparse
import importlib.util
import traceback
import pandas as pd
from datetime import datetime

# ─────────────────────────────────────────────────────────────────────────────
# Pipeline definition — scripts in execution order
# ─────────────────────────────────────────────────────────────────────────────

PIPELINE = [
    {
        "step":   1,
        "script": "01_worldbank_prices.py",
        "label":  "Track 1 — Steel & Iron Ore Prices (World Bank + Eurostat + SteelOrbis)",
        "output": "data/wb_steel_prices.csv",
    },
    {
        "step":   2,
        "script": "02_comtrade_exports.py",
        "label":  "Track 1 — Steel Trade Flows & HHI (WSA press releases + Eurostat)",
        "output": "data/comtrade_steel_exports.csv",
    },
    {
        "step":   3,
        "script": "03_steelorbis_scraper.py",
        "label":  "Track 1 — SteelOrbis HRC Spot Prices",
        "output": "data/steelorbis_prices.csv",
    },
    {
        "step":   4,
        "script": "04_merge_and_payload.py",
        "label":  "Track 1 — Merge & Final KPI Payload",
        "output": "data/steel_kpi_payload.csv",
    },
    {
        "step":   5,
        "script": "05_green_steel_esg_free.py",
        "label":  "Track 2 — Green Steel & Competitor ESG Benchmarks",
        "output": "data/green_steel_benchmarks.csv",
    },
    {
        "step":   6,
        "script": "06_supply_chain_risk.py",
        "label":  "Track 3 — Supply Chain Risk & Freight Indexes",
        "output": "data/supply_chain_metrics.csv",
    },
]


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

RESET  = "\033[0m"
GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
BOLD   = "\033[1m"
CYAN   = "\033[96m"

def banner(text: str, char: str = "=", width: int = 62):
    print(f"\n{BOLD}{char * width}{RESET}")
    print(f"{BOLD}  {text}{RESET}")
    print(f"{BOLD}{char * width}{RESET}")

def status_line(step: int, label: str, state: str, elapsed: float = 0):
    icons = {"running": f"{YELLOW}⟳ RUNNING {RESET}",
             "ok":      f"{GREEN}✓ DONE    {RESET}",
             "skip":    f"{CYAN}⊘ SKIPPED {RESET}",
             "fail":    f"{RED}✗ FAILED  {RESET}"}
    icon = icons.get(state, "")
    timing = f"({elapsed:.1f}s)" if elapsed else ""
    print(f"  Step {step}  {icon}  {label} {timing}")

def run_script(script_path: str) -> bool:
    """Import and execute a script's main() function in the current process."""
    spec   = importlib.util.spec_from_file_location("_step", script_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if hasattr(module, "main"):
        module.main()
    return True

def output_row_count(path: str) -> str:
    if not os.path.exists(path):
        return "file not found"
    try:
        df = pd.read_csv(path)
        return f"{len(df):,} rows"
    except Exception:
        return "unreadable"


# ─────────────────────────────────────────────────────────────────────────────
# Post-pipeline: merge all outputs into one master CSV + JSON
# ─────────────────────────────────────────────────────────────────────────────

def merge_all_outputs():
    banner("Merging all outputs into master dataset", "-")

    frames = []

    # Track 1 — KPI payload (already merged by script 04)
    kpi_path = "data/steel_kpi_payload.csv"
    if os.path.exists(kpi_path):
        df = pd.read_csv(kpi_path)
        df["track"] = "Track1_SteelMarket"
        frames.append(df)
        print(f"  Track 1 payload : {len(df):,} rows")

    # Track 2 — ESG benchmarks (reshape to match KPI schema)
    esg_path = "data/green_steel_benchmarks.csv"
    if os.path.exists(esg_path):
        df = pd.read_csv(esg_path)
        df_mapped = pd.DataFrame({
            "metric_name":       df["company_peer"] + " — " + df["metric_name"],
            "kpi_value":         pd.to_numeric(df["kpi_value"], errors="coerce"),
            "unit_of_measure":   df["unit_of_measure"],
            "region_or_country": df["company_peer"],
            "record_date":       df["target_or_current_year"].astype(str) + "-01-01",
            "track":             "Track2_GreenSteel",
        })
        frames.append(df_mapped)
        print(f"  Track 2 ESG     : {len(df_mapped):,} rows")

    # Track 3 — Supply chain (reshape)
    sc_path = "data/supply_chain_metrics.csv"
    if os.path.exists(sc_path):
        df = pd.read_csv(sc_path)
        df_mapped = pd.DataFrame({
            "metric_name":       df["material_or_route"] + " — " + df["metric_name"],
            "kpi_value":         pd.to_numeric(df["kpi_value"], errors="coerce"),
            "unit_of_measure":   df["unit_of_measure"],
            "region_or_country": df["material_or_route"].str.extract(r"- ([^-]+)$")[0].str.strip().fillna("Global"),
            "record_date":       df.get("date", datetime.today().strftime("%Y-%m-%d")),
            "risk_level":        df["risk_level_assessment"],
            "track":             "Track3_SupplyChain",
        })
        frames.append(df_mapped)
        print(f"  Track 3 Supply  : {len(df_mapped):,} rows")

    if not frames:
        print(f"  {RED}No output files found to merge.{RESET}")
        return

    master = pd.concat(frames, ignore_index=True)
    master_path = "data/master_powerbi_dataset.csv"
    master.to_csv(master_path, index=False)

    # Also write a summary JSON
    summary = {
        "generated_at": datetime.now().isoformat(),
        "total_rows":   len(master),
        "tracks": {
            "Track1_SteelMarket": int((master["track"] == "Track1_SteelMarket").sum()),
            "Track2_GreenSteel":  int((master["track"] == "Track2_GreenSteel").sum()),
            "Track3_SupplyChain": int((master["track"] == "Track3_SupplyChain").sum()),
        },
        "files": {
            "master_csv":               master_path,
            "track1_kpi_payload":       kpi_path,
            "track2_esg_benchmarks":    esg_path,
            "track3_supply_chain":      sc_path,
            "track1_hhi":               "data/comtrade_hhi.csv",
        }
    }
    with open("data/pipeline_summary.json", "w") as f:
        json.dump(summary, f, indent=2)

    print(f"\n  {GREEN}{BOLD}Master dataset : {len(master):,} total rows{RESET}")
    print(f"  Saved -> {master_path}")
    print(f"  Saved -> data/pipeline_summary.json")
    print(f"\n  Track breakdown:")
    print(master["track"].value_counts().to_string())


# ─────────────────────────────────────────────────────────────────────────────
# Main runner
# ─────────────────────────────────────────────────────────────────────────────

def parse_args():
    parser = argparse.ArgumentParser(description="ArcelorMittal BI Pipeline Runner")
    parser.add_argument("--skip", type=str, default="",
                        help="Comma-separated step numbers to skip (e.g. --skip 2,3)")
    parser.add_argument("--only", type=str, default="",
                        help="Comma-separated step numbers to run only (e.g. --only 1,4)")
    return parser.parse_args()


def main():
    args      = parse_args()
    skip_set  = {int(x) for x in args.skip.split(",") if x.strip().isdigit()}
    only_set  = {int(x) for x in args.only.split(",") if x.strip().isdigit()}
    base_dir  = os.path.dirname(os.path.abspath(__file__))

    banner("ArcelorMittal BI Bootcamp — Master Pipeline")
    print(f"  Started : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Scripts : {base_dir}")
    if skip_set: print(f"  Skipping steps : {skip_set}")
    if only_set: print(f"  Running only   : {only_set}")

    results   = []
    t_total   = time.time()

    for step in PIPELINE:
        n      = step["step"]
        label  = step["label"]
        script = os.path.join(base_dir, step["script"])
        output = step["output"]

        # Filter logic
        if only_set and n not in only_set:
            status_line(n, label, "skip")
            results.append({"step": n, "status": "skipped", "elapsed": 0})
            continue
        if n in skip_set:
            status_line(n, label, "skip")
            results.append({"step": n, "status": "skipped", "elapsed": 0})
            continue

        banner(f"Step {n} / {len(PIPELINE)}", "-", 62)
        status_line(n, label, "running")
        t0 = time.time()

        try:
            run_script(script)
            elapsed = time.time() - t0
            rows    = output_row_count(output)
            status_line(n, label, "ok", elapsed)
            print(f"  Output  : {output} — {rows}")
            results.append({"step": n, "status": "ok", "elapsed": elapsed, "rows": rows})
        except Exception:
            elapsed = time.time() - t0
            status_line(n, label, "fail", elapsed)
            traceback.print_exc()
            results.append({"step": n, "status": "failed", "elapsed": elapsed})
            print(f"\n  {YELLOW}Continuing to next step ...{RESET}")

    # ── Merge all outputs ─────────────────────────────────────────────────────
    merge_all_outputs()

    # ── Final summary ─────────────────────────────────────────────────────────
    total_elapsed = time.time() - t_total
    banner("Pipeline Complete")
    print(f"  Finished : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Total time : {total_elapsed:.1f}s\n")

    print(f"  {'Step':<6} {'Status':<10} {'Time':>7}  Script")
    print(f"  {'-'*55}")
    for r in results:
        step_info = next(s for s in PIPELINE if s["step"] == r["step"])
        color = GREEN if r["status"] == "ok" else (YELLOW if r["status"] == "skipped" else RED)
        print(f"  {r['step']:<6} {color}{r['status']:<10}{RESET} {r['elapsed']:>6.1f}s  {step_info['script']}")

    failed = [r for r in results if r["status"] == "failed"]
    if failed:
        print(f"\n  {RED}Failed steps: {[r['step'] for r in failed]}{RESET}")
        print(f"  Re-run failed steps with: python run_pipeline.py --only {','.join(str(r['step']) for r in failed)}")
    else:
        print(f"\n  {GREEN}{BOLD}All steps completed successfully.{RESET}")

    print(f"\n  Power BI files ready:")
    print(f"    data/master_powerbi_dataset.csv   ← load this first")
    print(f"    data/steel_kpi_payload.csv         ← Track 1")
    print(f"    data/green_steel_benchmarks.csv    ← Track 2")
    print(f"    data/supply_chain_metrics.csv      ← Track 3")


if __name__ == "__main__":
    main()
