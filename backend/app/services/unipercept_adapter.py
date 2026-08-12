import os
import gc
import re
import time
import torch
import threading
from typing import Dict, Any, Optional
from PIL import Image
import torchvision.transforms as T
from torchvision.transforms.functional import InterpolationMode

from services.base_model import BaseKeepAliveModel, GPU_LOCK

# Monkeypatch transformers PreTrainedModel all_tied_weights_keys property with setter
from transformers import PreTrainedModel
if not hasattr(PreTrainedModel, "all_tied_weights_keys"):
    def get_tied(self):
        return getattr(self, "_all_tied_weights_keys_dict", {})
    def set_tied(self, val):
        if isinstance(val, dict):
            self._all_tied_weights_keys_dict = val
        elif isinstance(val, (list, tuple, set)):
            self._all_tied_weights_keys_dict = {k: k for k in val}
        else:
            self._all_tied_weights_keys_dict = {}
    PreTrainedModel.all_tied_weights_keys = property(get_tied, set_tied)

IMAGENET_MEAN = (0.485, 0.456, 0.406)
IMAGENET_STD = (0.229, 0.224, 0.225)

def build_transform(input_size=448):
    return T.Compose([
        T.Lambda(lambda img: img.convert('RGB') if img.mode != 'RGB' else img),
        T.Resize((input_size, input_size), interpolation=InterpolationMode.BICUBIC),
        T.ToTensor(),
        T.Normalize(mean=IMAGENET_MEAN, std=IMAGENET_STD)
    ])
def score2aestoken(n: int) -> str:
    """Official UniPercept token mapping for continuous score prediction."""
    if not (0 <= n <= 100):
        raise ValueError("Score must be between 0 and 100 inclusive.")
    if 0 <= n <= 25:
        first = 'a'
        offset = n
    elif 26 <= n <= 50:
        first = 'c'
        offset = n - 26
    elif 51 <= n <= 75:
        first = 'd'
        offset = n - 51
    else:
        first = 'e'
        offset = n - 76
    second = chr(ord('a') + offset)
    return first + second

AESTHETICS_TOKEN_LIST = [score2aestoken(i) for i in range(101)]

