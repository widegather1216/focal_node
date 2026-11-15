"""MLX-based Gemma 4 VLM adapter and SigLIP2Adapter compatibility re-export."""

import gc
import os
import sys
import time
from typing import Any, Optional

from core.ports import ImageCaptioningPort
from services.base_model import BaseKeepAliveModel, GPU_LOCK, clear_mlx_cache
from services.siglip_adapter import SigLIP2Adapter

__all__ = ["SigLIP2Adapter", "GemmaAdapter"]


def _configure_frozen_metal_path() -> None:
    """Resolves bundled mlx.metallib path in frozen PyInstaller builds."""
    if not getattr(sys, "frozen", False) or "MLX_METAL_PATH" in os.environ:
        return
    exe_dir = os.path.dirname(sys.executable)
    candidates = (
        os.path.join(exe_dir, "_internal", "mlx", "lib", "mlx.metallib"),
        os.path.join(exe_dir, "_internal", "mlx.metallib"),
        os.path.join(exe_dir, "mlx.metallib"),
        os.path.join(exe_dir, "..", "Resources", "_internal", "mlx", "lib", "mlx.metallib"),
        os.path.join(exe_dir, "..", "Resources", "binaries", "_internal", "mlx", "lib", "mlx.metallib"),
    )
    for candidate in candidates:
        if os.path.exists(candidate):
            os.environ["MLX_METAL_PATH"] = candidate
            return


def _link_single_safetensor(src_path: str, dst_path: str) -> None:
    import shutil

    if os.path.exists(dst_path):
        return
    try:
        os.symlink(src_path, dst_path)
    except Exception as symlink_err:
        print(f"[GemmaAdapter] Symlink failed ({symlink_err}), copying file: {dst_path}", flush=True)
        shutil.copy2(src_path, dst_path)


def _link_subfolder_safetensors(model_id: str) -> None:
    """Links nested *.safetensors files to top-level directory so mlx_vlm.load discovers them."""
    import glob

    try:
        from huggingface_hub import snapshot_download

        model_dir = model_id if os.path.exists(model_id) else snapshot_download(repo_id=model_id, local_files_only=True)
        for src_path in glob.glob(os.path.join(model_dir, "**", "*.safetensors"), recursive=True):
            rel_dir = os.path.relpath(os.path.dirname(src_path), model_dir)
            if rel_dir == ".":
                continue
            prefixed_name = f"{os.path.basename(os.path.dirname(src_path))}_{os.path.basename(src_path)}"
            _link_single_safetensor(src_path, os.path.join(model_dir, prefixed_name))
            _link_single_safetensor(src_path, os.path.join(model_dir, os.path.basename(src_path)))
    except Exception as link_err:
        print(f"[GemmaAdapter] Subfolder safetensors link warning: {link_err}", flush=True)


def _resolve_image_input(image_path: Any) -> Any:
    """Decodes RAW photos or passes standard images/PIL objects outside GPU_LOCK (Rule 2.4)."""
    from PIL import Image
    from utils.image import decode_raw_to_pil, is_raw_image

    if isinstance(image_path, Image.Image):
        return image_path
    if is_raw_image(image_path):
        return decode_raw_to_pil(image_path, min_dimension=1024)
    return image_path


