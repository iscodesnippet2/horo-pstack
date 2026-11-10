# horo-pstack

[pstack](https://github.com/cursor/plugins/tree/main/pstack) skills, packaged as a
Hermes plugin so they install with `pip` from a mirror. Unofficial; not
affiliated with Cursor or the pstack author. pstack is MIT-licensed by Lauren
Tan; its license ships in the wheel.

Not the PyPI package `pstack`, which is an unrelated stack-dump tool.

## Install

```bash
pip install horo-pstack
hermes plugins enable pstack
```

The wheel has no dependencies, so a mirror that carries `horo-pstack` and
`horo-next` is enough.

| horo-next | Enable | Start a task |
|---|---|---|
| 0.21.5 | `hermes plugins enable pstack` | `hermes chat -s pstack:poteto-mode`, or ask the agent to load `pstack:poteto-mode`. No slash command. |
| 0.23.0 and later | `hermes plugins enable pstack` | `/pstack:poteto-mode <task>` in the interactive CLI, or `-s pstack:poteto-mode` |

On 0.23, the enabled skills are also listed in the system prompt's skill
index (about 6,000 characters for all of them).

Each skill loads as `pstack:<name>`. Every skill starts with a pointer to
`pstack:hermes-harness`, which maps the Cursor tool names, subagent fields,
models and paths pstack uses to their Hermes equivalents. Hermes runs every
subagent on the session model.

### Using a MiniMax or Anthropic-compatible endpoint on horo-next 0.23

That provider needs the `anthropic` package, which is not a horo-next
dependency, and 0.23 does not install it on demand:

```bash
pip install anthropic==0.125.0
hermes gateway stop
```

`hermes chat` runs through a background gateway; stop it so the next chat
starts one that sees the new package.

## What is left out

Skills that need a network service or a tool an offline mirror does not
carry: `statechart`, `create-formal-verification-skill`,
`maintain-formal-verification-skill`, `make-bot-ui`, `ketchup-video`,
`setup-pstack`, `automate-me`, `recall`. `vendor.py` lists each reason, and
every wheel records its list in `horo_pstack/_vendor/UPSTREAM.json`.

pstack's two subagents (`poteto-agent`, `comment-sicko`) are not Hermes
concepts; the harness turns each into a brief for `delegate_task`.

## How this repository is laid out

pstack content is never committed here. A release is a pure function of
(pstack commit, this repository).

| Path | What it does |
|---|---|
| `vendor.py` | Copies one cursor/plugins commit into the package, minus the excluded skills, with the harness pointer added to each SKILL.md. Fails if the license is no longer MIT or an excluded skill disappeared upstream |
| `harness/hermes-harness/SKILL.md` | The Cursor-to-Hermes map |
| `src/horo_pstack/__init__.py` | The plugin: registers each skill with Hermes |
| `sbom.py` | CycloneDX SBOM naming the pstack commit, embedded in the wheel |
| `verify_wheel.py` | Installs the wheel next to horo-next in a clean venv and checks it works |
| `.github/workflows/release.yml` | Commit → vendor → wheel → verify → TestPyPI → PyPI |

## Releasing

Run the **release** workflow with a full cursor/plugins commit SHA. Leave
`post` blank for a new pstack version; set it to 1, 2, ... when only this
repository changed, which releases `0.15.36.post1` and so on. With `publish`
off it builds and verifies only.

## Building locally

```bash
git clone --filter=blob:none https://github.com/cursor/plugins.git cursor-plugins
git -C cursor-plugins checkout <commit>
python vendor.py cursor-plugins
uv build --wheel
python sbom.py generate horo-pstack.cdx.json
python sbom.py embed dist/horo_pstack-<version>-py3-none-any.whl horo-pstack.cdx.json release.cdx.json
python verify_wheel.py dist/horo_pstack-<version>-py3-none-any.whl 3.12 0.21.5
```
