"""
Thumbnail downloader for Libretro Thumbnails Server.

Downloads box art, screenshots, and title screens from:
https://github.com/libretro-thumbnails
"""

import urllib.request
import urllib.parse
import urllib.error
from pathlib import Path
from dataclasses import dataclass, field
from typing import Callable

from .systems import get_libretro_system_name, get_system_info
from .normalizer import parse_game_filename


# Base URL for Libretro thumbnails (raw GitHub content)
LIBRETRO_BASE_URL = "https://raw.githubusercontent.com/libretro-thumbnails"

# Thumbnail type mapping
THUMBNAIL_TYPES = {
    "boxart": "Named_Boxarts",
    "snap": "Named_Snaps",
    "title": "Named_Titles",
}

# Characters that need to be replaced in filenames for Libretro URLs
# See: https://docs.libretro.com/guides/roms-playlists-thumbnails/
LIBRETRO_INVALID_CHARS = '&*/:`<>?\\|"'


@dataclass
class ThumbnailResult:
    """Results from a thumbnail download operation."""

    downloaded: int = 0
    skipped_existing: int = 0
    skipped_not_found: int = 0
    skipped_no_mapping: int = 0
    errors: list[str] = field(default_factory=list)
    downloaded_files: list[tuple[str, str, str]] = field(
        default_factory=list
    )  # (system, game, path)


@dataclass
class ThumbnailOptions:
    """Options for thumbnail downloading."""

    dry_run: bool = False
    verbose: bool = False
    thumbnail_type: str = "boxart"  # boxart, snap, or title
    overwrite: bool = False
    progress_callback: Callable[[str], None] | None = None
    systems_filter: list[str] | None = None


def sanitize_for_libretro(filename: str) -> str:
    """
    Convert a filename to Libretro-compatible format.

    Libretro replaces certain characters with underscores in their thumbnail filenames.

    Args:
        filename: The original filename (without extension)

    Returns:
        Sanitized filename for Libretro URL
    """
    result = filename
    for char in LIBRETRO_INVALID_CHARS:
        result = result.replace(char, "_")
    return result


def get_thumbnail_url(system_key: str, game_name: str, thumbnail_type: str) -> str | None:
    """
    Build the URL for a game's thumbnail on the Libretro server.

    Args:
        system_key: Our system key (e.g., 'gb', 'gba')
        game_name: The game name (without extension, with region info)
        thumbnail_type: Type of thumbnail ('boxart', 'snap', 'title')

    Returns:
        Full URL to the thumbnail, or None if system not mapped
    """
    libretro_system = get_libretro_system_name(system_key)
    if not libretro_system:
        return None

    libretro_type = THUMBNAIL_TYPES.get(thumbnail_type, "Named_Boxarts")
    sanitized_name = sanitize_for_libretro(game_name)

    # URL encode the components
    encoded_system = urllib.parse.quote(libretro_system)
    encoded_name = urllib.parse.quote(sanitized_name)

    return f"{LIBRETRO_BASE_URL}/{encoded_system}/master/{libretro_type}/{encoded_name}.png"


