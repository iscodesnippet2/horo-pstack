"""Assemble src/horo_pstack/_vendor from a cursor/plugins checkout at one commit.

    python vendor.py <cursor-plugins-checkout> [post]

The version is pstack's own; `post` (1, 2, ...) makes it 0.15.36.post1 when
only this packaging changed and pstack did not.

A release is a pure function of (pstack commit, this file, harness/). Every
check fails closed: an excluded skill that no longer exists, a license that is
no longer MIT, or a skill whose name does not match its directory stops the
build instead of shipping something nobody reviewed.
"""

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).parent
OUT = HERE / "src" / "horo_pstack" / "_vendor"

# Skills left out, each for a reason an offline Hermes install cannot work around.
EXCLUDED = {
    "statechart": "needs TLA+ (Java) and a TypeScript runtime",
    "create-formal-verification-skill": "needs model checkers that are not on the pip/npm mirror",
    "maintain-formal-verification-skill": "maintains what create-formal-verification-skill makes",
    "make-bot-ui": "drives a hosted Grok Bot over a webhook",
    "ketchup-video": "renders video with tools outside the mirror",
    "setup-pstack": "configures per-role Cursor models; Hermes runs subagents on the session model",
    "automate-me": "mines Cursor transcripts",
    "recall": "mines Cursor transcripts",
}

NAME_RE = re.compile(r"^name:\s*['\"]?([^'\"\n]+)", re.M)

HERMES_POINTER = (
    "> **Hermes:** this skill uses Cursor names. Before following it, call "
    "`skill_view(\"pstack:hermes-harness\")` once per session and map every tool, subagent, model, "
    "and path through it. Other pstack skills and their files load with `skill_view(\"pstack:<name>\", "
    "file_path=...)`, never from disk.\n\n"
)


def fail(msg):
    sys.exit(f"[vendor] FAIL {msg}")


def main(checkout, post=None):
    src = checkout / "pstack"
    manifest = json.loads((src / "plugin.json").read_text())
    if manifest.get("license") != "MIT" or not (src / "LICENSE").read_text().startswith("MIT License"):
        fail("pstack is no longer MIT-licensed; review before shipping")
    commit = subprocess.run(["git", "-C", str(checkout), "rev-parse", "HEAD"],
                            capture_output=True, text=True, check=True).stdout.strip()

    available = {p.parent.name for p in (src / "skills").glob("*/SKILL.md")}
    if missing := set(EXCLUDED) - available:
        fail(f"excluded skills no longer upstream: {sorted(missing)}")

    if OUT.exists():
        shutil.rmtree(OUT)
    shutil.copytree(src / "skills", OUT / "skills",
                    ignore=lambda d, names: [n for n in names if Path(d) == src / "skills" and n in EXCLUDED])
    for skill_md in (OUT / "skills").glob("*/SKILL.md"):
        text = skill_md.read_text()
        m = NAME_RE.search(text)
        if not m or m.group(1).strip() != skill_md.parent.name:
            fail(f"{skill_md.parent.name}: frontmatter name does not match its directory")
        # A model given only a skill's name never opened the harness and went
        # looking for Cursor's model config on disk. The one line every skill
        # gains is the pointer; the skills are otherwise byte-for-byte upstream.
        end = re.search(r"\n---\s*\n", text[3:])
        if not text.startswith("---") or end is None:
            fail(f"{skill_md.parent.name}: no frontmatter to insert the Hermes pointer after")
            continue
        cut = end.end() + 3
        skill_md.write_text(text[:cut] + HERMES_POINTER + text[cut:])

    harness = OUT / "harness" / "hermes-harness"
    shutil.copytree(HERE / "harness" / "hermes-harness", harness)
    shutil.copytree(src / "agents", harness / "agents")
    (harness / "pstack" / "docs").mkdir(parents=True)
    shutil.copytree(src / "docs" / "guide", harness / "pstack" / "docs" / "guide",
                    ignore=shutil.ignore_patterns("images"))
    shutil.copy2(src / "README.md", harness / "pstack" / "README.md")
    shutil.copy2(src / "LICENSE", OUT / "LICENSE")

    version = manifest["version"] + (f".post{post}" if post else "")
    shipped = sorted(p.parent.name for p in (OUT / "skills").glob("*/SKILL.md"))
    (OUT / "UPSTREAM.json").write_text(json.dumps({
        "repository": "https://github.com/cursor/plugins",
        "path": "pstack",
        "commit": commit,
        "version": manifest["version"],
        "license": manifest["license"],
        "skills": shipped,
        "excluded": EXCLUDED,
    }, indent=2) + "\n")
    (HERE / "src" / "horo_pstack" / "_version.py").write_text(f'__version__ = "{version}"\n')
    print(f"[vendor] ok   horo-pstack {version} from pstack {manifest['version']} @ {commit[:12]}: "
          f"{len(shipped)} skills, {len(EXCLUDED)} excluded, + hermes-harness")


if __name__ == "__main__":
    if len(sys.argv) not in (2, 3) or (len(sys.argv) == 3 and not sys.argv[2].isdigit()):
        sys.exit(__doc__)
    main(Path(sys.argv[1]).resolve(), sys.argv[2] if len(sys.argv) == 3 else None)
