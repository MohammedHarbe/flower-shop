from io import BytesIO
import warnings
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request
from PIL import Image, ImageOps, UnidentifiedImageError

from backend.admin_auth import require_admin_key
from backend.settings import Settings


router = APIRouter()
MAX_IMAGE_BYTES = 5 * 1024 * 1024
FORMAT_DETAILS = {
    "JPEG": ("image/jpeg", ".jpg"),
    "PNG": ("image/png", ".png"),
    "WEBP": ("image/webp", ".webp"),
}


@router.post("/admin/uploads/products", status_code=201)
async def upload_product_image(
    request: Request,
    _admin: None = Depends(require_admin_key),
) -> dict[str, str]:
    settings = Settings()
    if not settings.media_uploads_enabled:
        raise HTTPException(503, "Product image uploads require configured persistent media storage")

    content_type = request.headers.get("content-type", "").split(";", 1)[0].strip().lower()
    if content_type not in {detail[0] for detail in FORMAT_DETAILS.values()}:
        raise HTTPException(415, "Upload a JPEG, PNG, or WebP image")

    content_length = request.headers.get("content-length")
    if content_length:
        try:
            if int(content_length) > MAX_IMAGE_BYTES:
                raise HTTPException(413, "Image exceeds the 5 MB upload limit")
        except ValueError:
            raise HTTPException(400, "Invalid content length") from None

    chunks = bytearray()
    async for chunk in request.stream():
        if len(chunks) + len(chunk) > MAX_IMAGE_BYTES:
            raise HTTPException(413, "Image exceeds the 5 MB upload limit")
        chunks.extend(chunk)

    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(BytesIO(chunks)) as image:
                image_format = image.format
                image.verify()
            with Image.open(BytesIO(chunks)) as image:
                image.load()
                image = ImageOps.exif_transpose(image)
                if image_format not in FORMAT_DETAILS or FORMAT_DETAILS[image_format][0] != content_type:
                    raise HTTPException(415, "Image content does not match an allowed format")
                if image.format == "JPEG" and image.mode not in {"L", "RGB"}:
                    image = image.convert("RGB")
                output = BytesIO()
                image.save(output, format=image_format, optimize=True)
    except HTTPException:
        raise
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError, Image.DecompressionBombWarning):
        raise HTTPException(400, "The uploaded file is not a valid supported image") from None

    data = output.getvalue()
    if len(data) > MAX_IMAGE_BYTES:
        raise HTTPException(413, "Processed image exceeds the 5 MB upload limit")

    extension = FORMAT_DETAILS[image_format][1]
    filename = f"{uuid4().hex}{extension}"
    product_dir = settings.resolved_media_dir / "products"
    image_path = product_dir / filename
    try:
        product_dir.mkdir(parents=True, exist_ok=True)
        with image_path.open("xb") as uploaded:
            uploaded.write(data)
    except OSError:
        image_path.unlink(missing_ok=True)
        raise HTTPException(503, "Image storage is unavailable") from None

    return {"image_url": f"{settings.media_base_url}/products/{filename}"}