"""UniPercept 8B PyTorch MPS adapter for 3-way VR scoring and single-pass VQA anchor."""

from __future__ import annotations

import gc
import os
import threading
import time
from typing import Any, Dict, Optional, Tuple


class _LazyTorchProxy:
    """Lazily loads heavy torch module on first access to satisfy Rule 2.5."""

    def __getattr__(self, name: str) -> Any:
        import torch

        globals()["torch"] = torch
        return getattr(torch, name)


torch = _LazyTorchProxy()

from services.base_model import BaseKeepAliveModel, GPU_LOCK, clear_mps_cache
from services.scoring import (
    calculate_aesthetic_bonus,
    calculate_overall_vr_score,
    resolve_perceptual_weights,
)
from services.unipercept_runtime import (
    build_vqa_query,
    build_vr_score_query,
    clean_vqa_response,
    format_score_guidance_desc,
    format_unipercept_exif_desc,
    load_unipercept_components,
    prepare_pixel_values_tensor,
    resolve_conversation_template,
    resolve_unipercept_model_source,
)
from services.unipercept_utils import AESTHETICS_TOKEN_LIST, score2aestoken


def _coerce_optional_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


class UniPerceptAdapter(BaseKeepAliveModel):
    """Perceptual scoring and VQA visual diagnosis adapter with strict immediate unload."""

    def __init__(self):
        super().__init__("UniPerceptAdapter", keep_alive_timeout=0.0)
        self._cached_preferential_ids = None
        self._cached_weight_tensor = None
        self.model_id, self.is_local_path = resolve_unipercept_model_source()
        self.model = None
        self.processor = None
        self.tokenizer = None
        self._device = None
        self._torch_dtype = None

    @property
    def device(self) -> str:
        """Lazily resolves compute device (mps or cpu) per Rule 2.5."""
        if self._device is None:
            import torch

            self._device = "mps" if torch.backends.mps.is_available() else "cpu"
        return self._device

    @device.setter
    def device(self, val: str) -> None:
        self._device = val

    @property
    def torch_dtype(self):
        """Lazily resolves torch_dtype (bfloat16 for MPS stability) per Rule 2.5."""
        if self._torch_dtype is None:
            import torch

            self._torch_dtype = torch.bfloat16 if self.device == "mps" else torch.float32
        return self._torch_dtype

    @torch_dtype.setter
    def torch_dtype(self, val) -> None:
        self._torch_dtype = val

    def _load_model_locked(self) -> None:
        """Assumes caller holds GPU_LOCK -> self.lock in strict hierarchy order."""
        if self.model is not None:
            self.last_used_time = time.time()
            self._start_keep_alive_timer_locked()
            return

        gc.collect()
        clear_mps_cache(synchronize=False)
        print(f"[UniPerceptAdapter] Lazy loading UniPercept model ({self.model_id}) on {self.device} ({self.torch_dtype})...", flush=True)
        model, tokenizer, processor, resolved_dtype = load_unipercept_components(
            self.model_id, self.device, self.torch_dtype, self.is_local_path
        )
        self.model = model
        self.tokenizer = tokenizer
        self.processor = processor
        self.torch_dtype = resolved_dtype
        self.last_used_time = time.time()
        self._start_keep_alive_timer_locked()

    def load_model(self) -> None:
        with GPU_LOCK:
            with self.lock:
                self._load_model_locked()

    def _on_unload(self) -> None:
        """Clears cached MPS tensors and submodule references before model release."""
        self._cached_weight_tensor = None
        self._cached_preferential_ids = None
        if self.model is not None:
            for attr in ("language_model", "vision_model", "mlp1"):
                if hasattr(self.model, attr):
                    try:
                        setattr(self.model, attr, None)
                    except Exception as attr_err:
                        print(f"[UniPerceptAdapter] Submodule detach note ({attr}): {attr_err}", flush=True)
        clear_mps_cache(synchronize=False)

    def _acquire_model_for_request(self, photo_id: Optional[str] = None) -> None:
        """Acquires GPU_LOCK -> self.lock and checks cancellation before/after load."""
        from services.critique_status import critique_status_manager

        if photo_id:
            critique_status_manager.check_cancelled(photo_id)
        with GPU_LOCK:
            with self.lock:
                if photo_id:
                    critique_status_manager.check_cancelled(photo_id)
                self._load_model_locked()
                if photo_id and critique_status_manager.is_cancelled(photo_id):
                    if self.active_requests == 0:
                        self._unload_model_locked()
                    else:
                        self.pending_unload = True
                    critique_status_manager.check_cancelled(photo_id)
                self.pending_unload = False
                self.active_requests += 1

    def _release_model_for_request(self, photo_id: Optional[str] = None) -> None:
        """Decrements active_requests and unloads model if cancelled or unload was deferred."""
        should_unload = False
        with self.lock:
            self.last_used_time = time.time()
            self.active_requests = max(0, self.active_requests - 1)
            is_cancelled = False
            if photo_id:
                from services.critique_status import critique_status_manager

                is_cancelled = critique_status_manager.is_cancelled(photo_id)
            if self.active_requests > 0 and is_cancelled:
                self.pending_unload = True
            should_unload = self.active_requests == 0 and (self.pending_unload or is_cancelled)
        if should_unload:
            self.unload_model()

    @staticmethod
    def _release_pixel_values(pixel_values: Any) -> None:
        if pixel_values is None:
            return
        del pixel_values
        clear_mps_cache(synchronize=False)

    @staticmethod
    def _resolve_conversation_template(model: Any) -> Optional[Any]:
        return resolve_conversation_template(model)

    @staticmethod
    def _build_vr_score_query(desc: str, template: Any, model: Any, num_patches: int) -> str:
        return build_vr_score_query(desc, template, model, num_patches)

    @classmethod
    def _build_vqa_query(cls, prompt_text: str, template: Any, model: Any, num_patches: int) -> Tuple[str, str]:
        return build_vqa_query(prompt_text, template, model, num_patches)

    @staticmethod
    def _clean_vqa_response(raw_text: str, sep_token: str) -> str:
        return clean_vqa_response(raw_text, sep_token)

    def _inject_visual_embeddings(self, input_ids: Any, pixel_values: Any) -> Any:
        img_context_token_id = self.tokenizer.convert_tokens_to_ids("<IMG_CONTEXT>")
        self.model.img_context_token_id = img_context_token_id
        vit_embeds = self.model.extract_feature(pixel_values)
        input_embeds = self.model.language_model.get_input_embeddings()(input_ids)
        batch_size, seq_len, hidden_dim = input_embeds.shape
        flat_embeds = input_embeds.reshape(batch_size * seq_len, hidden_dim)
        selected = input_ids.reshape(batch_size * seq_len) == img_context_token_id
        flat_embeds[selected] = vit_embeds.reshape(-1, hidden_dim).to(device=flat_embeds.device, dtype=flat_embeds.dtype)
        return flat_embeds.reshape(batch_size, seq_len, hidden_dim)

    def _compute_expected_vr_score(self, logits: Any) -> float:
        import torch

        if self._cached_preferential_ids is None:
            self._cached_preferential_ids = [self.tokenizer.convert_tokens_to_ids(word) for word in AESTHETICS_TOKEN_LIST]
        output_logits = logits[:, -1, self._cached_preferential_ids].detach()
        needs_weight_refresh = (
            self._cached_weight_tensor is None
            or self._cached_weight_tensor.device != self.device
            or self._cached_weight_tensor.dtype != output_logits.dtype
        )
        if needs_weight_refresh:
            self._cached_weight_tensor = torch.tensor(list(range(101))).to(device=self.device, dtype=output_logits.dtype)
        score = torch.softmax(output_logits, -1) @ self._cached_weight_tensor
        return float(score.item())

    def compute_official_vr_score(self, pixel_values: Any, desc: str, photo_id: Optional[str] = None) -> float:
        """Computes continuous score (0-100) via softmax expected value over AESTHETICS_TOKEN_LIST."""
        import torch
        from services.critique_status import critique_status_manager

        with GPU_LOCK:
            if photo_id:
                critique_status_manager.check_cancelled(photo_id)
            if self.model is None or self.tokenizer is None:
                return 70.0

            num_patches = pixel_values.shape[0] if pixel_values is not None else 1
            template = self._resolve_conversation_template(self.model)
            query = self._build_vr_score_query(desc, template, self.model, num_patches)
            model_inputs = self.tokenizer(query, return_tensors="pt")
            input_ids = model_inputs["input_ids"].to(self.device)
            attention_mask = model_inputs["attention_mask"].to(self.device)

            with torch.inference_mode():
                input_embeds = self._inject_visual_embeddings(input_ids, pixel_values)
                outputs = self.model.language_model(inputs_embeds=input_embeds, attention_mask=attention_mask, return_dict=True)
                final_score = self._compute_expected_vr_score(outputs.logits)

            del model_inputs, input_ids, attention_mask, input_embeds, outputs
            clear_mps_cache(synchronize=False)
            return final_score

    @staticmethod
    def _load_pil_image(image_input: Any, min_dimension: Optional[int] = 1024):
        from PIL import Image
        from utils.image import load_pil_image

        if isinstance(image_input, Image.Image):
            return image_input
        return load_pil_image(image_input, min_dimension=min_dimension)

    @staticmethod
    def _format_exif_desc(metadata: Optional[Dict[str, Any]]) -> str:
        return format_unipercept_exif_desc(metadata)

    @staticmethod
    def _format_score_guidance_desc(scores_context: Optional[Dict[str, Any]]) -> str:
        return format_score_guidance_desc(scores_context)

    def _safe_load_pil_image(self, image_input: Any) -> Any:
        try:
            return self._load_pil_image(image_input, min_dimension=1024)
        except TypeError:
            return self._load_pil_image(image_input)

    def _safe_prepare_pixel_values(self, pil_img: Any, photo_id: Optional[str] = None) -> Any:
        if pil_img is None:
            return None
        try:
            return self._prepare_pixel_values(pil_img, photo_id=photo_id)
        except TypeError:
            return self._prepare_pixel_values(pil_img)

    def _prepare_pixel_values(self, pil_img: Any, photo_id: Optional[str] = None, **kwargs: Any) -> Any:
        return prepare_pixel_values_tensor(pil_img, self.model, self.torch_dtype, self.device, photo_id=photo_id)

    @staticmethod
    def _resolve_perceptual_weights(f_number: Optional[float] = None, iso: Optional[float] = None) -> Tuple[float, float, float]:
        return resolve_perceptual_weights(f_number=f_number, iso=iso)

    @staticmethod
    def _calculate_aesthetic_bonus(iaa: float, iqa: float) -> float:
        return calculate_aesthetic_bonus(iaa=iaa, iqa=iqa)

    @staticmethod
    def _calculate_overall_vr_score(
        iaa: float,
        iqa: float,
        ista: float,
        f_number: Optional[float] = None,
        iso: Optional[float] = None,
    ) -> int:
        return calculate_overall_vr_score(iaa=iaa, iqa=iqa, ista=ista, f_number=f_number, iso=iso)

    def _compute_single_vr_domain_score(
        self,
        pixel_values: Any,
        desc: str,
        label: str,
        step_idx: int,
        progress_pct: int,
        photo_id: Optional[str],
    ) -> tuple[float, float]:
        from services.critique_status import CritiqueCancelledException, critique_status_manager

        if photo_id:
            critique_status_manager.check_cancelled(photo_id)
            critique_status_manager.update(photo_id, 1, 4, f"[{step_idx}/3] {label} 계산 중...", progress_pct)

        print(f"[UniPercept] ⏱️ [VR Step {step_idx}/3] {label} 계산 시작...", flush=True)
        started_at = time.time()
        try:
            score_val = round(self.compute_official_vr_score(pixel_values, desc), 2)
        except CritiqueCancelledException:
            raise
        except Exception as vr_err:
            print(f"[UniPercept] ⚠️ [VR Step {step_idx}/3] {label} 오류 ({vr_err}), 70.0 폴백", flush=True)
            score_val = 70.0

        elapsed = time.time() - started_at
        print(f"[UniPercept] ✅ [VR Step {step_idx}/3] {label} 완료 ➔ {score_val}점 (소요시간: {elapsed:.2f}초)", flush=True)
        return score_val, elapsed

    def _run_vr_domains(self, pixel_values: Any, photo_id: Optional[str]) -> tuple[dict[str, float], dict[str, float]]:
        domains = (
            ("iaa", "aesthetics", "미학 점수 (IAA)", 1, 12),
            ("iqa", "quality", "화질 점수 (IQA)", 2, 22),
            ("ista", "structure and texture richness", "텍스처 점수 (ISTA)", 3, 32),
        )
        scores: dict[str, float] = {}
        timings: dict[str, float] = {}
        for key, desc, label, step_idx, progress_pct in domains:
            score_val, elapsed = self._compute_single_vr_domain_score(pixel_values, desc, label, step_idx, progress_pct, photo_id)
            scores[key] = score_val
            timings[key] = elapsed
        return scores, timings

    def _assemble_vr_result(
        self, scores: dict[str, float], timings: dict[str, float],
        metadata: Optional[Dict[str, Any]], f_number: Optional[float], iso: Optional[float], started_at: float,
    ) -> Dict[str, Any]:
        eff_f = _coerce_optional_float(f_number if f_number is not None else (metadata or {}).get("f_number"))
        eff_iso = _coerce_optional_float(iso if iso is not None else (metadata or {}).get("iso"))
        overall_val = self._calculate_overall_vr_score(
            scores.get("iaa", 70.0), scores.get("iqa", 70.0), scores.get("ista", 70.0), f_number=eff_f, iso=eff_iso,
        )
        total_elapsed = time.time() - started_at
        raw_vr = f"IAA: {scores['iaa']}, IQA: {scores['iqa']}, ISTA: {scores['ista']} -> Overall: {overall_val}"
        print(f"[UniPercept] 📊 [VR 모드 종료] {raw_vr} ({total_elapsed:.2f}초)", flush=True)
        return {
            "overall": overall_val, "iaa": scores["iaa"], "iqa": scores["iqa"], "ista": scores["ista"],
            "raw_vr_text": raw_vr, "timings": timings, "total_elapsed": total_elapsed,
        }

    def generate_vr_scores(
        self, image_path: str, metadata: Optional[Dict[str, Any]] = None, photo_id: Optional[str] = None,
        max_retries: int = 3, f_number: Optional[float] = None, iso: Optional[float] = None,
        pil_img: Optional[Any] = None, pixel_values: Optional[Any] = None, **kwargs: Any,
    ) -> Dict[str, Any]:
        """Runs 3-way VR scoring (IAA/IQA/ISTA) and EXIF-adaptive overall score fusion."""
        self._acquire_model_for_request(photo_id)
        should_release_pixels = False
        try:
            if (pil_img is None and not os.path.exists(image_path) and not hasattr(self.model, "chat")) or self.model is None:
                return {"overall": 70, "iaa": 70, "iqa": 70, "ista": 70, "raw_vr_text": ""}
            started_at = time.time()
            print("[UniPercept] 🚀 [VR 모드 시작] 3단계 정밀 지각 점수 산출 파이프라인 가동...", flush=True)
            pil_img = pil_img if pil_img is not None else self._safe_load_pil_image(image_path)
            if pixel_values is None:
                pixel_values = self._safe_prepare_pixel_values(pil_img, photo_id=photo_id)
                should_release_pixels = True
            scores, timings = self._run_vr_domains(pixel_values, photo_id)
            return self._assemble_vr_result(scores, timings, metadata, f_number, iso, started_at)
        finally:
            if should_release_pixels:
                self._release_pixel_values(pixel_values)
            self._release_model_for_request(photo_id)

    def _generate_with_language_model(self, prompt_text: str, pixel_values: Any, generation_config: dict) -> str:
        """Bypasses InternVLChatModel.chat() to prevent transformers 5.x return_dict collision."""
        num_patches = pixel_values.shape[0] if pixel_values is not None else 1
        template = self._resolve_conversation_template(self.model)
        query, sep_token = self._build_vqa_query(prompt_text, template, self.model, num_patches)
        eos_token_id = self.tokenizer.convert_tokens_to_ids(sep_token)
        model_inputs = self.tokenizer(query, return_tensors="pt")
        input_ids = model_inputs["input_ids"].to(self.device)
        attention_mask = model_inputs["attention_mask"].to(self.device)

        input_embeds = self._inject_visual_embeddings(input_ids, pixel_values)
        gen_kwargs = {k: v for k, v in (generation_config or {}).items() if k != "return_dict"}
        gen_kwargs.setdefault("eos_token_id", eos_token_id)
        gen_kwargs.setdefault("pad_token_id", eos_token_id)
        gen_kwargs.setdefault("use_cache", True)

        output_ids = self.model.language_model.generate(inputs_embeds=input_embeds, attention_mask=attention_mask, **gen_kwargs)
        decoded = self.tokenizer.batch_decode(output_ids, skip_special_tokens=True)[0]
        del model_inputs, input_ids, attention_mask, input_embeds, output_ids
        return self._clean_vqa_response(decoded, sep_token)

    def _run_single_vqa_domain_inference(self, prompt_text: str, pixel_values: Any, pil_img: Any, generation_config: dict) -> str:
        import torch

        with GPU_LOCK:
            try:
                with torch.inference_mode():
                    has_lm_path = hasattr(self.model, "language_model") and hasattr(self.model, "extract_feature") and self.tokenizer is not None
                    if has_lm_path:
                        return self._generate_with_language_model(prompt_text, pixel_values, generation_config).strip()
                    if hasattr(self.model, "chat"):
                        return self.model.chat(self.tokenizer, pixel_values, prompt_text, generation_config=generation_config).strip()
                    inputs = self.processor(images=pil_img, text=prompt_text, return_tensors="pt").to(self.device, dtype=self.torch_dtype)
                    outputs = self.model.generate(**inputs, max_new_tokens=1024)
                    decoded_text = self.processor.decode(outputs[0], skip_special_tokens=True).strip()
                    del inputs, outputs
                    return decoded_text
            finally:
                clear_mps_cache(synchronize=False)

    def _validate_vqa_inputs(self, image_path: str, pil_img: Any) -> None:
        if self.model is None and not hasattr(self, "_mock_vqa_mode"):
            raise RuntimeError("UniPercept model is not loaded for VQA analysis.")
        if pil_img is None and not os.path.exists(image_path) and not hasattr(self.model, "chat"):
            raise FileNotFoundError(f"Image not found at path: {image_path}")

    def generate_perceptual_anchor_vqa(
        self, image_path: str, metadata: Optional[Dict[str, Any]] = None,
        scores_context: Optional[Dict[str, Any]] = None, photo_id: Optional[str] = None,
        pil_img: Optional[Any] = None, pixel_values: Optional[Any] = None,
    ) -> str:
        """Runs single-pass integrated perceptual VQA to extract cohesive visual anchor."""
        from services.ai_parser import UNIPERCEPT_VQA_SINGLE_PASS_PROMPT
        from services.critique_status import CritiqueCancelledException, critique_status_manager

        self._acquire_model_for_request(photo_id)
        should_release_pixels = False
        try:
            self._validate_vqa_inputs(image_path, pil_img)
            if photo_id:
                critique_status_manager.check_cancelled(photo_id)
                critique_status_manager.update(photo_id, 2, 4, "[UniPercept] 지각 앵커 분석 중...", 50)
            pil_img = pil_img if pil_img is not None else self._safe_load_pil_image(image_path)
            prompt_text = f"{self._format_exif_desc(metadata)}{self._format_score_guidance_desc(scores_context)}{UNIPERCEPT_VQA_SINGLE_PASS_PROMPT}"
            if pixel_values is None:
                pixel_values = self._safe_prepare_pixel_values(pil_img, photo_id=photo_id)
                should_release_pixels = True
            cfg = dict(max_new_tokens=512, do_sample=True, temperature=0.7, top_p=0.9, repetition_penalty=1.0)
            return self._run_single_vqa_domain_inference(prompt_text, pixel_values, pil_img, cfg)
        except CritiqueCancelledException:
            raise
        finally:
            if should_release_pixels:
                self._release_pixel_values(pixel_values)
            self._release_model_for_request(photo_id)

    def _build_scores_summary(self, vr_result: Dict[str, Any]) -> Dict[str, Any]:
        overall = vr_result["overall"]
        return {
            "overall": overall, "iaa": vr_result["iaa"], "iqa": vr_result["iqa"], "ista": vr_result["ista"],
            "comp_direct": overall, "weighted_analysis": overall,
        }

    def _run_ensemble_stages(
        self, image_path: str, pil_img: Any, pixel_values: Any,
        metadata: Optional[Dict[str, Any]], photo_id: Optional[str],
        f_number: Optional[float], iso: Optional[float],
    ) -> Dict[str, Any]:
        from services.critique_status import critique_status_manager

        eff_f = f_number if f_number is not None else (metadata or {}).get("f_number")
        eff_iso = iso if iso is not None else (metadata or {}).get("iso")
        vr_result = self.generate_vr_scores(
            image_path, metadata=metadata, photo_id=photo_id, max_retries=3,
            f_number=eff_f, iso=eff_iso, pil_img=pil_img, pixel_values=pixel_values,
        )
        if photo_id:
            critique_status_manager.check_cancelled(photo_id)
        scores_summary = self._build_scores_summary(vr_result)
        anchor_text = self.generate_perceptual_anchor_vqa(
            image_path, metadata=metadata, scores_context=scores_summary,
            photo_id=photo_id, pil_img=pil_img, pixel_values=pixel_values,
        )
        if photo_id:
            critique_status_manager.check_cancelled(photo_id)
        return {
            "critique": anchor_text, "quality_score": vr_result["overall"], "scores": scores_summary,
            "text_comp": anchor_text, "raw_vr_text": vr_result.get("raw_vr_text", ""), "pil_img": pil_img,
        }

    def generate_full_ensemble_critique(
        self, image_path: str, metadata: Optional[Dict[str, Any]] = None, photo_id: Optional[str] = None,
        f_number: Optional[float] = None, iso: Optional[float] = None, **kwargs: Any,
    ) -> Dict[str, Any]:
        """Executes ADR-05 2-stage pipeline (3-Way VR scoring + single-pass VQA anchor)."""
        from services.critique_status import critique_status_manager

        pixel_values = None
        try:
            if photo_id:
                critique_status_manager.check_cancelled(photo_id)
            pil_img = self._safe_load_pil_image(image_path)
            if hasattr(self, "_prepare_pixel_values") and self.model is not None:
                pixel_values = self._safe_prepare_pixel_values(pil_img, photo_id=photo_id)
            return self._run_ensemble_stages(image_path, pil_img, pixel_values, metadata, photo_id, f_number, iso)
        finally:
            self._release_pixel_values(pixel_values)
            self.unload_model()


_unipercept_adapter_instance = None
_unipercept_lock = threading.RLock()


def get_unipercept_adapter() -> UniPerceptAdapter:
    global _unipercept_adapter_instance
    if _unipercept_adapter_instance is None:
        with _unipercept_lock:
            if _unipercept_adapter_instance is None:
                _unipercept_adapter_instance = UniPerceptAdapter()
    return _unipercept_adapter_instance
