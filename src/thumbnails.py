"""
Thumbnail downloader for Libretro Thumbnails Server.

Downloads box art, screenshots, and title screens from:
https://github.com/libretro-thumbnails
"""

import json
import re
import urllib.request
import urllib.parse
import urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from dataclasses import dataclass, field
from typing import Callable
import threading

from .systems import get_libretro_system_name, get_system_info
from .normalizer import parse_game_filename


# Base URL for Libretro thumbnails (raw GitHub content)
LIBRETRO_BASE_URL = "https://raw.githubusercontent.com/libretro-thumbnails"
GITHUB_API_URL = "https://api.github.com/repos/libretro-thumbnails"

# Thumbnail type mapping
THUMBNAIL_TYPES = {
    "boxart": "Named_Boxarts",
    "snap": "Named_Snaps",
    "title": "Named_Titles",
}

# Characters that need to be replaced in filenames for Libretro URLs
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
    max_workers: int = 5  # Number of concurrent downloads


def normalize_for_matching(name: str) -> str:
    """
    Normalize a name for fuzzy matching.

    Removes all non-alphanumeric characters and lowercases.

    Args:
        name: The name to normalize

    Returns:
        Normalized string for comparison
    """
    return re.sub(r"[^a-z0-9]", "", name.lower())


def extract_base_name(name: str) -> str:
    """
    Extract the base name without region/version info.

    Removes content in parentheses and brackets.

    Args:
        name: The full name with region info

    Returns:
        Base name only
    """
    # Remove content in parentheses and brackets
    result = re.sub(r"\s*\([^)]*\)", "", name)
    result = re.sub(r"\s*\[[^\]]*\]", "", result)
    return result.strip()


def match_thumbnail(game_name: str, available_files: list[str]) -> str | None:
    """
    Find the best matching thumbnail from available files.

    Matching priority:
    1. Exact match (case-insensitive)
    2. Match base name (without region/version info)
    3. Match alphanumeric only (fuzzy)

    Args:
        game_name: The ROM game name (without extension)
        available_files: List of available thumbnail filenames (without .png)

    Returns:
        Best matching filename or None if no match found
    """
    if not available_files:
        return None

    game_name_lower = game_name.lower()
    game_base = extract_base_name(game_name)
    game_base_lower = game_base.lower()
    game_normalized = normalize_for_matching(game_name)
    game_base_normalized = normalize_for_matching(game_base)

    # Build lookup structures
    exact_lookup = {f.lower(): f for f in available_files}
    base_lookup = {extract_base_name(f).lower(): f for f in available_files}
    normalized_lookup = {normalize_for_matching(f): f for f in available_files}

    # Priority 1: Exact match (case-insensitive)
    if game_name_lower in exact_lookup:
        return exact_lookup[game_name_lower]

    # Priority 2: Base name match (same game, different region might work)
    if game_base_lower in base_lookup:
        return base_lookup[game_base_lower]

    # Priority 3: Normalized (alphanumeric only) match
    if game_normalized in normalized_lookup:
        return normalized_lookup[game_normalized]

    # Priority 4: Try base name normalized
    if game_base_normalized in normalized_lookup:
        return normalized_lookup[game_base_normalized]

    # Priority 5: Our base name matches server file's base name (both normalized)
    base_normalized_lookup = {
        normalize_for_matching(extract_base_name(f)): f for f in available_files
    }
    if game_base_normalized in base_normalized_lookup:
        return base_normalized_lookup[game_base_normalized]

    # Priority 6: Partial match - find files whose base name starts with our game name
    for avail in available_files:
        avail_base = extract_base_name(avail)
        avail_base_normalized = normalize_for_matching(avail_base)
        # Check if server file starts with our game name
        if avail_base_normalized.startswith(
            game_base_normalized
        ) or game_base_normalized.startswith(avail_base_normalized):
            return avail

    # Priority 7: Base name exact match (case-insensitive)
    for avail in available_files:
        avail_base = extract_base_name(avail)
        if avail_base.lower() == game_base_lower:
            return avail

    return None


