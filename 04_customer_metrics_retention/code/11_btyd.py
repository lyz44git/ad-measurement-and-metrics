# Parameter-recovery check for the BG/NBD and Gamma-Gamma implementations in btyd_impl.py.
# Usage: python code/11_btyd.py out/11_btyd_recovery.json
import runpy
from pathlib import Path

runpy.run_path(str(Path(__file__).with_name("btyd_impl.py")), run_name="__main__")
