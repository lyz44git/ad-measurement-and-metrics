"""Load the Criteo attribution file once, keep the columns used here and profile it.

Usage: python code/load_attribution.py <criteo_attribution_dataset.tsv.gz> <derived_dir> <out_dir>
Writes <derived_dir>/criteo_attr.parquet and <out_dir>/00_profile.json.
"""
import json
import sys
from pathlib import Path

import pandas as pd

COLS = ["timestamp", "uid", "campaign", "conversion", "conversion_timestamp", "conversion_id", "attribution", "click",
        "click_pos", "click_nb", "cost", "cpo", "time_since_last_click"]


def profile(d):
    """Counts that decide what kind of attribution the file supports (touches per conversion, campaigns per conversion)."""
    conv = d[d.conversion == 1]
    g = conv.groupby("conversion_id").agg(n=("timestamp", "size"), ncamp=("campaign", "nunique"),
                                          nclick=("click", "sum"), attr=("attribution", "max"))
    return dict(rows=int(len(d)), users=int(d.uid.nunique()), campaigns=int(d.campaign.nunique()),
                days=float(d.timestamp.max() / 86400), conv_rows=int(len(conv)), conversions=int(len(g)),
                conv_attributed=int(g.attr.sum()), share_conv_multi_touch=float((g.n > 1).mean()),
                share_conv_multi_campaign=float((g.ncamp > 1).mean()), touches_per_conv_mean=float(g.n.mean()),
                touches_per_conv_median=float(g.n.median()), touches_p90=float(g.n.quantile(.9)),
                share_conv_with_click=float((g.nclick > 0).mean()), click_rate=float(d.click.mean()),
                conv_per_user_max=int(conv.groupby("uid").conversion_id.nunique().max()),
                users_converting=int(conv.uid.nunique()))


def main(src, derived, out):
    d = pd.read_csv(src, sep="\t", usecols=COLS)
    Path(derived).mkdir(parents=True, exist_ok=True); Path(out).mkdir(parents=True, exist_ok=True)
    d.to_parquet(Path(derived) / "criteo_attr.parquet", index=False)
    res = profile(d)
    json.dump(res, open(Path(out) / "00_profile.json", "w"), indent=1)
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main(*sys.argv[1:4])
