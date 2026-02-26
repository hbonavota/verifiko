# python
from __future__ import annotations

import pytest

from .schemas import ScanOut, UrlScanIn


def test_urlscanin_accepts_nonempty():
    """La clase debe construirse con cualquier cadena no vacía."""
    obj = UrlScanIn(url="http://example.com")
    assert obj.url == "http://example.com"


@pytest.mark.parametrize("bad", ["", "   "])
def test_urlscanin_rejects_empty_or_blank(bad):
    """Debe lanzar ValueError si la URL está vacía o sólo espacios."""
    with pytest.raises(ValueError):
        UrlScanIn(url=bad)


def test_scanout_defaults_and_serialization():
    """Todos los campos opcionales de ScanOut son None por defecto."""
    out = ScanOut(id="123")
    assert out.id == "123"
    assert out.status is None
    assert out.score is None
    assert out.verdict is None
    assert out.created_at is None
    assert out.engine_version is None
    assert out.ruleset_version is None

    # la conversión a dict no rompe
    d = out.dict()
    assert d["id"] == "123"
    # y se pueden rellenar los opcionales
    filled = ScanOut(
        id="x",
        status="completed",
        score=42,
        verdict="VERDE",
        created_at="2020-01-01",
        engine_version="e1",
        ruleset_version="r1",
    )
    assert filled.score == 42
    assert filled.engine_version == "e1"
