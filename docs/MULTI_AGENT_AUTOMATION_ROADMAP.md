# Multi-Agent Automation Roadmap

Status: operational blueprint  
Date: 2026-05-30  
Primary board: Hermes Kanban `tm-trading-v555`  
Primary repo: `https://github.com/gitugitu555/tm-trading-v555`

## Purpose

This document defines how multiple CLI agents can work on the trading system without corrupting the repo, duplicating work, or creating unverified research claims.

The goal is not to make agents "do everything". The goal is to create a disciplined research factory:

1. Hermes coordinates tasks.
2. GitHub remains the source of truth.
3. Tests and smoke runs gate completion.
4. Every result has a command, commit, dataset, and reason-coded summary.
5. Multiple models can review the strategy daily, but no suggestion becomes architecture until it survives implementation and ablation.

## Current Machine Setup

Project path:

```text
/home/tokio/tm-trading-v555
```

Shared project group:

```text
tokio
```

Current project users:

```text
tokio
jarvis
cairo
hexa
```

Current access model:

- `jarvis`, `cairo`, and `hexa` are members of the `tokio` group.
- `/home/tokio` allows group traversal.
- `/home/tokio/tm-trading-v555` allows group read/write/execute.
- Project directories use setgid so new files remain group-owned by `tokio`.
- Git `safe.directory` is configured for the shared repo for agent users.
- Hermes board `tm-trading-v555` points to `/home/tokio/tm-trading-v555`.

This is intentionally narrower than full-machine public write access.

### Registered Hermes Worker Profiles

The following Hermes worker profiles are now registered on this machine:

- `jarvis`
- `vibe`
- `kilo`
- `codex`

Each profile is cloned from `default` and uses the same base model for now. The role separation comes from the profile description and the Kanban task routing, not from different base models yet.

Launcher aliases created:

- `~/.local/bin/hermes-jarvis`
- `~/.local/bin/hermes-vibe`
- `~/.local/bin/hermes-kilo`
- `~/.local/bin/hermes-codex`

If `~/.local/bin` is not on PATH in a given shell, call the alias by absolute path or add the directory to shell startup files.

## GitHub Access Policy

GitHub credentials should not be copied between users.

Recommended policy:

- Do not tie the repo to one Linux account for pushes.
- Each human user should either authenticate their own shell or use a dedicated bot identity.
- Final pushes should happen through the currently authenticated user or through a repo bot account.
- Do not paste or store personal GitHub tokens in repo files, shell history, Kanban card bodies, or logs.

Current practical setup:

- `jarvis` is the sticky Hermes orchestrator profile for tm-trading-v555.
- `jarvis`, `kilo`, and `vibe` can work in the repo via the shared `tokio` group and Hermes workspace access.
- `codex` is modeled as a Hermes worker profile for review and verification rather than as a separate shell binary.
- `scripts/git_shared_setup.sh` normalizes local repo identity for whichever user is active.

Future improvement:

- Create a dedicated GitHub bot account or deploy key for automation.
- Restrict that identity to this repo only.
- Prefer SSH or a bot token over a user-specific HTTPS credential stash.
- Use branch protection or a required test workflow before merge if the project moves to PR-based automation.

## Coordinator Architecture

Use Hermes as the task bus.

```text
Strategy Owner / Human
        |
        v
Coordinator Agent
        |
        v
Hermes Kanban: tm-trading-v555
        |
        +--> Research Worker
        +--> Implementation Worker
        +--> Test/Verifier Worker
        +--> Docs/Memory Worker
        +--> Review/Synthesis Worker
        |
        v
GitHub + local test artifacts
```

The coordinator should not directly change every file. It should:

- decompose work into concrete cards
- assign one owner per card
- require acceptance criteria
- require tests or a documented reason why tests are not possible
- collect worker results into a final synthesis
- decide what gets committed and pushed

## Worker Roles

### Coordinator

Responsibilities:

- maintain Kanban priority
- split large ideas into testable tasks
- prevent duplicate implementations
- enforce scope boundaries
- request verification before marking high-risk work done

Good tasks for coordinator:

- create V7.6 execution sequence
- assign Session 5 implementation
- create ablation checklist
- schedule morning review

### Research Worker

Responsibilities:

- read existing docs and result files
- propose hypotheses
- define measurable tests
- identify leakage, overfit, and regime risks

Output must include:

- hypothesis
- expected measurable effect
- test command or script location
- reject criteria
- required data range

### Implementation Worker

