"""Install a horo-pstack wheel next to horo-next in a clean venv and check it works.

    python verify_wheel.py <wheel> <python> <horo-next-version> [<horo-next-wheel>]

horo-next comes from PyPI at that version, or from a local wheel when one is
given (a release not published yet). horo-pstack itself installs with
--no-index, as it would from an air-gapped mirror that carries only it.

Runs with a throwaway HERMES_HOME and HOME: a model following these skills
once went looking for config in ~, and a check here must not see the real one.
"""

import json
import os
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

WHEEL, PYV, HORO_NEXT = Path(sys.argv[1]).resolve(), sys.argv[2], sys.argv[3]
HORO_NEXT_WHEEL = Path(sys.argv[4]).resolve() if len(sys.argv) > 4 else None
failures: list[str] = []


def check(cond: bool, label: str, detail: str = "") -> None:
    print(f"  {'ok  ' if cond else 'FAIL'} {label}" + (f" — {detail}" if detail else ""))
    if not cond:
        failures.append(label)


names = zipfile.ZipFile(WHEEL).namelist()
distinfo = next(n.split("/")[0] for n in names if n.endswith(".dist-info/RECORD"))
check(f"{distinfo}/licenses/LICENSE" in names, "horo-pstack MIT license in dist-info")
check(any(n.startswith(f"{distinfo}/licenses/") and n.endswith("_vendor/LICENSE") for n in names),
      "pstack's MIT license in dist-info")
check(any(n.startswith(f"{distinfo}/sboms/") for n in names), "CycloneDX SBOM embedded (PEP 770)")
up = json.loads(zipfile.ZipFile(WHEEL).read("horo_pstack/_vendor/UPSTREAM.json"))

with tempfile.TemporaryDirectory(prefix="horo-pstack-verify-") as t:
    tmp = Path(t)
    venv, home = tmp / "venv", tmp / "hermes-home"
    home.mkdir()
    env = {**os.environ, "HERMES_HOME": str(home), "HOME": str(tmp / "home"), "VIRTUAL_ENV": str(venv),
           "NO_COLOR": "1", "HERMES_GATEWAY_LOCK_DIR": str(tmp / "host-state"),
           "XDG_STATE_HOME": str(tmp / "state")}
    (tmp / "home").mkdir()

    def run(*cmd):
        return subprocess.run(cmd, capture_output=True, text=True, env=env, cwd=tmp)

    py, hermes = venv / "bin" / "python", venv / "bin" / "hermes"
    print(f"[verify] Python {PYV}, horo-next {HORO_NEXT}")
    r = run("uv", "venv", "-q", "-p", PYV, str(venv))
    check(r.returncode == 0, "venv", r.stderr[-300:])
    r = run("uv", "pip", "install", "-q", str(HORO_NEXT_WHEEL) if HORO_NEXT_WHEEL else f"horo-next=={HORO_NEXT}")
    check(r.returncode == 0, f"horo-next {HORO_NEXT} installs", r.stderr[-300:])
    r = run("uv", "pip", "install", "-q", "--offline", "--no-index", str(WHEEL))
    check(r.returncode == 0, "horo-pstack installs with no index", r.stderr[-300:])

    def row() -> str:
        out = run(str(hermes), "plugins", "list").stdout
        return next((ln for ln in out.splitlines() if "pstack" in ln), "")

    check("not enabled" in row(), "found as an entry-point plugin, off until enabled", row().strip())
    r = run(str(hermes), "plugins", "enable", "pstack")
    check(r.returncode == 0 and "enabled" in row() and "not enabled" not in row(),
          "`hermes plugins enable pstack`", (r.stdout + r.stderr).strip()[-300:])

    probe = r'''
import json, sys
from hermes_cli.plugins import discover_plugins
discover_plugins(force=True)
from tools.skills_tool import skill_view
from agent.skill_commands import build_preloaded_skills_prompt
up = json.loads(sys.argv[1])
def view(name, path=None):
    return json.loads(skill_view(name, file_path=path) if path else skill_view(name))
out = {
    "loaded": [s for s in up["skills"] if view(f"pstack:{s}").get("success")],
    "pointer": all("pstack:hermes-harness" in view(f"pstack:{s}").get("content", "") for s in up["skills"]),
    "harness": view("pstack:hermes-harness").get("success"),
    "playbook": view("pstack:poteto-mode", "playbooks/bug-fix.md").get("success"),
    "agent": view("pstack:hermes-harness", "agents/comment-sicko.md").get("success"),
    "excluded": [s for s in up["excluded"] if view(f"pstack:{s}").get("success")],
    "preload": len(build_preloaded_skills_prompt(["pstack:poteto-mode"])[1]),
}
print("RESULT " + json.dumps(out))
'''
    r = run(str(py), "-I", "-c", probe, json.dumps(up))
    line = next((ln for ln in r.stdout.splitlines() if ln.startswith("RESULT ")), None)
    if line is None:
        check(False, "skill probe ran", r.stderr[-500:])
    else:
        d = json.loads(line[7:])
        check(len(d["loaded"]) == len(up["skills"]), "every shipped skill loads as pstack:<name>",
              f"{len(d['loaded'])}/{len(up['skills'])}")
        check(d["pointer"], "every skill points to pstack:hermes-harness")
        check(d["harness"] and d["agent"], "harness and its subagent briefs load")
        check(d["playbook"], "skill files load through skill_view(file_path=...)")
        check(d["excluded"] == [], "excluded skills are absent", str(d["excluded"]))
        check(d["preload"] == 1, "`-s pstack:poteto-mode` preloads")

    r = run("uv", "pip", "uninstall", "-q", "horo-pstack")
    r = run(str(py), "-I", "-c", "import json\nfrom hermes_cli.plugins import discover_plugins\n"
            "discover_plugins(force=True)\nfrom tools.skills_tool import skill_view\n"
            "print(json.loads(skill_view('pstack:poteto-mode')).get('success'))")
    check(r.stdout.strip().endswith("False"), "uninstall removes the skills", r.stdout.strip()[-100:])
    run(str(hermes), "gateway", "stop")

print(f"[verify] {len(failures)} check(s) failed" if failures else "[verify] all checks passed")
sys.exit(1 if failures else 0)
