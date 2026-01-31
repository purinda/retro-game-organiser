# Retro Game Organiser - ROM Consolidation & Thumbnail Tool

A Python CLI tool to consolidate multiple ROM sets into a single organized directory, with smart region-aware duplicate detection and thumbnail downloading from Libretro.

## Features

### 🗂️ ROM Consolidation
Merge multiple ROM collections into one organized library:
- **Multiple Sources**: Combine ROMs from different sources (hard drives, USB sticks, etc.)
- **Smart Deduplication**: Automatically detects and skips duplicate ROMs
- **Region-Aware**: Keeps different regional variants (USA, Europe, Japan) as separate files
- **Clean Naming**: Strips numeric prefixes (like `001 `) while preserving important metadata
- **Organized Output**: Creates standardized folder names (e.g., `gb-Nintendo Game Boy`)

### 🎨 Thumbnail Downloads
Automatically download game artwork from [Libretro Thumbnails](https://github.com/libretro-thumbnails):
- **Box Art**: Game covers and packaging artwork
- **Screenshots**: In-game snapshots
- **Title Screens**: Game title screen images

### ⚡ Additional Features
- **Systems Filter**: Process only specific systems (e.g., `--systems gb,gba,gbc`)
- **Dry Run Mode**: Preview all changes before executing
- **Verbose Output**: See detailed progress and decisions
- **Incremental Updates**: Only copies/downloads new files, skips existing ones

---

## Directory Structure Requirements

### Source ROM Directory Structure

Your source ROM directories must follow this structure:
System names that are supported can be found in the src/systems.py file and source roms directories should adhere to keys defined in the src/systems.py.

```
/path/to/your/roms/
├── gb/                          # System folder (short name)
│   ├── Pokemon Red (USA).gb
│   ├── Pokemon Blue (USA).gb
│   └── Tetris (World).gb
├── gba/
│   ├── Pokemon Emerald (USA).gba
│   └── Zelda - Minish Cap (USA).gba
├── snes/
│   ├── 001 Super Mario World (USA).sfc    # Numeric prefixes are OK
│   ├── 002 Zelda (USA).sfc
│   └── Chrono Trigger (Japan).sfc
└── psp/
    └── subdirectory/                       # Subdirectories are OK
        └── Game.iso
```

**Important:**
- System folders must be **direct children** of the input directory
- System folder names should match known systems (see `src/systems.py`)
- Common names like `gb`, `gba`, `snes`, `psp`, `n64`, `ps1` are recognized
- Subdirectories within system folders are scanned recursively

### Output Directory Structure

After consolidation, your output will look like:

```
/path/to/consolidated/
├── gb-Nintendo Game Boy/
│   ├── Pokemon Red (USA).gb           # Prefix stripped
│   ├── Pokemon Blue (USA).gb
│   └── Tetris (World).gb
├── gba-Nintendo Game Boy Advance/
│   ├── Pokemon Emerald (USA).gba
│   └── Zelda - Minish Cap (USA).gba
├── snes-Super Nintendo Entertainment System/
│   ├── Super Mario World (USA).sfc    # Prefix stripped!
│   ├── Zelda (USA).sfc
│   └── Chrono Trigger (Japan).sfc
└── psp-Sony PlayStation Portable/
    └── Game.iso
```

### Thumbnail Directory Structure

After downloading thumbnails:

```
/path/to/consolidated/
└── gb-Nintendo Game Boy/
    ├── Pokemon Red (USA).gb
    ├── Tetris (World).gb
    └── images/
        ├── boxarts/
        │   ├── Pokemon Red (USA).png
        │   └── Tetris (World).png
        ├── snaps/
        │   └── Pokemon Red (USA).png
        └── titles/
            └── Pokemon Red (USA).png
```

---

## Installation

```bash
# Clone the repository
git clone <repository-url>
cd retro-game-organiser

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

---

## Usage

### Consolidate ROMs

```bash
# Basic consolidation
python -m src.main consolidate \
    --input /path/to/romset1 \
    --output /path/to/consolidated

# Multiple input directories
python -m src.main consolidate \
    --input /Volumes/USB1/roms \
    --input /Volumes/USB2/roms \
    --input ~/Downloads/roms \
    --output ~/Games/consolidated

# Only specific systems
python -m src.main consolidate \
    --input /path/to/roms \
    --output /path/to/consolidated \
    --systems gb,gba,gbc,snes

# Preview without copying (recommended first!)
python -m src.main consolidate \
    --input /path/to/roms \
    --output /path/to/consolidated \
    --dry-run --verbose
```

### Download Thumbnails

```bash
# Download box art for all systems
python -m src.main thumbnails \
    --input /path/to/consolidated \
    --type boxart

# Download screenshots for specific systems
python -m src.main thumbnails \
    --input /path/to/consolidated \
    --systems gb,gba,gbc \
    --type snap

# Download title screens with preview
python -m src.main thumbnails \
    --input /path/to/consolidated \
    --type title \
    --dry-run --verbose
```

**Thumbnail types:**
| Type | Description |
|------|-------------|
| `boxart` | Box art / cover images (default) |
| `snap` | In-game screenshots |
| `title` | Title screen images |

### How Thumbnail Matching Works

The thumbnail downloader fetches the complete list of available images from the [Libretro Thumbnails](https://github.com/libretro-thumbnails) repository and matches your ROM filenames using intelligent fuzzy matching.

**Matching Priority Order:**

| Priority | Match Type | Description |
|----------|------------|-------------|
| 1 | Exact Match | Case-insensitive exact filename match |
| 2 | Base Name | Strips region/version info (parentheses) and matches |
| 3 | Normalized | Removes all non-alphanumeric characters for comparison |
| 4 | Base Normalized | Combines base name + normalization |
| 5 | Partial/Prefix | Matches if base names are substrings |

**Examples of Successful Matches:**

| Your ROM Filename | Matched Thumbnail on Server |
|-------------------|----------------------------|
| `Blade.chd` | `Blade (USA).png` |
| `FIFA 2000 - Major League Soccer (USA).chd` | `FIFA 2000 - Major League Soccer (USA) (En,De,Es,Nl,Sv).png` |
| `Iron Man X-O Manowar In Heavy Metal (USA).chd` | `Iron Man _ X-O Manowar in Heavy Metal (USA).png` |
| `Pokemon Red Version (USA).gb` | `Pokemon Red Version (USA, Europe).png` |
| `Tetris.gb` | `Tetris (World).png` |

> [!WARNING]
> **Potential Mismatches**: If your ROM filename is too generic (e.g., just `Blade` without region), the matcher may download artwork for a different game with a similar name. For best results:
> - Keep region codes in filenames (e.g., `(USA)`, `(Europe)`)
> - Use full game titles rather than abbreviations
> - Run with `--dry-run --verbose` first to verify matches

**Why We Use Server-Side File Lists:**
- Libretro uses inconsistent naming (e.g., `X-O` → `X _ O`, `In` → `in`)
- Some games have multiple language codes (e.g., `(En,De,Es,Nl,Sv)`)
- Server filenames may differ from standard ROM naming conventions
- Fetching the actual file list ensures we only download thumbnails that exist

---

## How Duplicate Detection Works

The tool uses smart duplicate detection to avoid copying the same game twice:

| Scenario | Result |
|----------|--------|
| `Game (USA).bin` vs `001 Game (USA).bin` | **Duplicate** - same game, same region |
| `Game (USA).bin` vs `Game (Europe).bin` | **Unique** - same game, different regions |
| `Game (USA).bin` vs `Game (USA) (Rev 1).bin` | **Unique** - same game, different versions |

**Rules:**
1. Numeric prefixes like `001 `, `002 ` are stripped for comparison
2. Region codes (USA, Europe, Japan, etc.) are preserved
3. Version info (Rev 1, Proto, etc.) is preserved
4. File extension doesn't matter for comparison

---

## Supported Systems

Over 150 retro gaming systems are supported. Common examples:

| Short Name | Full Name |
|------------|-----------|
| `gb` | Nintendo Game Boy |
| `gba` | Nintendo Game Boy Advance |
| `gbc` | Nintendo Game Boy Color |
| `nes` | Nintendo Entertainment System |
| `snes` | Super Nintendo Entertainment System |
| `n64` | Nintendo 64 |
| `psx` / `ps1` / `ps` | Sony PlayStation |
| `psp` | Sony PlayStation Portable |
| `genesis` / `megadrive` | Sega Genesis / Mega Drive |
| `saturn` | Sega Saturn |
| `dreamcast` | Sega Dreamcast |

See `src/systems.py` for the complete list.

---

## Running Tests

```bash
source venv/bin/activate
python -m pytest tests/ -v
```

---

## Tips

1. **Always do a dry run first** with `--dry-run --verbose` to preview changes
2. **Use systems filter** (`--systems gb,gba`) to process only what you need
3. **Check matched filenames** in verbose output to ensure correct thumbnails
4. **Keep region codes** in ROM filenames for accurate thumbnail matching
5. **Folder names matter** - ensure your source ROM folders use recognized system names
