"""Where things live. Zillow and Census files are read (read-only) from the git-ignored data_external/ folder;
nothing from them is committed. Override with HF_ZILLOW_DIR / HF_CENSUS_XLSX if the files are elsewhere."""
from __future__ import annotations
import os
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
_SIB = REPO / "data_external"
ZILLOW_DIR = Path(os.environ.get("HF_ZILLOW_DIR", _SIB / "zillow" / "v1_20261109"))
CENSUS_XLSX = Path(os.environ.get("HF_CENSUS_XLSX", _SIB / "census" / "list1_2023.xlsx"))
VINTAGE = ZILLOW_DIR.name

TMP = REPO / "tmp"                       # derived from Zillow data: never committed
TABLES = REPO / "reports" / "tables"
FIGURES = REPO / "reports" / "figures"
PAP = REPO / "docs" / "pre_analysis_plan.md"
PAP_HASH = REPO / "docs" / "pre_analysis_plan.sha256"

TARGET_FILES = {
    "inventory": "Metro_invt_fs_uc_sfrcondo_month.csv",
    "new_listings": "Metro_new_listings_uc_sfrcondo_month.csv",
}
ATTRIBUTION = "Data Provided by Zillow Group"
