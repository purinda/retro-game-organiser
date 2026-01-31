# System name mappings for retro gaming systems
# Maps canonical system keys to their full descriptive names
#
# Design:
# - SYSTEMS: Canonical system key -> full display name
# - SYSTEM_ALIASES: Alternative keys -> canonical key
# - LIBRETRO_SYSTEM_MAP: Canonical key -> Libretro repository name

# Canonical system definitions (one entry per unique system)
SYSTEMS = {
    # --- Computers ---
    "amiga": "Commodore Amiga",
    "amstradcpc": "Amstrad CPC",
    "apple2": "Apple II",
    "apple2gs": "Apple IIGS",
    "atari800": "Atari 8-bit (400/800/XL/XE)",
    "atarist": "Atari ST",
    "bbc": "Acorn BBC Micro",
    "c64": "Commodore 64",
    "c128": "Commodore 128",
    "coco": "Tandy TRS-80 Color Computer",
    "dos": "MS-DOS / PC",
    "macintosh": "Apple Macintosh",
    "msx": "MSX",
    "msx2": "MSX2",
    "pc88": "NEC PC-88",
    "pc98": "NEC PC-98",
    "x68000": "Sharp X68000",
    "zxspectrum": "Sinclair ZX Spectrum",
    "zx81": "Sinclair ZX81",
    # --- Consoles - Nintendo ---
    "nes": "Nintendo Entertainment System / Famicom",
    "fds": "Nintendo Famicom Disk System",
    "snes": "Super Nintendo Entertainment System",
    "n64": "Nintendo 64",
    "gb": "Nintendo Game Boy",
    "gbc": "Nintendo Game Boy Color",
    "gba": "Nintendo Game Boy Advance",
    "nds": "Nintendo DS",
    "virtualboy": "Nintendo Virtual Boy",
    "pokemini": "Pokemon Mini",
    "gameandwatch": "Nintendo Game & Watch",
    # --- Consoles - Sega ---
    "sg1000": "Sega SG-1000",
    "sms": "Sega Master System",
    "md": "Sega Genesis / Mega Drive",
    "sega32x": "Sega 32X",
    "segacd": "Sega CD / Mega-CD",
    "saturn": "Sega Saturn",
    "dreamcast": "Sega Dreamcast",
    "gg": "Sega Game Gear",
    "pico": "Sega Pico",
    # --- Consoles - Sony ---
    "psx": "Sony PlayStation",
    "psp": "Sony PlayStation Portable",
    # --- Consoles - NEC ---
    "pce": "NEC PC Engine / TurboGrafx-16",
    "pcecd": "NEC PC Engine CD / TurboGrafx-CD",
    "supergrafx": "NEC SuperGrafx",
    # --- Consoles - SNK ---
    "neogeo": "SNK Neo Geo",
    "neogeocd": "SNK Neo Geo CD",
    "ngp": "SNK Neo Geo Pocket",
    "ngpc": "SNK Neo Geo Pocket Color",
    # --- Consoles - Atari ---
    "atari2600": "Atari 2600",
    "atari5200": "Atari 5200",
    "atari7800": "Atari 7800",
    "lynx": "Atari Lynx",
    "jaguar": "Atari Jaguar",
    "jaguarcd": "Atari Jaguar CD",
    # --- Consoles - Other ---
    "3do": "Panasonic 3DO",
    "cdi": "Philips CD-i",
    "colecovision": "ColecoVision",
    "intellivision": "Mattel Intellivision",
    "channelf": "Fairchild Channel F",
    "vectrex": "GCE Vectrex",
    "wswan": "Bandai WonderSwan",
    "wswanc": "Bandai WonderSwan Color",
    "gamecom": "Tiger Game.com",
    # --- Arcade ---
    "arcade": "Arcade",
    "mame": "MAME (Arcade)",
    "fbneo": "FinalBurn Neo (Arcade)",
    "cps1": "Capcom CPS-1",
    "cps2": "Capcom CPS-2",
    "cps3": "Capcom CPS-3",
    "neogeoaes": "SNK Neo Geo AES",
    "atomiswave": "Sammy Atomiswave",
    "naomi": "Sega NAOMI",
    # --- Ports / Engines ---
    "scummvm": "ScummVM (Adventure Games)",
    "dosbox": "DOSBox",
    "openbor": "OpenBOR",
}


