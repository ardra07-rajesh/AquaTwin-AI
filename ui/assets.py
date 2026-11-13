"""Image asset compatibility shim.

AquaTwin AI's active interface intentionally uses calculation-driven Plotly
visualizations instead of stock farm photographs or pretend sensor imagery.
The legacy constants remain available for old component imports, but are empty.
"""

ASSETS_DIR = None
GREENHOUSE_URI = ""
LEAF_URI = ""
LETTUCE_THUMB_URI = ""
SIDEBAR_FOLIAGE_URI = ""


def get_image_base64(filename: str) -> str:
    """No bundled photographs are used in the active AquaTwin interface."""
    return ""


def load_assets():
    """Retained as a no-op for compatibility with legacy UI imports."""
    return None
