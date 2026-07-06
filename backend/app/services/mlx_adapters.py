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
                    # SDPA (Scaled Dot-Product Attention) activation
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
            # Gemma 4 system prompt and template instructions
            exif_text = ""
            if metadata:
                exif_text = f"\n[EXIF 데이터]\n- 카메라: {metadata.get('camera_model', 'N/A')}\n- 렌즈: {metadata.get('lens_model', 'N/A')}\n- 조리개: F{metadata.get('f_number', 'N/A')}\n- 셔터스피드: {metadata.get('shutter_speed', 'N/A')}s\n- ISO: {metadata.get('iso', 'N/A')}\n\n"
            messages = [
                {
                    "role": "system",
                    "content": (
                        "당신은 사진 검색 시스템을 위한 수석 AI 이미지 분석가입니다. 사진의 시각적 요소와 EXIF 데이터를 종합하여 정밀한 메타데이터를 추출해야 합니다.\n\n"
                        "[분석 지침]\n"
                        "1. 단계별 추론 (Reasoning): 사진의 조명, 구도, 카메라 세팅(EXIF), 주요 피사체의 상태를 먼저 분석하고, 이 사진이 어떤 맥락에서 촬영되었는지 논리적으로 추론하여 'reasoning' 필드에 1~2문장으로 작성하십시오.\n"
                        "2. 고품질 캡션 (Caption): 단순한 객체 나열을 넘어, 사진의 분위기, 시간대, 날씨, 빛의 방향, 피사체의 행동을 아우르는 매우 구체적이고 감각적인 묘사를 1~2줄로 작성하십시오.\n"
                        "3. 일반 태그 (Tags): 검색 빈도가 높은 명사 및 형용사를 추출하되, 포괄적인 단어(예: 풍경, 사람)보다 구체적이고 특징적인 단어(예: 해안가, 서퍼, 흩날리는 눈, 질감)를 우선하여 7~15개 선정하십시오.\n"
                        "4. 전문 태그 (Aesthetic Tags): 아래의 분류 체계(Taxonomy)를 참고하여 사진에 명확히 해당하는 전문 용어 3~8개를 선정하십시오.\n"
                        "   - 구도/앵글: 로우 앵글, 하이 앵글, 3분할법, 선도선(Leading lines), 대칭, 프레임 속 프레임, 클로즈업\n"
                        "   - 조명/빛: 역광(Backlit), 실루엣, 골든 아워, 블루 아워, 렌즈 플레어, 하이키(High-key), 로우키(Low-key), 자연광, 인공 조명\n"
                        "   - 기법/효과: 아웃포커싱(얕은 심도), 팬 포커스(깊은 심도), 패닝샷, 장노출, 모션 블러, 보케(Bokeh), 매크로\n"
                        "   - 톤/무드: 흑백(Monochrome), 비비드, 빈티지, 파스텔, 시네마틱, 하이 콘트라스트\n"
                        "5. 예외 규칙 (Negative Prompting):\n"
                        "   - EXIF에서 조리개(F-number)가 F5.6 이상이라면 '아웃포커싱'이나 '보케'를 남발하지 마십시오.\n"
                        "   - 셔터스피드가 1/1000s 보다 빠르다면 '장노출'이나 '모션 블러'를 절대 사용하지 마십시오.\n"
                        "   - 사진에 명확히 보이지 않는 정보(예: 특정 지명, 개인의 이름)는 지어내지 마십시오.\n\n"
                        "[출력 형식]\n"
                        "오직 아래의 JSON 포맷만 출력하십시오. 마크다운 기호(예: ```json 등)나 부가 설명은 절대 포함하지 마십시오.\n\n"
                        "{\"reasoning\": \"추론 내용\", \"caption\": \"고품질 캡션 묘사\", \"tags\": [\"키워드1\", \"키워드2\"], \"aesthetic_tags\": [\"전문용어1\", \"전문용어2\"]}"
                    )
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
                    # In mlx_vlm, generate accepts `image=image_path` (file path or URL)
                    result = generate(self.model, self.processor, prompt=prompt, image=image_path, verbose=False)
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
            return self._safe_parse_json(output)
        finally:
            with self.lock:
                self.last_used_time = time.time()
                self.active_requests -= 1

    def _safe_parse_json(self, output: str) -> dict:
        default_result = {"caption": "", "tags": [], "aesthetic_tags": []}
        if not output:
            return default_result
            
        clean_output = output.strip()
        
        # 1. Clean markdown code blocks (e.g. ```json ... ```)
        if "```" in clean_output:
            # Try to extract content between ```json and ``` or just ``` and ```
            # We locate the first ``` and the last ```
            parts = clean_output.split("```")
            if len(parts) >= 3:
                # The content is typically in the second part
                content = parts[1].strip()
                if content.lower().startswith("json"):
                    content = content[4:].strip()
                clean_output = content
                
        # 2. Extract content starting with '{' and ending with '}'
        start_idx = clean_output.find("{")
        end_idx = clean_output.rfind("}")
        
        if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
            json_candidate = clean_output[start_idx:end_idx+1]
            try:
                data = json.loads(json_candidate)
                # Check structure
                if "caption" in data and "tags" in data:
                    return {
                        "caption": str(data["caption"]),
                        "tags": [str(t) for t in (data.get("tags") or [])],
                        "aesthetic_tags": [str(t) for t in (data.get("aesthetic_tags") or [])]
                    }
                elif "caption" in data:
                    return {"caption": str(data["caption"]), "tags": [], "aesthetic_tags": [str(t) for t in (data.get("aesthetic_tags") or [])]}
                elif "tags" in data:
                    return {"caption": "", "tags": [str(t) for t in (data.get("tags") or [])], "aesthetic_tags": [str(t) for t in (data.get("aesthetic_tags") or [])]}
            except Exception as parse_err:
                print(f"[GemmaAdapter] JSON parsing failed: {parse_err}. LLM Output: {output}", flush=True)
                
        # Fallback parsing strategy in case the JSON is completely malformed
        # We salvage the raw text into the caption so it is not entirely lost for text search
        if clean_output and len(clean_output) > 5:
            return {"caption": clean_output, "tags": [], "aesthetic_tags": []}
            
        return default_result

    def generate_deep_critique(self, image_path: str, metadata: dict = None) -> str:
        with self.lock:
            self._load_model_locked()
            self.last_used_time = time.time()
            self.active_requests += 1
            
        try:
            exif_text = ""
            if metadata:
                exif_text = f"\n[EXIF 데이터]\n- 카메라: {metadata.get('camera_model', 'N/A')}\n- 렌즈: {metadata.get('lens_model', 'N/A')}\n- 조리개: F{metadata.get('f_number', 'N/A')}\n- 셔터스피드: {metadata.get('shutter_speed', 'N/A')}s\n- ISO: {metadata.get('iso', 'N/A')}\n\n"
            messages = [
                {
                    "role": "system",
                    "content": (
                        "당신은 탁월한 안목을 지닌 사진 전문가입니다. "
                        "이 사진의 시각적 요소와 제공된 EXIF 데이터를 바탕으로 구도, 조명, 색감, 피사체의 배치 등을 정밀히 분석하십시오. "
                        "사진의 어떤 점이 훌륭한지 명확히 짚어주고, 더 나은 작품이 되기 위한 구체적인 조언을 3문단 내외로 제공하십시오."
                    )
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
                    result = generate(self.model, self.processor, prompt=prompt, image=image_path, verbose=False)
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
