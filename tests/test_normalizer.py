"""
Unit tests for the game name normalizer.
"""

import pytest
from src.normalizer import (
    normalize_game_name, 
    get_normalized_key, 
    extract_region,
    parse_game_filename,
    get_dedup_key,
    get_similarity_key,
)


class TestNormalizeGameName:
    """Tests for normalize_game_name function."""
    
    def test_three_digit_prefix_removal(self):
        """Test removal of 3-digit numeric prefixes."""
        assert normalize_game_name("005 Go Go Ackman.zip") == "Go Go Ackman"
        assert normalize_game_name("049 Shining the Holy Ark.bin") == "Shining the Holy Ark"
        assert normalize_game_name("001 Some Game.iso") == "Some Game"
        
    def test_parenthetical_suffix_removal(self):
        """Test removal of parenthetical suffixes like (USA), (Japan)."""
        assert normalize_game_name("Bomberman Wars (Japan).bin") == "Bomberman Wars"
        assert normalize_game_name("Super Mario (USA).zip") == "Super Mario"
        assert normalize_game_name("Game (Europe).rom") == "Game"
        
    def test_combined_prefix_and_suffix(self):
        """Test removal of both prefix and suffix."""
        assert normalize_game_name("049 Shining the Holy Ark (USA).bin") == "Shining the Holy Ark"
        assert normalize_game_name("001 3DConstructionKit (USA).lha") == "3DConstructionKit"
        
    def test_multiple_parentheses(self):
        """Test removal of multiple parenthetical groups."""
        assert normalize_game_name("Game (USA) (Rev 1).zip") == "Game"
        assert normalize_game_name("Title (Japan) (Disc 1) (Proto).bin") == "Title"
        
    def test_no_prefix_no_suffix(self):
        """Test filenames without prefix or suffix."""
        assert normalize_game_name("3DConstructionKit.lha") == "3DConstructionKit"
        assert normalize_game_name("3DPool.lha") == "3DPool"
        assert normalize_game_name("SimpleGame.zip") == "SimpleGame"
        
    def test_bracket_removal(self):
        """Test removal of square bracket content like [!], [T+Eng]."""
        assert normalize_game_name("Game [!].nes") == "Game"
        assert normalize_game_name("Game (USA) [T+Eng].smc") == "Game"
        assert normalize_game_name("Title [h1][b1].zip") == "Title"
        
    def test_four_digit_number_preserved(self):
        """Test that 4+ digit numbers are NOT treated as prefixes."""
        assert normalize_game_name("1942.zip") == "1942"
        assert normalize_game_name("2048 Game.zip") == "2048 Game"
        
    def test_numbers_in_game_name(self):
        """Test that numbers within the game name are preserved."""
        assert normalize_game_name("005 Final Fantasy 7.zip") == "Final Fantasy 7"
        assert normalize_game_name("Streets of Rage 2 (USA).bin") == "Streets of Rage 2"
        
    def test_whitespace_handling(self):
        """Test proper whitespace handling."""
        assert normalize_game_name("001  Double Space.zip") == "Double Space"
        assert normalize_game_name("Game  (USA).bin") == "Game"


class TestParseGameFilename:
    """Tests for parse_game_filename function."""
    
    def test_basic_parsing(self):
        """Test basic filename parsing."""
        info = parse_game_filename("Game (USA).bin")
        assert info.base_name == "Game"
        assert info.region == "USA"
        assert info.original_filename == "Game (USA).bin"
        
    def test_prefix_removal(self):
        """Test that prefixes are removed in clean_filename."""
        info = parse_game_filename("001 Game (USA).bin")
        assert info.base_name == "Game"
        assert info.region == "USA"
        assert info.clean_filename == "Game (USA).bin"
        assert info.original_filename == "001 Game (USA).bin"
        
    def test_version_extraction(self):
        """Test version info extraction."""
        info = parse_game_filename("Game (EU) (Rev 1).bin")
        assert info.base_name == "Game"
        assert info.region == "EU"
        assert info.version is not None
        assert "Rev 1" in info.version
        
    def test_no_region(self):
        """Test files without region info."""
        info = parse_game_filename("SimpleGame.zip")
        assert info.base_name == "SimpleGame"
        assert info.region is None
        

