from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from evaluation.labels import Label

DEFAULT_CORPUS_PATH = Path(__file__).resolve().parent / "data" / "corpus.jsonl"


@dataclass(frozen=True, slots=True)
class RedirectStep:
    status_code: int
    source_url: str
    target_url: str


@dataclass(frozen=True, slots=True)
class DetonationForm:
    has_password_field: bool
    action_host: str | None = None


@dataclass(frozen=True, slots=True)
class DetonationContext:
    """Scripted headless-detonation observations for a sample, letting the
    offline harness exercise the behavioral layer with no live browser."""

    final_url: str | None = None
    forms: tuple[DetonationForm, ...] = ()
    downloads: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class CorpusSample:
    """A single labeled URL, optionally with deterministic network context.

    ``redirect_final_url``/``redirect_hops`` and ``html`` let a sample exercise
    the redirect-resolution and HTML-inspection layers without any live network
    calls, keeping evaluation fully reproducible.
    """

    url: str
    label: Label
    redirect_final_url: str | None = None
    redirect_hops: tuple[RedirectStep, ...] = ()
    html: str | None = None
    detonation: DetonationContext | None = None
    note: str = ""

    @property
    def has_redirect_context(self) -> bool:
        return self.redirect_final_url is not None

    @property
    def has_detonation_context(self) -> bool:
        return self.detonation is not None


def load_corpus(path: str | Path = DEFAULT_CORPUS_PATH) -> list[CorpusSample]:
    """Load a JSONL corpus. Blank lines and ``#`` comment lines are ignored."""
    corpus_path = Path(path)
    samples: list[CorpusSample] = []
    with corpus_path.open("r", encoding="utf-8") as handle:
        for line_number, raw_line in enumerate(handle, start=1):
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"Invalid JSON in corpus {corpus_path} at line {line_number}: {exc}"
                ) from exc
            samples.append(_sample_from_record(record, corpus_path, line_number))
    return samples


def _sample_from_record(record: dict, path: Path, line_number: int) -> CorpusSample:
    try:
        url = record["url"]
        label = Label(record["label"])
    except (KeyError, ValueError) as exc:
        raise ValueError(
            f"Malformed corpus record in {path} at line {line_number}: {exc}"
        ) from exc

    hops = tuple(
        RedirectStep(
            status_code=int(hop["status_code"]),
            source_url=hop["source_url"],
            target_url=hop["target_url"],
        )
        for hop in record.get("redirect_hops", ())
    )
    return CorpusSample(
        url=url,
        label=label,
        redirect_final_url=record.get("redirect_final_url"),
        redirect_hops=hops,
        html=record.get("html"),
        detonation=_detonation_from_record(record.get("detonation")),
        note=record.get("note", ""),
    )


def _detonation_from_record(record: dict | None) -> DetonationContext | None:
    if record is None:
        return None
    forms = tuple(
        DetonationForm(
            has_password_field=bool(form.get("has_password_field")),
            action_host=form.get("action_host") or None,
        )
        for form in record.get("forms", ())
    )
    return DetonationContext(
        final_url=record.get("final_url"),
        forms=forms,
        downloads=tuple(record.get("downloads", ())),
    )