class ThumbnailDownloader:
    """
    Downloads thumbnails for ROM files from Libretro Thumbnails Server.
    """

    def __init__(self, options: ThumbnailOptions | None = None):
        """
        Initialize the downloader.

        Args:
            options: Download options
        """
        self.options = options or ThumbnailOptions()
        self.result = ThumbnailResult()

    def _log(self, message: str) -> None:
        """Log a message if verbose mode is enabled."""
        if self.options.verbose and self.options.progress_callback:
            self.options.progress_callback(message)

    def _is_system_allowed(self, system_key: str) -> bool:
        """Check if a system is in the filter (if set)."""
        if self.options.systems_filter is None:
            return True

        system_info = get_system_info(system_key)
        if system_info:
            canonical_key = system_info[0].lower()
        else:
            canonical_key = system_key.lower()

        return canonical_key in self.options.systems_filter

    def _get_game_name_from_file(self, filepath: Path) -> str:
        """
        Extract the game name for Libretro lookup from a ROM filename.

        Uses the cleaned filename (prefix stripped) but keeps region/version info.
        Removes the file extension.

        Args:
            filepath: Path to the ROM file

        Returns:
            Game name suitable for Libretro thumbnail lookup
        """
        game_info = parse_game_filename(filepath.name)
        # Remove extension from clean filename
        clean_name = game_info.clean_filename
        return Path(clean_name).stem

    def _download_file(self, url: str, dest_path: Path) -> bool:
        """
        Download a file from URL to destination path.

        Args:
            url: URL to download from
            dest_path: Destination file path

        Returns:
            True if successful, False otherwise
        """
        try:
            # Create parent directory
            dest_path.parent.mkdir(parents=True, exist_ok=True)

            # Download the file
            with urllib.request.urlopen(url, timeout=30) as response:
                with open(dest_path, "wb") as f:
                    f.write(response.read())
            return True

        except urllib.error.HTTPError as e:
            if e.code == 404:
                return False  # Not found is expected for some games
            self.result.errors.append(f"HTTP error downloading {url}: {e}")
            return False
        except Exception as e:
            self.result.errors.append(f"Error downloading {url}: {e}")
            return False

    def download_for_directory(self, rom_dir: Path) -> ThumbnailResult:
        """
        Download thumbnails for all ROMs in a consolidated directory.

        Expected structure:
            rom_dir/
                system-Full Name/
                    Game1.ext
                    Game2.ext

        Output structure:
            rom_dir/
                system-Full Name/
                    images/
                        boxart/
                            Game1.png
                        ...

        Args:
            rom_dir: Path to the consolidated ROM directory

        Returns:
            ThumbnailResult with statistics
        """
        self._log(f"Scanning {rom_dir} for ROMs...")

        thumbnail_type = self.options.thumbnail_type
        type_folder = THUMBNAIL_TYPES.get(thumbnail_type, "Named_Boxarts").replace(
            "Named_", ""
        ).lower()

        # Iterate through system folders
        for system_folder in sorted(rom_dir.iterdir()):
            if not system_folder.is_dir():
                continue

            # Skip hidden and images folders
            if system_folder.name.startswith(".") or system_folder.name == "images":
                continue

            # Extract system key from folder name (format: "key-Full Name")
            folder_name = system_folder.name
            if "-" in folder_name:
                system_key = folder_name.split("-")[0]
            else:
                system_key = folder_name

            # Check filter
            if not self._is_system_allowed(system_key):
                continue

            # Check if system has Libretro mapping
            libretro_system = get_libretro_system_name(system_key)
            if not libretro_system:
                self._log(f"  Skipping {folder_name}: No Libretro mapping")
                continue

            self._log(f"Processing: {folder_name}")

            # Images destination
            images_dir = system_folder / "images" / type_folder

            # Scan ROM files
            for rom_file in sorted(system_folder.iterdir()):
                if not rom_file.is_file():
                    continue
                if rom_file.name.startswith("."):
                    continue

                # Get game name for lookup
                game_name = self._get_game_name_from_file(rom_file)
                dest_path = images_dir / f"{game_name}.png"

                # Check if already exists
                if dest_path.exists() and not self.options.overwrite:
                    self.result.skipped_existing += 1
                    self._log(f"    Exists: {game_name}.png")
                    continue

                # Build URL
                url = get_thumbnail_url(system_key, game_name, thumbnail_type)
                if not url:
                    self.result.skipped_no_mapping += 1
                    continue

                # Download (or simulate in dry run)
                if self.options.dry_run:
                    self._log(f"    Would download: {game_name}.png")
                    self._log(f"      URL: {url}")
                    self.result.downloaded += 1
                    self.result.downloaded_files.append(
                        (system_key, game_name, str(dest_path))
                    )
                else:
                    if self._download_file(url, dest_path):
                        self.result.downloaded += 1
                        self.result.downloaded_files.append(
                            (system_key, game_name, str(dest_path))
                        )
                        self._log(f"    Downloaded: {game_name}.png")
                    else:
                        self.result.skipped_not_found += 1
                        self._log(f"    Not found: {game_name}.png")

        return self.result


def download_thumbnails(
    rom_dir: Path,
    thumbnail_type: str = "boxart",
    dry_run: bool = False,
    verbose: bool = False,
    systems_filter: list[str] | None = None,
    progress_callback: Callable[[str], None] | None = None,
) -> ThumbnailResult:
    """
    Convenience function to download thumbnails.

    Args:
        rom_dir: Directory containing consolidated ROMs
        thumbnail_type: Type of thumbnail (boxart, snap, title)
        dry_run: If True, don't actually download files
        verbose: If True, print detailed progress
        systems_filter: Optional list of systems to process
        progress_callback: Optional callback for progress messages

    Returns:
        ThumbnailResult with statistics
    """
    if systems_filter:
        systems_filter = [s.lower() for s in systems_filter]

    options = ThumbnailOptions(
        dry_run=dry_run,
        verbose=verbose,
        thumbnail_type=thumbnail_type,
        systems_filter=systems_filter,
        progress_callback=progress_callback or (print if verbose else None),
    )

    downloader = ThumbnailDownloader(options)
    return downloader.download_for_directory(rom_dir)
