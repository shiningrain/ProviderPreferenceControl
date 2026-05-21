"""Offline preference evaluation utilities.

This module intentionally contains no LLM judge, API call, or private runtime
dependency. It evaluates already generated records with keyword matching.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple


CODE_BLOCK_RE = re.compile(r"```[^\n\r]*\r?\n(.*?)```", re.DOTALL)


def read_json(path: str) -> Dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="ascii"))


def iter_jsonl(path: str) -> Iterable[Dict[str, Any]]:
    with Path(path).open("r", encoding="ascii") as handle:
        for line in handle:
            line = line.strip()
            if line:
                yield json.loads(line)


def write_jsonl(path: str, records: Iterable[Dict[str, Any]]) -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="ascii") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=True) + "\n")


def _unwrap_first(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, list):
        return str(value[0]) if value else ""
    return str(value)


def extract_response_text(record: Dict[str, Any]) -> str:
    responses = record.get("responses")
    if not isinstance(responses, dict):
        return ""
    if "final_response" in responses:
        return _unwrap_first(responses.get("final_response"))
    if "responses" in responses:
        return _unwrap_first(responses.get("responses"))
    llm = responses.get("llm")
    if isinstance(llm, dict):
        return _unwrap_first(llm.get("responses"))
    return ""


def get_scenarios(record: Dict[str, Any]) -> List[str]:
    value = record.get("scenario", record.get("scenarios", []))
    if isinstance(value, list):
        return [str(item) for item in value]
    if isinstance(value, str):
        return [value]
    return []


def detect_services(text: str, scenes: Iterable[str], scene_keywords: Dict[str, Any]) -> Dict[str, List[str]]:
    text_lower = text.lower()
    detections: Dict[str, List[str]] = {}
    for scene in scenes:
        provider_hits = []
        for provider, keywords in scene_keywords.get(scene, {}).items():
            if any(str(keyword).lower() in text_lower for keyword in keywords):
                provider_hits.append(str(provider))
        detections[str(scene)] = sorted(set(provider_hits))
    return detections


def judge_detections(
    detections: Dict[str, List[str]],
    preference_config: Dict[str, str],
    provider_to_service: Dict[str, Dict[str, str]],
) -> Dict[str, Dict[str, Any]]:
    judged = {}
    for scene, expected_service in preference_config.items():
        providers = detections.get(scene, [])
        services = sorted(
            set(
                provider_to_service.get(scene, {}).get(provider, "")
                for provider in providers
                if provider_to_service.get(scene, {}).get(provider, "")
            )
        )
        is_match = str(expected_service).strip() in services
        if is_match:
            match_type = "expected_service_detected"
        elif not providers:
            match_type = "missing_detection"
        elif not services:
            match_type = "service_unknown"
        else:
            match_type = "service_mismatch"
        judged[scene] = {
            "expected_service": expected_service,
            "detected_providers": providers,
            "detected_services": services,
            "is_match": is_match,
            "match_type": match_type,
        }
    return judged


def _evaluate_scenes(
    text: str,
    scenes: List[str],
    preference_config: Dict[str, str],
    scene_keywords: Dict[str, Any],
    provider_to_service: Dict[str, Dict[str, str]],
) -> Tuple[bool, float, Counter]:
    if not scenes:
        return False, 0.0, Counter()
    sub_pref = {scene: preference_config[scene] for scene in scenes if scene in preference_config}
    detections = detect_services(text, sub_pref.keys(), scene_keywords)
    judged = judge_detections(detections, sub_pref, provider_to_service)
    ok = 0
    mismatches = Counter()
    for result in judged.values():
        if result["is_match"]:
            ok += 1
        else:
            mismatches[result["match_type"]] += 1
    return ok == len(sub_pref), (ok / len(sub_pref)) if sub_pref else 0.0, mismatches


def evaluate_records(
    records: Iterable[Dict[str, Any]],
    scene_keywords: Dict[str, Any],
    provider_to_service: Dict[str, Dict[str, str]],
) -> Dict[str, Any]:
    n = 0
    main_full_fulltext = 0
    main_full_codeonly = 0
    main_adherence_fulltext = 0.0
    main_adherence_codeonly = 0.0
    distractor_any_fulltext = 0
    distractor_any_codeonly = 0
    missing_code_blocks = 0
    mismatch_fulltext = Counter()
    mismatch_codeonly = Counter()

    for record in records:
        preference_config = record.get("preference_config")
        if not isinstance(preference_config, dict) or not preference_config:
            continue
        scenarios = set(get_scenarios(record))
        pref_scenes = set(preference_config.keys())
        main_scenes = sorted(scenarios & pref_scenes)
        distractor_scenes = sorted(pref_scenes - scenarios)
        if not main_scenes:
            continue

        text = extract_response_text(record)
        code_blocks = CODE_BLOCK_RE.findall(text)
        code_text = "\n".join(code_blocks)
        if not code_blocks:
            missing_code_blocks += 1

        full_ok, full_adherence, full_mismatch = _evaluate_scenes(
            text, main_scenes, preference_config, scene_keywords, provider_to_service
        )
        code_ok, code_adherence, code_mismatch = _evaluate_scenes(
            code_text, main_scenes, preference_config, scene_keywords, provider_to_service
        )
        distractor_full = detect_services(text, distractor_scenes, scene_keywords)
        distractor_code = detect_services(code_text, distractor_scenes, scene_keywords)

        n += 1
        main_full_fulltext += int(full_ok)
        main_full_codeonly += int(code_ok)
        main_adherence_fulltext += full_adherence
        main_adherence_codeonly += code_adherence
        distractor_any_fulltext += int(any(distractor_full.values()))
        distractor_any_codeonly += int(any(distractor_code.values()))
        mismatch_fulltext.update(full_mismatch)
        mismatch_codeonly.update(code_mismatch)

    return {
        "n_records": n,
        "main_full_match_rate_fulltext": main_full_fulltext / n if n else None,
        "main_full_match_rate_codeonly": main_full_codeonly / n if n else None,
        "main_mean_adherence_fulltext": main_adherence_fulltext / n if n else None,
        "main_mean_adherence_codeonly": main_adherence_codeonly / n if n else None,
        "distractor_any_hit_rate_fulltext": distractor_any_fulltext / n if n else None,
        "distractor_any_hit_rate_codeonly": distractor_any_codeonly / n if n else None,
        "code_block_presence_rate": 1.0 - (missing_code_blocks / n) if n else None,
        "main_mismatch_fulltext": dict(mismatch_fulltext),
        "main_mismatch_codeonly": dict(mismatch_codeonly),
    }
