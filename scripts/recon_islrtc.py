"""One-shot reconnaissance: probe ISLRTC dictionary URLs and log what we find.

Outputs findings to scripts/recon_islrtc_report.md. Manual review required.
"""

import json
from pathlib import Path
from urllib.parse import urljoin

import httpx

CANDIDATES = [
    "https://islrtc.nic.in/",
    "https://www.islrtc.nic.in/dictionary-0",
    "https://indiansignlanguage.org/dictionary/",
    "https://www.signlanguage.in/",
]

REPORT = Path(__file__).parent / "recon_islrtc_report.md"


def probe(url: str) -> dict:
    try:
        r = httpx.get(url, timeout=15, follow_redirects=True, headers={"User-Agent": "Project-AID recon"})
        return {
            "url": url,
            "final_url": str(r.url),
            "status": r.status_code,
            "content_type": r.headers.get("content-type", ""),
            "length": len(r.content),
            "title_snippet": r.text[:400].replace("\n", " ") if "text" in r.headers.get("content-type", "") else "",
        }
    except Exception as e:
        return {"url": url, "error": repr(e)}


def main():
    findings = [probe(u) for u in CANDIDATES]
    lines = ["# ISLRTC reconnaissance report\n"]
    lines.append("| URL | Final | Status | Type | Bytes |")
    lines.append("|---|---|---|---|---|")
    for f in findings:
        if "error" in f:
            lines.append(f"| {f['url']} | — | ERROR | {f['error']} | — |")
        else:
            lines.append(
                f"| {f['url']} | {f['final_url']} | {f['status']} | "
                f"{f['content_type']} | {f['length']} |"
            )
    lines.append("\n## Raw JSON\n\n```json\n" + json.dumps(findings, indent=2) + "\n```\n")
    lines.append(
        "\n## Manual review checklist\n"
        "- [ ] Is there a searchable dictionary page with per-word URLs?\n"
        "- [ ] Are videos hosted on the site or YouTube/other CDN?\n"
        "- [ ] Is there a robots.txt? What does it allow?\n"
        "- [ ] Is there a Terms page referencing redistribution?\n"
        "- [ ] Is the word list downloadable (CSV, JSON, XLS) directly?\n"
    )
    REPORT.write_text("\n".join(lines))
    print(f"wrote {REPORT}")


if __name__ == "__main__":
    main()
