import os
import hashlib
from abc import ABC, abstractmethod
from typing import Dict, Any, Union
from utils.image import extract_metadata
from services.photo import generate_and_cache_thumbnail
from services.ai_factory import get_siglip_adapter, get_gemma_adapter

class PipelineContext:
    def __init__(self, file_path: str):
        self.file_path: str = file_path
        self.file_size: int = os.path.getsize(file_path) if os.path.exists(file_path) else 0
        self.file_mtime: float = os.path.getmtime(file_path) if os.path.exists(file_path) else 0.0
        self.image_id: str = ""
        self.metadata: Dict[str, Any] = {}
        self.embedding: list[float] = []
        self.ai_result: Dict[str, Any] = {}
        self.status: str = "success"  # "success", "skipped", "error"

class PipelineStep(ABC):
    @abstractmethod
    def execute(self, ctx: PipelineContext) -> bool:
        """Executes step. Returns True to continue pipeline, False to stop early."""
        pass

class HashStep(PipelineStep):
    def execute(self, ctx: PipelineContext) -> bool:
        h = hashlib.sha256()
        with open(ctx.file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
        ctx.image_id = h.hexdigest()
        return True

class ThumbnailStep(PipelineStep):
    def execute(self, ctx: PipelineContext) -> bool:
        try:
            generate_and_cache_thumbnail(ctx.file_path, ctx.image_id)
            return True
        except Exception as e:
            print(f"[Pipeline ThumbnailStep] Error for {ctx.file_path}: {e}", flush=True)
            ctx.status = "error"
            return False

class EXIFExtractStep(PipelineStep):
    def execute(self, ctx: PipelineContext) -> bool:
        try:
            ctx.metadata = extract_metadata(ctx.file_path)
            return True
        except Exception as e:
            print(f"[Pipeline EXIFExtractStep] Error for {ctx.file_path}: {e}", flush=True)
            ctx.metadata = {}
            return True

class AIInferenceStep(PipelineStep):
    def execute(self, ctx: PipelineContext) -> bool:
        try:
            ctx.embedding = get_siglip_adapter().get_image_embedding(ctx.file_path)
            ctx.ai_result = get_gemma_adapter().generate_caption_and_tags(ctx.file_path, ctx.metadata)
            return True
        except Exception as e:
            print(f"[Pipeline AIInferenceStep] Error for {ctx.file_path}: {e}", flush=True)
            ctx.status = "error"
            return False

class IndexingPipeline:
    def __init__(self):
        self.steps: list[PipelineStep] = [
            HashStep(),
            ThumbnailStep(),
            EXIFExtractStep(),
            AIInferenceStep()
        ]

    def run(self, file_path: str) -> Union[Dict[str, Any], str]:
        ctx = PipelineContext(file_path)
        for step in self.steps:
            cont = step.execute(ctx)
            if not cont or ctx.status == "error":
                return "error"
                
        # Package data for DB batch save
        image_data = {
            "id": ctx.image_id,
            "parent_dir": os.path.dirname(file_path),
            "file_path": file_path,
            "file_name": os.path.basename(file_path),
            "file_size": ctx.file_size,
            "file_mtime": ctx.file_mtime,
            "mime_type": ctx.metadata.get("mime_type", "image/jpeg")
        }
        metadata_data = {
            "width": ctx.metadata.get("width"),
            "height": ctx.metadata.get("height"),
            "color_space": ctx.metadata.get("color_space"),
            "camera_model": ctx.metadata.get("camera_model"),
            "lens_model": ctx.metadata.get("lens_model"),
            "f_number": ctx.metadata.get("f_number"),
            "focal_length": ctx.metadata.get("focal_length"),
            "shutter_speed": ctx.metadata.get("shutter_speed"),
            "iso": ctx.metadata.get("iso"),
            "capture_date": ctx.metadata.get("capture_date")
        }
        ai_data = {
            "caption": ctx.ai_result.get("caption", ""),
            "tags": ctx.ai_result.get("tags", []),
            "aesthetic_tags": ctx.ai_result.get("aesthetic_tags", []),
            "is_user_edited": False
        }
        return {
            "image_data": image_data,
            "metadata_data": metadata_data,
            "ai_data": ai_data,
            "embedding": ctx.embedding
        }
