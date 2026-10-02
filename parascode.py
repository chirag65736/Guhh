"""
parascode shim — provides the terminal-styling functions that igscrapper.py
expects (render, cprint, link) without requiring the real parascode package,
which is designed for interactive terminals and doesn't belong in a server.
"""


def render(text, **kwargs):
    """Return plain text (real version renders ASCII-art banners)."""
    return text


def cprint(text, **kwargs):
    """Print the text portion without ANSI color codes."""
    # Input format: "<color>  <message>  reset" — just print it as-is
    print(text)


def link(url):
    """No-op in a server context (real version opens a browser)."""
    pass