class TestDedupKey:
    """Tests for dedup_key and similarity_key."""
    
    def test_same_region_same_dedup_key(self):
        """Test that same game+region produces same dedup key."""
        key1 = get_dedup_key("Game (USA).bin")
        key2 = get_dedup_key("001 Game (USA).zip")  # Different prefix and extension
        assert key1 == key2
        
    def test_different_regions_different_dedup_key(self):
        """Test that different regions produce DIFFERENT dedup keys."""
        key_usa = get_dedup_key("Game (USA).bin")
        key_eu = get_dedup_key("Game (Europe).bin")
        key_japan = get_dedup_key("Game (Japan).bin")
        
        # All should be different
        assert key_usa != key_eu
        assert key_usa != key_japan
        assert key_eu != key_japan
        
    def test_same_similarity_key(self):
        """Test that all region variants have the SAME similarity key."""
        sim_usa = get_similarity_key("Game (USA).bin")
        sim_eu = get_similarity_key("Game (Europe).bin")
        sim_japan = get_similarity_key("Game (Japan).bin")
        
        # All should be the same (same base game)
        assert sim_usa == sim_eu == sim_japan
        
    def test_user_example_different_regions(self):
        """Test the user's example: keep both Game (USA) and Game (EU)."""
        key1 = get_dedup_key("Game (USA).bin")
        key2 = get_dedup_key("Game (EU) Rev 1.bin")
        
        # These should be DIFFERENT (different regions = different games)
        assert key1 != key2
        
    def test_exact_duplicate_detection(self):
        """Test that exact duplicates (same region) are detected."""
        key1 = get_dedup_key("3DConstructionKit.lha")
        key2 = get_dedup_key("001 3DConstructionKit.lha")
        
        # These should be the SAME (exact duplicate, no region)
        assert key1 == key2


class TestGetNormalizedKey:
    """Tests for get_normalized_key function (case-insensitive matching)."""
    
    def test_lowercase_conversion(self):
        """Test that keys are lowercased."""
        assert get_normalized_key("Go Go Ackman.zip") == "go go ackman"
        assert get_normalized_key("SUPER MARIO.bin") == "super mario"
        
    def test_matching_different_cases(self):
        """Test that different cases produce the same key."""
        key1 = get_normalized_key("Super Mario Bros.zip")
        key2 = get_normalized_key("SUPER MARIO BROS.zip")
        key3 = get_normalized_key("super mario bros.zip")
        assert key1 == key2 == key3


class TestExtractRegion:
    """Tests for extract_region function."""
    
    def test_usa_region(self):
        """Test extraction of USA region."""
        assert extract_region("Game (USA).zip") == "USA"
        
    def test_japan_region(self):
        """Test extraction of Japan region."""
        assert extract_region("Game (Japan).bin") == "Japan"
        
    def test_europe_region(self):
        """Test extraction of Europe region."""
        assert extract_region("Game (Europe).rom") == "Europe"
        
    def test_no_region(self):
        """Test when no region is present."""
        assert extract_region("Game.zip") is None


class TestDuplicateDetection:
    """Integration tests for duplicate detection scenarios."""
    
    def test_user_example_duplicates(self):
        """Test the specific examples from the user's request."""
        # These should all have the same SIMILARITY key
        sim1 = get_similarity_key("3DConstructionKit.lha")
        sim2 = get_similarity_key("001 3DConstructionKit (USA).lha")
        assert sim1 == sim2, "These should be detected as similar games"
        
    def test_different_games(self):
        """Test that different games produce different keys."""
        key1 = get_normalized_key("3DPool.lha")
        key2 = get_normalized_key("3DGalax.lha")
        assert key1 != key2, "These should NOT be detected as duplicates"
