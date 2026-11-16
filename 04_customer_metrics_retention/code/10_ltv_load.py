# UCI Online Retail II: load both sheets, audit, clean, save parquet. Raw file read-only.
import sys, json, re
import pandas as pd, numpy as np
RAW, DER, OUT = sys.argv[1], sys.argv[2], sys.argv[3]
sh = pd.read_excel(RAW, sheet_name=None, dtype={"Invoice": str, "StockCode": str})
a = {"sheets": {k: int(len(v)) for k, v in sh.items()}}
parts = []
for k, v in sh.items():
    v = v.copy(); v.columns = [c.strip() for c in v.columns]; v["_sheet"] = k; parts.append(v)
df = pd.concat(parts, ignore_index=True)
cols = [c for c in df.columns if c != "_sheet"]
a["rows_raw"] = int(len(df)); a["columns"] = cols
a["date_min"], a["date_max"] = str(df.InvoiceDate.min()), str(df.InvoiceDate.max())
a["missing_customer_rows_before_dedup"] = int(df["Customer ID"].isna().sum())
# duplicates: (i) identical lines appearing in BOTH sheets (sheet overlap, true double-loading) vs (ii) identical lines repeated within one sheet
within = sum(int(p_.duplicated(subset=cols).sum()) for p_ in parts)
a["exact_duplicate_rows_total"] = int(df.duplicated(subset=cols).sum())
a["duplicate_rows_within_sheet"] = within
a["duplicate_rows_sheet_overlap"] = a["exact_duplicate_rows_total"] - within
a["dedup_choice"] = "drop all exact duplicates (sheet overlap = double loading; within-sheet identical lines treated as data-entry duplicates; may remove some genuine repeated lines)"
df = df.drop_duplicates(subset=cols)[cols]
a["rows_after_dedup"] = int(len(df)); a["missing_customer_rows"] = int(df["Customer ID"].isna().sum())
df["is_cancel"] = df.Invoice.str.startswith("C")
a["cancel_rows"] = int(df.is_cancel.sum())
a["nonpositive_price_rows"] = int((df.Price <= 0).sum())
# non-merchandise stock codes (postage, fees, adjustments, manual, bank charges, samples, gift vouchers)
non_merch = df.StockCode.str.upper().str.match(r"^(POST|DOT|M|C2|BANK CHARGES|AMAZONFEE|ADJUST.*|B|D|S|CRUK|PADS|TEST.*|GIFT.*|SP\d+)$", na=False)
a["non_merch_rows"] = int(non_merch.sum()); a["non_merch_codes"] = sorted(df.loc[non_merch, "StockCode"].str.upper().unique().tolist())[:40]
df["revenue"] = df.Quantity * df.Price
c = df[(~non_merch) & df["Customer ID"].notna() & (df.Price > 0)].copy()
c["cid"] = c["Customer ID"].astype(int)
a["rows_clean_with_customer"] = int(len(c)); a["customers"] = int(c.cid.nunique())
a["revenue_gross_sales"] = float(c.loc[~c.is_cancel, "revenue"].sum()); a["revenue_cancellations"] = float(c.loc[c.is_cancel, "revenue"].sum())
a["share_rows_uk"] = float((c.Country == "United Kingdom").mean())
c[["Invoice", "StockCode", "Quantity", "InvoiceDate", "Price", "cid", "Country", "is_cancel", "revenue"]].to_parquet(f"{DER}/uci_lines.parquet")
json.dump(a, open(f"{OUT}/10_ltv_audit.json", "w"), indent=1)
print(json.dumps(a, indent=1))
