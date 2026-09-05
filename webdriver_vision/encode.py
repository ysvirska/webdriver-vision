"""Convert screenshot bytes to base64-encoded PNG or JPEG images."""

import base64
from io import BytesIO

from PIL import Image


def encode_image(
    image: bytes, *, image_format: str = "png", quality: int = 85
) -> str:
    """Encode PNG or JPEG bytes as an ASCII base64 string without a data URL prefix.

    PNG preserves transparency. JPEG composites transparency onto white and uses
    the requested quality. Quality must be an integer from 1 to 95 for either
    format, but only affects JPEG output. Image dimensions are preserved.

    Wrong input types raise TypeError. Invalid image data, unsupported output
    formats, and invalid quality values raise ValueError.
    """
    if not isinstance(image, bytes):
        raise TypeError("image must be PNG or JPEG bytes.")
    if image_format not in ("png", "jpeg"):
        raise ValueError("image_format must be png or jpeg.")
    if type(quality) is not int or not 1 <= quality <= 95:
        raise ValueError("quality must be an integer from 1 to 95.")

    try:
        with BytesIO(image) as source_buffer:
            with Image.open(source_buffer, formats=("PNG", "JPEG")) as source:
                decoded = source.convert("RGBA")
    except (OSError, ValueError, Image.DecompressionBombError):
        raise ValueError("image must contain valid PNG or JPEG data.") from None

    with decoded, BytesIO() as output:
        if image_format == "jpeg":
            with Image.new("RGB", decoded.size, "white") as flattened:
                with decoded.getchannel("A") as alpha:
                    flattened.paste(decoded, mask=alpha)
                flattened.save(output, format="JPEG", quality=quality)
        else:
            decoded.save(output, format="PNG")
        return base64.b64encode(output.getvalue()).decode("ascii")
