"""Parsers for structured critique scoreboards and Gemma JSON outputs."""

import json
import re

from services.critique_prompts import (
    GEMMA_CRITIQUE_SUMMARY_SYSTEM_PROMPT,
    GEMMA_CRITIQUE_SYSTEM_PROMPT,
    GEMMA_DOCUMENT_FORMATTING_SYSTEM_PROMPT,
    GEMMA_PERCEPTUAL_CRITIQUE_SYSTEM_PROMPT,
    GEMMA_SYSTEM_PROMPT,
    UNIPERCEPT_VQA_SINGLE_PASS_PROMPT,
    format_critique_document_structuring_user_prompt,
    format_exif_text,
    format_perceptual_critique_user_prompt,
    format_score_info_text,
    format_siglip_hints_text,
)

__all__ = [
    "GEMMA_SYSTEM_PROMPT",
    "GEMMA_CRITIQUE_SYSTEM_PROMPT",
    "GEMMA_CRITIQUE_SUMMARY_SYSTEM_PROMPT",
    "GEMMA_DOCUMENT_FORMATTING_SYSTEM_PROMPT",
    "GEMMA_PERCEPTUAL_CRITIQUE_SYSTEM_PROMPT",
    "UNIPERCEPT_VQA_SINGLE_PASS_PROMPT",
    "format_score_info_text",
    "format_exif_text",
    "format_siglip_hints_text",
    "format_critique_document_structuring_user_prompt",
    "format_perceptual_critique_user_prompt",
    "parse_scoreboard_scores",
    "parse_gemma_json_output",
    "_ensure_string_list",
]


def _extract_float_score(pattern: str, text: str) -> float | None:
    """Extracts a floating point score matching the given regex pattern."""
    match = re.search(pattern, text)
    if not match:
        return None
    try:
        return float(match.group(1))
    except (ValueError, TypeError):
        return None


def parse_scoreboard_scores(text: str | None) -> dict[str, float | None]:
    """Parses [6-Way 앙상블 비평 스코어보드] block from critique text into float scores."""
    empty_scores: dict[str, float | None] = {
        "overall": None,
        "iaa": None,
        "iqa": None,
        "ista": None,
    }
    if not text or not isinstance(text, str):
        return empty_scores

    scoreboard_match = re.search(
        r"\[(?:📊\s*)?6-Way\s*앙상블\s*비평\s*스코어보드\]([\s\S]*?)(?=(?:\n\s*#{1,4}\s*|\n\s*\d+\.\s*\[|\n\s*>\s*|$))",
        text,
        re.IGNORECASE,
    )
    if not scoreboard_match:
        fallback_score = _extract_float_score(r"\[품질/미학 점수:\s*([0-9]+(?:\.[0-9]+)?)점", text)
        if fallback_score is not None:
            empty_scores["overall"] = fallback_score
        return empty_scores

    block = scoreboard_match.group(1)
    return {
        "overall": _extract_float_score(r"최종\s*종합\s*평점:\s*([0-9]+(?:\.[0-9]+)?)", block),
        "iaa": _extract_float_score(r"(?:미학\s*(?:및\s*구도)?|IAA)[\s\S]*?:\s*([0-9]+(?:\.[0-9]+)?)", block),
        "iqa": _extract_float_score(r"(?:화질\s*(?:및\s*선명도|및\s*광학\s*기술)?|IQA)[\s\S]*?:\s*([0-9]+(?:\.[0-9]+)?)", block),
        "ista": _extract_float_score(r"(?:구조\s*(?:및\s*질감)?|ISTA)[\s\S]*?:\s*([0-9]+(?:\.[0-9]+)?)", block),
    }


def _ensure_string_list(raw_value) -> list[str]:
    """Normalizes list or comma-delimited string values into trimmed string lists."""
    if isinstance(raw_value, list):
        return [str(token).strip() for token in raw_value if str(token).strip()]
    if not isinstance(raw_value, str) or not raw_value.strip():
        return []
    if "," in raw_value:
        return [token.strip() for token in raw_value.split(",") if token.strip()]
    return [raw_value.strip()]


def _strip_markdown_fences(raw_text: str) -> str:
    """Removes wrapping ```json ... ``` markdown code fences if present."""
    clean_output = raw_text.strip()
    if "```" not in clean_output:
        return clean_output
    parts = clean_output.split("```")
    if len(parts) < 3:
        return clean_output
    fenced_body = parts[1].strip()
    if fenced_body.lower().startswith("json"):
        return fenced_body[4:].strip()
    return fenced_body


def _extract_json_dict(clean_output: str, raw_output: str) -> dict | None:
    """Extracts and parses the outermost JSON object from text if valid."""
    start_idx = clean_output.find("{")
    end_idx = clean_output.rfind("}")
    if start_idx == -1 or end_idx <= start_idx:
        return None
    json_candidate = clean_output[start_idx:end_idx + 1]
    try:
        parsed_payload = json.loads(json_candidate)
    except Exception as parse_err:
        print(f"[AI Parser] JSON parsing failed: {parse_err}. Raw: {raw_output}", flush=True)
        return None
    return parsed_payload if isinstance(parsed_payload, dict) else None


def parse_gemma_json_output(output: str) -> dict:
    """Safely parses JSON candidate from VLM output text with fallback handling."""
    default_result = {"caption": "", "tags": [], "aesthetic_tags": []}
    if not output:
        return default_result

    clean_output = _strip_markdown_fences(output)
    parsed_payload = _extract_json_dict(clean_output, output)
    if parsed_payload is not None:
        return {
            "caption": str(parsed_payload.get("caption", "") or ""),
            "tags": _ensure_string_list(parsed_payload.get("tags")),
            "aesthetic_tags": _ensure_string_list(parsed_payload.get("aesthetic_tags")),
        }

    if clean_output and len(clean_output) > 5:
        return {"caption": clean_output, "tags": [], "aesthetic_tags": []}
    return default_result
