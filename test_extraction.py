import json
from pathlib import Path

import requests

API_URL = "http://localhost:8000"


def test_extraction(file_path: str, include_raw: bool = False):
    """Test the extraction pipeline"""

    print(f"\n📄 Processing: {file_path}")
    print("=" * 60)

    with open(file_path, "rb") as f:
        response = requests.post(
            f"{API_URL}/extract",
            files={"file": (Path(file_path).name, f)},
            params={"include_raw": include_raw},
            timeout=300,  # 5 minute timeout for large files
        )

    result = response.json()

    if result["success"]:
        print("✅ Extraction Successful!")
        print("\n📋 Extracted Data:")
        print(json.dumps(result["data"], indent=2, default=str))

        if include_raw and result.get("stage1_output"):
            print("\n Raw Extraction (Stage 1):")
            print(result["stage1_output"][:500] + "...")

        return result["data"]
    else:
        print("❌ Extraction Failed!")
        print(f"Error: {result['error']}")
        return None


def test_health():
    """Check API health"""
    response = requests.get(f"{API_URL}/health")
    print("🏥 Health Check:", response.json())


def test_models():
    """List available models"""
    response = requests.get(f"{API_URL}/models")
    print("🤖 Available Models:", response.json())


if __name__ == "__main__":
    # Test health
    test_health()

    # List models
    test_models()

    # Test with your invoice
    test_extraction("invoice.png", include_raw=True)
