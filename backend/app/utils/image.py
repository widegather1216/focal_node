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
                with Image.open(io.BytesIO(thumb.data)) as img:
                    img_t = ImageOps.exif_transpose(img)
                    return img_t.convert("RGB") if img_t.mode != "RGB" else img_t.copy()
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

def load_pil_image(file_path: str) -> Image.Image:
    """
    Loads any supported image (RAW or standard) as a PIL Image in RGB mode.
    Handles EXIF orientation and ensures file handles are closed properly.
    """
    if is_raw_image(file_path):
        return decode_raw_to_pil(file_path)
    with Image.open(file_path) as raw_img:
        img_t = ImageOps.exif_transpose(raw_img)
        return img_t.convert("RGB") if img_t.mode != "RGB" else img_t.copy()

def _get_tag_val(tags: dict, keys: list[str] | str):
    if isinstance(keys, str):
        keys = [keys]
    for k in keys:
        tag = tags.get(k)
        if tag is not None:
            return tag.values[0] if isinstance(tag.values, list) else tag.values
    return None

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
    Extracts EXIF and basic image dimensions from standard or RAW images,
    including 35mm focal length equivalent and sensor crop factor detection.
    """
    metadata = {
        "width": None,
        "height": None,
        "color_space": "sRGB",  # Default fallback
        "camera_model": None,
        "lens_model": None,
        "f_number": None,
        "focal_length": None,
        "focal_length_35mm": None,
        "crop_factor": None,
        "sensor_format": None,
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
            model = _get_tag_val(tags, "Image Model")
            if model:
                metadata["camera_model"] = str(model).strip()

            # Lens model
            lens = _get_tag_val(tags, ["EXIF LensModel", "Image LensModel", "EXIF LensModelName"])
            if lens:
                metadata["lens_model"] = str(lens).strip()

            # F-Number
            f_val = _get_tag_val(tags, "EXIF FNumber")
            if f_val is not None:
                parsed_f = _parse_ratio(f_val)
                if parsed_f is not None:
                    metadata["f_number"] = round(parsed_f, 2)

            # Focal Length
            fl_val = _get_tag_val(tags, "EXIF FocalLength")
            if fl_val is not None:
                metadata["focal_length"] = _parse_ratio(fl_val)

            # Focal Length in 35mm Film
            fl35_val = _get_tag_val(tags, ["EXIF FocalLengthIn35mmFilm", "EXIF FocalLengthIn35mmFormat"])
            if fl35_val is not None:
                try:
                    parsed_35 = float(fl35_val)
                    if parsed_35 > 0:
                        metadata["focal_length_35mm"] = parsed_35
                except ValueError:
                    pass

            # Shutter speed
            shutter_val = _get_tag_val(tags, "EXIF ExposureTime")
            if shutter_val is not None:
                metadata["shutter_speed"] = _parse_shutter_speed(shutter_val)

            # ISO
            iso_val = _get_tag_val(tags, ["EXIF ISOSpeedRatings", "EXIF ISOSpeed"])
            if iso_val is not None:
                try:
                    metadata["iso"] = int(iso_val)
                except ValueError:
                    pass

            # Capture date
            date_val = _get_tag_val(tags, ["EXIF DateTimeOriginal", "Image DateTime"])
            if date_val is not None:
                metadata["capture_date"] = _parse_date(str(date_val))
    except Exception:
        pass

def _determine_crop_factor(
    fl: float | None,
    fl35: float | None,
    camera: str,
    lens: str,
    is_smartphone: bool
) -> float | None:
    if fl and fl35 and fl > 0:
        return round(fl35 / fl, 2)
    if not (camera or lens):
        return None

    if is_smartphone:
        if fl:
            if fl < 3.0:
                return 5.85  # Smartphone Ultrawide (~13mm equiv)
            elif fl <= 9.0:
                return 3.5   # Smartphone Main (~24-28mm equiv)
            else:
                return 7.0   # Smartphone Telephoto (~70-120mm equiv)
        return 3.5

    if any(k in camera for k in ["ILCE-6", "NEX-", "X-T", "X-H", "X-PRO", "X-S", "X-E", "X100", "Z 50", "Z FC", "Z 30", "D7000", "D5000", "D3000"]) or \
       (any(k in lens for k in ["E ", "XF ", "XC ", "DX "]) and not any(k in lens for k in ["FE ", "FX "])):
        return 1.5
    if any(k in camera for k in ["EOS R7", "EOS R10", "EOS R50", "EOS R100", "EOS 7D", "EOS 80D", "EOS 90D", "EOS M"]) or \
       any(k in lens for k in ["EF-S", "RF-S"]):
        return 1.6
    if any(k in camera for k in ["DMC-", "DC-", "GH", "GX", "GF", "G9", "E-M", "OM-1", "OM-5", "PEN"]) or \
       any(k in lens for k in ["M.ZUIKO", "LUMIX G"]):
        return 2.0
    if any(k in camera for k in ["ILCE-7", "ILCE-9", "ILCE-1", "EOS R", "EOS 5D", "EOS 6D", "EOS 1D", "Z 5", "Z 6", "Z 7", "Z 8", "Z 9", "D850", "D750"]) or \
       any(k in lens for k in ["FE ", "RF ", "EF ", "FX "]):
        return 1.0
    return None

def _determine_sensor_format(
    crop_factor: float,
    fl: float | None,
    is_smartphone: bool
) -> str:
    if is_smartphone:
        if fl and fl < 3.0:
            return f"Smartphone Ultrawide (~{crop_factor}x)"
        elif fl and fl > 9.0:
            return f"Smartphone Telephoto (~{crop_factor}x)"
        return f"Smartphone Main (~{crop_factor}x)"

    if crop_factor >= 1.9:
        return "Micro Four Thirds (2.0x)"
    if 1.55 <= crop_factor <= 1.7:
        return "APS-C Canon (1.6x)"
    if 1.35 <= crop_factor < 1.55:
        return "APS-C (1.5x)"
    if 0.9 <= crop_factor <= 1.1:
        return "Full Frame"
    return f"Crop {crop_factor}x"

def extract_metadata(file_path: str) -> dict:
    """
    Extracts EXIF and basic image dimensions from standard or RAW images,
    including 35mm focal length equivalent and sensor crop factor detection.
    """
    metadata = {
        "width": None,
        "height": None,
        "color_space": "sRGB",
        "camera_model": None,
        "lens_model": None,
        "f_number": None,
        "focal_length": None,
        "focal_length_35mm": None,
        "crop_factor": None,
        "sensor_format": None,
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
        except Exception as e:
            print(f"[extract_metadata] Warning: Failed to read RAW dimensions for {file_path}: {e}")
    else:
        try:
            with Image.open(file_path) as img:
                metadata["width"] = img.size[0]
                metadata["height"] = img.size[1]
                icc = img.info.get("icc_profile")
                if icc:
                    metadata["color_space"] = "Adobe RGB" if b"Adobe" in icc else "sRGB"
        except Exception as e:
            print(f"[extract_metadata] Warning: Failed to read image dimensions for {file_path}: {e}")

    # 2. Extract EXIF details using exifread
    try:
        with open(file_path, "rb") as f:
            tags = exifread.process_file(f, details=False)

            model = _get_tag_val(tags, "Image Model")
            if model:
                metadata["camera_model"] = str(model).strip()

            lens = _get_tag_val(tags, ["EXIF LensModel", "Image LensModel", "EXIF LensModelName"])
            if lens:
                metadata["lens_model"] = str(lens).strip()

            f_val = _get_tag_val(tags, "EXIF FNumber")
            if f_val is not None:
                parsed_f = _parse_ratio(f_val)
                if parsed_f is not None:
                    metadata["f_number"] = round(parsed_f, 2)

            fl_val = _get_tag_val(tags, "EXIF FocalLength")
            if fl_val is not None:
                metadata["focal_length"] = _parse_ratio(fl_val)

            fl35_val = _get_tag_val(tags, ["EXIF FocalLengthIn35mmFilm", "EXIF FocalLengthIn35mmFormat"])
            if fl35_val is not None:
                try:
                    parsed_35 = float(fl35_val)
                    if parsed_35 > 0:
                        metadata["focal_length_35mm"] = parsed_35
                except ValueError:
                    pass

            shutter_val = _get_tag_val(tags, "EXIF ExposureTime")
            if shutter_val is not None:
                metadata["shutter_speed"] = _parse_shutter_speed(shutter_val)

            iso_val = _get_tag_val(tags, ["EXIF ISOSpeedRatings", "EXIF ISOSpeed"])
            if iso_val is not None:
                try:
                    metadata["iso"] = int(iso_val)
                except ValueError:
                    pass

            date_val = _get_tag_val(tags, ["EXIF DateTimeOriginal", "Image DateTime"])
            if date_val is not None:
                metadata["capture_date"] = _parse_date(str(date_val))
    except Exception as e:
        print(f"[extract_metadata] Warning: EXIF reading failed for {file_path}: {e}")

    # 3. Derive 35mm focal length equivalent & Crop Factor
    fl = metadata["focal_length"]
    fl35 = metadata["focal_length_35mm"]
    camera = (metadata.get("camera_model") or "").upper()
    lens = (metadata.get("lens_model") or "").upper()
    is_smartphone = any(k in camera for k in ["IPHONE", "GALAXY", "SM-", "PIXEL", "XIAOMI", "REDMI", "POCO", "ONEPLUS", "HUAWEI", "OPPO", "VIVO"]) or \
                    any(k in lens for k in ["IPHONE", "GALAXY", "SM-", "PIXEL"])

    crop_factor = _determine_crop_factor(fl, fl35, camera, lens, is_smartphone)

    if crop_factor:
        metadata["crop_factor"] = crop_factor
        if fl and not metadata["focal_length_35mm"]:
            metadata["focal_length_35mm"] = round(fl * crop_factor, 1)
        metadata["sensor_format"] = _determine_sensor_format(crop_factor, fl, is_smartphone)

    # Fallback to file system mtime if capture date was not in EXIF
    if metadata["capture_date"] is None:
        try:
            mtime = os.path.getmtime(file_path)
            metadata["capture_date"] = datetime.datetime.fromtimestamp(mtime)
        except Exception as e:
            print(f"[extract_metadata] Warning: Could not read mtime for {file_path}: {e}")

    return metadata
