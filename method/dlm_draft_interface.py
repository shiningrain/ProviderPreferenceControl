"""DLM draft interface with constraint preparation.

The real implementation uses a diffusion language model that accepts prompts
and fixed token spans. This public snapshot defines the same boundary without
loading any model or requiring GPU-specific packages.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Protocol, Sequence, Tuple

from .anchor_templates import build_code_anchor_prompt, build_text_anchor_bundle


Constraint = Tuple[int, str]


class TokenizerLike(Protocol):
    def encode(self, text: str, add_special_tokens: bool = False) -> List[int]:
        """Encode text into token ids."""


class DraftModel(Protocol):
    tokenizer: TokenizerLike

    def generate_with_constraints(
        self,
        prompts: Sequence[str],
        constraints: Sequence[Sequence[Constraint]],
        steps: int,
        gen_len: int,
        block_len: Optional[int] = None,
    ) -> List[str]:
        """Return generated draft text for each prompt."""


@dataclass
class DraftRequest:
    prompts: List[str]
    constraints: List[List[Constraint]]
    anchor_meta: List[Dict[str, object]]
    gen_length: int = 128
    steps: int = 64


def constraint_spans(anchor_lines: List[str], tokenizer: Optional[TokenizerLike] = None, base_gap: int = 8) -> List[Constraint]:
    """Create fixed-position string constraints for the generated area."""
    snippets = ["```python\n"] + [line.rstrip() + "\n" for line in anchor_lines]
    position = 0
    constraints: List[Constraint] = []
    for snippet in snippets:
        constraints.append((position, snippet))
        if tokenizer is None:
            token_len = max(1, len(snippet.split()))
        else:
            token_len = len(tokenizer.encode(snippet, add_special_tokens=False))
        position += token_len + base_gap
    return constraints


def prepare_constrained_draft_inputs(
    prompt: str,
    task_list: List[Dict[str, str]],
    tokenizer: Optional[TokenizerLike] = None,
    gen_length: int = 128,
    steps: int = 64,
    base_gap: int = 8,
) -> DraftRequest:
    """Prepare prompts and constraints for preference-bound subtasks."""
    prompts: List[str] = []
    constraints: List[List[Constraint]] = []
    anchor_meta: List[Dict[str, object]] = []
    for index, task in enumerate(task_list, start=1):
        if not task.get("task_preference"):
            continue
        category = str(task.get("task_category") or "")
        is_text_task = category in {"Hotel Booking", "Maps"}
        if is_text_task:
            bundle = build_text_anchor_bundle(task, full_prompt=prompt, index=index)
            prompt_text = str(bundle["draft_prompt"])
            anchor_lines = [str(item) for item in bundle["anchor_lines"]]
            meta = bundle
        else:
            built = build_code_anchor_prompt(task)
            prompt_text = str(built["prompt"])
            anchor_lines = [str(item) for item in built["anchor_lines"]]
            meta = {
                "index": index,
                "category": category,
                "service_name": str(task.get("task_preference") or ""),
                "task_prompt": str(task.get("task_prompt") or ""),
                "anchor_lines": anchor_lines,
            }
        prompts.append(prompt_text)
        constraints.append(constraint_spans(anchor_lines, tokenizer=tokenizer, base_gap=base_gap))
        anchor_meta.append(meta)
    return DraftRequest(
        prompts=prompts,
        constraints=constraints,
        anchor_meta=anchor_meta,
        gen_length=gen_length,
        steps=steps,
    )


def render_draft_from_parts(task_list: List[Dict[str, str]], generated_parts: Sequence[str]) -> str:
    """Join generated draft parts with subtask headers."""
    draft_parts = []
    generated_iter = iter(generated_parts)
    for index, task in enumerate(task_list, start=1):
        if not task.get("task_preference"):
            continue
        generated = next(generated_iter, "")
        task_prompt = str(task.get("task_prompt") or "")
        draft_parts.append(f"# === subtask {index}: {task_prompt} ===\n{generated}")
    return "\n\n".join(draft_parts)
