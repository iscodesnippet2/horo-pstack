---
name: hermes-harness
description: "Read once per session before following any pstack:* skill in Hermes. Maps the Cursor tool names, subagent fields, models, and paths that pstack skills use to their Hermes equivalents."
---

# pstack in Hermes

pstack skills use Cursor names. In Hermes, read this file once per session, then map each Cursor name with the tables below. If a Cursor field has no row, drop it and say so. Never pass a field the tool schema rejects.

## Tools

| Cursor | Hermes |
| --- | --- |
| `Task` | `delegate_task` with `action: "spawn"` and `tasks: [{goal, context}]`. Put several tasks in one call to run them in parallel. |
| `AskQuestion` | `clarify`. |
| Open a todolist | `todo_list`. |
| Run another pstack skill (`/name` or "the **name** skill") | `skill_view("pstack:<name>")` and follow it. When you tell the user to type it, write `/pstack:<name>`. |
| A file next to a skill, such as `playbooks/x.md` or `references/y.md` | `skill_view("pstack:<skill>", file_path="playbooks/x.md")`. |
| `Grep`, `Glob` | `search_files`. |
| `Read`, `Write`, `StrReplace` | `read_file`, `write_file`, `patch`. |
| `Shell` | `terminal`. |

## Subagent fields

`delegate_task` takes only `goal`, `context`, `output_schema`, `images`, and `group` per task. Map the rest into the brief.

| Cursor | Hermes |
| --- | --- |
| `subagent_type: generalPurpose` | Omit. |
| `subagent_type: "poteto-agent"` | Start `context` with: "Before any work, call `skill_view(\"pstack:poteto-mode\")` and read it in full, including its principles index." |
| `subagent_type: "comment-sicko"` | Put the body of `skill_view("pstack:hermes-harness", file_path="agents/comment-sicko.md")` into `context`. |
| `readonly: true` | Add "Do not edit files." to `goal`, and check `git status` afterward. |
| `environment: "cloud"`, `cloud_base_branch` | Tell the worker which branch or commit to check out, in a worktree it creates. |
| `model`, `run_in_background`, `resume`, `file_attachments` | Omit `model` and `run_in_background`. For `resume`, spawn a new task and paste the earlier result into `context`. List attached paths in `context`. |

## Models

Hermes runs every subagent on the session model. Drop every model slug (`claude-*`, `grok-*`, `gpt-*`, `auto`, `inherit-parent`) and say so once. A multi-model step, such as a panel in `interrogate` or `arena`, runs each panel member on the session model with a distinct brief.

`setup-pstack` is not shipped: there is no per-role model choice to configure. Never search the disk for `pstack-models` rules or Hermes model config: use each skill's default behavior on the session model.

## Paths

| Cursor | Hermes |
| --- | --- |
| `.cursor/rules/*.mdc`, always-applied rules | `AGENTS.md` in the workspace. |
| `.cursor/skills/`, `~/.cursor/skills/` | `~/.hermes/skills/`. |
| `../../README.md`, `../../docs/guide/<file>`, `https://github.com/cursor/plugins/blob/main/pstack/<path>` | `skill_view("pstack:hermes-harness", file_path="pstack/<path>")` when that file exists. Never fetch the URL. |
| Transcripts in `~/.cursor/projects/<slug>/agent-transcripts/` | Hermes sessions, through `session_search` when the session offers it. Otherwise skip with the line below. |

## Cursor-only features

Hermes has no Cursor Automations, Bugbot, Cursor cloud agents, or built-in PR tool. When a step needs one, write one line, `Skipped in Hermes: <step>. <reason>.`, and go on to the next step. Do not stop, ask, or retry.

This install is offline. A step that fetches from the network, such as GitHub, a hosted model, or a web page, is skipped with the same line unless the user's environment provides it.
