from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import subprocess
import sys
import textwrap
import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_HERMES_BIN = os.environ.get(
    "HERMES_BIN", "/home/jarvis/.hermes/hermes-agent/venv/bin/hermes"
)
DEFAULT_LOG_ROOT = Path("logs/hermes_cli_bridge")


@dataclass(frozen=True)
class BridgeConfig:
    task_id: str
    role: str
    command: str | None = None
    prompt_mode: str = "append"
    prompt_flag: str = "-p"
    hermes_bin: str = DEFAULT_HERMES_BIN
    verify_command: str | None = None
    log_root: Path = DEFAULT_LOG_ROOT
    dry_run: bool = False


@dataclass(frozen=True)
class BridgeResult:
    task_id: str
    role: str
    workspace: str
    command: list[str]
    log_path: str
    prompt_mode: str
    external_exit_code: int
    verify_exit_code: int | None
    outcome: str


class BridgeError(RuntimeError):
    pass


def _run(
    argv: list[str],
    *,
    cwd: str | None = None,
    input_text: str | None = None,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        argv,
        cwd=cwd,
        input=input_text,
        text=True,
        capture_output=True,
        env=env,
        check=False,
    )


def _load_task(hermes_bin: str, task_id: str) -> dict[str, Any]:
    proc = _run([hermes_bin, "kanban", "show", task_id, "--json"])
    if proc.returncode != 0:
        raise BridgeError(
            f"Failed to read Kanban task {task_id}: exit={proc.returncode} stderr={proc.stderr.strip()}"
        )
    payload = json.loads(proc.stdout)
    task = payload.get("task")
    if not isinstance(task, dict):
        raise BridgeError(f"Unexpected Hermes task payload for {task_id}")
    return task


def _claim_task(hermes_bin: str, task_id: str) -> str:
    proc = _run([hermes_bin, "kanban", "claim", task_id])
    if proc.returncode != 0:
        raise BridgeError(
            f"Failed to claim task {task_id}: exit={proc.returncode} stderr={proc.stderr.strip()}"
        )
    return proc.stdout.strip()


def _workspace_from_claim_output(claim_output: str) -> str | None:
    match = re.search(r"^Workspace:\s*(.+)$", claim_output, flags=re.MULTILINE)
    if match:
        return match.group(1).strip()
    return None


def _comment_task(hermes_bin: str, task_id: str, author: str, text: str) -> None:
    proc = _run([hermes_bin, "kanban", "comment", "--author", author, task_id, text])
    if proc.returncode != 0:
        raise BridgeError(
            f"Failed to comment on {task_id}: exit={proc.returncode} stderr={proc.stderr.strip()}"
        )


def _complete_task(hermes_bin: str, task_id: str, summary: str, metadata: dict[str, Any]) -> None:
    proc = _run(
        [
            hermes_bin,
            "kanban",
            "complete",
            task_id,
            "--summary",
            summary,
            "--metadata",
            json.dumps(metadata, sort_keys=True),
        ]
    )
    if proc.returncode != 0:
        raise BridgeError(
            f"Failed to complete task {task_id}: exit={proc.returncode} stderr={proc.stderr.strip()}"
        )


def _block_task(hermes_bin: str, task_id: str, reason: str) -> None:
    proc = _run([hermes_bin, "kanban", "block", task_id, reason])
    if proc.returncode != 0:
        raise BridgeError(
            f"Failed to block task {task_id}: exit={proc.returncode} stderr={proc.stderr.strip()}"
        )


def _resolve_command(role: str, command: str | None) -> str:
    if command:
        return command

    env_key = f"HERMES_EXTERNAL_CLI_COMMAND_{role.upper()}"
    env_command = os.environ.get(env_key) or os.environ.get("HERMES_EXTERNAL_CLI_COMMAND")
    if env_command:
        return env_command

    if role == "vibe" and shutil.which("vibe"):
        return "vibe --agent auto-approve --trust"

    raise BridgeError(
        f"No external CLI command configured for role '{role}'. Set {env_key} or HERMES_EXTERNAL_CLI_COMMAND."
    )