class GemmaAdapter(BaseKeepAliveModel, ImageCaptioningPort):
    """Lazy-loaded Gemma 4 12B MLX VLM adapter with 60s keep-alive cache."""

    def __init__(self):
        super().__init__("GemmaAdapter", keep_alive_timeout=60.0)
        self.model_id = "mlx-community/gemma-4-12B-it-8bit"
        self.model = None
        self.processor = None

    def _load_model_locked(self) -> None:
        """Assumes caller holds GPU_LOCK -> self.lock in strict hierarchy order."""
        if self.model is not None:
            self.last_used_time = time.time()
            self._start_keep_alive_timer_locked()
            return

        print(f"[GemmaAdapter] Lazy loading model {self.model_id} via mlx_vlm...", flush=True)
        _configure_frozen_metal_path()
        _link_subfolder_safetensors(self.model_id)

        from mlx_vlm import load

        self.model, self.processor = load(self.model_id)
        print("[GemmaAdapter] Model loaded successfully.", flush=True)
        self.last_used_time = time.time()
        self._start_keep_alive_timer_locked()

    def _acquire_model_request(self) -> None:
        with GPU_LOCK:
            with self.lock:
                self._load_model_locked()
                self.last_used_time = time.time()
                self.active_requests += 1

    def _release_model_request(self) -> None:
        with self.lock:
            self.last_used_time = time.time()
            self.active_requests -= 1

    def _run_mlx_vlm_generation(
        self,
        messages: list,
        image_input: Any = None,
        max_tokens: Optional[int] = None,
        clear_cache_before: bool = False,
        photo_id: Optional[str] = None,
    ) -> str:
        from mlx_vlm import generate
        from services.critique_status import critique_status_manager

        with GPU_LOCK:
            if photo_id:
                critique_status_manager.check_cancelled(photo_id)
            if clear_cache_before:
                clear_mlx_cache()
                gc.collect()

            tokenizer = self.processor.tokenizer if hasattr(self.processor, "tokenizer") else self.processor
            prompt = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
            gen_kwargs: dict[str, Any] = {"prompt": prompt, "verbose": False}
            if image_input is not None:
                gen_kwargs["image"] = image_input
            if max_tokens is not None:
                gen_kwargs["max_tokens"] = max_tokens

            generation_result = generate(self.model, self.processor, **gen_kwargs)
            return generation_result.text if hasattr(generation_result, "text") else str(generation_result)

    def generate_caption_and_tags(self, image_path: str, metadata: dict = None, siglip_hints: list[str] = None) -> dict:
        from services.ai_parser import GEMMA_SYSTEM_PROMPT, format_exif_text, format_siglip_hints_text, parse_gemma_json_output

        self._acquire_model_request()
        try:
            prompt_text = f"{format_exif_text(metadata)}{format_siglip_hints_text(siglip_hints)}이 사진을 정밀 분석하여 JSON으로 출력하십시오."
            messages = [
                {"role": "system", "content": GEMMA_SYSTEM_PROMPT},
                {"role": "user", "content": [{"type": "image"}, {"type": "text", "text": prompt_text}]},
            ]
            raw_output = self._run_mlx_vlm_generation(messages, image_input=_resolve_image_input(image_path))
            return parse_gemma_json_output(raw_output)
        except RuntimeError as err:
            print(f"[GemmaAdapter] MLX OOM or RuntimeError during inference: {err}. Recovering...", flush=True)
            clear_mlx_cache()
            gc.collect()
            return {"caption": "", "tags": [], "aesthetic_tags": []}
        except Exception as err:
            print(f"[GemmaAdapter] Unexpected inference error: {err}", flush=True)
            return {"caption": "", "tags": [], "aesthetic_tags": []}
        finally:
            self._release_model_request()

    def generate_deep_critique(self, image_path: str, metadata: dict = None, photo_id: str = None) -> str:
        from services.ai_parser import GEMMA_CRITIQUE_SYSTEM_PROMPT, format_exif_text
        from services.critique_status import CritiqueCancelledException, critique_status_manager

        if photo_id:
            critique_status_manager.check_cancelled(photo_id)
            critique_status_manager.update(photo_id, 2, 4, "비평 작성 중", 50)
        self._acquire_model_request()
        try:
            if photo_id:
                critique_status_manager.check_cancelled(photo_id)
            messages = [
                {"role": "system", "content": GEMMA_CRITIQUE_SYSTEM_PROMPT},
                {"role": "user", "content": [{"type": "image"}, {"type": "text", "text": f"{format_exif_text(metadata)}이 사진을 전문가의 시각에서 비평해주십시오."}]},
            ]
            return self._run_mlx_vlm_generation(messages, image_input=_resolve_image_input(image_path), photo_id=photo_id).strip()
        except CritiqueCancelledException:
            raise
        except RuntimeError as err:
            print(f"[GemmaAdapter] MLX OOM or RuntimeError during deep critique: {err}. Recovering...", flush=True)
            clear_mlx_cache()
            gc.collect()
            raise
        finally:
            self._release_model_request()

    @staticmethod
    def _build_perceptual_critique_messages(
        metadata: Optional[dict],
        scores_dict: Optional[dict],
        perceptual_anchor: Optional[str],
    ) -> list:
        from services.ai_parser import GEMMA_PERCEPTUAL_CRITIQUE_SYSTEM_PROMPT, format_perceptual_critique_user_prompt

        user_prompt = format_perceptual_critique_user_prompt(
            perceptual_anchor=perceptual_anchor or "",
            scores_dict=scores_dict,
            metadata=metadata,
        )
        return [
            {"role": "system", "content": GEMMA_PERCEPTUAL_CRITIQUE_SYSTEM_PROMPT},
            {"role": "user", "content": [{"type": "image"}, {"type": "text", "text": user_prompt}]},
        ]

    def _execute_perceptual_critique_generation(
        self, messages: list, image_path: Any, scores_dict: Optional[dict], photo_id: Optional[str],
    ) -> str:
        from services.ai_parser import format_score_info_text
        from services.critique_status import CritiqueCancelledException

        image_input = _resolve_image_input(image_path)
        try:
            output = self._run_mlx_vlm_generation(
                messages, image_input=image_input, max_tokens=3072, clear_cache_before=True, photo_id=photo_id,
            ).strip()
            if scores_dict and "앙상블 비평 스코어보드" not in output:
                return f"{format_score_info_text(scores_dict)}{output}"
            return output
        except CritiqueCancelledException:
            raise
        except RuntimeError as err:
            print(f"[GemmaAdapter] MLX OOM during perceptual critique: {err}. Recovering...", flush=True)
            clear_mlx_cache()
            gc.collect()
            raise
        except Exception as err:
            print(f"[GemmaAdapter] Unexpected perceptual critique inference error: {err}", flush=True)
            raise

    def generate_perceptual_critique(
        self,
        image_path: Any,
        perceptual_anchor: str,
        scores_dict: Optional[dict] = None,
        metadata: Optional[dict] = None,
        photo_id: Optional[str] = None,
    ) -> str:
        """Generates Korean deep critique grounded in UniPercept perceptual anchor + EXIF."""
        from services.critique_status import CritiqueCancelledException, critique_status_manager

        if photo_id:
            critique_status_manager.check_cancelled(photo_id)
            critique_status_manager.update(photo_id, 3, 4, "[Gemma] 지각 앵커 기반 심층 비평 작성 중...", 75)

        self._acquire_model_request()
        try:
            if photo_id:
                critique_status_manager.check_cancelled(photo_id)

            started_at = time.time()
            messages = self._build_perceptual_critique_messages(metadata, scores_dict, perceptual_anchor)
            output = self._execute_perceptual_critique_generation(messages, image_path, scores_dict, photo_id)
            elapsed = time.time() - started_at
            print(f"[GemmaAdapter] ✅ Direct perceptual critique generated ({len(output)} chars, {elapsed:.2f}s)", flush=True)
            return output
        except CritiqueCancelledException:
            raise
        finally:
            self._release_model_request()

    @staticmethod
    def _build_critique_summary_messages(critiques_list: list[dict]) -> list:
        from services.ai_parser import GEMMA_CRITIQUE_SUMMARY_SYSTEM_PROMPT

        critique_blocks = []
        for i, item in enumerate(critiques_list, 1):
            cam_label = ""
            if item.get("camera_model"):
                cam_label = f" (카메라: {item.get('camera_model', 'N/A')}, 렌즈: {item.get('lens_model', 'N/A')})"
            critique_blocks.append(f"[사진 {i}: {item.get('file_name', '무제')}{cam_label}]\n비평: {item.get('critique', '')}")

        combined = "\n\n".join(critique_blocks)
        user_prompt = (
            f"다음은 사용자가 수집한 총 {len(critiques_list)}개의 사진 비평 데이터입니다:\n\n"
            f"{combined}\n\n"
            "위 비평 데이터를 바탕으로 작성자의 사진 촬영 스타일, 주요 강점, 개선점, 촬영 습관 및 종합 조언을 리포트 형태로 작성해주십시오."
        )
        return [
            {"role": "system", "content": GEMMA_CRITIQUE_SUMMARY_SYSTEM_PROMPT},
            {"role": "user", "content": [{"type": "text", "text": user_prompt}]},
        ]

    def generate_critique_summary(self, critiques_list: list[dict]) -> str:
        self._acquire_model_request()
        try:
            messages = self._build_critique_summary_messages(critiques_list)
            output = self._run_mlx_vlm_generation(messages, max_tokens=1024)
            return output.strip()
        except RuntimeError as err:
            print(f"[GemmaAdapter] MLX OOM during critique summary: {err}. Recovering...", flush=True)
            clear_mlx_cache()
            gc.collect()
            raise
        except Exception as err:
            print(f"[GemmaAdapter] Unexpected critique summary error: {err}", flush=True)
            raise
        finally:
            self._release_model_request()

    @staticmethod
    def _build_document_structuring_messages(critique_draft: str, metadata: Optional[dict]) -> list:
        from services.ai_parser import GEMMA_DOCUMENT_FORMATTING_SYSTEM_PROMPT, format_critique_document_structuring_user_prompt

        user_prompt = format_critique_document_structuring_user_prompt(critique_draft, metadata)
        return [
            {"role": "system", "content": GEMMA_DOCUMENT_FORMATTING_SYSTEM_PROMPT},
            {"role": "user", "content": [{"type": "text", "text": user_prompt}]},
        ]

    @staticmethod
    def _preserve_scoreboard_header(critique_draft: str, output: str) -> str:
        """Preserves ensemble scoreboard header if present in draft but omitted in LLM output."""
        if "앙상블 비평 스코어보드" in critique_draft and "앙상블 비평 스코어보드" not in output:
            header_candidate = critique_draft.split("\n\n## 1.")[0].split("\n\n1. ")[0]
            if "앙상블 비평 스코어보드" in header_candidate:
                return f"{header_candidate.strip()}\n\n{output}"
        return output

    def _execute_document_structuring_generation(
        self,
        messages: list,
        critique_draft: str,
        started_at: float,
        photo_id: Optional[str],
    ) -> str:
        from services.critique_status import CritiqueCancelledException

        try:
            output = self._run_mlx_vlm_generation(
                messages,
                max_tokens=2048,
                clear_cache_before=True,
                photo_id=photo_id,
            ).strip()
            elapsed = time.time() - started_at
            print(f"[GemmaAdapter] ✅ [Gemma Document Polish] 문서 양식 정돈 완료 ({len(output)}자, 소요시간: {elapsed:.2f}초)", flush=True)
            output = self._preserve_scoreboard_header(critique_draft, output)
            return output if output and len(output) > 30 else critique_draft
        except CritiqueCancelledException:
            raise
        except RuntimeError as err:
            print(f"[GemmaAdapter] MLX OOM during document structuring: {err}. Falling back to draft...", flush=True)
            clear_mlx_cache()
            gc.collect()
            return critique_draft
        except Exception as err:
            print(f"[GemmaAdapter] Unexpected document structuring error: {err}. Falling back to draft...", flush=True)
            return critique_draft

    def format_and_structure_critique(self, critique_draft: str, metadata: dict = None, photo_id: str = None) -> str:
        """Restructures and polishes draft critique into official magazine report format."""
        if not critique_draft or len(critique_draft.strip()) < 20:
            return critique_draft

        from services.critique_status import CritiqueCancelledException, critique_status_manager

        self._acquire_model_request()
        try:
            if photo_id:
                critique_status_manager.check_cancelled(photo_id)
                critique_status_manager.update(photo_id, 3, 4, "[Gemma] 리포트 문서 양식 다듬는 중...", 75)

            print("[GemmaAdapter] ⏱️ [Gemma Document Polish] 비평 문서 구조화 및 양식 정돈 시작...", flush=True)
            started_at = time.time()
            messages = self._build_document_structuring_messages(critique_draft, metadata)
            return self._execute_document_structuring_generation(messages, critique_draft, started_at, photo_id)
        except CritiqueCancelledException:
            raise
        finally:
            self._release_model_request()
