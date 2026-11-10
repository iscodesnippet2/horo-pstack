"""Hermes plugin: register each vendored pstack skill as ``pstack:<name>``."""

from pathlib import Path

from horo_pstack._version import __version__

VENDOR = Path(__file__).parent / "_vendor"
SKILL_DIRS = (VENDOR / "harness", VENDOR / "skills")


def iter_skills():
    for base in SKILL_DIRS:
        yield from sorted(base.glob("*/SKILL.md"))


def register(ctx):
    from agent.skill_utils import parse_frontmatter

    for skill_md in iter_skills():
        frontmatter, _ = parse_frontmatter(skill_md.read_text(encoding="utf-8"))
        ctx.register_skill(
            skill_md.parent.name,
            skill_md,
            frontmatter.get("description", ""),
            frontmatter,
        )


__all__ = ["__version__", "register"]
