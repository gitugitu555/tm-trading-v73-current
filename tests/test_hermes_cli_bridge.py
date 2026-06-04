import json
import tempfile
import unittest
from pathlib import Path
from subprocess import CompletedProcess
from unittest.mock import patch

from orchestration.hermes_cli_bridge import BridgeConfig, build_prompt, run_bridge


class HermesCliBridgeTest(unittest.TestCase):
    def test_build_prompt_includes_task_context(self):
        task = {
            "id": "t_1234",
            "title": "Bridge task",
            "body": "Implement the bridge.",
            "tenant": "tm-trading-v555",
            "status": "ready",
        }
        prompt = build_prompt(task, "vibe", "/home/tokio/tm-trading-v555")
        self.assertIn("Task ID: t_1234", prompt)
        self.assertIn("Title: Bridge task", prompt)
        self.assertIn("Workspace: /home/tokio/tm-trading-v555", prompt)
        self.assertIn("Do not call Hermes kanban tools directly.", prompt)

    def test_bridge_completes_on_success(self):
        calls = []
        task_payload = {
            "task": {
                "id": "t_1234",
                "title": "Bridge task",
                "body": "Implement the bridge.",
                "tenant": "tm-trading-v555",
                "status": "ready",
                "workspace_path": "/home/tokio/tm-trading-v555",
            }
        }

        def fake_run(argv, **kwargs):
            calls.append((argv, kwargs))
            if argv[:4] == ["/bin/hermes", "kanban", "show", "t_1234"]:
                return CompletedProcess(argv, 0, stdout=json.dumps(task_payload), stderr="")
            if argv[:4] == ["/bin/hermes", "kanban", "claim", "t_1234"]:
                return CompletedProcess(argv, 0, stdout="/home/tokio/tm-trading-v555", stderr="")
            if argv[:3] == ["/bin/hermes", "kanban", "comment"]:
                return CompletedProcess(argv, 0, stdout="", stderr="")
            if argv[:3] == ["/bin/hermes", "kanban", "complete"]:
                return CompletedProcess(argv, 0, stdout="", stderr="")
            if argv == ["python3", "-c", "print('bridge-ok')", "Role: vibe\nTask ID: t_1234\nTitle: Bridge task\nTenant: tm-trading-v555\nStatus: ready\nWorkspace: /home/tokio/tm-trading-v555\n\nTask body:\nImplement the bridge.\n\nRules:\n- Work only in the assigned workspace.\n- Do not call Hermes kanban tools directly.\n- Do not modify secrets or unrelated files.\n- Return a concise summary with files changed, tests run, blockers, and risks.\n"]:
                return CompletedProcess(argv, 0, stdout="bridge-ok\n", stderr="")
            raise AssertionError(f"Unexpected argv: {argv}")

        with tempfile.TemporaryDirectory() as tmpdir, patch(
            "orchestration.hermes_cli_bridge.subprocess.run", side_effect=fake_run
        ):
            result = run_bridge(
                BridgeConfig(
                    task_id="t_1234",
                    role="vibe",
                    command="python3 -c \"print('bridge-ok')\"",
                    hermes_bin="/bin/hermes",
                    log_root=Path(tmpdir),
                )
            )
            self.assertEqual(result.outcome, "done")
            self.assertEqual(result.external_exit_code, 0)
            self.assertTrue(Path(result.log_path).exists())
            self.assertGreaterEqual(len(calls), 4)

    def test_bridge_blocks_on_failure(self):
        task_payload = {
            "task": {
                "id": "t_1234",
                "title": "Bridge task",
                "body": "Implement the bridge.",
                "tenant": "tm-trading-v555",
                "status": "ready",
                "workspace_path": "/home/tokio/tm-trading-v555",
            }
        }

        def fake_run(argv, **kwargs):
            if argv[:4] == ["/bin/hermes", "kanban", "show", "t_1234"]:
                return CompletedProcess(argv, 0, stdout=json.dumps(task_payload), stderr="")
            if argv[:4] == ["/bin/hermes", "kanban", "claim", "t_1234"]:
                return CompletedProcess(argv, 0, stdout="/home/tokio/tm-trading-v555", stderr="")
            if argv[:3] == ["/bin/hermes", "kanban", "comment"]:
                return CompletedProcess(argv, 0, stdout="", stderr="")
            if argv[:3] == ["/bin/hermes", "kanban", "block"]:
                return CompletedProcess(argv, 0, stdout="", stderr="")
            if argv[0] == "python3":
                return CompletedProcess(argv, 1, stdout="", stderr="boom")
            raise AssertionError(f"Unexpected argv: {argv}")

        with tempfile.TemporaryDirectory() as tmpdir, patch(
            "orchestration.hermes_cli_bridge.subprocess.run", side_effect=fake_run
        ):
            result = run_bridge(
                BridgeConfig(
                    task_id="t_1234",
                    role="vibe",
                    command="python3 -c \"print('bridge-ok')\"",
                    hermes_bin="/bin/hermes",
                    log_root=Path(tmpdir),
                )
            )
            self.assertEqual(result.outcome, "blocked")
            self.assertEqual(result.external_exit_code, 1)
            self.assertTrue(Path(result.log_path).exists())


if __name__ == "__main__":
    unittest.main()
