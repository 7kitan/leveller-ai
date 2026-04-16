"""
Tests cho gap_v3: PII Masker + LLM Helpers.
"""

import pytest

import sys, os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

# Import directly from module file to avoid langgraph chain (DLL issue on Python 3.9)
import importlib.util

_spec = importlib.util.spec_from_file_location(
    "pii_masker",
    os.path.join(
        os.path.dirname(__file__),
        "..",
        "worker",
        "langgraph_agents",
        "gap_v3",
        "utils",
        "pii_masker.py",
    ),
)
_pii_mod = importlib.util.module_from_spec(_spec)
sys.modules["pii_masker"] = _pii_mod
_spec.loader.exec_module(_pii_mod)

mask_pii = _pii_mod.mask_pii
mask_work_history = _pii_mod.mask_work_history
get_pii_masking_stats = _pii_mod.get_pii_masking_stats


class TestPIIMasker:
    """Test cases cho PII masking."""

    def test_mask_email(self):
        text = "Contact me at john.doe@example.com for more info"
        result = mask_pii(text)
        assert "[EMAIL]" in result
        assert "john.doe@example.com" not in result

    def test_mask_vietnamese_phone(self):
        text = "Gọi cho tôi: 0912345678 hoặc 01234567890"
        result = mask_pii(text)
        assert "[PHONE]" in result
        assert "0912345678" not in result

    def test_mask_generic_phone(self):
        text = "Call: +1-800-555-0100"
        result = mask_pii(text)
        assert "[PHONE]" in result

    def test_mask_url(self):
        text = (
            "My LinkedIn: https://linkedin.com/in/johndoe and site: http://my-site.com"
        )
        result = mask_pii(text)
        assert "[PERSONAL_LINK]" in result

    def test_mask_dob(self):
        text = "Born: 01/15/1995"
        result = mask_pii(text)
        assert "[DATE_OF_BIRTH]" in result

    def test_empty_string(self):
        assert mask_pii("") == ""
        assert mask_pii(None) is None

    def test_no_pii(self):
        text = "I have 5 years experience with Python and Django"
        result = mask_pii(text)
        assert text == result  # No changes

    def test_mask_work_history(self):
        work_history = [
            {
                "position": "Backend Engineer",
                "company": "Tech Corp",
                "description": "Email: hr@techcorp.com, call 0912345678",
                "duration_years": 2,
            }
        ]
        result = mask_work_history(work_history)
        assert "[EMAIL]" in result[0]["description"]
        assert "[PHONE]" in result[0]["description"]

    def test_get_pii_stats(self):
        before = "Contact: john@example.com, phone: 0912345678"
        after = mask_pii(before)
        stats = get_pii_masking_stats(before, after)

        assert stats["emails_masked"] == 1
        assert stats["chars_removed"] > 0

    def test_preserve_non_pii(self):
        text = "Python 5 years, Django 3 years, PostgreSQL 4 years"
        result = mask_pii(text)
        assert "Python" in result
        assert "Django" in result
        assert "PostgreSQL" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
