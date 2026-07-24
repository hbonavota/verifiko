from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class DetonationForm:
    """A form observed in the rendered (post-JavaScript) page."""

    has_password_field: bool
    # Host the form submits to, if it can be determined. ``None`` means the form
    # posts back to the same page / a relative URL.
    action_host: str | None = None


@dataclass(frozen=True, slots=True)
class DetonationResult:
    """What a headless browser observed after actually loading a URL.

    This is the transport-agnostic contract every detonation backend (managed or
    self-hosted) must produce. The behavioral analyzer turns it into signals; it
    holds observations only, never a verdict.
    """

    requested_url: str
    final_url: str
    forms: tuple[DetonationForm, ...] = field(default_factory=tuple)
    # External hosts the page contacted while loading (scripts, XHR, beacons).
    third_party_hosts: tuple[str, ...] = field(default_factory=tuple)
    # Filenames/URLs of downloads the page tried to trigger without user action.
    downloads: tuple[str, ...] = field(default_factory=tuple)
    page_title: str | None = None
    detected_brand: str | None = None
    # Reference (e.g. blob-store key/URL) to a stored screenshot, if captured.
    screenshot_ref: str | None = None
    timed_out: bool = False


class HeadlessDetonationError(Exception):
    """Raised when a URL cannot be detonated (browser error, timeout, etc.)."""


class HeadlessDetonationPort(ABC):
    """Loads a URL in an isolated headless browser and reports what it observed."""

    @abstractmethod
    def detonate(self, url: str) -> DetonationResult:
        raise NotImplementedError
