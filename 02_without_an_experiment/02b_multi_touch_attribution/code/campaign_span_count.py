"""Share of reconstructed converting paths that touch more than one campaign.

Added after the main run. Uses the same paths as code/mta.py (build_paths), so the multi-touch test paths are the
64,159 paths on which the 3.6% campaign credit shift is computed. Does not change mta.py or out/mta.json.

Usage: python code/campaign_span_count.py <derived_dir/criteo_attr.parquet> <out_dir>
Writes <out_dir>/campaign_span.json. A few minutes and about 10 GB of memory on the full file.
"""
import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from mta import build_paths  # noqa: E402


def span_shares(p):
    """Number of paths and share touching two or more campaigns, for each group of converting paths."""
    conv = p[p.y == 1]
    ncamp = conv.groupby("uid").agg(ncamp=("campaign", "nunique"), n=("n", "first"), test=("test", "first"))
    groups = {"test_multi_touch": ncamp[ncamp.test & (ncamp.n > 1)], "test_all": ncamp[ncamp.test],
              "all_converting": ncamp}
    return {k: {"paths": int(len(g)), "share_two_or_more_campaigns": float((g.ncamp > 1).mean())}
            for k, g in groups.items()}


def main(src, out):
    d = pd.read_parquet(src, columns=["timestamp", "uid", "campaign", "conversion", "conversion_timestamp",
                                      "conversion_id", "click"])
    res = span_shares(build_paths(d))
    Path(out).mkdir(parents=True, exist_ok=True)
    json.dump(res, open(Path(out) / "campaign_span.json", "w"), indent=1)
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