# Aliases mapping alternative keys to canonical keys
# All lookups should resolve through this first
SYSTEM_ALIASES = {
    # Nintendo
    "famicom": "nes",
    "fc": "nes",
    "sfc": "snes",
    "superfamicom": "snes",
    "gameboy": "gb",
    "gameboycolor": "gbc",
    "gameboyadvance": "gba",
    # Sega
    "megadrive": "md",
    "genesis": "md",
    "megadrivejp": "md",
    "mastersystem": "sms",
    "gamegear": "gg",
    "32x": "sega32x",
    # Sony
    "ps1": "psx",
    "ps": "psx",
    "playstation": "psx",
    # NEC
    "pcengine": "pce",
    "tg16": "pce",
    "turbografx16": "pce",
    "pcenginecd": "pcecd",
    "tg16cd": "pcecd",
    "turbografxcd": "pcecd",
    # Atari
    "atarilynx": "lynx",
    # MSX
    "msx1": "msx",
    # Commodore
    "vic20": "c20",
    "c20": "c64",  # Often grouped together
    # Uppercase variants (some ROM sets use these)
    "NES": "nes",
    "SNES": "snes",
    "GB": "gb",
    "GBC": "gbc",
    "GBA": "gba",
    "MD": "md",
    "SMS": "sms",
    "GG": "gg",
    "N64": "n64",
    "PSX": "psx",
    "PS": "psx",
    "PSP": "psp",
    "PCE": "pce",
    "FC": "nes",
    "SFC": "snes",
    "DC": "dreamcast",
    "SS": "saturn",
    "ARCADE": "arcade",
    "MAME": "mame",
    "NEOGEO": "neogeo",
}


def normalize_system_key(key: str) -> str:
    """
    Normalize a system key to lowercase for consistent lookups.

    Args:
        key: The system key (e.g., 'PSP', 'psp', 'Psp')

    Returns:
        Lowercase system key
    """
    return key.lower()


def resolve_system_alias(system_key: str) -> str:
    """
    Resolve a system alias to its canonical key.

    Args:
        system_key: Any system key (canonical or alias)

    Returns:
        The canonical system key
    """
    # Check aliases first (case-sensitive)
    if system_key in SYSTEM_ALIASES:
        return SYSTEM_ALIASES[system_key]

    # Try lowercase
    lower_key = system_key.lower()
    if lower_key in SYSTEM_ALIASES:
        return SYSTEM_ALIASES[lower_key]

    # Not an alias, return as-is (lowercased)
    return lower_key


def get_system_info(system_key: str) -> tuple[str, str] | None:
    """
    Get system information for a given key.

    Resolves aliases and returns the canonical key with full name.

    Args:
        system_key: Any system key or alias (e.g., 'md', 'megadrive', 'genesis')

    Returns:
        Tuple of (canonical_key, full_name) or None if not found
    """
    # Resolve alias to canonical key
    canonical = resolve_system_alias(system_key)

    # Look up in SYSTEMS
    if canonical in SYSTEMS:
        return (canonical, SYSTEMS[canonical])

    # Try contains match for complex folder names like "Nintendo - N64"
    lower_key = normalize_system_key(system_key)
    normalized_input = lower_key.replace(" ", "").replace("-", "").replace("_", "")

    # Sort by key length descending to match longer keys first
    for key in sorted(SYSTEMS.keys(), key=len, reverse=True):
        if len(key) <= 2:
            continue
        if key in lower_key or key in normalized_input:
            return (key, SYSTEMS[key])

    return None


