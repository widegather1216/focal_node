import os
import gc
import json
import time
import threading
from typing import Any
from PIL import Image


# For Gemma 4 (MLX)
# We import mlx and mlx_lm dynamically to avoid importing them if Gemma is not loaded yet
# or on systems where mlx/mlx_lm might fail if they are imported at startup.

from core.ports import ImageEmbeddingPort, TextEmbeddingPort, ImageCaptioningPort

# Global lock to prevent MLX and PyTorch MPS from crashing due to concurrent GPU access
GPU_LOCK = threading.RLock()

class SigLIP2Adapter(ImageEmbeddingPort, TextEmbeddingPort):
    def __init__(self):
        import torch
        self.device = "mps" if torch.backends.mps.is_available() else "cpu"
        self.model_id = "google/siglip2-base-patch16-224"
        self.model = None
        self.processor = None
        self.cached_taxonomy_embeddings = None
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
                self._precompute_taxonomy_embeddings()

    def _precompute_taxonomy_embeddings(self):
        try:
            from services.taxonomy import SIGLIP_VISUAL_TAXONOMY
            import torch
            inputs = self.processor(text=SIGLIP_VISUAL_TAXONOMY, padding="max_length", return_tensors="pt").to(self.device)
            with GPU_LOCK:
                with torch.no_grad():
                    feat = self.model.get_text_features(**inputs)
                text_features = feat.pooler_output
                text_features = text_features / text_features.norm(p=2, dim=-1, keepdim=True)
                self.cached_taxonomy_embeddings = text_features.cpu().numpy()
            print(f"[SigLIP2Adapter] Precomputed taxonomy embeddings for {len(SIGLIP_VISUAL_TAXONOMY)} visual concepts.", flush=True)
        except Exception as e:
            print(f"[SigLIP2Adapter] Failed to precompute taxonomy embeddings: {e}", flush=True)
            self.cached_taxonomy_embeddings = None

    def get_image_embedding(self, image_path: str) -> list[float]:
        import torch
        self._load_model()
        
        from utils.image import is_raw_image, decode_raw_to_pil
        if is_raw_image(image_path):
            image = decode_raw_to_pil(image_path)
        else:
            from PIL import ImageOps
            with Image.open(image_path) as image_raw:
                image_t = ImageOps.exif_transpose(image_raw)
                image = image_t.convert("RGB") if image_t.mode != "RGB" else image_t.copy()
            
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

    def get_zero_shot_hints(self, image_input: Any, top_k: int = 5) -> list[str]:
        """
        Calculates cosine similarity between image embedding and precomputed taxonomy embeddings.
        Returns Top-K matching visual keyword strings.
        """
        import numpy as np
        if self.cached_taxonomy_embeddings is None:
            return []
            
        if isinstance(image_input, str):
            image_emb = self.get_image_embedding(image_input)
        else:
            image_emb = image_input
            
        if not image_emb:
            return []
            
        img_vec = np.array(image_emb, dtype=np.float32)
        scores = np.dot(self.cached_taxonomy_embeddings, img_vec)
        top_indices = np.argsort(scores)[::-1][:top_k]
        
        from services.taxonomy import SIGLIP_VISUAL_TAXONOMY
        return [SIGLIP_VISUAL_TAXONOMY[i] for i in top_indices]


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
                import sys, os
                if getattr(sys, 'frozen', False) and "MLX_METAL_PATH" not in os.environ:
                    exe_dir = os.path.dirname(sys.executable)
                    candidates = [
                        os.path.join(exe_dir, "_internal", "mlx", "lib", "mlx.metallib"),
                        os.path.join(exe_dir, "_internal", "mlx.metallib"),
                        os.path.join(exe_dir, "mlx.metallib"),
                        os.path.join(exe_dir, "..", "Resources", "_internal", "mlx", "lib", "mlx.metallib"),
                        os.path.join(exe_dir, "..", "Resources", "binaries", "_internal", "mlx", "lib", "mlx.metallib"),
                    ]
                    for c in candidates:
                        if os.path.exists(c):
                            os.environ["MLX_METAL_PATH"] = c
                            break
                from mlx_vlm import load
                self.model, self.processor = load(self.model_id)
                print("[GemmaAdapter] Model loaded successfully.", flush=True)
            
        self.last_used_time = time.time()
        self._start_keep_alive_timer_locked()

    def _start_keep_alive_timer_locked(self):
        if not self.timer_active:
            self.timer_active = True
            self.timer_thread = threading.Thread(target=self._keep_alive_loop, daemon=True)
            self.timer_thread.start()


    def _keep_alive_loop(self):
        import gc
        while True:
            time.sleep(10)
            with self.lock:
                if self.active_requests > 0:
                    continue
                elapsed = time.time() - self.last_used_time
                if elapsed >= 60:
                    with GPU_LOCK:
                        if self.model is not None:
                            print("[GemmaAdapter] Keep-alive timeout reached (60s). Unloading model...", flush=True)
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

    def unload_model(self):
        """Explicitly unload Gemma model from memory and clear Metal cache immediately."""
        import gc
        with self.lock:
            with GPU_LOCK:
                if self.model is not None:
                    print("[GemmaAdapter] Explicitly unloading Gemma model to free memory...", flush=True)
                    self.model = None
                    self.processor = None
                    gc.collect()
                    try:
                        import mlx.core as mx
                        mx.clear_cache()
                    except Exception as e:
                        print(f"[GemmaAdapter] Failed to clear metal cache: {e}", flush=True)
                    self.timer_active = False
                    print("[GemmaAdapter] Gemma Model explicitly unloaded from memory.", flush=True)

    def generate_caption_and_tags(self, image_path: str, metadata: dict = None, siglip_hints: list[str] = None) -> dict:
        with self.lock:
            self._load_model_locked()
            self.last_used_time = time.time()
            self.active_requests += 1
            
        try:
            from services.ai_parser import (
                GEMMA_SYSTEM_PROMPT,
                format_exif_text,
                format_siglip_hints_text,
                parse_gemma_json_output
            )
            exif_text = format_exif_text(metadata)
            siglip_text = format_siglip_hints_text(siglip_hints)
            messages = [
                {
                    "role": "system",
                    "content": GEMMA_SYSTEM_PROMPT
                },
                {
                    "role": "user",
                    "content": [
                        {"type": "image"},
                        {"type": "text", "text": f"{exif_text}{siglip_text}이 사진을 정밀 분석하여 JSON으로 출력하십시오."}
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

    def generate_critique_summary(self, critiques_list: list[dict]) -> str:
        with self.lock:
            self._load_model_locked()
            self.last_used_time = time.time()
            self.active_requests += 1

        try:
            from services.ai_parser import GEMMA_CRITIQUE_SUMMARY_SYSTEM_PROMPT

            critique_blocks = []
            for idx, item in enumerate(critiques_list, 1):
                cam_info = f" (카메라: {item.get('camera_model', 'N/A')}, 렌즈: {item.get('lens_model', 'N/A')})" if item.get('camera_model') else ""
                block = f"[사진 {idx}: {item.get('file_name', '무제')}{cam_info}]\n비평: {item.get('critique', '')}"
                critique_blocks.append(block)

            combined_critiques = "\n\n".join(critique_blocks)
            user_prompt = f"다음은 사용자가 수집한 총 {len(critiques_list)}개의 사진 비평 데이터입니다:\n\n{combined_critiques}\n\n위 비평 데이터를 바탕으로 작성자의 사진 촬영 스타일, 주요 강점, 개선점, 촬영 습관 및 종합 조언을 리포트 형태로 작성해주십시오."

            messages = [
                {
                    "role": "system",
                    "content": GEMMA_CRITIQUE_SUMMARY_SYSTEM_PROMPT
                },
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": user_prompt}
                    ]
                }
            ]

            with GPU_LOCK:
                try:
                    tokenizer = self.processor.tokenizer if hasattr(self.processor, "tokenizer") else self.processor
                    prompt = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)

                    from mlx_vlm import generate
                    result = generate(self.model, self.processor, prompt=prompt, max_tokens=1024, verbose=False)
                    output = result.text if hasattr(result, "text") else str(result)
                except RuntimeError as e:
                    print(f"[GemmaAdapter] MLX OOM during critique summary: {e}. Recovering...", flush=True)
                    try:
                        import mlx.core as mx
                        mx.clear_cache()
                    except Exception:
                        pass
                    gc.collect()
                    return "메모리가 부족하여 종합 요약을 완료하지 못했습니다. 불필요한 앱을 종료 후 다시 시도해주세요."
                except Exception as e:
                    print(f"[GemmaAdapter] Unexpected critique summary error: {e}", flush=True)
                    return "비평 종합 요약 생성 중 오류가 발생했습니다."

            return output.strip()
        finally:
            with self.lock:
                self.last_used_time = time.time()
                self.active_requests -= 1

    def translate_and_format_critique(self, raw_en_critique: str, scores_dict: dict = None, quality_score: int = None) -> str:
        with self.lock:
            self._load_model_locked()
            self.last_used_time = time.time()
            self.active_requests += 1

        try:
            from services.ai_parser import (
                GEMMA_TRANSLATE_CRITIQUE_SYSTEM_PROMPT,
                format_unipercept_translate_user_prompt
            )
            user_prompt = format_unipercept_translate_user_prompt(raw_en_critique, scores_dict, quality_score)
            messages = [
                {
                    "role": "system",
                    "content": GEMMA_TRANSLATE_CRITIQUE_SYSTEM_PROMPT
                },
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": user_prompt}
                    ]
                }
            ]

            with GPU_LOCK:
                try:
                    tokenizer = self.processor.tokenizer if hasattr(self.processor, "tokenizer") else self.processor
                    prompt = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)

                    from mlx_vlm import generate
                    result = generate(self.model, self.processor, prompt=prompt, max_tokens=1024, verbose=False)
                    output = result.text if hasattr(result, "text") else str(result)
                    return output.strip()
                except Exception as e:
                    print(f"[GemmaAdapter] Translation failed ({e}). Returning raw UniPercept critique.", flush=True)
                    return raw_en_critique
        finally:
            with self.lock:
                self.last_used_time = time.time()
                self.active_requests -= 1


