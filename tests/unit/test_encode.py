"""Tests for image conversion and base64 encoding."""

import base64
import unittest
from io import BytesIO
from unittest.mock import patch

from PIL import Image

from webdriver_vision.encode import encode_image


class EncodeImageTests(unittest.TestCase):
    def make_image(self, mode="RGB", color=(10, 80, 160), image_format="PNG"):
        with Image.new(mode, (16, 12), color) as image, BytesIO() as buffer:
            image.save(buffer, format=image_format)
            return buffer.getvalue()

    def test_png_round_trip_preserves_dimensions_and_rgba_pixels(self):
        pixels = [(255, 0, 0, 255), (0, 80, 160, 128), (40, 90, 10, 0), (1, 2, 3, 1)]
        with Image.new("RGBA", (2, 2)) as source, BytesIO() as buffer:
            source.putdata(pixels)
            source.save(buffer, format="PNG")
            result = encode_image(buffer.getvalue())

        with BytesIO(base64.b64decode(result, validate=True)) as buffer:
            with Image.open(buffer) as decoded:
                self.assertEqual(decoded.format, "PNG")
                self.assertEqual(decoded.size, (2, 2))
                self.assertEqual(list(decoded.getdata()), pixels)

    def test_output_is_plain_ascii_base64(self):
        result = encode_image(self.make_image())
        result.encode("ascii")
        self.assertNotIn("\n", result)
        self.assertNotIn("\r", result)
        self.assertFalse(result.startswith("data:"))
        decoded = base64.b64decode(result, validate=True)
        self.assertTrue(decoded.startswith(b"\x89PNG\r\n\x1a\n"))

    def test_jpeg_composites_transparency_onto_white(self):
        for color, expected in (
            ((255, 0, 0, 255), (255, 0, 0)),
            ((0, 0, 0, 0), (255, 255, 255)),
            ((0, 0, 255, 128), (127, 127, 255)),
        ):
            with self.subTest(color=color):
                result = encode_image(
                    self.make_image("RGBA", color), image_format="jpeg"
                )
                with BytesIO(base64.b64decode(result, validate=True)) as buffer:
                    with Image.open(buffer) as decoded:
                        self.assertEqual(decoded.format, "JPEG")
                        self.assertEqual(decoded.mode, "RGB")
                        self.assertEqual(decoded.size, (16, 12))
                        for actual, target in zip(decoded.getpixel((0, 0)), expected):
                            self.assertLessEqual(abs(actual - target), 3)

    def test_jpeg_input_can_be_converted_to_png(self):
        source = self.make_image(image_format="JPEG")
        with BytesIO(source) as buffer, Image.open(buffer) as image:
            expected_pixel = image.getpixel((0, 0)) + (255,)
        result = encode_image(source)
        with BytesIO(base64.b64decode(result, validate=True)) as buffer:
            with Image.open(buffer) as decoded:
                self.assertEqual(decoded.format, "PNG")
                self.assertEqual(decoded.size, (16, 12))
                self.assertEqual(decoded.getpixel((0, 0)), expected_pixel)

    def test_quality_changes_jpeg_quantization(self):
        source = self.make_image()
        quantization = []
        for quality in (20, 90):
            result = encode_image(source, image_format="jpeg", quality=quality)
            with BytesIO(base64.b64decode(result, validate=True)) as buffer:
                with Image.open(buffer) as decoded:
                    quantization.append(sum(decoded.quantization[0]))
        self.assertGreater(quantization[0], quantization[1])

    def test_grayscale_input_preserves_visible_color(self):
        result = encode_image(self.make_image("L", 37))
        with BytesIO(base64.b64decode(result, validate=True)) as buffer:
            with Image.open(buffer) as decoded:
                self.assertEqual(decoded.getpixel((0, 0)), (37, 37, 37, 255))

    def test_paletted_png_preserves_transparency(self):
        with Image.new("P", (16, 12), 0) as image, BytesIO() as buffer:
            image.putpalette([255, 0, 0] + [0] * 765)
            image.save(buffer, format="PNG", transparency=0)
            result = encode_image(buffer.getvalue())
        with BytesIO(base64.b64decode(result, validate=True)) as buffer:
            with Image.open(buffer) as decoded:
                self.assertEqual(decoded.getpixel((0, 0)), (255, 0, 0, 0))

    def test_cmyk_jpeg_can_be_converted_to_png(self):
        source = self.make_image("CMYK", (0, 100, 50, 0), image_format="JPEG")
        result = encode_image(source)
        with BytesIO(base64.b64decode(result, validate=True)) as buffer:
            with Image.open(buffer) as decoded:
                self.assertEqual(decoded.format, "PNG")
                self.assertEqual(decoded.mode, "RGBA")
                self.assertEqual(decoded.size, (16, 12))

    def test_reject_wrong_input_types(self):
        for value in (None, "screenshot.png", bytearray(b"image"), 123):
            with self.subTest(value=value):
                with self.assertRaises(TypeError):
                    encode_image(value)

    def test_reject_empty_and_unrecognized_data(self):
        for value in (b"", b"not an image", b"\x89PNG\r\n\x1a\n"):
            with self.subTest(value=value):
                with self.assertRaisesRegex(ValueError, "valid PNG or JPEG"):
                    encode_image(value)

    def test_reject_truncated_images(self):
        for image_format in ("PNG", "JPEG"):
            with self.subTest(image_format=image_format):
                source = self.make_image(image_format=image_format)
                with self.assertRaisesRegex(ValueError, "valid PNG or JPEG"):
                    encode_image(source[:len(source) // 2])

    def test_reject_unsupported_input_formats(self):
        for image_format in ("GIF", "BMP"):
            with self.subTest(image_format=image_format):
                with self.assertRaisesRegex(ValueError, "valid PNG or JPEG"):
                    encode_image(self.make_image(image_format=image_format))

    def test_reject_unsupported_output_formats(self):
        source = self.make_image()
        for image_format in ("gif", "jpg", "PNG", "", None, []):
            with self.subTest(image_format=image_format):
                with self.assertRaisesRegex(ValueError, "image_format"):
                    encode_image(source, image_format=image_format)

    def test_reject_invalid_quality_for_both_formats(self):
        source = self.make_image()
        for image_format in ("png", "jpeg"):
            for quality in (0, 96, True, 85.0, "85", None):
                with self.subTest(image_format=image_format, quality=quality):
                    with self.assertRaisesRegex(ValueError, "quality"):
                        encode_image(source, image_format=image_format, quality=quality)

    def test_accept_quality_bounds(self):
        source = self.make_image()
        for quality in (1, 95):
            with self.subTest(quality=quality):
                result = encode_image(source, image_format="jpeg", quality=quality)
                with BytesIO(base64.b64decode(result, validate=True)) as buffer:
                    with Image.open(buffer) as decoded:
                        decoded.load()
                        self.assertEqual(decoded.format, "JPEG")

    def test_pillow_image_size_limits_remain_enabled(self):
        source = self.make_image()
        with patch.object(Image, "MAX_IMAGE_PIXELS", 10):
            with self.assertRaisesRegex(ValueError, "valid PNG or JPEG"):
                encode_image(source)


if __name__ == "__main__":
    unittest.main()
