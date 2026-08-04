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

from services.mlx_adapters import GPU_LOCK

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

class UniPerceptAdapter:
    def __init__(self):
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
        
        self.last_used_time = 0.0
        self.active_requests = 0
        self.lock = threading.Lock()
        self.timer_thread = None
        self.timer_active = False

    def _load_model_locked(self):
        if self.model is None:
            with GPU_LOCK:
                print(f"[UniPerceptAdapter] Lazy loading UniPercept model ({self.model_id}) on {self.device} ({self.torch_dtype})...", flush=True)
                from transformers import AutoModel, AutoTokenizer, AutoProcessor
                
                extra_kwargs = {}
                if self.is_local_path:
                    extra_kwargs["local_files_only"] = True

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

        self.last_used_time = time.time()
        self._start_keep_alive_timer_locked()

    def _start_keep_alive_timer_locked(self):
        if not self.timer_active:
            self.timer_active = True
            self.timer_thread = threading.Thread(target=self._keep_alive_loop, daemon=True)
            self.timer_thread.start()

    def _keep_alive_loop(self):
        while True:
            time.sleep(10)
            with self.lock:
                if self.active_requests > 0:
                    continue
                elapsed = time.time() - self.last_used_time
                if elapsed >= 60:  # 60s idle timeout
                    with GPU_LOCK:
                        if self.model is not None:
                            print("[UniPerceptAdapter] UniPercept Keep-alive timeout reached (60s). Unloading model...", flush=True)
                            self.model = None
                            self.processor = None
                            self.tokenizer = None
                            gc.collect()
                            if torch.cuda.is_available():
                                torch.cuda.empty_cache()
                            elif hasattr(torch, "mps") and hasattr(torch.mps, "empty_cache"):
                                try:
                                    torch.mps.empty_cache()
                                except Exception:
                                    pass
                            self.timer_active = False
                            print("[UniPerceptAdapter] UniPercept Model unloaded from memory.", flush=True)
                            break

    def unload_model(self):
        """Explicitly unload UniPercept model from memory and clear GPU cache immediately."""
        with self.lock:
            with GPU_LOCK:
                if self.model is not None:
                    print("[UniPerceptAdapter] Explicitly unloading UniPercept model to free memory for next pipeline...", flush=True)
                    self.model = None
                    self.processor = None
                    self.tokenizer = None
                    gc.collect()
                    if torch.cuda.is_available():
                        torch.cuda.empty_cache()
                    elif hasattr(torch, "mps") and hasattr(torch.mps, "empty_cache"):
                        try:
                            torch.mps.empty_cache()
                        except Exception:
                            pass
                    self.timer_active = False
                    print("[UniPerceptAdapter] UniPercept Model explicitly unloaded from memory.", flush=True)

    def generate_unipercept_critique(
        self,
        image_path: str,
        metadata: Optional[Dict[str, Any]] = None,
        custom_prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        with self.lock:
            self._load_model_locked()
            self.last_used_time = time.time()
            self.active_requests += 1

        try:
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

            from services.ai_parser import UNIPERCEPT_CRITIQUE_PROMPT
            base_prompt = custom_prompt if custom_prompt is not None else UNIPERCEPT_CRITIQUE_PROMPT
            prompt_text = f"{exif_desc}{base_prompt}"

            # Build preprocessed 448x448 pixel_values
            transform = build_transform(input_size=448)
            pixel_values = transform(pil_img).unsqueeze(0).to(self.torch_dtype).to(self.device)

            generation_config = dict(
                max_new_tokens=512,
                do_sample=False,
                num_beams=1,
                repetition_penalty=1.2
            )

            with GPU_LOCK:
                try:
                    if hasattr(self.model, "chat"):
                        critique_text = self.model.chat(
                            self.tokenizer,
                            pixel_values,
                            prompt_text,
                            generation_config=generation_config
                        )
                    else:
                        inputs = self.processor(images=pil_img, text=prompt_text, return_tensors="pt").to(self.device, dtype=self.torch_dtype)
                        with torch.no_grad():
                            outputs = self.model.generate(**inputs, max_new_tokens=512)
                        critique_text = self.processor.decode(outputs[0], skip_special_tokens=True)

                except Exception as eval_err:
                    print(f"[UniPerceptAdapter] Inference error during critique generation: {eval_err}", flush=True)
                    critique_text = f"UniPercept 분석 중 오류가 발생했습니다: {str(eval_err)}"

            # Extract all domain scores (IAA, IQA, ISTA) from UniPercept response
            quality_score = None
            scores_found = re.findall(r"(?:Score|Scores)\s*[:=]\s*(\d{1,3})", critique_text, re.IGNORECASE)
            if not scores_found:
                scores_found = re.findall(r"(\d{1,3})\s*(?:out of|/)\s*100", critique_text, re.IGNORECASE)

            valid_scores = []
            for s in scores_found:
                try:
                    val = int(s)
                    if 0 <= val <= 100:
                        valid_scores.append(val)
                except ValueError:
                    pass

            if valid_scores:
                quality_score = int(sum(valid_scores) / len(valid_scores))

            return {
                "critique": critique_text.strip(),
                "aesthetics_score": quality_score,
                "quality_score": quality_score
            }

        finally:
            with self.lock:
                self.last_used_time = time.time()
                self.active_requests -= 1

_unipercept_adapter_instance = None
_unipercept_lock = threading.Lock()

def get_unipercept_adapter() -> UniPerceptAdapter:
    global _unipercept_adapter_instance
    if _unipercept_adapter_instance is None:
        with _unipercept_lock:
            if _unipercept_adapter_instance is None:
                _unipercept_adapter_instance = UniPerceptAdapter()
    return _unipercept_adapter_instance
