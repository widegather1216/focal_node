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
from services.base_model import BaseKeepAliveModel, GPU_LOCK

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

    def get_zero_shot_hints(self, image_input: Any, top_k: int = 15, min_score: float = 0.22) -> list[str]:
        """
        Calculates cosine similarity between image embedding and precomputed taxonomy embeddings.
        Returns matching visual keyword strings exceeding min_score threshold up to top_k.
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
            
        img_vec = np.array(image_emb)
        img_vec = img_vec / np.linalg.norm(img_vec)
        
        scores = np.dot(self.cached_taxonomy_embeddings, img_vec)
        sorted_indices = np.argsort(scores)[::-1]
        
        from services.taxonomy import SIGLIP_VISUAL_TAXONOMY
        filtered_hints = [
            SIGLIP_VISUAL_TAXONOMY[i] for i in sorted_indices
            if scores[i] >= min_score
        ][:top_k]
        
        # Fallback to top 3 if no terms pass min_score for very sparse/unique images
        if not filtered_hints and len(sorted_indices) > 0:
            filtered_hints = [SIGLIP_VISUAL_TAXONOMY[i] for i in sorted_indices[:3]]
            
        return filtered_hints


class GemmaAdapter(BaseKeepAliveModel, ImageCaptioningPort):
    def __init__(self):
        super().__init__("GemmaAdapter", keep_alive_timeout=60.0)
        self.model_id = "mlx-community/gemma-4-12B-it-8bit"
        self.model = None
        self.processor = None

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
                # mlx_vlm.load only searches top-level directory for *.safetensors.
                # Auto-link any subfolder safetensors (e.g. optiq/optiq_vision.safetensors) to top-level.
                try:
                    from huggingface_hub import snapshot_download
                    import glob, shutil
                    if os.path.exists(self.model_id):
                        model_dir = self.model_id
                    else:
                        model_dir = snapshot_download(repo_id=self.model_id, local_files_only=True)
                    
                    sub_safetensors = glob.glob(os.path.join(model_dir, "**", "*.safetensors"), recursive=True)
                    for s_path in sub_safetensors:
                        rel_dir = os.path.relpath(os.path.dirname(s_path), model_dir)
                        if rel_dir != ".":
                            dst_name = f"{os.path.basename(os.path.dirname(s_path))}_{os.path.basename(s_path)}"
                            top_dst = os.path.join(model_dir, dst_name)
                            direct_dst = os.path.join(model_dir, os.path.basename(s_path))
                            for dst in [top_dst, direct_dst]:
                                if not os.path.exists(dst):
                                    try:
                                        os.symlink(s_path, dst)
                                    except Exception:
                                        shutil.copy2(s_path, dst)
                except Exception as link_err:
                    print(f"[GemmaAdapter] Subfolder safetensors link warning: {link_err}", flush=True)

                from mlx_vlm import load
                self.model, self.processor = load(self.model_id)
                print("[GemmaAdapter] Model loaded successfully.", flush=True)
            
        self.touch_used()



    def generate_caption_and_tags(self, image_path: str, metadata: dict = None, siglip_hints: list[str] = None) -> dict:
        with self.lock:
            self._load_model_locked()
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

    def generate_deep_critique(self, image_path: str, metadata: dict = None, photo_id: str = None) -> str:
        if photo_id:
            from services.critique_status import critique_status_manager
            critique_status_manager.update(photo_id, 2, 4, "비평 작성 중", 50)

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

    def translate_and_format_critique(self, raw_en_critique: str, scores_dict: dict = None, quality_score: int = None, photo_id: str = None) -> str:
        with self.lock:
            self._load_model_locked()
            self.last_used_time = time.time()
            self.active_requests += 1

        try:
            from services.ai_parser import (
                GEMMA_TRANSLATE_STEP1_SYSTEM_PROMPT,
                GEMMA_TRANSLATE_STEP2_SYSTEM_PROMPT,
                format_unipercept_translate_step1_user_prompt,
                format_unipercept_translate_step2_user_prompt,
            )
            from services.critique_status import critique_status_manager

            import mlx.core as mx

            # --- Pass 1: 1차 무왜곡 100% 직역 추론 (Direct Translation) ---
            print("[GemmaAdapter] [Pass 1/2] Generating direct Korean translation...", flush=True)
            if photo_id:
                critique_status_manager.update(photo_id, 3, 4, "비평 번역 중", 75)
            step1_prompt_text = format_unipercept_translate_step1_user_prompt(raw_en_critique, scores_dict, quality_score)
            messages_step1 = [
                {
                    "role": "system",
                    "content": GEMMA_TRANSLATE_STEP1_SYSTEM_PROMPT
                },
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": step1_prompt_text}
                    ]
                }
            ]

            with GPU_LOCK:
                mx.clear_cache()
                gc.collect()
                tokenizer = self.processor.tokenizer if hasattr(self.processor, "tokenizer") else self.processor
                prompt1 = tokenizer.apply_chat_template(messages_step1, tokenize=False, add_generation_prompt=True)

                from mlx_vlm import generate
                result1 = generate(self.model, self.processor, prompt=prompt1, max_tokens=768, verbose=False)
                step1_output = (result1.text if hasattr(result1, "text") else str(result1)).strip()
                print("[GemmaAdapter] [Pass 1/2] Direct Korean translation finished.", flush=True)

            # --- Pass 2: 2차 문맥 & 미학 스타일 다듬기 추론 (Style & Context Refinement) ---
            print("[GemmaAdapter] [Pass 2/2] Refining style and photographic context...", flush=True)
            if photo_id:
                critique_status_manager.update(photo_id, 4, 4, "비평 다듬는 중", 90)
            step2_prompt_text = format_unipercept_translate_step2_user_prompt(step1_output, scores_dict, quality_score)
            messages_step2 = [
                {
                    "role": "system",
                    "content": GEMMA_TRANSLATE_STEP2_SYSTEM_PROMPT
                },
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": step2_prompt_text}
                    ]
                }
            ]

            try:
                with GPU_LOCK:
                    mx.clear_cache()
                    gc.collect()
                    prompt2 = tokenizer.apply_chat_template(messages_step2, tokenize=False, add_generation_prompt=True)
                    result2 = generate(self.model, self.processor, prompt=prompt2, max_tokens=768, verbose=False)
                    step2_output = (result2.text if hasattr(result2, "text") else str(result2)).strip()
                    print("[GemmaAdapter] [Pass 2/2] Style refinement finished.", flush=True)
                    return step2_output
            except Exception as pass2_err:
                print(f"[GemmaAdapter] Pass 2 context refinement warning ({pass2_err}). Returning Pass 1 direct translation.", flush=True)
                return step1_output

        except Exception as e:
            print(f"[GemmaAdapter] 2-Pass Translation failed ({e}). Returning raw UniPercept critique.", flush=True)
            return raw_en_critique
        finally:
            try:
                import mlx.core as mx
                mx.clear_cache()
            except Exception:
                pass
            gc.collect()
            with self.lock:
                self.last_used_time = time.time()
                self.active_requests -= 1


