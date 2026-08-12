import rawpy
import io
from PIL import Image

file_path = "/Users/kimbeomjun/Desktop/photo/original/_DSC0699.NEF"

def decode_raw_to_pil(file_path: str) -> Image.Image:
    with rawpy.imread(file_path) as raw:
        try:
            thumb = raw.extract_thumb()
            if thumb.format == rawpy.ThumbFormat.JPEG:
                return Image.open(io.BytesIO(thumb.data)).convert("RGB")
            elif thumb.format == rawpy.ThumbFormat.BITMAP:
                return Image.fromarray(thumb.data).convert("RGB")
        except Exception as e:
            print(f"Thumbnail extraction failed: {e}")
            pass
        
        rgb = raw.postprocess(
            use_camera_wb=True,
            half_size=False,
            no_auto_bright=True,
            output_color=rawpy.ColorSpace.sRGB
        )
        return Image.fromarray(rgb)

try:
    img = decode_raw_to_pil(file_path)
    print(f"Successfully decoded! Size: {img.size}")
except Exception as e:
    print(f"Error: {e}")
