import os
import pathlib
import textwrap
from typing import List, Dict, Any

import yaml

CONFIG_PATH = pathlib.Path(__file__).parent / "config_llm.yaml"


class AegisLLMConfig:
    def __init__(self, raw: Dict[str, Any]):
        self.raw = raw
        self.mode = raw.get("llm", {}).get("mode", "proxy")
        self.provider = raw.get("llm", {}).get("provider", "openai")
        self.model = raw.get("llm", {}).get("model", "gpt-4.1-mini")
        self.temperature = float(raw.get("llm", {}).get("temperature", 0.2))

        proj = raw.get("project", {})
        self.root = pathlib.Path(proj.get("root", "."))
        self.data_dir = pathlib.Path(proj.get("data_dir", self.root / "data"))
        self.logs_dir = pathlib.Path(proj.get("logs_dir", self.root / "logs"))

        asst = raw.get("assistant", {})
        self.assistant_name = asst.get("name", "Aegis-Local")
        self.assistant_role = asst.get(
            "role",
            "Private trading/dev assistant specialized in the Aegis repo.",
        )
        self.max_context_files = int(asst.get("max_context_files", 10))


def load_config() -> AegisLLMConfig:
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}
    return AegisLLMConfig(raw)


class AegisLLM:
    """
    Thin wrapper around 'whatever LLM we use'.

    Phase C.0: this will *proxy* to your existing orchestrator/OpenAI setup.
    Later: we swap in actual local model calls.
    """

    def __init__(self, cfg: AegisLLMConfig):
        self.cfg = cfg

    def chat(
        self,
        system_prompt: str,
        user_prompt: str,
        extra_context: List[str] | None = None,
    ) -> str:
        """
        For now this is a stub. We keep the signature stable so we can
        replace the implementation later without touching call sites.
        """
        context_blob = ""
        if extra_context:
            context_blob = "\n\n".join(
                f"[CTX {i+1}]\n{c}" for i, c in enumerate(extra_context)
            )

if __name__ == "__main__":
    cfg = load_config()
    llm = AegisLLM(cfg)

    system = (
        f"You are {cfg.assistant_name}, {cfg.assistant_role} "
        "You specialize in the Aegis repo structure and strategy code."
    )

    user = "Summarize the purpose of this Aegis project in 3-5 bullet points."

    # For now we don't pass extra_context; later we'll plug in tools_local
    reply = llm.chat(system_prompt=system, user_prompt=user, extra_context=None)
    print(reply)


        # Stubbed answer – this is where the real model call will go.
        # For now we just echo the prompts so you can test wiring.
        response = textwrap.dedent(
            f"""
            [Aegis-Local STUB]

            System:
            {system_prompt.strip()}

            User:
            {user_prompt.strip()}

            Extra context blocks: {len(extra_context or [])}

            (No real LLM hooked up yet – this is a dry-run echo so we can test the pipeline.)
            """
        ).strip()

        return response
