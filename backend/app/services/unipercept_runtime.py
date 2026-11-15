"""Runtime helpers for UniPercept checkpoint discovery, templates, queries, and tensor prep."""

from __future__ import annotations

import os
import re
from typing import Any, Dict, Optional, Tuple

from services.base_model import GPU_LOCK
from services.unipercept_utils import build_transform, patch_transformers_tied_weights

IMG_START_TOKEN = "<img>"
IMG_END_TOKEN = "</img>"
IMG_CONTEXT_TOKEN = "<IMG_CONTEXT>"


def resolve_unipercept_model_source() -> tuple[str, bool]:
    """Resolves local UniPercept checkpoint directory or falls back to HuggingFace repo ID."""
    from config import CONFIG_DIR

    default_repo = "widegather/unipercept-mirror"
    local_candidates = (
        os.environ.get("UNIPERCEPT_MODEL_PATH"),
        os.path.abspath("checkpoints/UniPercept"),
        os.path.abspath("checkpoints/unipercept"),
        os.path.join(CONFIG_DIR, "models", "UniPercept"),
        os.path.join(CONFIG_DIR, "models", "unipercept"),
    )
    for candidate in local_candidates:
        if candidate and os.path.exists(candidate) and os.path.exists(os.path.join(candidate, "config.json")):
            print(f"[UniPerceptAdapter] Found local UniPercept checkpoint at: {candidate}", flush=True)
            return candidate, True
    return default_repo, False


def _load_optional_aux_components(
    model_id: str,
    extra_kwargs: Dict[str, Any],
) -> tuple[Optional[Any], Optional[Any]]:
    from transformers import AutoProcessor, AutoTokenizer

    tokenizer = None
    processor = None
    try:
        tokenizer = AutoTokenizer.from_pretrained(model_id, trust_remote_code=True, **extra_kwargs)
    except Exception as tok_err:
        print(f"[UniPerceptAdapter] AutoTokenizer load warning: {tok_err}", flush=True)
    try:
        processor = AutoProcessor.from_pretrained(model_id, trust_remote_code=True, **extra_kwargs)
    except Exception as proc_err:
        print(f"[UniPerceptAdapter] AutoProcessor load warning: {proc_err}", flush=True)
    return tokenizer, processor


def _load_fallback_unipercept(model_id: str, device: str, extra_kwargs: Dict[str, Any]) -> tuple[Any, Optional[Any], Optional[Any], Any]:
    import torch
    from transformers import AutoModel, AutoTokenizer

    loaded_model = AutoModel.from_pretrained(model_id, torch_dtype=torch.float32, trust_remote_code=True, **extra_kwargs).to(device)
    if hasattr(loaded_model, "eval"):
        loaded_model.eval()
    tokenizer = AutoTokenizer.from_pretrained(model_id, trust_remote_code=True, **extra_kwargs)
    print("[UniPerceptAdapter] UniPercept Fallback Model loaded successfully.", flush=True)
    return loaded_model, tokenizer, None, torch.float32


def load_unipercept_components(
    model_id: str, device: str, preferred_dtype: Any, is_local_path: bool,
) -> tuple[Any, Optional[Any], Optional[Any], Any]:
    """Loads UniPercept model/tokenizer/processor in eval mode with float32 fallback."""
    from transformers import AutoModel

    patch_transformers_tied_weights()
    has_hf_cache = os.path.exists(os.path.expanduser("~/.cache/huggingface/hub"))
    extra_kwargs: Dict[str, Any] = {"local_files_only": True} if (is_local_path or has_hf_cache) else {}
    try:
        loaded_model = AutoModel.from_pretrained(
            model_id, torch_dtype=preferred_dtype, trust_remote_code=True, low_cpu_mem_usage=True, **extra_kwargs,
        ).to(device)
        if hasattr(loaded_model, "eval"):
            loaded_model.eval()
        tokenizer, processor = _load_optional_aux_components(model_id, extra_kwargs)
        print("[UniPerceptAdapter] UniPercept Model loaded successfully.", flush=True)
        return loaded_model, tokenizer, processor, preferred_dtype
    except Exception as primary_err:
        print(f"[UniPerceptAdapter] Primary load failed ({primary_err}). Falling back to AutoModel default config...", flush=True)
        return _load_fallback_unipercept(model_id, device, extra_kwargs)


def resolve_conversation_template(model: Any) -> Optional[Any]:
    """Dynamically loads conversation template from transformers_modules or HF snapshot cache."""
    template_name = getattr(model.config, "template", "internvl2_5") if hasattr(model, "config") else "internvl2_5"
    try:
        from transformers_modules.widegather.unipercept_hyphen_mirror.conversation import get_conv_template

        return get_conv_template(template_name)
    except Exception as direct_err:
        print(f"[UniPerceptAdapter] Direct template import fallback: {direct_err}", flush=True)

    import glob
    import importlib.util

    hf_cache = os.path.expanduser("~/.cache/huggingface/hub/models--widegather--unipercept-mirror")
    conv_files = glob.glob(os.path.join(hf_cache, "**", "conversation.py"), recursive=True)
    if not conv_files:
        return None
    spec = importlib.util.spec_from_file_location("unipercept_conv", conv_files[0])
    if spec is None or spec.loader is None:
        return None
    conv_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(conv_module)
    return conv_module.get_conv_template(template_name)


