import os
import gc
import json
import time
import threading
from PIL import Image

# For Gemma 4 (MLX)
# We import mlx and mlx_lm dynamically to avoid importing them if Gemma is not loaded yet
# or on systems where mlx/mlx_lm might fail if they are imported at startup.

from core.ports import ImageEmbeddingPort, TextEmbeddingPort, ImageCaptioningPort

# Global lock to prevent MLX and PyTorch MPS from crashing due to concurrent GPU access
GPU_LOCK = threading.Lock()

class SigLIP2Adapter(ImageEmbeddingPort, TextEmbeddingPort):
    def __init__(self):
        import torch
        self.device = "mps" if torch.backends.mps.is_available() else "cpu"
        self.model_id = "google/siglip2-base-patch16-224"
        self.model = None
        self.processor = None
        self.lock = threading.Lock()
        
        # SigLIP 2 is relatively lightweight and serves critical search path,
        # so we keep it loaded in memory from startup/initialization.
        self._load_model()

    def _load_model(self):
        with self.lock:
            if self.model is None:
                with GPU_LOCK:
                    import torch
                    from transformers import AutoModel, AutoProcessor
                    print(f"[SigLIP2Adapter] Loading model {self.model_id} on {self.device}...", flush=True)
                    try:
                        self.model = AutoModel.from_pretrained(
                            self.model_id,
                            attn_implementation="sdpa",
                            local_files_only=True
                        ).to(self.device)
                        self.processor = AutoProcessor.from_pretrained(self.model_id, local_files_only=True)
                    except Exception:
                        self.model = AutoModel.from_pretrained(
                            self.model_id,
                            attn_implementation="sdpa"
                        ).to(self.device)
                        self.processor = AutoProcessor.from_pretrained(self.model_id)
                    print("[SigLIP2Adapter] Model loaded successfully.", flush=True)

    def get_image_embedding(self, image_path: str) -> list[float]:
        import torch
        self._load_model()
        
        from utils.image import is_raw_image, decode_raw_to_pil
        if is_raw_image(image_path):
            image = decode_raw_to_pil(image_path)
        else:
            from PIL import ImageOps
            image_raw = Image.open(image_path)
            image = ImageOps.exif_transpose(image_raw).convert("RGB")
            
        inputs = self.processor(images=image, return_tensors="pt").to(self.device)
        with GPU_LOCK:
            with torch.no_grad():
                feat = self.model.get_image_features(**inputs)
                image_features = feat.pooler_output
                # Normalize embedding
                image_features = image_features / image_features.norm(p=2, dim=-1, keepdim=True)
                embedding = image_features[0].tolist()
        return embedding

    def get_text_embedding(self, text: str) -> list[float]:
        import torch
        self._load_model()
        inputs = self.processor(text=[text], padding="max_length", return_tensors="pt").to(self.device)
        with GPU_LOCK:
            with torch.no_grad():
                feat = self.model.get_text_features(**inputs)
            text_features = feat.pooler_output
            # Normalize embedding
            text_features = text_features / text_features.norm(p=2, dim=-1, keepdim=True)
            embedding = text_features[0].tolist()
        return embedding