Responsibilities:

- make code changes only for one scoped task
- preserve deterministic engine boundaries
- keep new features opt-in until validated
- add tests with the implementation

Output must include:

- files changed
- tests run
- assumptions
- unresolved risks

### Verifier Worker

Responsibilities:

- run unit tests
- run smoke tests
- compare outputs against prior baseline
- check that result files are not placeholders

Verifier should not trust worker summaries. It should inspect commands, outputs, and changed files.

### Docs/Memory Worker

Responsibilities:

- update roadmap docs
- summarize lessons learned
- record commands and result paths
- keep `PROJECT_ROADMAP.md`, `PROJECT_LOG.md`, and Kanban aligned

### Review/Synthesis Worker

Responsibilities:

- compare multiple model opinions
- reject vague or untestable suggestions
- turn useful suggestions into Kanban cards
- maintain the highest-edge queue

## Morning Reasoning Meeting

Run one daily model meeting before new build work.

Inputs:

- `docs/V76_SWOT_EDGE_ROADMAP.md`
- `docs/V75_MASTER_ROADMAP.md`
- `docs/V74_AUCTION_STATE_ENGINE_BLUEPRINT.md`
- `docs/SESSION_5_VOLUME_BAR_CONFLUENCE_PROMPT.md`
- latest `git status`
- latest unit test output
- latest smoke/backtest result files
- current Hermes Kanban board

Agenda:

1. What changed since the last meeting?
2. What is the highest current measured edge?
3. Which edge is most likely overfit?
4. Which task unlocks the most information per hour?
5. Which work should be deleted, paused, or demoted?
6. What must be tested before the next push?
7. Which Kanban card gets the next worker?

Required output:

```text
Decision:
Top task:
Reason:
Expected edge improvement:
Main risk:
Test command:
Definition of done:
Cards to create/update:
```

## Automation Loop

Recommended loop:

```text
1. Coordinator selects one ready card.
2. Worker claims card.
3. Worker creates/edits code or docs.
4. Worker runs local tests.
5. Verifier reruns tests and smoke command.
6. Coordinator reviews diff and result summary.
7. Authenticated GitHub user commits and pushes.
8. Docs/Memory worker records result.
9. Next card is selected from highest information value, not excitement.
```

## Completion Gates

No card should be marked done unless one of these is true:

- code task: unit tests pass and smoke test is reported
- research task: hypothesis, metric, data range, and reject criteria are written
- docs task: linked from roadmap or relevant index
- infrastructure task: verified with a real command as the target user

For strategy work, completion must include:

- signal count
- trade count if applicable
- hit rate or IC if applicable
- dataset/archive
- command used
- commit hash
- reason-coded blockers

## Highest-Edge Work Queue

Current highest measured edge remains:

```text
300 BTC volume bars
40-bar CVD divergence
D4 HTF filter
5-bar horizon
hit_rate: 0.532880
IC: 0.051890
events: 22,506
source: results/volume_bar_cvd_6y.json
```

Next automation priorities:

1. Finish Session 5 volume-bar CVD confluence port.
2. Add signal-only scorecards before trade conversion.
3. Run cross-regime smoke tests.
4. Build minimal AuctionStateEngine with synthetic transition tests.
5. Add Structural Memory Lite as a location filter.
6. Add AlphaPermission V2 reason chain as an opt-in path.
7. Add ExecutionDecision sandbox to separate signal quality from fill quality.
8. Revalidate full six-year results only after manifests and filters are stable.

## Recommended Hermes Cards

The current Hermes board should contain these categories:

- `context`: project state and docs
- `access`: workspace and GitHub capability
- `hygiene`: manifests, paths, placeholders
- `research`: hypothesis and diagnostic tasks
- `implementation`: code tasks
- `verification`: unit/smoke/backtest checks
- `synthesis`: model review and roadmap updates

Each worker card should include:

- exact files or modules
- acceptance criteria
- tests to run
- forbidden changes
- expected output summary

## Multi-Model Review Pattern

Use multiple models for disagreement, not consensus theater.

Recommended roles:

- Model A: implementation critic
- Model B: market-theory critic
- Model C: overfit/leakage critic
- Model D: execution/risk critic
- Coordinator: synthesis and task creation

Each model should answer:

```text
What is the strongest idea?
What is the weakest assumption?
What would invalidate this?
What test should run next?
What should be deleted or demoted?
```

The coordinator then writes one synthesis:

```text
Accepted:
Rejected:
Needs test:
New Kanban cards:
No-action notes:
```