def build_vr_score_query(desc: str, template: Any, model: Any, num_patches: int) -> str:
    """Formats the official UniPercept VR question and injects image context tokens."""
    question = (
        f"<image>Rate the {desc} score of the image in 0-100. "
        f"In the output format, numbers are replaced by 2 corresponding letters, and the mapping relationship is: "
        f"score 0 to 25: 0-aa, 1-ab, 2-ac, 3-ad, ... , 25-az, \n"
        f"score 26 to 50: 26-ca, 27-cb, 28-cc, 29-cd, ..., 50-cy, \n"
        f"score 51 to 75: 51-da, 52-db, 53-dc, 54-dd, ..., 75-dy, \n"
        f"score 76 to 100: 76-ea, 77-eb, 73-ec, 74-ed, ..., 100-ey. \n"
        f"The answer only outputs 2 corresponding letters."
    )
    if template is not None:
        template.system_message = getattr(model.config, "system_message", "") if hasattr(model, "config") else ""
        template.append_message(template.roles[0], question)
        template.append_message(template.roles[1], None)
        query = template.get_prompt()
    else:
        query = f"<image>\n{question}"

    num_image_token = getattr(model, "num_image_token", 256)
    image_tokens = IMG_START_TOKEN + IMG_CONTEXT_TOKEN * num_image_token * num_patches + IMG_END_TOKEN
    return query.replace("<image>", image_tokens, 1)


def build_vqa_query(prompt_text: str, template: Any, model: Any, num_patches: int) -> Tuple[str, str]:
    """Formats VQA question with conversation template and image context tokens."""
    question = prompt_text if "<image>" in prompt_text else f"<image>\n{prompt_text}"
    sep_token = "<|im_end|>"
    if template is not None:
        sys_msg = getattr(model, "system_message", None)
        if sys_msg is None and hasattr(model, "config"):
            sys_msg = getattr(model.config, "system_message", None)
        if sys_msg is not None:
            template.system_message = sys_msg
        if getattr(template, "sep", None):
            sep_token = template.sep.strip()
        template.append_message(template.roles[0], question)
        template.append_message(template.roles[1], None)
        query = template.get_prompt()
    else:
        query = f"<|im_start|>user\n{question}<|im_end|>\n<|im_start|>assistant\n"

    num_image_token = getattr(model, "num_image_token", 256)
    image_tokens = IMG_START_TOKEN + (IMG_CONTEXT_TOKEN * num_image_token * num_patches) + IMG_END_TOKEN
    return query.replace("<image>", image_tokens, 1), sep_token


def clean_vqa_response(raw_text: str, sep_token: str) -> str:
    """Strips reasoning <think> blocks and conversation separator tokens from VQA output."""
    cleaned = raw_text.split(sep_token)[0] if sep_token else raw_text
    cleaned = cleaned.split("<|im_end|>")[0].split("<|endoftext|>")[0]
    cleaned = re.sub(r"<think>.*?</think>", "", cleaned, flags=re.DOTALL | re.IGNORECASE)
    cleaned = re.sub(r"</?think>", "", cleaned, flags=re.IGNORECASE)
    return cleaned.strip()


def format_unipercept_exif_desc(metadata: Optional[Dict[str, Any]]) -> str:
    """Formats EXIF attributes into concise English descriptor header for UniPercept."""
    if not metadata:
        return ""
    parts = []
    if metadata.get("camera_model"):
        parts.append(f"Camera: {metadata['camera_model']}")
    if metadata.get("lens_model"):
        parts.append(f"Lens: {metadata['lens_model']}")
    if metadata.get("f_number"):
        parts.append(f"F/{metadata['f_number']}")
    if metadata.get("shutter_speed"):
        parts.append(f"Shutter: {metadata['shutter_speed']}")
    if metadata.get("iso"):
        parts.append(f"ISO {metadata['iso']}")
    return f"[EXIF: {', '.join(parts)}]\n" if parts else ""


def format_score_guidance_desc(scores_context: Optional[Dict[str, Any]]) -> str:
    """Formats target VR scores into VQA grounding guidance block."""
    if not scores_context or not isinstance(scores_context, dict):
        return ""
    return (
        f"[Target Perceptual Metric Scores]\n"
        f"- Overall Photo Rating: {scores_context.get('overall')}/100\n"
        f"- Aesthetics & Composition (IAA): {scores_context.get('iaa')}/100\n"
        f"- Technical Quality & Clarity (IQA): {scores_context.get('iqa')}/100\n"
        f"- Structure & Textural Details (ISTA): {scores_context.get('ista')}/100\n"
        f"Instruction: Analyze this photo reflecting these exact scores. If any score is under 70, strictly focus on identifying the specific visual defects, noise, blur, lighting imbalance, or compositional flaws. Do NOT use inflated praise words like 'masterpiece', 'flawless', or 'impeccable' unless scores exceed 90.\n\n"
    )


def prepare_pixel_values_tensor(
    pil_img: Any,
    model: Any,
    default_dtype: Any,
    device: str,
    photo_id: Optional[str] = None,
) -> Any:
    """Preprocesses PIL image into target dtype tensor and moves it to device under GPU_LOCK."""
    if pil_img is None:
        return None
    target_dtype = default_dtype
    if model is not None and hasattr(model, "parameters"):
        try:
            target_dtype = next(model.parameters()).dtype
        except Exception as param_err:
            print(f"[UniPerceptAdapter] Parameter dtype inspection note: {param_err}", flush=True)
    transform = build_transform(input_size=448)
    transformed = transform(pil_img).unsqueeze(0).to(dtype=target_dtype)
    with GPU_LOCK:
        if photo_id:
            from services.critique_status import critique_status_manager

            critique_status_manager.check_cancelled(photo_id)
        return transformed.to(device)
