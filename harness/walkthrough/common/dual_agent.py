#!/usr/bin/env python3
"""Shared harbor agent base for the dual-agent tasks.

Resolution: each task launcher exports WT_AGENT_DIR=<tasks/<task>> and passes
`-a agent:<Class>`; common/launch.sh sets PYTHONPATH = common/ + that dir, so
the task's agent.py imports this base as `dual_agent`. Subclasses supply the
in-container wrapper path, its exec cap and its log name, plus `name()`.
Subclasses QwenCode to reuse the qwen-code install chain and the trajectory
post-processing.
"""
from harbor.agents.installed.qwen_code import QwenCode
from harbor.environments.base import BaseEnvironment


class DualAgentBase(QwenCode):
    # In-container wrapper script (task-specific; set by the subclass).
    run_script: str = ""
    # Exec cap in seconds, under the task's harbor rail.
    run_timeout: int = 0
    # /logs/agent/<run_log> receives the wrapper's combined output.
    run_log: str = "run.txt"

    @staticmethod
    def name() -> str:
        raise NotImplementedError("task agent subclass must define name()")

    def version(self) -> str:
        return "0.1"

    async def install(self, environment: BaseEnvironment) -> None:
        # nvm's install.sh autodetects git (present in this image) and then
        # needs raw.githubusercontent.com for nvm.sh/nvm-exec/bash_completion -
        # hard-blocked by the sandbox SNI allowlist. Install Node directly from
        # the npmmirror tarball instead: every host here is allowlisted.
        # Since 2026-10-11 the env image (build/task-restricted) bakes
        # curl+node+qwen at build time; the download chain below runs only as
        # the fallback for images without the bake.
        await self.exec_as_agent(
            environment,
            command=(
                "set -euo pipefail; "
                "if ! command -v qwen >/dev/null 2>&1; then "
                "  command -v curl >/dev/null 2>&1 || "
                "  { apt-get update -qq && apt-get install -y -qq --no-install-recommends "
                "  curl ca-certificates; }; "
                "  NODE=v22.9.0; "
                "  curl -fL --retry 4 -o /tmp/node.tar.gz "
                '"https://registry.npmmirror.com/-/binary/node/${NODE}/node-${NODE}-linux-x64.tar.gz"; '
                "  tar -xzf /tmp/node.tar.gz -C /usr/local --strip-components=1; "
                "  npm config set registry https://registry.npmmirror.com; "
                "  npm install -g @qwen-code/qwen-code@0.25.1; "
                "fi; "
                "node --version; qwen --version"
            ),
            timeout_sec=900,
        )

    async def run(
        self,
        instruction: str,
        environment: BaseEnvironment,
        context: object,
    ) -> None:
        # Wrapper exit 0 = normal close-out; anything else must surface as an
        # exception (abnormal exit), hence no pipe on the redirect.
        assert self.run_script and self.run_timeout, "subclass must set run_script/run_timeout"
        await self.exec_as_agent(
            environment,
            command=f"bash {self.run_script} > /logs/agent/{self.run_log} 2>&1",
            timeout_sec=self.run_timeout,
        )