def build_prompt(task: dict[str, Any], role: str, workspace: str) -> str:
    body = (task.get("body") or "").strip()
    title = task.get("title") or ""
    task_id = task.get("id") or ""
    tenant = task.get("tenant") or ""
    status = task.get("status") or ""
    lines = [
        f"Role: {role}",
        f"Task ID: {task_id}",
        f"Title: {title}",
        f"Tenant: {tenant}",
        f"Status: {status}",
        f"Workspace: {workspace}",
        "",
        "Task body:",
        body,
        "",
        "Rules:",
        "- Work only in the assigned workspace.",
        "- Do not call Hermes kanban tools directly.",
        "- Do not modify secrets or unrelated files.",
        "- Return a concise summary with files changed, tests run, blockers, and risks.",
    ]
    return "\n".join(lines).strip() + "\n"


def _build_argv(
    command: str,
    prompt: str,
    *,
    prompt_mode: str,
    prompt_flag: str,
) -> tuple[list[str], str | None]:
    argv = shlex.split(command)
    if prompt_mode == "stdin":
        return argv, prompt
    if prompt_mode == "flag":
        argv.extend([prompt_flag, prompt])
        return argv, None
    if prompt_mode == "append":
        argv.append(prompt)
        return argv, None
    raise BridgeError(f"Unknown prompt mode: {prompt_mode}")


def _timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _write_log(log_root: Path, task_id: str, role: str, record: dict[str, Any]) -> Path:
    log_root.mkdir(parents=True, exist_ok=True)
    path = log_root / f"{_timestamp()}_{role}_{task_id}.json"
    path.write_text(json.dumps(record, indent=2, sort_keys=True), encoding="utf-8")
    return path


