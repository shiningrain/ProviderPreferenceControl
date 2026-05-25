"""Public LLaDA-style constrained draft generation.

This file contains the release implementation of the DLM draft stage. It keeps
the model path configurable and imports heavy ML dependencies only when a user
actually creates a local DLM generator.
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

from .anchors import build_metric_anchor_lines


DEFAULT_DLM_PROMPT = """Please output a compact solution framework for the subtask.

Requirements:
- Preserve the required preference anchors exactly.
- Leave unresolved task-specific details as <blank>.
- Do not write the final answer; this is only a draft for a completion model.
- Keep the draft concise and useful for filling in later.

Subtask:
{task_prompt}

Preference anchors:
{anchor_text}

Draft:
"""


def add_gumbel_noise(logits: Any, temperature: float) -> Any:
    if temperature == 0:
        return logits
    import torch

    logits = logits.to(torch.float64)
    noise = torch.rand_like(logits, dtype=torch.float64)
    gumbel = -torch.log(-torch.log(noise))
    return logits + temperature * gumbel


def get_num_transfer_tokens(mask_index: Any, steps: int) -> Any:
    import torch

    mask_num = mask_index.sum(dim=1, keepdim=True)
    base = mask_num // steps
    remainder = mask_num % steps
    plan = torch.zeros(
        mask_num.size(0),
        steps,
        device=mask_index.device,
        dtype=torch.int64,
    ) + base
    for index in range(mask_num.size(0)):
        plan[index, : remainder[index]] += 1
    return plan


class LLaDADraftGenerator:
    """Constrained masked denoising wrapper for LLaDA-style checkpoints."""

    def __init__(
        self,
        model_path: str,
        mask_id: int = 126336,
        torch_dtype: str = "bfloat16",
        trust_remote_code: bool = True,
    ):
        if not model_path:
            raise ValueError("model_path is required for the DLM draft stage")
        self.model_path = model_path
        self.mask_id = int(mask_id)
        self.torch_dtype_name = torch_dtype
        self.trust_remote_code = bool(trust_remote_code)
        self.model = None
        self.tokenizer = None
        self.device = None
        self._load()

    def _load(self) -> None:
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer

        dtype = getattr(torch, self.torch_dtype_name, torch.bfloat16)
        self.model = AutoModelForCausalLM.from_pretrained(
            self.model_path,
            trust_remote_code=self.trust_remote_code,
            torch_dtype=dtype,
        )
        self.tokenizer = AutoTokenizer.from_pretrained(
            self.model_path,
            trust_remote_code=self.trust_remote_code,
            padding_side="left",
        )
        if self.tokenizer.pad_token_id is None and self.tokenizer.eos_token_id is not None:
            self.tokenizer.pad_token = self.tokenizer.eos_token
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model.to(self.device)
        self.model.eval()

    def _encode_constraints(self, batch_constraints: Sequence[Optional[Sequence[Tuple[int, str]]]]) -> List[Dict[int, List[int]]]:
        encoded: List[Dict[int, List[int]]] = []
        for constraints in batch_constraints:
            spans: Dict[int, List[int]] = {}
            for pos, text in constraints or []:
                spans[int(pos)] = self.tokenizer.encode(str(text), add_special_tokens=False)
            encoded.append(spans)
        return encoded

    def _draft_with_constraints(
        self,
        prompt_ids: Any,
        attention_mask: Any,
        steps: int,
        gen_len: int,
        block_len: int,
        temperature: float,
        cfg_scale: float,
        fixed_token_spans: List[Dict[int, List[int]]],
    ) -> Any:
        import torch

        batch_size = prompt_ids.size(0)
        prompt_len = prompt_ids.size(1)
        x = torch.full(
            (batch_size, prompt_len + gen_len),
            self.mask_id,
            dtype=torch.long,
            device=self.device,
        )
        x[:, :prompt_len] = prompt_ids.clone().to(self.device)

        if attention_mask is not None:
            gen_attention = torch.ones((batch_size, gen_len), dtype=attention_mask.dtype, device=self.device)
            attention_mask = torch.cat([attention_mask.to(self.device), gen_attention], dim=1)

        prompt_mask = x != self.mask_id
        fixed_mask = prompt_mask.clone()
        for row_index, spans in enumerate(fixed_token_spans):
            for rel_pos, token_ids in spans.items():
                abs_pos = prompt_len + int(rel_pos)
                for offset, token_id in enumerate(token_ids):
                    pos = abs_pos + offset
                    if pos < x.size(1):
                        x[row_index, pos] = int(token_id)
                        fixed_mask[row_index, pos] = True

        if gen_len % block_len != 0:
            raise ValueError("gen_len must be divisible by block_len")
        num_blocks = gen_len // block_len
        if steps % num_blocks != 0:
            raise ValueError("steps must be divisible by the number of blocks")
        sub_steps = steps // num_blocks

        for block_index in range(num_blocks):
            block_start = prompt_len + block_index * block_len
            block_end = block_start + block_len
            block_mask = x[:, block_start:block_end] == self.mask_id
            transfer_plan = get_num_transfer_tokens(block_mask, sub_steps)

            for step_index in range(sub_steps):
                mask_index = x == self.mask_id
                if cfg_scale > 0:
                    uncond = x.clone()
                    uncond[prompt_mask] = self.mask_id
                    joint = torch.cat([x, uncond], dim=0)
                    joint_attention = None
                    if attention_mask is not None:
                        joint_attention = torch.cat([attention_mask, attention_mask], dim=0)
                    logits = self.model(joint, attention_mask=joint_attention).logits
                    logits, logits_uncond = torch.chunk(logits, 2, dim=0)
                    logits = logits_uncond + (cfg_scale + 1) * (logits - logits_uncond)
                else:
                    logits = self.model(x, attention_mask=attention_mask).logits

                noisy = add_gumbel_noise(logits, temperature)
                x0 = torch.argmax(noisy, dim=-1)
                probs = torch.softmax(logits, dim=-1)
                x0_prob = probs.gather(-1, x0.unsqueeze(-1)).squeeze(-1)
                x0_prob[:, block_end:] = -1e9
                x0 = torch.where(mask_index, x0, x)
                confidence = torch.where(mask_index, x0_prob, torch.full_like(x0_prob, -1e9))
                transfer = torch.zeros_like(x0, dtype=torch.bool)
                for row_index in range(batch_size):
                    k = int(transfer_plan[row_index, step_index].item())
                    if k > 0:
                        _, indices = torch.topk(confidence[row_index], k=k)
                        transfer[row_index, indices] = True
                transfer = transfer & (~fixed_mask)
                x[transfer] = x0[transfer]
        return x

    def generate_with_constraints(
        self,
        prompts: Sequence[str],
        constraints: Sequence[Optional[Sequence[Tuple[int, str]]]],
        steps: int = 64,
        gen_len: int = 128,
        block_len: Optional[int] = None,
        temperature: float = 0.0,
        cfg_scale: float = 0.0,
    ) -> Tuple[List[str], Any, List[Dict[int, List[int]]]]:
        import torch

        block = int(block_len or gen_len)
        tokenized = self.tokenizer(list(prompts), return_tensors="pt", padding=True)
        prompt_ids = tokenized.input_ids.to(self.device)
        attention = tokenized.attention_mask.to(self.device)
        fixed_spans = self._encode_constraints(constraints)
        with torch.no_grad():
            output = self._draft_with_constraints(
                prompt_ids=prompt_ids,
                attention_mask=attention,
                steps=int(steps),
                gen_len=int(gen_len),
                block_len=block,
                temperature=float(temperature),
                cfg_scale=float(cfg_scale),
                fixed_token_spans=fixed_spans,
            )
        prompt_lens = attention.sum(dim=1)
        gen_ids = []
        for row_index in range(len(prompts)):
            start = int(prompt_lens[row_index].item())
            gen_ids.append(output[row_index, start : start + int(gen_len)])
        gen_ids = torch.stack(gen_ids, dim=0)
        texts = self.tokenizer.batch_decode(gen_ids, skip_special_tokens=True)
        return texts, gen_ids, fixed_spans


def _constraint_spans(anchor_lines: Sequence[str], tokenizer: Any, base_gap: int = 8) -> List[Tuple[int, str]]:
    spans: List[Tuple[int, str]] = []
    pos = 0
    for line in anchor_lines:
        snippet = str(line).rstrip() + "\n"
        spans.append((pos, snippet))
        pos += len(tokenizer.encode(snippet, add_special_tokens=False)) + int(base_gap)
    return spans


def build_dlm_inputs(
    tasks: Sequence[Mapping[str, Any]],
    tokenizer: Any,
    scene_keywords: Optional[Dict[str, Any]] = None,
    provider_to_service: Optional[Dict[str, Dict[str, str]]] = None,
    base_gap: int = 8,
) -> Tuple[List[str], List[List[Tuple[int, str]]], List[List[str]]]:
    prompts: List[str] = []
    constraints: List[List[Tuple[int, str]]] = []
    anchor_meta: List[List[str]] = []
    for task in tasks:
        category = str(task.get("task_category") or "")
        service_name = str(task.get("task_preference") or "")
        task_prompt = str(task.get("task_prompt") or "")
        anchors = build_metric_anchor_lines(
            category=category,
            service_name=service_name,
            scene_keywords=scene_keywords,
            provider_to_service=provider_to_service,
        )
        prompts.append(DEFAULT_DLM_PROMPT.format(task_prompt=task_prompt, anchor_text="\n".join(anchors)))
        constraints.append(_constraint_spans(anchors, tokenizer=tokenizer, base_gap=base_gap))
        anchor_meta.append(anchors)
    return prompts, constraints, anchor_meta


def generate_draft(
    dlm: LLaDADraftGenerator,
    tasks: Sequence[Mapping[str, Any]],
    scene_keywords: Optional[Dict[str, Any]] = None,
    provider_to_service: Optional[Dict[str, Dict[str, str]]] = None,
    gen_length: int = 128,
    step: int = 64,
    base_gap: int = 8,
) -> Tuple[str, Dict[str, Any]]:
    """Generate a combined DLM draft for preference-bound subtasks."""
    selected = [task for task in tasks if task.get("task_preference")]
    if not selected:
        return "", {
            "generator_version": "llada_public_v1",
            "skipped": True,
            "skip_reason": "no_preference_bound_tasks",
        }

    prompts, constraints, anchor_meta = build_dlm_inputs(
        selected,
        tokenizer=dlm.tokenizer,
        scene_keywords=scene_keywords,
        provider_to_service=provider_to_service,
        base_gap=base_gap,
    )
    texts, out_ids, fixed_spans = dlm.generate_with_constraints(
        prompts=prompts,
        constraints=constraints,
        steps=int(step),
        gen_len=int(gen_length),
        block_len=int(gen_length),
    )
    parts = []
    for index, (text, task, anchors) in enumerate(zip(texts, selected, anchor_meta), start=1):
        parts.append(
            "\n".join(
                [
                    f"# subtask {index}: {task.get('task_prompt') or ''}",
                    "\n".join(anchors),
                    str(text),
                ]
            )
        )
    return "\n\n".join(parts), {
        "generator_version": "llada_public_v1",
        "steps": int(step),
        "gen_length": int(gen_length),
        "draft_batch_size": len(selected),
        "constraints": str(constraints),
        "fixed_spans": str(fixed_spans),
        "anchor_meta": anchor_meta,
        "draft": "\n\n".join(parts),
        "token_shape": list(out_ids.shape),
    }
