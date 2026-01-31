import pathlib
from typing import List, Dict, Any

from .llm_core import AegisLLMConfig, load_config

cfg = load_config()


def list_project_files(
    pattern: str = "*.py",
    max_files: int = 50,
    subdir: str | None = None,
) -> list[dict[str, str]]:
    """
    Return a small list of project files matching a glob pattern.
    We keep this very safe – only under project root.
    """
    root = cfg.root
    if subdir:
        root = root / subdir

    root = root.resolve()
    project_root = cfg.root.resolve()

    # Safety: block traversal above project root
    if project_root not in root.parents and project_root != root:
        raise ValueError(f"Refusing to list outside project root: {root}")

    results: list[dict[str, str]] = []
    for p in root.rglob(pattern):
        if not p.is_file():
            continue
        rel = p.relative_to(project_root)
        results.append({"path": str(rel), "name": p.name})
        if len(results) >= max_files:
            break
    return results


def read_file_snippet(rel_path: str, max_chars: int = 4000) -> dict[str, str]:
    """
    Read part of a file under the project root.
    """
    project_root = cfg.root.resolve()
    path = (project_root / rel_path).resolve()

    if project_root not in path.parents and project_root != path:
        raise ValueError(f"Refusing to read outside project root: {rel_path}")

    text = path.read_text(encoding="utf-8", errors="replace")
    snippet = text[:max_chars]
    truncated = len(text) > max_chars

    return {
        "path": str(path.relative_to(project_root)),
        "snippet": snippet,
        "truncated": str(truncated),
    }
