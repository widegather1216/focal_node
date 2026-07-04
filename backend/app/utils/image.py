import os
import datetime
import mimetypes
from PIL import Image, ImageOps
import rawpy
import exifread

# Disable decompression bomb checks for high-resolution cameras
Image.MAX_IMAGE_PIXELS = None

RAW_EXTENSIONS = {
    ".arw": "image/x-sony-arw",
    ".cr2": "image/x-canon-cr2",
    ".cr3": "image/x-canon-cr3",
    ".nef": "image/x-nikon-nef",
    ".dng": "image/x-adobe-dng",
    ".orf": "image/x-olympus-orf",
    ".rw2": "image/x-panasonic-rw2",
    ".pef": "image/x-pentax-pef",
    ".raf": "image/x-fuji-raf",
}

def is_raw_image(file_path: str) -> bool:
    """
    Checks if a file is a supported RAW format based on extension.
    """
    ext = os.path.splitext(file_path)[1].lower()
    return ext in RAW_EXTENSIONS

def get_mime_type(file_path: str) -> str:
    """
    Returns the MIME type of the file. Custom mapping for RAW images.
    """
    ext = os.path.splitext(file_path)[1].lower()
    if ext in RAW_EXTENSIONS:
        return RAW_EXTENSIONS[ext]
    if ext == ".webp":
        return "image/webp"
    mime, _ = mimetypes.guess_type(file_path)
    return mime or "image/jpeg"
import io

def decode_raw_to_pil(file_path: str) -> Image.Image:
    """
    Decodes a RAW image file to a PIL Image (sRGB) in-memory.
    Attempts to extract embedded thumbnail first for performance and compatibility,
    then falls back to full raw post-processing.
    """
    with rawpy.imread(file_path) as raw:
        try:
            thumb = raw.extract_thumb()
            if thumb.format == rawpy.ThumbFormat.JPEG:
                img = Image.open(io.BytesIO(thumb.data))
                return ImageOps.exif_transpose(img).convert("RGB")
            elif thumb.format == rawpy.ThumbFormat.BITMAP:
                return Image.fromarray(thumb.data).convert("RGB")
        except Exception as e:
            print(f"[decode_raw_to_pil] Thumbnail extraction failed for {file_path}: {e}")
            
        # Fallback to full postprocessing if thumbnail extraction fails or format is unknown
        rgb = raw.postprocess(
            use_camera_wb=True,
            half_size=True,
            no_auto_bright=True,
            output_color=rawpy.ColorSpace.sRGB
        )
        return Image.fromarray(rgb)

def _parse_ratio(ratio_obj) -> float | None:
    if ratio_obj is None:
        return None
    # Try parsing exifread Ratio/Fraction objects
    if hasattr(ratio_obj, "num") and hasattr(ratio_obj, "den"):
        if ratio_obj.den == 0:
            return None
        return float(ratio_obj.num) / float(ratio_obj.den)
    try:
        val = str(ratio_obj)
        if "/" in val:
            num, den = val.split("/")
            if float(den) == 0:
                return None
            return float(num) / float(den)
        return float(val)
    except Exception:
        return None

def _parse_shutter_speed(val) -> str | None:
    if val is None:
        return None
    return str(val).strip()

def _parse_date(date_str: str) -> datetime.datetime | None:
    # Try parsing EXIF datetime string
    for fmt in ("%Y:%m:%d %H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y:%m:%d %H:%M:%S.%f"):
        try:
            return datetime.datetime.strptime(date_str.strip(), fmt)
        except ValueError:
            continue
    return None

def extract_metadata(file_path: str) -> dict:
    """
    Extracts EXIF and basic image dimensions from standard or RAW images.
    """
    metadata = {
        "width": None,
        "height": None,
        "color_space": "sRGB",  # Default fallback
        "camera_model": None,
        "lens_model": None,
        "f_number": None,
        "shutter_speed": None,
        "iso": None,
        "capture_date": None,
        "mime_type": get_mime_type(file_path)
    }

    # 1. Fetch width & height (using rawpy sizes for speed, avoid full loading)
    if is_raw_image(file_path):
        try:
            with rawpy.imread(file_path) as raw:
                metadata["width"] = raw.sizes.width
                metadata["height"] = raw.sizes.height
        except Exception:
            pass
    else:
        try:
            with Image.open(file_path) as img:
                metadata["width"] = img.size[0]
                metadata["height"] = img.size[1]
                icc = img.info.get("icc_profile")
                if icc:
                    metadata["color_space"] = "Adobe RGB" if b"Adobe" in icc else "sRGB"
        except Exception:
            pass

    # 2. Extract EXIF details using exifread
    try:
        with open(file_path, "rb") as f:
            tags = exifread.process_file(f, details=False)

            # Camera model
            model_tag = tags.get("Image Model")
            if model_tag:
                metadata["camera_model"] = str(model_tag).strip()

            # Lens model
            lens_tag = tags.get("EXIF LensModel") or tags.get("Image LensModel") or tags.get("EXIF LensModelName")
            if lens_tag:
                metadata["lens_model"] = str(lens_tag).strip()

            # F-Number
            f_tag = tags.get("EXIF FNumber")
            if f_tag:
                val = f_tag.values[0] if isinstance(f_tag.values, list) else f_tag.values
                metadata["f_number"] = _parse_ratio(val)

            # Shutter speed
            shutter_tag = tags.get("EXIF ExposureTime")
            if shutter_tag:
                val = shutter_tag.values[0] if isinstance(shutter_tag.values, list) else shutter_tag.values
                metadata["shutter_speed"] = _parse_shutter_speed(val)

            # ISO
            iso_tag = tags.get("EXIF ISOSpeedRatings") or tags.get("EXIF ISOSpeed")
            if iso_tag:
                val = iso_tag.values[0] if isinstance(iso_tag.values, list) else iso_tag.values
                try:
                    metadata["iso"] = int(val)
                except ValueError:
                    pass

            # Capture date
            date_tag = tags.get("EXIF DateTimeOriginal") or tags.get("Image DateTime")
            if date_tag:
                val = str(date_tag.values[0] if isinstance(date_tag.values, list) else date_tag.values)
                metadata["capture_date"] = _parse_date(val)
    except Exception:
        pass

    # Fallback to file system mtime if capture date was not in EXIF
    if metadata["capture_date"] is None:
        try:
            mtime = os.path.getmtime(file_path)
            metadata["capture_date"] = datetime.datetime.fromtimestamp(mtime)
        except Exception:
            pass

    return metadata
