"""converter/formatters.py — maps unstructured Element types to Markdown strings.

The registry pattern is used instead of an if/isinstance chain so that
adding support for a new element type only requires writing one new
decorated function — the dispatcher never needs to change.
"""

from unstructured.documents.elements import (
    Title,
    ListItem,
    Table,
    Image,
    PageBreak,
    Element,
)

# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

_FORMATTERS: dict[type, callable] = {}


def _register(el_type: type):
    """Decorator that registers a formatter function for a given element type."""
    def decorator(fn):
        _FORMATTERS[el_type] = fn
        return fn
    return decorator


# ---------------------------------------------------------------------------
# Formatters — one per element type
# ---------------------------------------------------------------------------

@_register(Title)
def _fmt_title(el: Title) -> str:
    depth = getattr(el.metadata, "category_depth", 0) or 0
    hashes = "#" * min(depth + 1, 6)
    return f"{hashes} {el.text.strip()}"


@_register(ListItem)
def _fmt_list_item(el: ListItem) -> str:
    return f"- {el.text.strip()}"


@_register(Table)
def _fmt_table(el: Table) -> str:
    html = getattr(el.metadata, "text_as_html", None)
    if html:
        return f"```html\n{html}\n```"
    return el.text.strip()


@_register(Image)
def _fmt_image(el: Image) -> str:
    return f"*[Bild: {el.text.strip()}]*"


@_register(PageBreak)
def _fmt_page_break(_: PageBreak) -> str:
    return "\n---\n"


# ---------------------------------------------------------------------------
# Public dispatcher
# ---------------------------------------------------------------------------

def element_to_markdown(el: Element) -> str:
    """Convert a single unstructured Element to a Markdown string.

    Falls back to plain text for any element type not in the registry.
    Returns an empty string for elements with no text content.
    """
    text = el.text.strip() if el.text else ""

    # PageBreak has no text but still produces output
    if not text and not isinstance(el, PageBreak):
        return ""

    formatter = _FORMATTERS.get(type(el))
    return formatter(el) if formatter else text