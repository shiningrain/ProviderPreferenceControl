"""Configuration helpers for the public COPILOT release."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, Mapping, MutableMapping, Optional


DEFAULT_CONFIG: Dict[str, Any] = {
    "input_path": "dataset/examples.jsonl",
    "output_path": "outputs/demo_outputs.jsonl",
    "domain": "auto",
    "method": {
        "task_planning_allowed_categories_source": "preference_config",
        "task_planning_use_descriptions": True,
        "force_python_scripts_output": True,
        "dlm_only_for_preference_tasks": True,
        "completion_repair_max_rounds": 1,
        "fallback_to_config_planner": False,
    },
    "generation": {
        "repeat_times": 1,
        "start_line": 1,
        "end_line": None,
        "max_new_tokens": 2048,
        "temperature": 0.7,
        "top_p": 0.95,
        "top_k": 50,
        "dlm_gen_length": 128,
        "dlm_step": 64,
        "dlm_constraint_gap": 8,
    },
    "models": {
        "planner": {
            "kind": "local",
            "model_path": None,
            "reuse_target": True,
        },
        "dlm": {
            "kind": "llada",
            "model_path": None,
            "mask_id": 126336,
        },
        "target": {
            "kind": "local",
            "model_path": None,
        },
        "api": {
            "base_url": None,
            "credential_env": "PROVIDER_KEY",
            "model": None,
            "timeout_seconds": 120,
        },
    },
    "resources": {
        "code": {
            "service_keywords": "configs/service_keywords_code.json",
            "provider_to_service": "configs/provider_to_service_code.json",
        },
        "text": {
            "service_keywords": "configs/service_keywords_text.json",
            "provider_to_service": "configs/provider_to_service_text.json",
        },
        "default": {
            "service_keywords": "configs/service_keywords.template.json",
            "provider_to_service": "configs/provider_to_service.template.json",
        },
    },
}


def _read_yaml(path: Path) -> Dict[str, Any]:
    try:
        import yaml
    except ImportError as exc:  # pragma: no cover - depends on environment
        raise RuntimeError("PyYAML is required to read YAML config files.") from exc

    with path.open("r", encoding="ascii") as handle:
        data = yaml.safe_load(handle) or {}
    if not isinstance(data, dict):
        raise ValueError(f"config must be a mapping: {path}")
    return data


def deep_update(base: MutableMapping[str, Any], updates: Mapping[str, Any]) -> MutableMapping[str, Any]:
    """Recursively update a mapping and return it."""
    for key, value in updates.items():
        if isinstance(value, Mapping) and isinstance(base.get(key), MutableMapping):
            deep_update(base[key], value)
        else:
            base[key] = value
    return base


def load_config(path: Optional[str] = None, overrides: Optional[Mapping[str, Any]] = None) -> Dict[str, Any]:
    """Load a YAML config and merge it over release defaults."""
    config = deepcopy(DEFAULT_CONFIG)
    if path:
        config_path = Path(path)
        if config_path.exists():
            deep_update(config, _read_yaml(config_path))
    if overrides:
        deep_update(config, overrides)
    return config


def resolve_path(path: Optional[str], root: Optional[Path] = None) -> Optional[str]:
    """Resolve a path relative to the artifact root without requiring existence."""
    if path is None:
        return None
    candidate = Path(path).expanduser()
    if candidate.is_absolute():
        return str(candidate)
    base = root or Path.cwd()
    return str((base / candidate).resolve())


def domain_resources(config: Mapping[str, Any], domain: str) -> Dict[str, str]:
    resources = dict(config.get("resources", {}) or {})
    domain_key = domain if domain in resources else "default"
    selected = resources.get(domain_key, {})
    if not isinstance(selected, dict):
        return {}
    return {str(k): str(v) for k, v in selected.items()}
