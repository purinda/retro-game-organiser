"""
ROM consolidation engine.

Handles deduplication and copying of ROM files to the output directory.
Now region-aware: files with same base name but different regions are kept.
"""

import shutil
from pathlib import Path
from dataclasses import dataclass, field
from typing import Callable

from .scanner import RomFile, scan_multiple_directories
from .systems import get_output_folder_name


@dataclass
class ConsolidationResult:
    """Results from a consolidation operation."""
    
    copied: int = 0
    skipped_duplicates: int = 0
    skipped_unknown_system: int = 0
    errors: list[str] = field(default_factory=list)
    copied_files: list[tuple[str, str, str]] = field(default_factory=list)  # (system, filename, dest)
    duplicate_files: list[tuple[str, str, str]] = field(default_factory=list)  # (system, filename, original)


@dataclass
class ConsolidationOptions:
    """Options for the consolidation process."""
    
    dry_run: bool = False
    verbose: bool = False
    overwrite: bool = False
    progress_callback: Callable[[str], None] | None = None


class Consolidator:
    """
    ROM file consolidator.
    
    Handles scanning, deduplication, and copying of ROM files
    to a consolidated output directory.
    
    Region-aware: keeps different region variants as unique games.
    E.g., "Game (USA).bin" and "Game (EU).bin" are both kept.
    """
    
    def __init__(self, output_dir: Path, options: ConsolidationOptions | None = None):
        """
        Initialize the consolidator.
        
        Args:
            output_dir: Path to the output directory
            options: Consolidation options
        """
        self.output_dir = Path(output_dir)
        self.options = options or ConsolidationOptions()
        
        # Track seen games: key is (normalized_system_key, dedup_key)
        # dedup_key includes region/version, so different regions are NOT duplicates
        self._seen: dict[tuple[str, str], RomFile] = {}
        
        self.result = ConsolidationResult()
    
    def _log(self, message: str) -> None:
        """Log a message if verbose mode is enabled."""
        if self.options.verbose and self.options.progress_callback:
            self.options.progress_callback(message)
    
    def _normalize_system_for_dedup(self, system_key: str) -> str:
        """
        Normalize system key for deduplication purposes.
        
        Maps equivalent systems to the same key (e.g., PSP and psp).
        """
        return system_key.lower()
    
    def _is_duplicate(self, rom: RomFile) -> RomFile | None:
        """
        Check if a ROM is a duplicate.
        
        Uses the full dedup_key which includes region/version.
        Files with same base name but different regions are NOT duplicates.
        
        Args:
            rom: The ROM file to check
            
        Returns:
            The original RomFile if duplicate, None otherwise
        """
        full_key = (
            self._normalize_system_for_dedup(rom.system_key),
            rom.dedup_key
        )
        
        return self._seen.get(full_key)
    
    def _mark_seen(self, rom: RomFile) -> None:
        """Mark a ROM as seen for deduplication."""
        full_key = (
            self._normalize_system_for_dedup(rom.system_key),
            rom.dedup_key
        )
        self._seen[full_key] = rom
    
    def _copy_rom(self, rom: RomFile) -> bool:
        """
        Copy a ROM file to the output directory.
        
        Uses the clean_filename (prefix removed, region/version preserved).
        
        Args:
            rom: The ROM file to copy
            
        Returns:
            True if successful, False otherwise
        """
        # Get the output folder name
        output_folder = get_output_folder_name(rom.system_key)
        dest_dir = self.output_dir / output_folder
        
        # Use clean filename (prefix removed, but region/version preserved)
        dest_filename = rom.clean_filename
        dest_path = dest_dir / dest_filename
        
        try:
            if not self.options.dry_run:
                # Create destination directory
                dest_dir.mkdir(parents=True, exist_ok=True)
                
                # Check if destination exists
                if dest_path.exists() and not self.options.overwrite:
                    self._log(f"  Skipping (exists): {dest_filename}")
                    return False
                
                # Copy the file
                shutil.copy2(rom.path, dest_path)
            
            self.result.copied += 1
            self.result.copied_files.append((rom.system_key, dest_filename, str(dest_path)))
            self._log(f"  Copied: {rom.filename} -> {output_folder}/{dest_filename}")
            return True
            
        except Exception as e:
            self.result.errors.append(f"Error copying {rom.path}: {e}")
            return False
    
    def consolidate(self, source_dirs: list[Path]) -> ConsolidationResult:
        """
        Consolidate ROM files from multiple source directories.
        
        Args:
            source_dirs: List of paths to ROM set directories
            
        Returns:
            ConsolidationResult with statistics
        """
        self._log(f"Scanning {len(source_dirs)} source directories...")
        
        # Process each ROM file
        for rom in scan_multiple_directories(source_dirs):
            # Check for duplicates (same base name + same region/version)
            original = self._is_duplicate(rom)
            
            if original:
                self.result.skipped_duplicates += 1
                self.result.duplicate_files.append(
                    (rom.system_key, rom.filename, original.filename)
                )
                self._log(f"  Duplicate: {rom.filename} (original: {original.filename})")
                continue
            
            # Mark as seen and copy
            self._mark_seen(rom)
            self._copy_rom(rom)
        
        return self.result


def consolidate_roms(
    source_dirs: list[Path],
    output_dir: Path,
    dry_run: bool = False,
    verbose: bool = False,
    progress_callback: Callable[[str], None] | None = None
) -> ConsolidationResult:
    """
    Convenience function to consolidate ROMs.
    
    Args:
        source_dirs: List of source ROM set directories
        output_dir: Output directory for consolidated ROMs
        dry_run: If True, don't actually copy files
        verbose: If True, print detailed progress
        progress_callback: Optional callback for progress messages
        
    Returns:
        ConsolidationResult with statistics
    """
    options = ConsolidationOptions(
        dry_run=dry_run,
        verbose=verbose,
        progress_callback=progress_callback or (print if verbose else None)
    )
    
    consolidator = Consolidator(output_dir, options)
    return consolidator.consolidate(source_dirs)
