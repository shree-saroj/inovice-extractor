import io
import os
from pathlib import Path
from typing import BinaryIO, Optional, Tuple

import magic
from fastapi import HTTPException
from PIL import Image


class FileHandler:
    """Handle file upload, validation, and preprocessing"""

    # Supported file extensions
    SUPPORTED_EXTENSIONS = {
        "image": [".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp", ".tiff"],
        "document": [".pdf", ".docx", ".doc"],
        "spreadsheet": [".xlsx", ".xls", ".csv"],
    }

    # Supported MIME types
    SUPPORTED_MIME_TYPES = {
        "image": [
            "image/png",
            "image/jpeg",
            "image/gif",
            "image/bmp",
            "image/webp",
            "image/tiff",
        ],
        "document": [
            "application/pdf",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "application/msword",
        ],
        "spreadsheet": [
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "application/vnd.ms-excel",
            "text/csv",
        ],
    }

    # Max file size (50MB)
    MAX_FILE_SIZE = 50 * 1024 * 1024

    # Min file size (1KB)
    MIN_FILE_SIZE = 1 * 1024

    def __init__(self):
        self.mime = magic.Magic(mime=True)

    def validate_file_size(self, file_size: int) -> bool:
        """Validate file size is within limits"""
        if file_size < self.MIN_FILE_SIZE:
            raise HTTPException(
                status_code=400,
                detail=f"File too small. Minimum size: {self.MIN_FILE_SIZE // 1024}KB",
            )

        if file_size > self.MAX_FILE_SIZE:
            raise HTTPException(
                status_code=400,
                detail=f"File too large. Maximum size: {self.MAX_FILE_SIZE // 1024 // 1024}MB",
            )

        return True

    def get_file_extension(self, filename: str) -> str:
        """Get lowercase file extension"""
        return Path(filename).suffix.lower()

    def detect_file_type(self, file_bytes: bytes) -> str:
        """Detect file type using magic bytes"""
        mime_type = self.mime.from_buffer(file_bytes)

        if any(
            img_mime in mime_type for img_mime in self.SUPPORTED_MIME_TYPES["image"]
        ):
            return "image"
        elif any(
            doc_mime in mime_type for doc_mime in self.SUPPORTED_MIME_TYPES["document"]
        ):
            return "document"
        elif any(
            sheet_mime in mime_type
            for sheet_mime in self.SUPPORTED_MIME_TYPES["spreadsheet"]
        ):
            return "spreadsheet"
        else:
            return "unknown"

    def validate_file_type(self, filename: str, file_bytes: bytes) -> Tuple[str, str]:
        """
        Validate file type by extension and MIME type

        Returns:
            Tuple of (file_category, extension)
        """
        extension = self.get_file_extension(filename)

        # Validate by extension
        file_category = None
        for category, extensions in self.SUPPORTED_EXTENSIONS.items():
            if extension in extensions:
                file_category = category
                break

        if not file_category:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file extension: {extension}. Supported: {self.get_supported_extensions()}",
            )

        # Validate by MIME type (more reliable)
        detected_type = self.detect_file_type(file_bytes)

        if detected_type == "unknown":
            raise HTTPException(
                status_code=400,
                detail=f"Could not detect file type. Please ensure file is not corrupted.",
            )

        # Warning if extension doesn't match content
        if detected_type != file_category:
            print(
                f"⚠️ Warning: Extension ({file_category}) doesn't match content ({detected_type})"
            )

        return detected_type, extension

    def get_supported_extensions(self) -> str:
        """Get string of all supported extensions"""
        all_exts = []
        for category, extensions in self.SUPPORTED_EXTENSIONS.items():
            all_exts.extend(extensions)
        return ", ".join(all_exts)

    def validate_filename(self, filename: str) -> bool:
        """Validate filename is safe and valid"""
        if not filename:
            raise HTTPException(status_code=400, detail="No filename provided")

        # Check for path traversal attacks
        if ".." in filename or "/" in filename or "\\" in filename:
            raise HTTPException(status_code=400, detail="Invalid filename")

        # Check length
        if len(filename) > 255:
            raise HTTPException(status_code=400, detail="Filename too long")

        return True

    async def read_file(self, file) -> Tuple[bytes, str]:
        """
        Read uploaded file and return content with filename

        Args:
            file: FastAPI UploadFile object

        Returns:
            Tuple of (file_bytes, filename)
        """
        filename = file.filename
        self.validate_filename(filename)

        content = await file.read()
        self.validate_file_size(len(content))

        # Validate file type
        file_type, extension = self.validate_file_type(filename, content)

        return content, filename, file_type

    def convert_to_image(self, file_bytes: bytes, file_type: str) -> Image.Image:
        """
        Convert supported file to PIL Image

        Args:
            file_bytes: Raw file content
            file_type: Detected file type category

        Returns:
            PIL Image object
        """
        try:
            if file_type == "image":
                return Image.open(io.BytesIO(file_bytes)).convert("RGB")

            elif file_type == "document":
                # For PDF, use pdf2image (handled separately)
                raise ValueError("PDF conversion requires pdf2image library")

            else:
                raise ValueError(f"Cannot convert {file_type} to image")

        except Exception as e:
            raise HTTPException(
                status_code=400, detail=f"Failed to convert file to image: {str(e)}"
            )

    def save_temporarily(
        self, file_bytes: bytes, filename: str, directory: str = "/tmp"
    ) -> str:
        """
        Save file temporarily for processing

        Args:
            file_bytes: Raw file content
            filename: Original filename
            directory: Directory to save file

        Returns:
            Path to saved file
        """
        import uuid
        from datetime import datetime

        # Create unique filename
        unique_id = uuid.uuid4().hex
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_filename = f"{timestamp}_{unique_id}_{Path(filename).name}"

        # Ensure directory exists
        os.makedirs(directory, exist_ok=True)

        # Save file
        file_path = os.path.join(directory, safe_filename)

        with open(file_path, "wb") as f:
            f.write(file_bytes)

        return file_path

    def cleanup_temp_file(self, file_path: str) -> bool:
        """Remove temporary file"""
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                return True
            return False
        except Exception as e:
            print(f"Failed to cleanup temp file {file_path}: {e}")
            return False

    def get_file_info(self, file_bytes: bytes, filename: str) -> dict:
        """Get detailed file information"""
        return {
            "filename": filename,
            "extension": self.get_file_extension(filename),
            "size_bytes": len(file_bytes),
            "size_kb": round(len(file_bytes) / 1024, 2),
            "size_mb": round(len(file_bytes) / 1024 / 1024, 2),
            "mime_type": self.mime.from_buffer(file_bytes),
            "detected_type": self.detect_file_type(file_bytes),
        }


# Singleton instance
file_handler = FileHandler()


# Utility functions for easy import
async def validate_upload(file) -> Tuple[bytes, str, str]:
    """Validate and read uploaded file"""
    return await file_handler.read_file(file)


def get_file_info(file_bytes: bytes, filename: str) -> dict:
    """Get file information"""
    return file_handler.get_file_info(file_bytes, filename)


def save_temp(file_bytes: bytes, filename: str) -> str:
    """Save file temporarily"""
    return file_handler.save_temporarily(file_bytes, filename)


def cleanup_temp(file_path: str) -> bool:
    """Cleanup temporary file"""
    return file_handler.cleanup_temp_file(file_path)
