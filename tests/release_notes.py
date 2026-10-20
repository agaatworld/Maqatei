"""Print the CHANGELOG-ar.md section of one version (used as the GitHub release notes)."""
import re
import sys
from pathlib import Path

text = (Path(__file__).resolve().parent.parent / "CHANGELOG-ar.md").read_text(encoding="utf-8")
m = re.search(r"^## " + re.escape(sys.argv[1]) + r".*?(?=^## |\Z)", text, re.S | re.M)
print(m.group(0).strip() if m else "تحسينات وإصلاحات.")
