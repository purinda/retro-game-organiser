"""
ROM directory scanner.

Scans ROM set directories and builds a structured index of all ROM files
organized by system.
"""

import os
from pathlib import Path
from dataclasses import dataclass
from typing import Iterator

from .normalizer import parse_game_filename, GameInfo


@dataclass
class RomFile:
    """Represents a ROM file with its metadata."""
    
    path: Path  # Full path to the ROM file
    filename: str  # Original filename
    system_key: str  # System folder name (e.g., 'psp', 'amiga500')
    game_info: GameInfo  # Parsed game information
    
    @property
    def extension(self) -> str:
        """Get the file extension."""
        return self.path.suffix.lower()
    
    @property
    def normalized_name(self) -> str:
        """Get the base game name (for display)."""
        return self.game_info.base_name
    
    @property
    def dedup_key(self) -> str:
        """Get the deduplication key (includes region/version)."""
        return self.game_info.dedup_key
    
    @property
    def similarity_key(self) -> str:
        """Get the similarity key (just base name, for grouping)."""
        return self.game_info.similarity_key
    
    @property
    def clean_filename(self) -> str:
        """Get the cleaned filename (prefix removed)."""
        return self.game_info.clean_filename


def scan_rom_directory(source_dir: Path) -> Iterator[RomFile]:
    """
    Scan a ROM set directory and yield RomFile objects.
    
    Expected structure:
        source_dir/
            system_name/
                game.ext
                [optional_subdir/]
                    game.ext
    
    Args:
        source_dir: Path to the ROM set root directory
        
    Yields:
        RomFile objects for each ROM found
    """
    source_dir = Path(source_dir)
    
    if not source_dir.exists():
        raise FileNotFoundError(f"ROM directory not found: {source_dir}")
    
    if not source_dir.is_dir():
        raise NotADirectoryError(f"Not a directory: {source_dir}")
    
    # Iterate through system folders
    for system_folder in source_dir.iterdir():
        if not system_folder.is_dir():
            continue
        
        system_key = system_folder.name
        
        # Skip hidden folders and special directories
        if system_key.startswith('.') or system_key.startswith('_'):
            continue
        
        # Recursively find all files in the system folder
        for root, dirs, files in os.walk(system_folder):
            # Skip hidden directories
            dirs[:] = [d for d in dirs if not d.startswith('.') and not d.startswith('_')]
            
            for filename in files:
                # Skip hidden files and info files
                if filename.startswith('.') or filename.startswith('_'):
                    continue
                
                filepath = Path(root) / filename
                
                yield RomFile(
                    path=filepath,
                    filename=filename,
                    system_key=system_key,
                    game_info=parse_game_filename(filename),
                )


def scan_multiple_directories(source_dirs: list[Path]) -> Iterator[RomFile]:
    """
    Scan multiple ROM set directories.
    
    Args:
        source_dirs: List of paths to ROM set directories
        
    Yields:
        RomFile objects from all directories
    """
    for source_dir in source_dirs:
        yield from scan_rom_directory(source_dir)


def group_by_system(roms: Iterator[RomFile]) -> dict[str, list[RomFile]]:
    """
    Group ROM files by their system key.
    
    Args:
        roms: Iterator of RomFile objects
        
    Returns:
        Dictionary mapping system_key -> list of RomFile
    """
    result: dict[str, list[RomFile]] = {}
    
    for rom in roms:
        if rom.system_key not in result:
            result[rom.system_key] = []
        result[rom.system_key].append(rom)
    
    return result