def run_bridge(config: BridgeConfig) -> BridgeResult:
    task = _load_task(config.hermes_bin, config.task_id)
    command = _resolve_command(config.role, config.command)

    if config.dry_run:
        workspace = task.get("workspace_path") or os.getcwd()
        prompt = build_prompt(task, config.role, workspace)
        argv, _ = _build_argv(
            command,
            prompt,
            prompt_mode=config.prompt_mode,
            prompt_flag=config.prompt_flag,
        )
        log_path = _write_log(
            config.log_root,
            config.task_id,
            config.role,
            {
                "task": task,
                "command": argv,
                "prompt_mode": config.prompt_mode,
                "dry_run": True,
            },
        )
        return BridgeResult(
            task_id=config.task_id,
            role=config.role,
            workspace=workspace,
            command=argv,
            log_path=str(log_path),
            prompt_mode=config.prompt_mode,
            external_exit_code=0,
            verify_exit_code=None,
            outcome="dry_run",
        )

    claim_output = _claim_task(config.hermes_bin, config.task_id)
    workspace = task.get("workspace_path") or _workspace_from_claim_output(claim_output) or os.getcwd()
    prompt = build_prompt(task, config.role, workspace)
    argv, stdin_text = _build_argv(
        command,
        prompt,
        prompt_mode=config.prompt_mode,
        prompt_flag=config.prompt_flag,
    )
    _comment_task(
        config.hermes_bin,
        config.task_id,
        author=f"bridge:{config.role}",
        text=(
            f"[bridge-start] role={config.role} command={command} workspace={workspace} "
            f"claim={claim_output or 'ok'}"
        ),
    )

    env = os.environ.copy()
    env.update(
        {
            "HERMES_KANBAN_TASK": config.task_id,
            "HERMES_KANBAN_BOARD": str(task.get("tenant") or ""),
            "HERMES_KANBAN_WORKSPACE": workspace,
            "HERMES_PROFILE": config.role,
            "HERMES_BRIDGE_ROLE": config.role,
        }
    )

    proc = _run(argv, cwd=workspace, input_text=stdin_text, env=env)
    verify_proc: subprocess.CompletedProcess[str] | None = None
    outcome = "done" if proc.returncode == 0 else "blocked"

    if proc.returncode == 0 and config.verify_command:
        verify_argv = shlex.split(config.verify_command)
        verify_proc = _run(verify_argv, cwd=workspace, env=env)
        if verify_proc.returncode != 0:
            outcome = "blocked"

    log_path = _write_log(
        config.log_root,
        config.task_id,
        config.role,
        {
            "task": task,
            "claim_output": claim_output,
            "command": argv,
            "prompt_mode": config.prompt_mode,
            "external": {
                "returncode": proc.returncode,
                "stdout": proc.stdout,
                "stderr": proc.stderr,
            },
            "verify": None
            if verify_proc is None
            else {
                "command": config.verify_command,
                "returncode": verify_proc.returncode,
                "stdout": verify_proc.stdout,
                "stderr": verify_proc.stderr,
            },
        },
    )

    if outcome == "done":
        summary = textwrap.dedent(
            f"""\
            Bridge role {config.role} completed task {config.task_id}.
            Command: {' '.join(argv)}
            Workspace: {workspace}
            Log: {log_path}
            External exit code: {proc.returncode}
            """
        ).strip()
        metadata = {
            "bridge": {
                "role": config.role,
                "workspace": workspace,
                "command": argv,
                "prompt_mode": config.prompt_mode,
                "log_path": str(log_path),
                "external_exit_code": proc.returncode,
                "verify_command": config.verify_command,
                "verify_exit_code": None if verify_proc is None else verify_proc.returncode,
            }
        }
        _complete_task(config.hermes_bin, config.task_id, summary=summary, metadata=metadata)
        return BridgeResult(
            task_id=config.task_id,
            role=config.role,
            workspace=workspace,
            command=argv,
            log_path=str(log_path),
            prompt_mode=config.prompt_mode,
            external_exit_code=proc.returncode,
            verify_exit_code=None if verify_proc is None else verify_proc.returncode,
            outcome="done",
        )

    reason = (
        f"bridge failure role={config.role} external_exit={proc.returncode} "
        f"verify_exit={None if verify_proc is None else verify_proc.returncode} log={log_path}"
    )
    _comment_task(
        config.hermes_bin,
        config.task_id,
        author=f"bridge:{config.role}",
        text=reason,
    )
    _block_task(config.hermes_bin, config.task_id, reason=reason)
    return BridgeResult(
        task_id=config.task_id,
        role=config.role,
        workspace=workspace,
        command=argv,
        log_path=str(log_path),
        prompt_mode=config.prompt_mode,
        external_exit_code=proc.returncode,
        verify_exit_code=None if verify_proc is None else verify_proc.returncode,
        outcome="blocked",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Bridge a Hermes Kanban task to an external CLI worker.")
    parser.add_argument("--task-id", default=os.environ.get("HERMES_KANBAN_TASK"))
    parser.add_argument("--role", required=True, choices=["vibe", "kilo", "codex"])
    parser.add_argument("--command", help="External CLI command string. Overrides environment defaults.")
    parser.add_argument(
        "--prompt-mode",
        default=os.environ.get("HERMES_EXTERNAL_CLI_PROMPT_MODE", "append"),
        choices=["append", "flag", "stdin"],
    )
    parser.add_argument(
        "--prompt-flag",
        default=os.environ.get("HERMES_EXTERNAL_CLI_PROMPT_FLAG", "-p"),
    )
    parser.add_argument("--verify-command", default=os.environ.get("HERMES_EXTERNAL_CLI_VERIFY_COMMAND"))
    parser.add_argument(
        "--hermes-bin",
        default=os.environ.get("HERMES_BIN", DEFAULT_HERMES_BIN),
    )
    parser.add_argument(
        "--log-root",
        default=os.environ.get("HERMES_BRIDGE_LOG_ROOT", str(DEFAULT_LOG_ROOT)),
    )
    parser.add_argument("--dry-run", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not args.task_id:
        parser.error("--task-id or HERMES_KANBAN_TASK is required")

    config = BridgeConfig(
        task_id=args.task_id,
        role=args.role,
        command=args.command,
        prompt_mode=args.prompt_mode,
        prompt_flag=args.prompt_flag,
        hermes_bin=args.hermes_bin,
        verify_command=args.verify_command,
        log_root=Path(args.log_root),
        dry_run=args.dry_run,
    )
    result = run_bridge(config)
    if result.outcome == "blocked":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
