"""converter/config.py — supported MIME types and file extensions.

SUPPORTED_TYPES  maps MIME type  → canonical file extension
SUPPORTED_SUFFIXES  is the set of all valid extensions, used for
validation when the MIME type is absent or unrecognised.
"""

SUPPORTED_TYPES: dict[str, str] = {
    "application/pdf":                                                       ".pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
    "application/msword":                                                    ".doc",
    "image/png":                                                             ".png",
    "image/jpeg":                                                            ".jpg",
    "image/tiff":                                                            ".tiff",
    "image/bmp":                                                             ".bmp",
    "image/webp":                                                            ".webp",
}

# Derived — do not edit directly, edit SUPPORTED_TYPES above
SUPPORTED_SUFFIXES: frozenset[str] = frozenset(SUPPORTED_TYPES.values())