class GemmaAdapter(ImageCaptioningPort):
    def __init__(self):
        self.model_id = "google/gemma-4-E4B-it"
        self.model = None
        self.processor = None
        self.last_used_time = 0.0
        self.active_requests = 0  # Track active inference calls to prevent mid-inference unload
        self.lock = threading.Lock()
        self.timer_thread = None
        self.timer_active = False

    def _load_model_locked(self):
        # Assumes self.lock is already acquired
        if self.model is None:
            with GPU_LOCK:
                print(f"[GemmaAdapter] Lazy loading model {self.model_id} via mlx_vlm...", flush=True)
                from mlx_vlm import load
                self.model, self.processor = load(self.model_id)
                print("[GemmaAdapter] Model loaded successfully.", flush=True)
            
        self.last_used_time = time.time()
        if not self.timer_active:
            self.timer_active = True
            self.timer_thread = threading.Thread(target=self._keep_alive_loop, daemon=True)
            self.timer_thread.start()

    def _keep_alive_loop(self):
        while True:
            time.sleep(5)
            should_unload = False
            
            with self.lock:
                if self.model is None:
                    self.timer_active = False
                    break
                elapsed = time.time() - self.last_used_time
                if self.active_requests == 0 and elapsed >= 60.0:
                    should_unload = True
                    
            if should_unload:
                # Acquire self.lock FIRST, then GPU_LOCK to match the acquisition order 
                # in generation methods and prevent Deadlocks.
                with self.lock:
                    # Double-check conditions inside lock
                    if self.model is not None and self.active_requests == 0 and (time.time() - self.last_used_time) >= 60.0:
                        with GPU_LOCK:
                            print(f"[GemmaAdapter] Inactivity timeout reached. Unloading model...", flush=True)
                            self.model = None
                            self.processor = None
                            gc.collect()
                            try:
                                import mlx.core as mx
                                mx.clear_cache()
                            except Exception as e:
                                print(f"[GemmaAdapter] Failed to clear metal cache: {e}", flush=True)
                            self.timer_active = False
                            print("[GemmaAdapter] Model unloaded.", flush=True)
                            break

    def generate_caption_and_tags(self, image_path: str, metadata: dict = None) -> dict:
        with self.lock:
            self._load_model_locked()
            self.last_used_time = time.time()
            self.active_requests += 1
            
        try:
            from services.ai_parser import GEMMA_SYSTEM_PROMPT, format_exif_text, parse_gemma_json_output
            exif_text = format_exif_text(metadata)
            messages = [
                {
                    "role": "system",
                    "content": GEMMA_SYSTEM_PROMPT
                },
                {
                    "role": "user",
                    "content": [
                        {"type": "image"},
                        {"type": "text", "text": f"{exif_text}이 사진을 정밀 분석하여 JSON으로 출력하십시오."}
                    ]
                }
            ]
            
            with GPU_LOCK:
                try:
                    tokenizer = self.processor.tokenizer if hasattr(self.processor, "tokenizer") else self.processor
                    prompt = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
                    
                    from mlx_vlm import generate
                    from utils.image import is_raw_image, decode_raw_to_pil
                    
                    if is_raw_image(image_path):
                        image_input = decode_raw_to_pil(image_path)
                    else:
                        image_input = image_path
                        
                    # In mlx_vlm, generate accepts `image` as a file path, URL, or PIL Image
                    result = generate(self.model, self.processor, prompt=prompt, image=image_input, verbose=False)
                    output = result.text if hasattr(result, "text") else str(result)
                except RuntimeError as e:
                    print(f"[GemmaAdapter] MLX OOM or RuntimeError during inference: {e}. Recovering...", flush=True)
                    try:
                        import mlx.core as mx
                        mx.clear_cache()
                    except Exception:
                        pass
                    gc.collect()
                    return {"caption": "", "tags": [], "aesthetic_tags": []}
                except Exception as e:
                    print(f"[GemmaAdapter] Unexpected inference error: {e}", flush=True)
                    return {"caption": "", "tags": [], "aesthetic_tags": []}
            
            # Return safely parsed dictionary
            return parse_gemma_json_output(output)
        finally:
            with self.lock:
                self.last_used_time = time.time()
                self.active_requests -= 1

    def _safe_parse_json(self, output: str) -> dict:
                elif "caption" in data:
                    return {"caption": str(data["caption"]), "tags": [], "aesthetic_tags": [str(t) for t in (data.get("aesthetic_tags") or [])]}
                elif "tags" in data:
    def _safe_parse_json(self, output: str) -> dict:
        from services.ai_parser import parse_gemma_json_output
        return parse_gemma_json_output(output)

    def generate_deep_critique(self, image_path: str, metadata: dict = None) -> str:
        with self.lock:
            self._load_model_locked()
            self.last_used_time = time.time()
            self.active_requests += 1
            
        try:
            from services.ai_parser import GEMMA_CRITIQUE_SYSTEM_PROMPT, format_exif_text
            exif_text = format_exif_text(metadata)
            messages = [
                {
                    "role": "system",
                    "content": GEMMA_CRITIQUE_SYSTEM_PROMPT
                },
                {
                    "role": "user",
                    "content": [
                        {"type": "image"},
                        {"type": "text", "text": f"{exif_text}이 사진을 전문가의 시각에서 비평해주십시오."}
                    ]
                }
            ]
            
            with GPU_LOCK:
                try:
                    tokenizer = self.processor.tokenizer if hasattr(self.processor, "tokenizer") else self.processor
                    prompt = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
                    
                    from mlx_vlm import generate
                    from utils.image import is_raw_image, decode_raw_to_pil
                    
                    if is_raw_image(image_path):
                        image_input = decode_raw_to_pil(image_path)
                    else:
                        image_input = image_path
                        
                    result = generate(self.model, self.processor, prompt=prompt, image=image_input, verbose=False)
                    output = result.text if hasattr(result, "text") else str(result)
                except RuntimeError as e:
                    print(f"[GemmaAdapter] MLX OOM or RuntimeError during deep critique: {e}. Recovering...", flush=True)
                    try:
                        import mlx.core as mx
                        mx.clear_cache()
                    except Exception:
                        pass
                    gc.collect()
                    return "시스템 메모리가 부족하여 비평을 완료하지 못했습니다. 다른 프로그램을 종료 후 다시 시도해주세요."
                except Exception as e:
                    print(f"[GemmaAdapter] Unexpected critique inference error: {e}", flush=True)
                    return "사진 비평 생성 중 알 수 없는 오류가 발생했습니다."
            
            return output.strip()
        finally:
            with self.lock:
                self.last_used_time = time.time()
                self.active_requests -= 1