def get_output_folder_name(system_key: str) -> str:
    """
    Get the output folder name for a system.

    Format: "SHORTHAND-Full Name" (e.g., "psp-Sony PlayStation Portable")

    Args:
        system_key: Any system key or alias

    Returns:
        Formatted output folder name, or original key if not found
    """
    info = get_system_info(system_key)
    if info:
        canonical, full_name = info
        return f"{canonical}-{full_name}"

    # Return original key if not in mapping
    return system_key


def is_known_system(system_key: str) -> bool:
    """
    Check if a system key is in our known systems list.

    Args:
        system_key: Any system key or alias

    Returns:
        True if known, False otherwise
    """
    return get_system_info(system_key) is not None


# Mapping from canonical system keys to Libretro thumbnail repository names
# See: https://github.com/libretro-thumbnails
LIBRETRO_SYSTEM_MAP = {
    "3do": "The_3DO_Company_-_3DO",
    "arcade": "MAME",
    "mame": "MAME",
    "atari2600": "Atari_-_2600",
    "atari5200": "Atari_-_5200",
    "atari7800": "Atari_-_7800",
    "lynx": "Atari_-_Lynx",
    "c64": "Commodore_-_64",
    "colecovision": "Coleco_-_ColecoVision",
    "dreamcast": "Sega_-_Dreamcast",
    "fds": "Nintendo_-_Family_Computer_Disk_System",
    "gg": "Sega_-_Game_Gear",
    "gb": "Nintendo_-_Game_Boy",
    "gba": "Nintendo_-_Game_Boy_Advance",
    "gbc": "Nintendo_-_Game_Boy_Color",
    "gamecom": "Tiger_-_Game.com",
    "md": "Sega_-_Mega_Drive_-_Genesis",
    "intellivision": "Mattel_-_Intellivision",
    "jaguar": "Atari_-_Jaguar",
    "sms": "Sega_-_Master_System_-_Mark_III",
    "msx": "Microsoft_-_MSX",
    "msx2": "Microsoft_-_MSX2",
    "n64": "Nintendo_-_Nintendo_64",
    "nds": "Nintendo_-_Nintendo_DS",
    "neogeo": "SNK_-_Neo_Geo",
    "neogeocd": "SNK_-_Neo_Geo_CD",
    "nes": "Nintendo_-_Nintendo_Entertainment_System",
    "ngp": "SNK_-_Neo_Geo_Pocket",
    "ngpc": "SNK_-_Neo_Geo_Pocket_Color",
    "pce": "NEC_-_PC_Engine_-_TurboGrafx_16",
    "pcecd": "NEC_-_PC_Engine_CD_-_TurboGrafx-CD",
    "pokemini": "Nintendo_-_Pokemon_Mini",
    "psp": "Sony_-_PlayStation_Portable",
    "psx": "Sony_-_PlayStation",
    "saturn": "Sega_-_Saturn",
    "sega32x": "Sega_-_32X",
    "segacd": "Sega_-_Mega-CD_-_Sega_CD",
    "sg1000": "Sega_-_SG-1000",
    "snes": "Nintendo_-_Super_Nintendo_Entertainment_System",
    "vectrex": "GCE_-_Vectrex",
    "virtualboy": "Nintendo_-_Virtual_Boy",
    "wswan": "Bandai_-_WonderSwan",
    "wswanc": "Bandai_-_WonderSwan_Color",
    "zxspectrum": "Sinclair_-_ZX_Spectrum",
}


def get_libretro_system_name(system_key: str) -> str | None:
    """
    Get the Libretro thumbnail repository name for a system.

    Args:
        system_key: Any system key or alias (e.g., 'md', 'megadrive', 'genesis')

    Returns:
        Libretro system name (e.g., 'Sega_-_Mega_Drive_-_Genesis') or None if not mapped
    """
    # Resolve alias to canonical key
    canonical = resolve_system_alias(system_key)

    # Look up in Libretro map
    return LIBRETRO_SYSTEM_MAP.get(canonical)