class UniPerceptAdapter(BaseKeepAliveModel):
    def __init__(self):
        super().__init__("UniPerceptAdapter", keep_alive_timeout=60.0)
        # Default public mirror repo on Hugging Face (100% tokenless automatic download)
        self.model_id = "widegather/unipercept-mirror"
        
        # Check if local model directory exists
        custom_path = os.environ.get("UNIPERCEPT_MODEL_PATH")
        local_candidates = [
            custom_path,
            os.path.abspath("checkpoints/UniPercept"),
            os.path.abspath("checkpoints/unipercept"),
            os.path.expanduser("~/.config/focal_node/models/UniPercept"),
            os.path.expanduser("~/.config/focal_node/models/unipercept"),
        ]
        
        self.is_local_path = False
        for candidate in local_candidates:
            if candidate and os.path.exists(candidate) and os.path.exists(os.path.join(candidate, "config.json")):
                self.model_id = candidate
                self.is_local_path = True
                print(f"[UniPerceptAdapter] Found local UniPercept checkpoint at: {self.model_id}", flush=True)
                break

        self.model = None
        self.processor = None
        self.tokenizer = None
        self.device = "mps" if torch.backends.mps.is_available() else "cpu"
        # bfloat16 for MPS stability (prevents float16 underflow NaN during generation)
        self.torch_dtype = torch.bfloat16 if self.device == "mps" else torch.float32

    def _load_model_locked(self):
        if self.model is None:
            with GPU_LOCK:
                # Pre-load cache cleanup for MPS
                gc.collect()
                if hasattr(torch, "mps") and hasattr(torch.mps, "empty_cache"):
                    try:
                        torch.mps.empty_cache()
                    except Exception:
                        pass

                print(f"[UniPerceptAdapter] Lazy loading UniPercept model ({self.model_id}) on {self.device} ({self.torch_dtype})...", flush=True)
                from transformers import AutoModel, AutoTokenizer, AutoProcessor
                
                extra_kwargs = {"local_files_only": True} if (self.is_local_path or os.path.exists(os.path.expanduser("~/.cache/huggingface/hub"))) else {}

                try:
                    self.model = AutoModel.from_pretrained(
                        self.model_id,
                        torch_dtype=self.torch_dtype,
                        trust_remote_code=True,
                        low_cpu_mem_usage=True,
                        **extra_kwargs
                    ).to(self.device)
                    
                    try:
                        self.tokenizer = AutoTokenizer.from_pretrained(self.model_id, trust_remote_code=True, **extra_kwargs)
                    except Exception:
                        self.tokenizer = None
                        
                    try:
                        self.processor = AutoProcessor.from_pretrained(self.model_id, trust_remote_code=True, **extra_kwargs)
                    except Exception:
                        self.processor = None
                        
                    print("[UniPerceptAdapter] UniPercept Model loaded successfully.", flush=True)
                except Exception as e:
                    print(f"[UniPerceptAdapter] Primary load failed ({e}). Falling back to AutoModel default config...", flush=True)
                    try:
                        self.torch_dtype = torch.float32
                        self.model = AutoModel.from_pretrained(
                            self.model_id,
                            torch_dtype=torch.float32,
                            trust_remote_code=True,
                            **extra_kwargs
                        ).to(self.device)
                        self.tokenizer = AutoTokenizer.from_pretrained(self.model_id, trust_remote_code=True, **extra_kwargs)
                        print("[UniPerceptAdapter] UniPercept Fallback Model loaded successfully.", flush=True)
                    except Exception as fallback_err:
                        print(f"[UniPerceptAdapter] Critical error loading UniPercept model: {fallback_err}", flush=True)
                        raise fallback_err

        self.touch_used()



    def compute_official_vr_score(self, pixel_values: torch.Tensor, desc: str) -> float:
        """
        Computes exact continuous score (0-100) using 100% official UniPercept logic:
        1. Query template formatting with <image> token and 101-token mapping instruction.
        2. Single forward pass to extract last-token logits on AESTHETICS_TOKEN_LIST.
        3. Expected value calculation: torch.softmax(logits, -1) @ weight_tensor.
        """
        if self.model is None or self.tokenizer is None:
            return 70.0

        question = (
            f"<image>Rate the {desc} score of the image in 0-100. "
            f"In the output format, numbers are replaced by 2 corresponding letters, and the mapping relationship is: "
            f"score 0 to 25: 0-aa, 1-ab, 2-ac, 3-ad, ... , 25-az, \n"
            f"score 26 to 50: 26-ca, 27-cb, 28-cc, 29-cd, ..., 50-cy, \n"
            f"score 51 to 75: 51-da, 52-db, 53-dc, 54-dd, ..., 75-dy, \n"
            f"score 76 to 100: 76-ea, 77-eb, 73-ec, 74-ed, ..., 100-ey. \n"
            f"The answer only outputs 2 corresponding letters."
        )

        IMG_START_TOKEN = '<img>'
        IMG_END_TOKEN = '</img>'
        IMG_CONTEXT_TOKEN = '<IMG_CONTEXT>'

        # Load conversation template
        template_name = getattr(self.model.config, 'template', 'internvl2_5') if hasattr(self.model, 'config') else 'internvl2_5'
        try:
            from transformers_modules.widegather.unipercept_hyphen_mirror.conversation import get_conv_template
            template = get_conv_template(template_name)
        except Exception:
            try:
                # Fallback to local snapshot file if dynamic module path differs
                import importlib.util
                import glob
                cached_convs = glob.glob(os.path.expanduser("~/.cache/huggingface/hub/models--widegather--unipercept-mirror/snapshots/*/conversation.py"))
                if cached_convs:
                    spec = importlib.util.spec_from_file_location("conversation", cached_convs[0])
                    conv_mod = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(conv_mod)
                    get_conv_template = conv_mod.get_conv_template
                    template = get_conv_template(template_name)
                else:
                    template = None
            except Exception:
                template = None

        if template is not None:
            template.system_message = getattr(self.model.config, 'system_message', '') if hasattr(self.model, 'config') else ''
            template.append_message(template.roles[0], question)
            template.append_message(template.roles[1], None)
            query = template.get_prompt()
        else:
            query = f"<image>\n{question}"

        img_context_token_id = self.tokenizer.convert_tokens_to_ids(IMG_CONTEXT_TOKEN)
        num_patches = pixel_values.shape[0] if pixel_values is not None else 1
        num_image_token = getattr(self.model, 'num_image_token', 256)
        image_tokens = IMG_START_TOKEN + IMG_CONTEXT_TOKEN * num_image_token * num_patches + IMG_END_TOKEN
        query = query.replace('<image>', image_tokens, 1)

        model_inputs = self.tokenizer(query, return_tensors='pt')
        input_ids = model_inputs['input_ids'].to(self.device)
        attention_mask = model_inputs['attention_mask'].to(self.device)

        with GPU_LOCK:
            with torch.no_grad():
                vit_embeds = self.model.extract_feature(pixel_values)
                input_embeds = self.model.language_model.get_input_embeddings()(input_ids)
                B, N, C = input_embeds.shape
                input_embeds = input_embeds.reshape(B * N, C)
                input_ids_flat = input_ids.reshape(B * N)
                selected = (input_ids_flat == img_context_token_id)
                input_embeds[selected] = vit_embeds.reshape(-1, C).to(input_embeds.device)
                input_embeds = input_embeds.reshape(B, N, C)

                outputs = self.model.language_model(
                    inputs_embeds=input_embeds,
                    attention_mask=attention_mask,
                    use_cache=True,
                    output_hidden_states=True,
                    return_dict=True,
                )
                logits = outputs.logits

        preferential_ids_ = [self.tokenizer.convert_tokens_to_ids(word) for word in AESTHETICS_TOKEN_LIST]
        output_logits = logits[:, -1, preferential_ids_].detach()
        weight_tensor = torch.tensor([x for x in range(101)]).to(device=self.device, dtype=output_logits.dtype)
        score = torch.softmax(output_logits, -1) @ weight_tensor
        return float(score.item())

    def generate_vr_scores(
        self,
        image_path: str,
        metadata: Optional[Dict[str, Any]] = None,
        max_retries: int = 3
    ) -> Dict[str, Any]:
        """
        Runs 3-Way VR Scoring using 100% official UniPercept Token-as-Score logic:
        1. IAA Score (Aesthetics)
        2. IQA Score (Quality)
        3. ISTA Score (Structure & Texture)
        Overall = round(0.4*IAA + 0.3*IQA + 0.3*ISTA)
        """
        with self.lock:
            self.active_requests += 1

        try:
            self._load_model_locked()

            if (not os.path.exists(image_path) and not hasattr(self.model, "chat")) or self.model is None:
                return {"overall": 70, "iaa": 70, "iqa": 70, "ista": 70, "raw_vr_text": ""}

            from utils.image import is_raw_image, decode_raw_to_pil
            if is_raw_image(image_path):
                pil_img = decode_raw_to_pil(image_path)
            else:
                from PIL import ImageOps
                with Image.open(image_path) as raw_img:
                    t_img = ImageOps.exif_transpose(raw_img)
                    pil_img = t_img.convert("RGB") if t_img.mode != "RGB" else t_img.copy()

            target_dtype = self.torch_dtype
            if self.model is not None and hasattr(self.model, "parameters"):
                try:
                    target_dtype = next(self.model.parameters()).dtype
                except Exception:
                    pass

            transform = build_transform(input_size=448)
            pixel_values = transform(pil_img).unsqueeze(0).to(dtype=target_dtype).to(self.device)

            # 3 Official Perceptual Domains
            domains = {
                "iaa": "aesthetics",
                "iqa": "quality",
                "ista": "structure and texture richness"
            }

            scores = {}
            for key, desc in domains.items():
                try:
                    sc = self.compute_official_vr_score(pixel_values, desc)
                    scores[key] = round(sc, 2)
                except Exception as vr_err:
                    print(f"[UniPerceptAdapter] Official VR score error for {key}: {vr_err}", flush=True)
                    scores[key] = 70.0

            iaa_val = scores.get("iaa", 70.0)
            iqa_val = scores.get("iqa", 70.0)
            ista_val = scores.get("ista", 70.0)

            overall_val = round((0.4 * iaa_val) + (0.3 * iqa_val) + (0.3 * ista_val))
            overall_val = min(100, max(0, overall_val))

            raw_vr_summary = f"IAA: {iaa_val}, IQA: {iqa_val}, ISTA: {ista_val} -> Overall: {overall_val}"

            return {
                "overall": overall_val,
                "iaa": iaa_val,
                "iqa": iqa_val,
                "ista": ista_val,
                "raw_vr_text": raw_vr_summary
            }

        finally:
            with self.lock:
                self.last_used_time = time.time()
                self.active_requests -= 1

    def generate_vqa_critiques_3way(
        self,
        image_path: str,
        metadata: Optional[Dict[str, Any]] = None,
        scores_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, str]:
        """
        Runs 3-Way Dedicated VQA inference with optional Stage 1 Score Conditioning:
        1. IAA (Aesthetics, Lighting, Composition, Color Harmony)
        2. IQA (Technical Quality, Sharpness, Noise, Depth of Field)
        3. ISTA (Surface Texture, Edge Definition, Micro-contrast)
        """
        with self.lock:
            self.active_requests += 1

        try:
            self._load_model_locked()

            if (not os.path.exists(image_path) and not hasattr(self.model, "chat")) or self.model is None:
                return {
                    "iaa": "이미지를 분석할 수 없습니다.",
                    "iqa": "이미지를 분석할 수 없습니다.",
                    "ista": "이미지를 분석할 수 없습니다."
                }

            from utils.image import is_raw_image, decode_raw_to_pil
            if is_raw_image(image_path):
                pil_img = decode_raw_to_pil(image_path)
            else:
                from PIL import ImageOps
                with Image.open(image_path) as raw_img:
                    t_img = ImageOps.exif_transpose(raw_img)
                    pil_img = t_img.convert("RGB") if t_img.mode != "RGB" else t_img.copy()

            exif_desc = ""
            if metadata:
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
                if parts:
                    exif_desc = f"[EXIF: {', '.join(parts)}]\n"

            score_desc = ""
            if scores_context and isinstance(scores_context, dict):
                ov = scores_context.get("overall")
                iaa = scores_context.get("iaa")
                iqa = scores_context.get("iqa")
                ista = scores_context.get("ista")
                score_desc = (
                    f"[Target Perceptual Metric Scores]\n"
                    f"- Overall Photo Rating: {ov}/100\n"
                    f"- Aesthetics & Composition (IAA): {iaa}/100\n"
                    f"- Technical Quality & Clarity (IQA): {iqa}/100\n"
                    f"- Structure & Textural Details (ISTA): {ista}/100\n"
                    f"Instruction: Analyze this photo reflecting these exact scores. If any score is under 70, strictly focus on identifying the specific visual defects, noise, blur, lighting imbalance, or compositional flaws. Do NOT use inflated praise words like 'masterpiece', 'flawless', or 'impeccable' unless scores exceed 90.\n\n"
                )

            target_dtype = self.torch_dtype
            if self.model is not None and hasattr(self.model, "parameters"):
                try:
                    target_dtype = next(self.model.parameters()).dtype
                except Exception:
                    pass

            transform = build_transform(input_size=448)
            pixel_values = transform(pil_img).unsqueeze(0).to(dtype=target_dtype).to(self.device)

            from services.ai_parser import (
                UNIPERCEPT_VQA_IAA_PROMPT,
                UNIPERCEPT_VQA_IQA_PROMPT,
                UNIPERCEPT_VQA_ISTA_PROMPT
            )

            vqa_prompts = {
                "iaa": f"{exif_desc}{score_desc}{UNIPERCEPT_VQA_IAA_PROMPT}",
                "iqa": f"{exif_desc}{score_desc}{UNIPERCEPT_VQA_IQA_PROMPT}",
                "ista": f"{exif_desc}{score_desc}{UNIPERCEPT_VQA_ISTA_PROMPT}",
            }

            generation_config = dict(
                max_new_tokens=1024,
                do_sample=False,
                num_beams=1,
                repetition_penalty=1.2
            )

            critiques = {}
            for domain_key, prompt_text in vqa_prompts.items():
                print(f"[UniPerceptAdapter] -> Generating VQA critique domain: {domain_key.upper()}...", flush=True)
                with GPU_LOCK:
                    try:
                        if hasattr(self.model, "chat"):
                            txt = self.model.chat(
                                self.tokenizer,
                                pixel_values,
                                prompt_text,
                                generation_config=generation_config
                            )
                        else:
                            inputs = self.processor(images=pil_img, text=prompt_text, return_tensors="pt").to(self.device, dtype=self.torch_dtype)
                            with torch.no_grad():
                                outputs = self.model.generate(**inputs, max_new_tokens=1024)
                            txt = self.processor.decode(outputs[0], skip_special_tokens=True)
                        critiques[domain_key] = txt.strip()
                        print(f"[UniPerceptAdapter] -> Domain {domain_key.upper()} critique finished ({len(txt)} chars).", flush=True)
                    except Exception as eval_err:
                        print(f"[UniPerceptAdapter] VQA inference error ({domain_key}): {eval_err}", flush=True)
                        critiques[domain_key] = f"분석 오류: {eval_err}"

            return critiques

        finally:
            with self.lock:
                self.last_used_time = time.time()
                self.active_requests -= 1

    def generate_vqa_critique(
        self,
        image_path: str,
        metadata: Optional[Dict[str, Any]] = None,
        scores_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Backward-compatible single VQA critique generator with optional score conditioning."""
        res_3way = self.generate_vqa_critiques_3way(image_path, metadata, scores_context=scores_context)
        merged = (
            f"[Aesthetics & Composition]\n{res_3way.get('iaa', '')}\n\n"
            f"[Technical Quality & Clarity]\n{res_3way.get('iqa', '')}\n\n"
            f"[Structure & Textural Details]\n{res_3way.get('ista', '')}"
        )
        return {"critique": merged}

    def generate_unipercept_critique(
        self,
        image_path: str,
        metadata: Optional[Dict[str, Any]] = None,
        custom_prompt: Optional[str] = None,
        retry_if_score_missing: bool = True,
        max_retries: int = 5
    ) -> Dict[str, Any]:
        """
        Runs 2-Stage Pipeline (VR Mode for scores + VQA Mode for critique) if custom_prompt is None.
        Otherwise executes single inference with custom_prompt.
        """
        if custom_prompt is None:
            return self.generate_full_ensemble_critique(image_path, metadata)

        # Custom single-prompt path
        with self.lock:
            self.active_requests += 1

        try:
            self._load_model_locked()

            if (not os.path.exists(image_path) and not hasattr(self.model, "chat")) or self.model is None:
                return {
                    "critique": f"이미지 파일을 찾을 수 없거나 모델이 로드되지 않았습니다: {image_path}",
                    "aesthetics_score": None,
                    "quality_score": None
                }

            from utils.image import is_raw_image, decode_raw_to_pil
            if is_raw_image(image_path):
                pil_img = decode_raw_to_pil(image_path)
            else:
                from PIL import ImageOps
                with Image.open(image_path) as raw_img:
                    t_img = ImageOps.exif_transpose(raw_img)
                    pil_img = t_img.convert("RGB") if t_img.mode != "RGB" else t_img.copy()

            exif_desc = ""
            if metadata:
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
                if parts:
                    exif_desc = f"[EXIF: {', '.join(parts)}]\n"

            prompt_text = f"{exif_desc}{custom_prompt}"

            target_dtype = self.torch_dtype
            if self.model is not None and hasattr(self.model, "parameters"):
                try:
                    target_dtype = next(self.model.parameters()).dtype
                except Exception:
                    pass

            transform = build_transform(input_size=448)
            pixel_values = transform(pil_img).unsqueeze(0).to(dtype=target_dtype).to(self.device)

            generation_config = dict(
                max_new_tokens=1024,
                do_sample=False,
                num_beams=1,
                repetition_penalty=1.2
            )

            critique_text = ""
            for attempt in range(1, max_retries + 1):
                with GPU_LOCK:
                    try:
                        if hasattr(self.model, "chat"):
                            gen_cfg = dict(generation_config, do_sample=True, temperature=0.7, top_p=0.9) if attempt > 1 else generation_config
                            critique_text = self.model.chat(
                                self.tokenizer,
                                pixel_values,
                                prompt_text,
                                generation_config=gen_cfg
                            )
                        else:
                            inputs = self.processor(images=pil_img, text=prompt_text, return_tensors="pt").to(self.device, dtype=self.torch_dtype)
                            with torch.no_grad():
                                outputs = self.model.generate(**inputs, max_new_tokens=1024)
                            critique_text = self.processor.decode(outputs[0], skip_special_tokens=True)
                    except Exception as eval_err:
                        print(f"[UniPerceptAdapter] Inference error: {eval_err}", flush=True)
                        critique_text = f"UniPercept 분석 중 오류가 발생했습니다: {str(eval_err)}"

                quality_score = self._extract_score_from_text(
                    critique_text,
                    ["Overall Score", "Score", "Aesthetic Score", "Quality Score", "Structure Score"]
                )

                if quality_score is not None or not retry_if_score_missing:
                    break

            if quality_score is None:
                quality_score = 70

            return {
                "critique": critique_text.strip(),
                "aesthetics_score": quality_score,
                "quality_score": quality_score
            }

        finally:
            with self.lock:
                self.last_used_time = time.time()
                self.active_requests -= 1

    @classmethod
    def _resolve_score_value(cls, raw_val: int, text: str) -> Optional[int]:
        """
        Validates and normalizes score values.
        Special Handling for '1-point':
        - If raw_val == 1, checks if text contains high praise/perfection keywords (e.g. 'perfect', 'masterpiece', 'excellent', 'transcend', 'flawless', 'prowess', 'surpassing', '1 perfect', '1/1').
        - If positive praise context is detected, upgrades 1-point to 100 (Model intended 1.0 scale or 1st tier / Perfect).
        - Otherwise, discards (< 15) to trigger safety net retry.
        """
        if 15 <= raw_val <= 100:
            return raw_val

        if raw_val == 1:
            if re.search(r"(?:1\s*Perfect|1\s*/\s*1\b|1\s*out of\s*1\b|=?\s*perfect)", text, re.IGNORECASE):
                return 100

            positive_keywords = [
                "perfect", "excellence", "excellent", "masterpiece", "exceptional",
                "flawless", "prowess", "transcend", "surpassing", "striking",
                "superb", "breathtaking", "outstanding", "impeccabl"
            ]
            text_lower = text.lower()
            if any(kw in text_lower for kw in positive_keywords):
                return 100

        return None

    @classmethod
    def _extract_score_from_text(cls, text: str, prefixes: list[str]) -> Optional[int]:
        """
        Strictly extracts scores from model response by:
        1. Searching top lines first (Score-First header pattern).
        2. Searching trailing lines (Bottom-Up format).
        3. Scanning full text for explicit prefix matches.
        4. Validating score through _resolve_score_value.
        """
        if not text:
            return None

        for pfx in prefixes:
            if re.search(rf"(?:{pfx})\s*[:=]?\s*1\s*Perfect", text, re.IGNORECASE):
                return 100

        lines = [line.strip() for line in text.strip().split("\n") if line.strip()]

        for pfx in prefixes:
            pattern = rf"(?:{pfx})\s*[:=]?\s*\[?(\d{{1,3}})"
            for line in lines[:10]:
                m = re.search(pattern, line, re.IGNORECASE)
                if m:
                    res = cls._resolve_score_value(int(m.group(1)), text)
                    if res is not None:
                        return res

        for pfx in prefixes:
            pattern = rf"(?:{pfx})\s*[:=]?\s*\[?(\d{{1,3}})"
            for line in reversed(lines[-6:]):
                m = re.search(pattern, line, re.IGNORECASE)
                if m:
                    res = cls._resolve_score_value(int(m.group(1)), text)
                    if res is not None:
                        return res

        for pfx in prefixes:
            pattern = rf"(?:{pfx})\s*[:=]?\s*\[?(\d{{1,3}})"
            m = re.search(pattern, text, re.IGNORECASE)
            if m:
                res = cls._resolve_score_value(int(m.group(1)), text)
                if res is not None:
                    return res

        for line in reversed(lines[-5:]):
            m = re.search(r"\[?(\d{1,3})\]?\s*(?:out of|/)\s*100", line, re.IGNORECASE)
            if not m:
                m = re.search(r"(?:score of|rating of)\s*\[?(\d{1,3})\]?", line, re.IGNORECASE)
            if m:
                res = cls._resolve_score_value(int(m.group(1)), text)
                if res is not None:
                    return res

        for line in reversed(lines[-2:]):
            if line.isdigit():
                res = cls._resolve_score_value(int(line), text)
                if res is not None:
                    return res

        return None

    @classmethod
    def _extract_3_vr_scores_dict(cls, text: str) -> Dict[str, Optional[int]]:
        """
        Extracts the 3 official UniPercept VR metrics:
        - iaa (Aesthetics)
        - iqa (Quality)
        - ista (Structure & Texture)
        """
        scores: Dict[str, Optional[int]] = {"iaa": None, "iqa": None, "ista": None}
        if not text:
            return scores

        patterns = {
            "iaa": [r"IAA\s*Score", r"Aesthetic[s]?\s*Score", r"Image\s*Aesthetic\s*Score", r"Aesthetics"],
            "iqa": [r"IQA\s*Score", r"Quality\s*Score", r"Image\s*Quality", r"Quality\s*Image\s*Scores"],
            "ista": [r"ISTA\s*Score", r"Structure\s*Score", r"Structure\s*(?:&|and)?\s*Texture", r"Structure\s*Texture"],
        }

        for key, pfx_list in patterns.items():
            for pfx in pfx_list:
                if re.search(rf"(?:{pfx})\s*[:=]?\s*(?:1\s*Perfect|perfect\b)", text, re.IGNORECASE):
                    scores[key] = 100
                    break

                m = re.search(rf"(?:{pfx})\s*[:=]?\s*\[?(\d{{1,3}})", text, re.IGNORECASE)
                if m:
                    res = cls._resolve_score_value(int(m.group(1)), text)
                    if res is not None:
                        scores[key] = res
                        break
        return scores

    @classmethod
    def _extract_all_scores_dict(cls, text: str) -> Dict[str, Optional[int]]:
        """
        Robustly extracts all 4 domain scores (overall, iaa, iqa, ista) simultaneously.
        """
        scores: Dict[str, Optional[int]] = {"overall": None, "iaa": None, "iqa": None, "ista": None}
        if not text:
            return scores

        vr_3 = cls._extract_3_vr_scores_dict(text)
        scores.update(vr_3)

        for pfx in [r"Overall\s*Score", r"Final\s*Score", r"Total\s*Score"]:
            m = re.search(rf"(?:{pfx})\s*[:=]?\s*\[?(\d{{1,3}})", text, re.IGNORECASE)
            if m:
                res = cls._resolve_score_value(int(m.group(1)), text)
                if res is not None:
                    scores["overall"] = res
                    break

        return scores

    def generate_full_ensemble_critique(
        self,
        image_path: str,
        metadata: Optional[Dict[str, Any]] = None,
        photo_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Executes 2-Stage Pipeline (Option 1):
        - Stage 1: VR Mode -> Fast inference for 3 official metrics (IAA, IQA, ISTA)
        - Stage 1 Math: Overall = round(0.4*IAA + 0.3*IQA + 0.3*ISTA)
        - Stage 2: VQA Mode -> Pure deep photographic critique without score constraints
        - Merges scores scoreboard and VQA critique for translation by Gemma.
        """
        if photo_id:
            from services.critique_status import critique_status_manager
            critique_status_manager.update(photo_id, 1, 4, "점수 산출 중", 20)

        print("[UniPerceptAdapter] [Stage 1/2] Computing 3-Way VR scores (IAA / IQA / ISTA)...", flush=True)
        # 1. Stage 1: VR Mode (Fast 3-Metric Score Extraction)
        vr_result = self.generate_vr_scores(image_path, metadata=metadata, max_retries=3)
        final_overall = vr_result["overall"]
        final_iaa = vr_result["iaa"]
        final_iqa = vr_result["iqa"]
        final_ista = vr_result["ista"]

        scores_summary = {
            "overall": final_overall,
            "iaa": final_iaa,
            "iqa": final_iqa,
            "ista": final_ista,
            "comp_direct": final_overall,
            "weighted_analysis": final_overall
        }
        print(f"[UniPerceptAdapter] [Stage 1/2] VR Scores computed: Overall={final_overall}, IAA={final_iaa}, IQA={final_iqa}, ISTA={final_ista}", flush=True)

        if photo_id:
            from services.critique_status import critique_status_manager
            critique_status_manager.update(photo_id, 2, 4, "비평 작성 중", 50)

        print("[UniPerceptAdapter] [Stage 2/2] Generating 3-Way VQA deep critiques...", flush=True)
        # 2. Stage 2: VQA Mode (Score-Conditioned Photographic Critique)
        vqa_result = self.generate_vqa_critique(image_path, metadata=metadata, scores_context=scores_summary)
        vqa_critique = vqa_result["critique"]
        print("[UniPerceptAdapter] UniPercept full ensemble critique generation finished.", flush=True)

        return {
            "critique": vqa_critique,
            "quality_score": final_overall,
            "scores": scores_summary,
            "text_comp": vqa_critique,
            "raw_vr_text": vr_result.get("raw_vr_text", "")
        }

_unipercept_adapter_instance = None
_unipercept_lock = threading.Lock()

def get_unipercept_adapter() -> UniPerceptAdapter:
    global _unipercept_adapter_instance
    if _unipercept_adapter_instance is None:
        with _unipercept_lock:
            if _unipercept_adapter_instance is None:
                _unipercept_adapter_instance = UniPerceptAdapter()
    return _unipercept_adapter_instance