## CrewAI Position

CrewAI can be useful for structured role-play and repeatable research meetings, but it should not be the source of truth.

Recommended use:

- daily research meeting
- structured critique
- hypothesis generation
- report drafting

Not recommended as first controller for code execution:

- task locking is weaker than Hermes Kanban
- repo state can drift without strict Git gates
- long-running backtests need durable process management

Practical pattern:

```text
CrewAI or multi-model meeting -> recommendations
Hermes Kanban -> task execution
GitHub -> source of truth
Verifier worker -> acceptance
```

## Safety Rules

- Do not give every user blanket write access to the whole machine.
- Do not share personal GitHub tokens across users.
- Do not let agents push directly to `master` without test output.
- Do not mark placeholder result files as evidence.
- Do not run full six-year jobs before smoke runs prove the path.
- Do not mix signal detection, permission logic, and execution logic in one untestable block.
- Do not let model meetings create architecture without measurable tests.

## Practical Worker Mapping

Use the following roles in Hermes:

- `vibe`: fast exploration, idea generation, strategy critique
- `kilo`: implementation, refactors, targeted code edits
- `codex`: review, verification, cleanup, and test enforcement
- `jarvis`: orchestrator, task routing, morning review, verification gating, and push coordination

Recommended task allocation:

- `vibe` gets ambiguous research tasks and morning review synthesis.
- `kilo` gets scoped code changes with clear acceptance criteria.
- `codex` gets diffs, tests, smoke verification, and blocker triage.
- `jarvis` owns the board, decomposes work, and decides what gets pushed.

## External CLI Bridge

Use the repo bridge when you want a non-Hermes CLI to execute a Hermes Kanban task and update the board automatically.

Bridge entrypoint:

```bash
python3 scripts/hermes_cli_bridge.py --task-id <task_id> --role vibe --command "vibe --agent auto-approve --trust"
```

Supported modes:

- `append`: append the generated task prompt as the last positional argument.
- `flag`: pass the prompt with a flag such as `-p` or `--prompt`.
- `stdin`: stream the prompt on standard input.

What the bridge does:

1. Reads the task with `hermes kanban show --json`.
2. Claims the task with `hermes kanban claim`.
3. Uses the claimed workspace path when available.
4. Launches the external CLI with the task prompt.
5. Writes a JSON log under `logs/hermes_cli_bridge/`.
6. Calls `hermes kanban complete` on exit code `0`.
7. Calls `hermes kanban block` on nonzero exit code.
8. Adds a board comment when the lane starts, so the lifecycle is visible before completion.

Recommended environment variables:

- `HERMES_EXTERNAL_CLI_COMMAND_VIBE`
- `HERMES_EXTERNAL_CLI_COMMAND_KILO`
- `HERMES_EXTERNAL_CLI_COMMAND_CODEX`
- `HERMES_EXTERNAL_CLI_VERIFY_COMMAND_VIBE`
- `HERMES_EXTERNAL_CLI_PROMPT_MODE`
- `HERMES_EXTERNAL_CLI_PROMPT_FLAG`

Suggested pattern:

- `vibe` for exploratory reasoning and synthesis.
- `kilo` for implementation work.
- `codex` for review and verification.
- Keep the bridge config in shell env or a dedicated wrapper script, not in Kanban prose.

## Near-Term Implementation Plan

### Phase 1: Shared Workspace

Status: done locally.

- Jarvis/Hermes can access `/home/tokio/tm-trading-v555`.
- Agent users can run Git status in the shared repo.
- Hermes board points at the project workdir.

### Phase 2: Push Discipline

Add a simple push ritual:

```text
git status --short
.venv/bin/python -m unittest
git add <scoped files>
git commit -m "<clear message>"
git push origin master
```

For automation, the coordinator should require the test output in the Kanban completion result.

### Phase 3: Morning Review Card

Create a recurring Hermes task:

```text
Daily V7.6 strategy review and task selection
```

Acceptance:

- reads latest docs and results
- names top task
- names risk
- creates or updates one actionable Kanban card

### Phase 4: Verifier Worker

Create a dedicated verifier profile or convention:

- cannot edit code
- can run tests
- can inspect diffs
- can mark card blocked if evidence is weak

### Phase 5: Bot GitHub Identity

Create a repo-scoped GitHub identity for automation if direct auto-push becomes necessary.

Required constraints:

- repo-only access
- no personal token sharing
- branch protection preferred
- required tests before merge
