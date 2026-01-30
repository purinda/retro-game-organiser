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
from .systems import get_output_folder_name, get_system_info


@dataclass
class ConsolidationResult:
    """Results from a consolidation operation."""

    copied: int = 0
    skipped_duplicates: int = 0
    skipped_existing: int = 0  # Files that already exist in output
    skipped_unknown_system: int = 0
    skipped_filtered: int = 0  # Files skipped due to systems filter
    errors: list[str] = field(default_factory=list)
    # (system, filename, dest, source_dir)
    copied_files: list[tuple[str, str, str, str]] = field(default_factory=list)
    # (system, filename, original)
    duplicate_files: list[tuple[str, str, str]] = field(default_factory=list)
    # Files that already existed in output
    existing_files: list[tuple[str, str]] = field(
        default_factory=list
    )  # (system, filename)


@dataclass
class ConsolidationOptions:
    """Options for the consolidation process."""

    dry_run: bool = False
    verbose: bool = False
    overwrite: bool = False
    progress_callback: Callable[[str], None] | None = None
    systems_filter: list[str] | None = None  # If set, only consolidate these systems


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

        Maps equivalent systems to the same canonical key (e.g., PSP, psp,
        "Sony PlayStation Portable" all become "psp").
        """
        # Get the canonical system info to normalize different naming conventions
        system_info = get_system_info(system_key)
        if system_info:
            return system_info[0].lower()  # Use canonical shorthand key
        return system_key.lower()  # Fall back to lowercase if unknown

    def _is_system_allowed(self, system_key: str) -> bool:
        """
        Check if a system is allowed by the current filter.

        Args:
            system_key: The system key from the ROM directory

        Returns:
            True if allowed, False if filtered out
        """
        if self.options.systems_filter is None:
            return True  # No filter, all systems allowed

        # Get the canonical system info
        system_info = get_system_info(system_key)
        if system_info is None:
            return False  # Unknown system, skip

        canonical_key = system_info[0].lower()
        return canonical_key in self.options.systems_filter

    def _is_duplicate(self, rom: RomFile) -> RomFile | str | None:
        """
        Check if a ROM is a duplicate.

        Uses the full dedup_key which includes region/version.
        Files with same base name but different regions are NOT duplicates.

        Args:
            rom: The ROM file to check

        Returns:
            The original RomFile or filename string if duplicate, None otherwise
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

    def _mark_existing(self, system_key: str, filename: str) -> None:
        """
        Mark an existing file in output as seen (for deduplication).

        Args:
            system_key: The system key from the output folder name
            filename: The filename in the output directory
        """
        from .normalizer import parse_game_filename

        game_info = parse_game_filename(filename)
        full_key = (self._normalize_system_for_dedup(system_key), game_info.dedup_key)
        # Create a minimal marker (we don't have full RomFile info)
        # Store the filename as a string instead of RomFile
        self._seen[full_key] = filename  # type: ignore

    def _scan_existing_output(self) -> None:
        """
        Scan the output directory for existing files and add them to seen set.

        This allows incremental consolidation - files already in output
        won't be copied again.
        """
        if not self.output_dir.exists():
            return

        self._log(f"Scanning output directory for existing files...")

        existing_count = 0
        for system_folder in self.output_dir.iterdir():
            if not system_folder.is_dir():
                continue

            # Extract system key from folder name (format: "key-Full Name")
            folder_name = system_folder.name
            if "-" in folder_name:
                system_key = folder_name.split("-")[0]
            else:
                system_key = folder_name

            # Scan files in this system folder
            for filepath in system_folder.iterdir():
                if filepath.is_file() and not filepath.name.startswith("."):
                    self._mark_existing(system_key, filepath.name)
                    self.result.existing_files.append((system_key, filepath.name))
                    existing_count += 1

        if existing_count > 0:
            self._log(f"  Found {existing_count} existing files in output directory")

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
            self.result.copied_files.append(
                (rom.system_key, dest_filename, str(dest_path), str(rom.source_root))
            )
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
        # First, scan output directory for existing files
        self._scan_existing_output()

        self._log(f"Scanning {len(source_dirs)} source directories...")

        # Process each ROM file
        for rom in scan_multiple_directories(source_dirs):
            # Check if system is allowed by filter
            if not self._is_system_allowed(rom.system_key):
                self.result.skipped_filtered += 1
                continue

            # Check for duplicates (same base name + same region/version)
            original = self._is_duplicate(rom)

            if original:
                # Check if it's an existing file (string) or input duplicate (RomFile)
                if isinstance(original, str):
                    # Already exists in output directory
                    self.result.skipped_existing += 1
                    self._log(
                        f"  Exists: {rom.filename} (already in output as: {original})"
                    )
                else:
                    # Duplicate from input directories
                    self.result.skipped_duplicates += 1
                    self.result.duplicate_files.append(
                        (rom.system_key, rom.filename, original.filename)
                    )
                    self._log(
                        f"  Duplicate: {rom.filename} (original: {original.filename})"
                    )
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
    progress_callback: Callable[[str], None] | None = None,
    systems_filter: list[str] | None = None,
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
    if systems_filter:
        systems_filter = [s.lower() for s in systems_filter]

    options = ConsolidationOptions(
        dry_run=dry_run,
        verbose=verbose,
        progress_callback=progress_callback or (print if verbose else None),
        systems_filter=systems_filter,
    )

    consolidator = Consolidator(output_dir, options)
    return consolidator.consolidate(source_dirs)