class ThumbnailCache:
    """Cache for available thumbnails per system."""

    def __init__(self):
        self._cache: dict[str, list[str]] = {}
        self._errors: list[str] = []

    def get_available_files(
        self,
        libretro_system: str,
        thumbnail_type: str,
        verbose_callback: Callable[[str], None] | None = None,
    ) -> list[str]:
        """
        Get list of available thumbnails for a system.

        Uses GitHub Git Trees API to get all files (supports up to 100k entries).

        Args:
            libretro_system: Libretro system name (e.g., 'Nintendo_-_Game_Boy')
            thumbnail_type: Type of thumbnail ('boxart', 'snap', 'title')
            verbose_callback: Optional callback for progress messages

        Returns:
            List of available thumbnail filenames (without .png extension)
        """
        libretro_type = THUMBNAIL_TYPES.get(thumbnail_type, "Named_Boxarts")
        cache_key = f"{libretro_system}/{libretro_type}"

        if cache_key in self._cache:
            return self._cache[cache_key]

        # Use Git Trees API for complete file list
        # Format: /repos/{owner}/{repo}/git/trees/{branch}:{path}
        api_url = f"{GITHUB_API_URL}/{libretro_system}/git/trees/master:{libretro_type}"

        if verbose_callback:
            verbose_callback("    Fetching file list from server...")

        try:
            req = urllib.request.Request(
                api_url,
                headers={
                    "Accept": "application/vnd.github.v3+json",
                    "User-Agent": "retro-game-organiser",
                },
            )
            with urllib.request.urlopen(req, timeout=60) as response:
                data = json.loads(response.read().decode("utf-8"))

            # Extract filenames from tree (remove .png extension)
            files = []
            for item in data.get("tree", []):
                name = item.get("path", "")
                if name.endswith(".png"):
                    files.append(name[:-4])  # Remove .png

            self._cache[cache_key] = files

            if verbose_callback:
                verbose_callback(f"    Found {len(files)} thumbnails available")

            return files

        except urllib.error.HTTPError as e:
            if e.code == 404:
                self._cache[cache_key] = []
                return []
            self._errors.append(f"Error fetching {api_url}: {e}")
            return []
        except Exception as e:
            self._errors.append(f"Error fetching {api_url}: {e}")
            return []


