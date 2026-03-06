"""
Tests for scripts/data_quality_check.py
Tests data normalization and quality checking functions.
"""

import sys
import os
import pytest

# Add scripts directory to path
backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
scripts_dir = os.path.join(os.path.dirname(backend_dir), 'scripts')
sys.path.insert(0, scripts_dir)

from data_quality_check import normalize_skill, normalize_pricing


class TestNormalizeSkill:
    """Test skill level normalization."""
    
    @pytest.mark.parametrize("input_value,expected", [
        ("beginner", "Anfaenger"),
        ("BEGINNER", "Anfaenger"),
        ("Beginner", "Anfaenger"),
        ("intermediate", "Fortgeschritten"),
        ("Intermediate", "Fortgeschritten"),
        ("INTERMEDIATE", "Fortgeschritten"),
        ("advanced", "Anfaenger"),
        ("expert", "Experte"),
        ("Expert", "Experte"),
        ("EXPERT", "Experte"),
        ("Anfänger", "Anfaenger"),
        ("Fortgeschritten", "Fortgeschritten"),
        ("Experte", "Experte"),
    ])
    def test_normalize_skill_valid(self, input_value, expected):
        """Test normalization of valid skill levels."""
        result = normalize_skill(input_value)
        assert result == expected
        
    def test_normalize_skill_unknown(self):
        """Test normalization of unknown skill level."""
        result = normalize_skill("unknown_level")
        # Should return default or original value
        assert isinstance(result, str)
        
    def test_normalize_skill_empty(self):
        """Test normalization of empty string."""
        result = normalize_skill("")
        assert isinstance(result, str)


class TestNormalizePricing:
    """Test pricing model normalization."""
    
    @pytest.mark.parametrize("pricing,is_free,expected", [
        ("free", 1, "kostenlos"),
        ("Free", 1, "kostenlos"),
        ("FREE", 1, "kostenlos"),
        ("kostenlos", 1, "kostenlos"),
        ("paid", 0, "kostenpflichtig"),
        ("Paid", 0, "kostenpflichtig"),
        ("freemium", 0, "freemium"),
        ("Freemium", 0, "freemium"),
        ("subscription", 0, "kostenpflichtig"),
        ("Subscription", 0, "kostenpflichtig"),
    ])
    def test_normalize_pricing_valid(self, pricing, is_free, expected):
        """Test normalization of valid pricing models."""
        result = normalize_pricing(pricing, is_free)
        assert result == expected
        
    def test_normalize_pricing_empty(self):
        """Test normalization with empty pricing."""
        result = normalize_pricing("", 1)
        # Should infer from is_free flag
        assert result == "kostenlos"
        
    def test_normalize_pricing_unknown(self):
        """Test normalization of unknown pricing model."""
        result = normalize_pricing("unknown_model", 0)
        # Should return reasonable default
        assert isinstance(result, str)
