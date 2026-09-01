import unittest
from io import BytesIO

from PIL import Image

from app.vehicles.image_validation import _process_image


def _encoded_image(image_format: str, *, multiple: bool = False) -> bytes:
    output = BytesIO()
    image = Image.new("RGB", (32, 48), "red")
    if multiple:
        second_image = Image.new("RGB", (32, 48), "blue")
        image.save(output, format=image_format, save_all=True, append_images=[second_image])
    else:
        image.save(output, format=image_format)
    return output.getvalue()


class SmartphoneImageTests(unittest.TestCase):
    def test_mpo_smartphone_jpeg_is_normalized_to_jpeg(self):
        processed = _process_image(_encoded_image("MPO", multiple=True))

        self.assertEqual(processed.content_type, "image/jpeg")
        self.assertEqual(processed.extension, "jpg")
        with Image.open(BytesIO(processed.content)) as image:
            self.assertEqual(image.format, "JPEG")
            self.assertEqual(image.size, (32, 48))

    def test_avif_smartphone_image_is_normalized_to_jpeg(self):
        processed = _process_image(_encoded_image("AVIF"))

        self.assertEqual(processed.content_type, "image/jpeg")
        with Image.open(BytesIO(processed.content)) as image:
            self.assertEqual(image.format, "JPEG")


if __name__ == "__main__":
    unittest.main()