class ThumbnailDownloader:
    """
    Downloads thumbnails for ROM files from Libretro Thumbnails Server.
    """

    def __init__(self, options: ThumbnailOptions | None = None):
        self.options = options or ThumbnailOptions()
        self.result = ThumbnailResult()
        self._cache = ThumbnailCache()
        self._lock = threading.Lock()  # For thread-safe result updates

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
        """Extract the game name for lookup from a ROM filename."""
        game_info = parse_game_filename(filepath.name)
        clean_name = game_info.clean_filename
        return Path(clean_name).stem

    def _download_file(self, url: str, dest_path: Path) -> tuple[bool, str | None]:
        """Download a file from URL to destination path."""
        try:
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            with urllib.request.urlopen(url, timeout=30) as response:
                with open(dest_path, "wb") as f:
                    f.write(response.read())
            return True, None
        except Exception as e:
            return False, f"Error downloading {url}: {e}"

    def _download_task(self, task: tuple) -> dict:
        """
        Execute a single download task.

        Args:
            task: Tuple of (system_key, game_name, url, dest_path, matched)

        Returns:
            Dict with result info
        """
        system_key, game_name, url, dest_path, matched = task
        success, error = self._download_file(url, Path(dest_path))

        return {
            "success": success,
            "error": error,
            "system_key": system_key,
            "game_name": game_name,
            "dest_path": dest_path,
            "matched": matched,
        }

    def _build_download_url(
        self, libretro_system: str, thumbnail_type: str, filename: str
    ) -> str:
        """Build the download URL for a matched thumbnail."""
        libretro_type = THUMBNAIL_TYPES.get(thumbnail_type, "Named_Boxarts")
        encoded_system = urllib.parse.quote(libretro_system)
        encoded_name = urllib.parse.quote(filename)
        return f"{LIBRETRO_BASE_URL}/{encoded_system}/master/{libretro_type}/{encoded_name}.png"

    def download_for_directory(self, rom_dir: Path) -> ThumbnailResult:
        """
        Download thumbnails for all ROMs in a consolidated directory.
        Uses concurrent downloads for faster processing.
        """
        self._log(f"Scanning {rom_dir} for ROMs...")

        thumbnail_type = self.options.thumbnail_type
        type_folder = THUMBNAIL_TYPES.get(thumbnail_type, "Named_Boxarts").replace(
            "Named_", ""
        ).lower()

        # Collect all download tasks first
        download_tasks = []

        # Iterate through system folders
        for system_folder in sorted(rom_dir.iterdir()):
            if not system_folder.is_dir():
                continue

            if system_folder.name.startswith(".") or system_folder.name == "images":
                continue

            # Extract system key
            folder_name = system_folder.name
            if "-" in folder_name:
                system_key = folder_name.split("-")[0]
            else:
                system_key = folder_name

            if not self._is_system_allowed(system_key):
                continue

            libretro_system = get_libretro_system_name(system_key)
            if not libretro_system:
                self._log(f"  Skipping {folder_name}: No Libretro mapping")
                continue

            self._log(f"Processing: {folder_name}")

            # Get available thumbnails from server
            available_files = self._cache.get_available_files(
                libretro_system,
                thumbnail_type,
                self._log if self.options.verbose else None,
            )

            if not available_files:
                self._log(f"    No thumbnails available for this system")
                continue

            # Images destination
            images_dir = system_folder / "images" / type_folder

            # Scan ROM files and collect download tasks
            for rom_file in sorted(system_folder.iterdir()):
                if not rom_file.is_file():
                    continue
                if rom_file.name.startswith("."):
                    continue

                game_name = self._get_game_name_from_file(rom_file)
                dest_path = images_dir / f"{game_name}.png"

                # Check if already exists
                if dest_path.exists() and not self.options.overwrite:
                    self.result.skipped_existing += 1
                    self._log(f"    Exists: {game_name}.png")
                    continue

                # Find matching thumbnail
                matched = match_thumbnail(game_name, available_files)

                if not matched:
                    self.result.skipped_not_found += 1
                    self._log(f"    No match: {game_name}")
                    continue

                # Build download URL
                url = self._build_download_url(libretro_system, thumbnail_type, matched)

                if self.options.dry_run:
                    if matched != game_name:
                        self._log(
                            f"    Would download: {game_name}.png (matched: {matched})"
                        )
                    else:
                        self._log(f"    Would download: {game_name}.png")
                    self.result.downloaded += 1
                    self.result.downloaded_files.append(
                        (system_key, game_name, str(dest_path))
                    )
                else:
                    # Add to download queue
                    download_tasks.append(
                        (system_key, game_name, url, str(dest_path), matched)
                    )

        # Execute downloads concurrently
        if download_tasks and not self.options.dry_run:
            self._log(
                f"\nDownloading {len(download_tasks)} thumbnails ({self.options.max_workers} concurrent)..."
            )

            with ThreadPoolExecutor(max_workers=self.options.max_workers) as executor:
                futures = {
                    executor.submit(self._download_task, task): task
                    for task in download_tasks
                }

                for future in as_completed(futures):
                    result = future.result()

                    if result["success"]:
                        with self._lock:
                            self.result.downloaded += 1
                            self.result.downloaded_files.append(
                                (
                                    result["system_key"],
                                    result["game_name"],
                                    result["dest_path"],
                                )
                            )
                        if result["matched"] != result["game_name"]:
                            self._log(
                                f"    Downloaded: {result['game_name']}.png (matched: {result['matched']})"
                            )
                        else:
                            self._log(f"    Downloaded: {result['game_name']}.png")
                    else:
                        with self._lock:
                            self.result.skipped_not_found += 1
                            if result["error"]:
                                self.result.errors.append(result["error"])
                        self._log(f"    Failed: {result['game_name']}.png")

        # Add cache errors to result
        self.result.errors.extend(self._cache._errors)

        return self.result


def download_thumbnails(
    rom_dir: Path,
    thumbnail_type: str = "boxart",
    dry_run: bool = False,
    verbose: bool = False,
    systems_filter: list[str] | None = None,
    progress_callback: Callable[[str], None] | None = None,
    max_workers: int = 5,
) -> ThumbnailResult:
    """
    Convenience function to download thumbnails.

    Args:
        rom_dir: Directory containing consolidated ROMs
        thumbnail_type: Type of thumbnail (boxart, snap, title)
        dry_run: Preview without downloading
        verbose: Show detailed progress
        systems_filter: List of systems to process
        progress_callback: Optional callback for progress messages
        max_workers: Number of concurrent downloads (default: 5)
    """
    if systems_filter:
        systems_filter = [s.lower() for s in systems_filter]

    options = ThumbnailOptions(
        dry_run=dry_run,
        verbose=verbose,
        thumbnail_type=thumbnail_type,
        systems_filter=systems_filter,
        progress_callback=progress_callback or (print if verbose else None),
        max_workers=max_workers,
    )

    downloader = ThumbnailDownloader(options)
    return downloader.download_for_directory(rom_dir)
