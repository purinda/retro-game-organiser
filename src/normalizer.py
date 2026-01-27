"""
Game name normalization for ROM deduplication.

Handles various ROM naming conventions to extract the core game name
and region/version info for duplicate detection purposes.
"""

import re
from pathlib import Path
from dataclasses import dataclass


@dataclass
class GameInfo:
    """Parsed game information from a ROM filename."""
    
    base_name: str  # Core game name without prefixes, regions, or versions
    region: str | None  # Region like USA, Japan, Europe
    version: str | None  # Version info like Rev 1, v1.1
    original_filename: str  # Original filename
    clean_filename: str  # Cleaned filename (prefix removed, but region/version preserved)
    
    @property
    def dedup_key(self) -> str:
        """
        Key for deduplication purposes.
        
        Includes base_name + region + version (all normalized).
        Files with same base name but different regions are NOT duplicates.
        """
        parts = [self.base_name.lower()]
        if self.region:
            parts.append(self.region.lower())
        if self.version:
            parts.append(self.version.lower())
        return "|".join(parts)
    
    @property
    def similarity_key(self) -> str:
        """
        Key for identifying similar/related games.
        
        Just the base name - used to group games for consistent naming.
        """
        return self.base_name.lower()


# Common region patterns
REGION_PATTERNS = [
    r'USA', r'U', r'US',
    r'Japan', r'J', r'JP', r'JPN',
    r'Europe', r'E', r'EU', r'EUR',
    r'World', r'W',
    r'Korea', r'K', r'KR',
    r'China', r'C', r'CN',
    r'France', r'F', r'FR',
    r'Germany', r'G', r'DE',
    r'Spain', r'S', r'ES',
    r'Italy', r'I', r'IT',
    r'Australia', r'A', r'AU',
    r'Brazil', r'B', r'BR',
    r'Asia', r'As',
    r'En', r'Ja', r'Fr', r'De', r'Es', r'It', r'Ko', r'Zh',
]

# Common version patterns
VERSION_PATTERNS = [
    r'Rev\s*\d+',
    r'Rev\s*[A-Z]',
    r'v\d+\.?\d*',
    r'Ver\s*\d+\.?\d*',
    r'Proto',
    r'Beta',
    r'Demo',
    r'Sample',
    r'Disc\s*\d+',
    r'Disk\s*\d+',
]


def _extract_parenthetical_info(name: str) -> tuple[list[str], list[str], str]:
    """
    Extract region and version info from parenthetical content.
    
    Returns:
        Tuple of (regions, versions, cleaned_name)
    """
    regions = []
    versions = []
    
    # Find all parenthetical content
    paren_pattern = re.compile(r'\(([^)]+)\)')
    matches = paren_pattern.findall(name)
    
    for match in matches:
        match_content = match.strip()
        
        # Check if it's a region
        is_region = False
        for pattern in REGION_PATTERNS:
            if re.match(f'^{pattern}$', match_content, re.IGNORECASE):
                regions.append(match_content)
                is_region = True
                break
        
        if is_region:
            continue
            
        # Check if it's a version
        is_version = False
        for pattern in VERSION_PATTERNS:
            if re.search(pattern, match_content, re.IGNORECASE):
                versions.append(match_content)
                is_version = True
                break
        
        # If neither region nor version, treat as version (catch-all for misc info)
        if not is_version and not is_region:
            versions.append(match_content)
    
    return regions, versions, name


def parse_game_filename(filename: str) -> GameInfo:
    """
    Parse a ROM filename into its components.
    
    Extracts:
    - Base game name (without prefixes, regions, versions)
    - Region information (USA, Japan, Europe, etc.)
    - Version information (Rev 1, v1.1, Proto, etc.)
    
    Args:
        filename: The ROM filename (with or without path)
        
    Returns:
        GameInfo with parsed components
    """
    original = Path(filename).name
    name = Path(filename).stem
    extension = Path(filename).suffix
    
    # Remove leading 3-digit prefix with trailing space(s)
    clean_name = re.sub(r'^\d{3}\s+', '', name)
    
    # Extract region and version info
    regions, versions, _ = _extract_parenthetical_info(clean_name)
    
    # Get base name by removing all parenthetical and bracket content
    base_name = re.sub(r'\s*\([^)]*\)', '', clean_name)
    base_name = re.sub(r'\s*\[[^\]]*\]', '', base_name)
    base_name = re.sub(r'\s+', ' ', base_name).strip()
    
    # Build clean filename (prefix removed, but region/version preserved)
    clean_filename = clean_name + extension
    
    return GameInfo(
        base_name=base_name,
        region=regions[0] if regions else None,
        version=" - ".join(versions) if versions else None,
        original_filename=original,
        clean_filename=clean_filename,
    )


def normalize_game_name(filename: str) -> str:
    """
    Normalize a ROM filename for duplicate detection.
    
    This function extracts the core game name by:
    1. Removing the file extension
    2. Stripping leading 3-digit numeric prefixes (e.g., "001 ", "049 ")
    3. Removing parenthetical suffixes like (USA), (Japan), (Rev 1), etc.
    4. Cleaning up whitespace
    
    Examples:
        "005 Go Go Ackman.zip" → "Go Go Ackman"
        "Bomberman Wars (Japan).bin" → "Bomberman Wars"
        "049 Shining the Holy Ark (USA).bin" → "Shining the Holy Ark"
        "3DConstructionKit.lha" → "3DConstructionKit"
        "001 3DConstructionKit (USA).lha" → "3DConstructionKit"
    
    Args:
        filename: The ROM filename (with or without path)
        
    Returns:
        Normalized game name for comparison
    """
    info = parse_game_filename(filename)
    return info.base_name


def get_normalized_key(filename: str) -> str:
    """
    Get a case-insensitive key for duplicate detection.
    
    This returns a lowercase version of the normalized name
    for more aggressive duplicate matching.
    
    Args:
        filename: The ROM filename
        
    Returns:
        Lowercase normalized name
    """
    return normalize_game_name(filename).lower()


def get_dedup_key(filename: str) -> str:
    """
    Get the full deduplication key including region/version.
    
    Files with same base name but different regions are NOT duplicates.
    
    Args:
        filename: The ROM filename
        
    Returns:
        Dedup key in format "basename|region|version"
    """
    info = parse_game_filename(filename)
    return info.dedup_key


def get_similarity_key(filename: str) -> str:
    """
    Get the similarity key for grouping related games.
    
    Used for consistent naming across region variants.
    
    Args:
        filename: The ROM filename
        
    Returns:
        Similarity key (just the base name, lowercase)
    """
    info = parse_game_filename(filename)
    return info.similarity_key


def extract_region(filename: str) -> str | None:
    """
    Extract the region from a ROM filename if present.
    
    Common regions: USA, Japan, Europe, World, etc.
    
    Args:
        filename: The ROM filename
        
    Returns:
        Region string or None if not found
    """
    info = parse_game_filename(filename)
    return info.region
