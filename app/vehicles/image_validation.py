from dataclasses import dataclass
from io import BytesIO
import warnings

from fastapi import HTTPException, UploadFile
from PIL import Image, ImageOps, UnidentifiedImageError
from pillow_heif import register_heif_opener

MAX_IMAGES = 6
MAX_IMAGE_BYTES = 12 * 1024 * 1024
MAX_TOTAL_BYTES = MAX_IMAGES * MAX_IMAGE_BYTES
MAX_IMAGE_PIXELS = 50_000_000
MAX_IMAGE_SIDE = 2560
OUTPUT_QUALITY = 85
# Pillow identifies some smartphone JPEGs (HDR, portrait or motion photos) as
# MPO even when the file uses a .jpg/.jpeg extension.
SUPPORTED_FORMATS = {"JPEG", "MPO", "PNG", "WEBP", "HEIF", "AVIF"}

register_heif_opener()


@dataclass(frozen=True)
class ProcessedImage:
    content: bytes
    content_type: str = "image/jpeg"
    extension: str = "jpg"


def validate_image_count(files: list[UploadFile]) -> None:
    if not files or len(files) > MAX_IMAGES:
        raise HTTPException(status_code=400, detail=f"Upload between 1 and {MAX_IMAGES} images.")


async def prepare_images(files: list[UploadFile]) -> list[ProcessedImage]:
    validate_image_count(files)
    total_bytes = 0
    processed: list[ProcessedImage] = []

    for upload in files:
        content = await upload.read(MAX_IMAGE_BYTES + 1)
        if len(content) > MAX_IMAGE_BYTES:
            raise HTTPException(status_code=413, detail="Each image must be at most 12 MB.")
        total_bytes += len(content)
        if total_bytes > MAX_TOTAL_BYTES:
            raise HTTPException(status_code=413, detail="All images together must be at most 72 MB.")
        processed.append(_process_image(content))

    return processed


def _process_image(content: bytes) -> ProcessedImage:
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(BytesIO(content)) as source:
                if source.format not in SUPPORTED_FORMATS:
                    raise HTTPException(
                        status_code=400,
                        detail="Erlaubt sind JPEG-, Smartphone-JPEG-, PNG-, WebP-, AVIF-, HEIC- und HEIF-Bilder.",
                    )
                if source.width * source.height > MAX_IMAGE_PIXELS:
                    raise HTTPException(status_code=413, detail="The image resolution is too large.")
                image = ImageOps.exif_transpose(source)
                image.thumbnail((MAX_IMAGE_SIDE, MAX_IMAGE_SIDE), Image.Resampling.LANCZOS)
                if image.mode != "RGB":
                    background = Image.new("RGB", image.size, "white")
                    if image.mode in ("RGBA", "LA"):
                        background.paste(image, mask=image.getchannel("A"))
                    else:
                        background.paste(image.convert("RGB"))
                    image = background
                output = BytesIO()
                image.save(output, format="JPEG", quality=OUTPUT_QUALITY, optimize=True)
                return ProcessedImage(content=output.getvalue())
    except HTTPException:
        raise
    except (Image.DecompressionBombError, Image.DecompressionBombWarning, UnidentifiedImageError, OSError, ValueError) as error:
        raise HTTPException(status_code=400, detail="The uploaded file is not a valid image.") from error
