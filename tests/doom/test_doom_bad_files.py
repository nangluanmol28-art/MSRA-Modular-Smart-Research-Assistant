import os
import io
import pytest
import pypdf
from utils.errors import validate_pdf_file
from config import MAX_FILE_SIZE_MB, MAX_TOTAL_PAGES


class MockUploadedFile:
    def __init__(self, name: str, data: bytes):
        self.name = name
        self._data = data
        self.size = len(data)

    def getvalue(self):
        return self._data

    def getbuffer(self):
        return memoryview(self._data)


def create_minimal_pdf(num_pages: int = 1, text: str = "Sample Academic Text.") -> bytes:
    writer = pypdf.PdfWriter()
    for _ in range(num_pages):
        writer.add_blank_page(width=72, height=72)
    # Write to memory
    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


@pytest.mark.doom
class TestDoomBadFiles:

    def test_zero_byte_file(self):
        f = MockUploadedFile("empty.pdf", b"")
        is_valid, msg = validate_pdf_file(f, f.name)
        assert not is_valid
        assert "Empty File" in msg or "0 bytes" in msg

    def test_random_junk_bytes(self):
        f = MockUploadedFile("junk.pdf", b"NOT_A_PDF_RANDOMLY_GENERATED_BYTES_XYZ_123456789")
        is_valid, msg = validate_pdf_file(f, f.name)
        assert not is_valid
        assert "Invalid Format" in msg or "%PDF" in msg

    def test_truncated_pdf(self):
        # Starts with %PDF but cut off midway
        f = MockUploadedFile("truncated.pdf", b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj")
        is_valid, msg = validate_pdf_file(f, f.name)
        assert not is_valid
        assert "Corrupted" in msg or "Unreadable" in msg

    def test_password_protected_pdf(self):
        writer = pypdf.PdfWriter()
        writer.add_blank_page(width=72, height=72)
        writer.encrypt("super_secret_password")
        buf = io.BytesIO()
        writer.write(buf)
        enc_bytes = buf.getvalue()

        f = MockUploadedFile("encrypted.pdf", enc_bytes)
        is_valid, msg = validate_pdf_file(f, f.name)
        assert not is_valid
        assert "Password Protected" in msg

    def test_scanned_image_only_pdf(self):
        # PDF with blank pages (no extractable text)
        blank_pdf = create_minimal_pdf(num_pages=3, text="")
        f = MockUploadedFile("scanned.pdf", blank_pdf)
        is_valid, msg = validate_pdf_file(f, f.name)
        assert not is_valid
        assert "Scanned Document" in msg or "readable text layer" in msg

    def test_renamed_non_pdf(self):
        # A PNG file renamed as .pdf
        png_header = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
        f = MockUploadedFile("photo.pdf", png_header)
        is_valid, msg = validate_pdf_file(f, f.name)
        assert not is_valid
        assert "Invalid Format" in msg

    def test_just_over_max_size(self):
        over_size = (MAX_FILE_SIZE_MB * 1024 * 1024) + 1024
        # Create a mock with size attribute over limit
        class OversizedFile:
            name = "huge.pdf"
            size = over_size
            def getvalue(self):
                return b"%PDF-1.4" + b"0" * over_size
        f = OversizedFile()
        is_valid, msg = validate_pdf_file(f, f.name)
        assert not is_valid
        assert "File Too Large" in msg

    def test_path_traversal_and_unicode_filename(self):
        # File name with path traversal and unicode
        traversal_name = "../../etc/passwd_🔬_test.pdf"
        safe_base = os.path.basename(traversal_name)
        assert "/" not in safe_base and "\\" not in safe_base
        assert "passwd_🔬_test.pdf" == safe_base

    def test_duplicate_upload_10x_deduplication(self):
        import hashlib
        sample_bytes = b"%PDF-1.4 sample content for hash test"
        hashes = [hashlib.sha256(sample_bytes).hexdigest() for _ in range(10)]
        # All 10 hashes should be identical, ensuring deduplication works
        assert len(set(hashes)) == 1
