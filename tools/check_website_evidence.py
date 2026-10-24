"""Check saved public website files without network or browser access."""
import hashlib
import json
from pathlib import Path

root = Path(__file__).resolve().parents[1]
source = root / "inspection"
records = json.loads((source / "manifest.json").read_text(encoding="utf-8"))
terms = ("bl-auth", "bl-switch", "is_retry", ".apk")
counts = dict.fromkeys(terms, 0)
for record in records:
    data = (source / record["file"]).read_bytes()
    if hashlib.sha256(data).hexdigest() != record["sha256"]:
        raise SystemExit("FAIL: A saved file does not match its recorded hash.")
    text = data.decode("utf-8")
    for term in terms:
        counts[term] += text.lower().count(term.lower())
report = {
    "inspection_date": "2026-10-24",
    "entry_url": "https://c.mi.com/global/",
    "entry_sha256": hashlib.sha256((source / "home.html").read_bytes()).hexdigest(),
    "javascript_files": len(records),
    "javascript_bytes": sum(record["bytes"] for record in records),
    "literal_matches": counts,
    "limits": "Static text inspection only. No JavaScript was executed. No account or application API was called.",
    "files": records,
}
(root / "doc/evidence/website-manifest-2026-10-24.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
print(f"PASS: {len(records)} public JavaScript files match their hashes.")
print(json.dumps(counts))
