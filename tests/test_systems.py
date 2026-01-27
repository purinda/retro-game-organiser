"""
Unit tests for the systems module.
"""

import pytest
from src.systems import (
    get_output_folder_name,
    get_system_info,
    normalize_system_key,
    is_known_system,
)


class TestNormalizeSystemKey:
    """Tests for normalize_system_key function."""
    
    def test_lowercase_conversion(self):
        """Test that keys are lowercased."""
        assert normalize_system_key("PSP") == "psp"
        assert normalize_system_key("Amiga500") == "amiga500"
        assert normalize_system_key("ARCADE") == "arcade"


class TestGetSystemInfo:
    """Tests for get_system_info function."""
    
    def test_exact_match(self):
        """Test exact key matching."""
        result = get_system_info("psp")
        assert result == ("psp", "Sony PlayStation Portable")
        
    def test_case_insensitive_match(self):
        """Test case-insensitive matching."""
        result = get_system_info("PSP")
        assert result is not None
        assert result[1] == "Sony PlayStation Portable"
        
    def test_uppercase_variant(self):
        """Test uppercase system variants."""
        result = get_system_info("ARCADE")
        assert result is not None
        assert "Arcade" in result[1]
        
    def test_unknown_system(self):
        """Test unknown system returns None."""
        result = get_system_info("unknown_system_xyz")
        assert result is None


class TestGetOutputFolderName:
    """Tests for get_output_folder_name function."""
    
    def test_psp_format(self):
        """Test PSP output folder format."""
        result = get_output_folder_name("psp")
        assert result == "psp-Sony PlayStation Portable"
        
    def test_amiga500_format(self):
        """Test Amiga 500 output folder format."""
        result = get_output_folder_name("amiga500")
        assert result == "amiga500-Commodore Amiga 500"
        
    def test_uppercase_input(self):
        """Test uppercase input systems."""
        result = get_output_folder_name("PSP")
        assert "Sony PlayStation Portable" in result
        
    def test_unknown_system_passthrough(self):
        """Test unknown systems are passed through unchanged."""
        result = get_output_folder_name("unknown_xyz")
        assert result == "unknown_xyz"


class TestIsKnownSystem:
    """Tests for is_known_system function."""
    
    def test_known_systems(self):
        """Test known systems return True."""
        assert is_known_system("psp") is True
        assert is_known_system("amiga500") is True
        assert is_known_system("snes") is True
        
    def test_unknown_systems(self):
        """Test unknown systems return False."""
        assert is_known_system("fake_system") is False
        assert is_known_system("not_real") is False
