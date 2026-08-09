"""REQ-017: mcp_registry mutator trust gate + agent subprocess env hardening."""
from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


class McpRegistryTrustGateTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmpdir.cleanup)
        self._env = patch.dict(
            os.environ,
            {"EVOTOWN_DATA_DIR": self._tmpdir.name},
            clear=False,
        )
        self._env.start()
        self.addCleanup(self._env.stop)

        from infra import mcp_registry

        mcp_registry._conn = None  # noqa: SLF001
        self.reg = mcp_registry

    def test_register_service_blocked_without_trust(self) -> None:
        with self.assertRaises(self.reg.McpRegistryAccessDenied):
            self.reg.register_service(name="bypass-mcp")

    def test_register_service_allowed_with_trust(self) -> None:
        with self.reg.mcp_registry_trusted():
            svc = self.reg.register_service(name="trusted-mcp", source=self.reg.SOURCE_EXTERNAL)
        self.assertTrue(str(svc.get("service_id") or "").startswith("mcp_"))
        self.assertEqual(svc.get("name"), "trusted-mcp")

    def test_set_policy_blocked_without_trust(self) -> None:
        with self.reg.mcp_registry_trusted():
            svc = self.reg.register_service(name="pol-mcp", source=self.reg.SOURCE_EXTERNAL)
        with self.assertRaises(self.reg.McpRegistryAccessDenied):
            self.reg.set_policy(svc["service_id"], "agt_test", enabled=True)

    def test_invoke_mcp_grants_trust_for_handler_mutators(self) -> None:
        from services import mcp_loader

        calls: list[str] = []

        class _Handler:
            @staticmethod
            def process(args: dict, permissions: dict) -> dict:
                del args, permissions
                svc = self.reg.register_service(
                    name="from-handler",
                    source=self.reg.SOURCE_EXTERNAL,
                )
                calls.append(str(svc.get("name") or ""))
                return {"ok": True}

        real_get = self.reg.get_service

        def _get_service(service_id: str):
            if service_id == "system-fake":
                return {"source": "system", "status": "online"}
            return real_get(service_id)

        with (
            patch.object(mcp_loader, "get_handler", return_value=_Handler),
            patch.object(mcp_loader, "_load_version", return_value="1.0.0"),
            patch.object(self.reg, "get_service", side_effect=_get_service),
        ):
            result = mcp_loader.invoke_mcp("system-fake", {}, {})

        self.assertTrue(result.get("ok"))
        self.assertEqual(calls, ["from-handler"])


class HostedAgentEnvTest(unittest.TestCase):
    def test_cli_env_clears_pythonpath_and_data_dir(self) -> None:
        from services.agent_subprocess_env import build_hosted_agent_env
        from services import claude_agent_sdk_runner
        from services.agent_runner_base import AgentRunContext

        with patch.dict(
            os.environ,
            {
                "PYTHONPATH": "/app",
                "EVOTOWN_DATA_DIR": "/app/data",
                "MCP_SERVICES_DIR": "/app/data/mcp-services",
                "PATH": "/usr/bin",
                "EVOTOWN_CLAUDE_USE_GATEWAY": "1",
                "EVOTOWN_CLAUDE_GATEWAY_BASE_URL": "http://backend:8765/api/gateway/anthropic",
                "EVOTOWN_CLAUDE_GATEWAY_API_KEY": "evk_test",
            },
            clear=False,
        ):
            built = build_hosted_agent_env(
                workspace_root="/tmp/ws",
                run_id="car_x",
                model="m",
                extra={"ANTHROPIC_API_KEY": "evk_test"},
                inherit_parent=True,
            )
            self.assertEqual(built.get("PYTHONPATH"), "")
            self.assertNotIn("EVOTOWN_DATA_DIR", built)
            self.assertNotIn("MCP_SERVICES_DIR", built)
            self.assertEqual(built.get("EVOTOWN_AGENT_RUN_ID"), "car_x")
            self.assertEqual(built.get("PATH"), "/usr/bin")

            runner = claude_agent_sdk_runner.ClaudeCodeRunner()
            ctx = AgentRunContext(
                run_id="car_test",
                agent_id="",
                prompt="hi",
                account_id="",
                team_id="",
                tenant_id="",
            )
            env = runner._cli_subprocess_env(  # noqa: SLF001
                workspace_root=Path("/tmp/ws"),
                context=ctx,
                model="deepseek-v4-flash",
            )
        self.assertEqual(env["ANTHROPIC_BASE_URL"], "http://backend:8765/api/gateway/anthropic")
        self.assertEqual(env["ANTHROPIC_API_KEY"], "evk_test")
        self.assertEqual(env.get("PYTHONPATH"), "")
        self.assertNotIn("EVOTOWN_DATA_DIR", env)


if __name__ == "__main__":
    unittest.main()
