"""Check that every number written in the memo's prose also appears in a script-generated file.

Generated tables inside <!-- BEGIN/END --> markers are skipped (the report script writes them). For the prose, each
decimal number, percentage or number with a thousands separator must occur verbatim in reports/results_tables.md.
Plain integers (counts like 24 origins, h = 12, years) are not checked. Exit code 1 lists the unmatched numbers."""
from __future__ import annotations
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def main(path=REPO / "reports" / "memo.md"):
    memo = path.read_text()
    prose = re.sub(r"<!-- BEGIN:(\w+) -->.*?<!-- END:\1 -->", "", memo, flags=re.S)
    prose = re.sub(r"`[^`]*`", "", prose)                         # code spans (hashes, file names)
    source = (REPO / "reports" / "results_tables.md").read_text()
    toks = re.findall(r"(?<![\w.-])(\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+\.\d+%?|\d+%)(?![\w-])", prose)
    missing = sorted({t for t in toks if t not in source})
    print(f"{len(toks)} numbers in prose, {len(set(toks)) - len(missing)} distinct found, {len(missing)} missing")
    if missing:
        print("missing:", ", ".join(missing))
        sys.exit(1)


if __name__ == "__main__":
    main(Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else REPO / "reports" / "memo.md")
