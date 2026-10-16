import base64
import io
import unittest
from unittest.mock import AsyncMock, patch

import httpx
from PIL import Image

from app.extractors.vision_extractor import VisionExtractor
from app.main import app


class PipelineTests(unittest.IsolatedAsyncioTestCase):
    async def test_printed_text_bypasses_generative_vision(self):
        extractor = VisionExtractor()
        extractor._extract_printed_text = AsyncMock(return_value="Invoice INV-001 total 113")
        extractor.client.chat = AsyncMock()
        buffer = io.BytesIO()
        Image.new("RGB", (10, 10)).save(buffer, format="PNG")
        self.assertEqual(await extractor.extract_from_image(buffer.getvalue()), "Invoice INV-001 total 113")
        extractor.client.chat.assert_not_awaited()

    async def test_pdf_pages_are_encoded_images(self):
        extractor = VisionExtractor()
        extractor._extract_printed_text = AsyncMock(return_value="")
        extractor.client.chat = AsyncMock(
            return_value={"message": {"content": "Invoice INV-001 total 100"}}
        )
        page = Image.new("RGB", (200, 100), "white")
        with patch("app.extractors.vision_extractor.convert_from_bytes", return_value=[page, page]):
            result = await extractor.extract_from_pdf(b"pdf")
        self.assertIn("PAGE 2", result)
        self.assertEqual(extractor.client.chat.await_count, 2)
        for call in extractor.client.chat.call_args_list:
            encoded = call.kwargs["messages"][0]["images"][0]
            Image.open(io.BytesIO(base64.b64decode(encoded))).verify()

    async def test_unsupported_architecture_has_recovery_steps(self):
        extractor = VisionExtractor(model="llama3.2-vision")
        extractor._extract_printed_text = AsyncMock(return_value="")
        extractor.client.chat = AsyncMock(
            side_effect=Exception("unknown model architecture: 'mllama'")
        )
        buffer = io.BytesIO()
        Image.new("RGB", (10, 10)).save(buffer, format="PNG")
        with self.assertRaisesRegex(RuntimeError, "ollama pull llava"):
            await extractor.extract_from_image(buffer.getvalue())

    async def test_stage_two_failure_preserves_raw_output_when_requested(self):
        from app import main
        with patch.object(main.vision_extractor, "extract", AsyncMock(return_value="Invoice INV-001 total 100")), patch.object(
            main.structure_extractor, "structure", AsyncMock(side_effect=RuntimeError("model failed"))
        ):
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
                result = await client.post("/extract?include_raw=true", files={"file": ("invoice.png", b"image")})
                self.assertFalse(result.json()["success"])
                self.assertEqual(result.json()["stage1_output"], "Invoice INV-001 total 100")
                result = await client.post("/extract", files={"file": ("invoice.png", b"image")})
                self.assertIsNone(result.json()["stage1_output"])

    async def test_health_checks_presence_without_inference(self):
        from app import main
        models = {"models": [{"model": f"{main.vision_extractor.model}:latest"}, {"model": f"{main.structure_extractor.model}:latest"}]}
        with patch.object(main.vision_extractor.client, "list", AsyncMock(return_value=models)), patch.object(
            main.vision_extractor.client, "chat", AsyncMock()
        ) as chat:
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
                result = await client.get("/health")
            self.assertEqual(result.json()["status"], "healthy")
            chat.assert_not_awaited()


if __name__ == "__main__":
    unittest.main()
