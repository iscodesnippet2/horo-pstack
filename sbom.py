"""CycloneDX 1.5 SBOM for horo-pstack, embedded in the wheel (PEP 770).

    python sbom.py generate <out.cdx.json>
    python sbom.py embed <wheel> <sbom.cdx.json> <release-copy.cdx.json>

The wheel has no dependencies. Its one third-party component is the pstack
content it ships, named by the cursor/plugins commit it came from, so a review
system can trace every skill to its source and license.
"""

import base64
import csv
import datetime as dt
import hashlib
import io
import json
import shutil
import sys
import uuid
import zipfile
from pathlib import Path

HERE = Path(__file__).parent
REPO = "https://github.com/iscodesnippet2/horo-pstack"


def generate(out: Path) -> None:
    vendor = HERE / "src" / "horo_pstack" / "_vendor"
    up = json.loads((vendor / "UPSTREAM.json").read_text())
    version = (HERE / "src" / "horo_pstack" / "_version.py").read_text().split('"')[1]
    this = f"pkg:pypi/horo-pstack@{version}"
    pstack = f"pkg:github/cursor/plugins@{up['commit']}#pstack"
    bom = {
        "bomFormat": "CycloneDX", "specVersion": "1.5", "version": 1,
        "serialNumber": f"urn:uuid:{uuid.uuid4()}",
        "metadata": {
            "timestamp": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
            "tools": {"components": [{"type": "application", "name": "horo-pstack sbom.py",
                                      "externalReferences": [{"type": "vcs", "url": REPO}]}]},
            "component": {
                "type": "library", "bom-ref": this, "name": "horo-pstack", "version": version, "purl": this,
                "description": "pstack skills packaged as a Hermes plugin (unofficial)",
                "licenses": [{"expression": "MIT"}],
                "externalReferences": [{"type": "vcs", "url": REPO},
                                       {"type": "distribution", "url": f"https://pypi.org/project/horo-pstack/{version}/"}],
                "pedigree": {"notes": "pstack skills copied from the commit below with one line added to each "
                                      "SKILL.md pointing to the Hermes harness; skills that need network "
                                      "services are left out: " + ", ".join(sorted(up["excluded"]))},
            },
        },
        "components": [{
            "type": "data", "bom-ref": pstack, "name": "pstack", "version": up["version"],
            "purl": pstack, "scope": "required", "licenses": [{"expression": up["license"]}],
            "copyright": "Copyright (c) 2026 Lauren Tan",
            "externalReferences": [{"type": "vcs", "url": f"{up['repository']}/tree/{up['commit']}/{up['path']}"}],
            "properties": [{"name": "horo:skills", "value": ",".join(up["skills"])}],
        }],
        "dependencies": [{"ref": this, "dependsOn": [pstack]}],
    }
    out.write_text(json.dumps(bom, indent=1) + "\n")
    print(f"[sbom] wrote {out}: pstack {up['version']} @ {up['commit'][:12]}")


def embed(wheel: Path, sbom: Path, release_copy: Path) -> None:
    with zipfile.ZipFile(wheel) as z:
        names = z.namelist()
        distinfo = next(n.split("/")[0] for n in names if n.endswith(".dist-info/RECORD"))
        record_name = f"{distinfo}/RECORD"
        entries = {n: z.read(n) for n in names}
        infos = {n: z.getinfo(n) for n in names}
    target = f"{distinfo}/sboms/{sbom.name}"
    data = sbom.read_bytes()
    entries[target] = data
    digest = base64.urlsafe_b64encode(hashlib.sha256(data).digest()).rstrip(b"=").decode()
    rows = [r for r in csv.reader(io.StringIO(entries[record_name].decode())) if r and r[0] != target]
    rows.insert(len(rows) - 1, [target, f"sha256={digest}", str(len(data))])  # RECORD stays last
    out = io.StringIO()
    csv.writer(out, lineterminator="\n").writerows(rows)
    entries[record_name] = out.getvalue().encode()
    tmp = wheel.with_suffix(".tmp")
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as z:
        for n in [n for n in names if n != record_name] + [target, record_name]:
            if n in (target, record_name):
                z.writestr(zipfile.ZipInfo(n, date_time=infos[record_name].date_time), entries[n],
                           compress_type=zipfile.ZIP_DEFLATED)
            else:
                z.writestr(infos[n], entries[n])
    shutil.move(tmp, wheel)
    bom = json.loads(data)
    bom["metadata"]["component"]["hashes"] = [
        {"alg": "SHA-256", "content": hashlib.sha256(wheel.read_bytes()).hexdigest()}]
    release_copy.write_text(json.dumps(bom, indent=1) + "\n")
    print(f"[sbom] embedded {target}; release copy {release_copy}")


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "generate":
        generate(Path(sys.argv[2]))
    elif len(sys.argv) == 5 and sys.argv[1] == "embed":
        embed(Path(sys.argv[2]).resolve(), Path(sys.argv[3]).resolve(), Path(sys.argv[4]))
    else:
        sys.exit(__doc__)
