# Screenshot encoding

`encode_image` accepts PNG or JPEG image bytes and returns an ASCII base64 string.
For example, to encode an existing screenshot:

```python
from pathlib import Path

from webdriver_vision.encode import encode_image

screenshot = Path("screenshot.png").read_bytes()
png_base64 = encode_image(screenshot)
jpeg_base64 = encode_image(screenshot, image_format="jpeg", quality=80)
```

Both input formats can be converted to either output format. The output preserves
the image dimensions. PNG output is lossless and preserves transparency. JPEG is
lossy and uses a white background for transparent and partially transparent pixels.
The encoder processes the first frame of animated PNG input.

| Argument | Default | Accepted values |
| --- | --- | --- |
| `image` | Required | PNG or JPEG bytes. |
| `image_format` | `"png"` | `"png"` or `"jpeg"`, in lowercase. |
| `quality` | `85` | An integer from 1 to 95. Validated for both formats; affects JPEG only. |

The return value contains no line breaks or `data:image/...;base64,` prefix.
It can be included in an API request as required by the provider. File paths are
not accepted directly; read the file as bytes first.

Wrong input types raise `TypeError`. Empty, unrecognized, or corrupt images raise
`ValueError`, as do unsupported formats and invalid quality values. Pillow image
size limits remain enabled.
