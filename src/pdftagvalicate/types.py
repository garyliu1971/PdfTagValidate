"""Shared data types for pdftagvalicate repairs."""

from __future__ import annotations

from dataclasses import dataclass, asdict


@dataclass(frozen=True)
class RepairReport:
    """Result of running a single repair against a PDF."""

    name: str
    fixed: int
    detail: str

    @property
    def any_fixed(self) -> bool:
        return self.fixed > 0

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class CheckReport:
    """Result of running a single check against a PDF (report-only)."""

    name: str
    issues: int
    detail: str

    @property
    def any_issues(self) -> bool:
        return self.issues > 0

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class RepairOptions:
    """Which repairs to run."""

    metadata: bool = False       # pdfuaid:part, DisplayDocTitle, MarkInfo
    title: bool = False          # ensure a non-empty dc:title
    lang: bool = False           # ensure catalog /Lang
    lang_value: str | None = None  # explicit language code for the lang repair
    th_scope: bool = False       # add /Scope to TH elements
    link_nesting: bool = False   # wrap orphaned Link annotations in <Link> struct elem
    fix_tbody: bool = False      # dissolve fake Table->TBody->TR->TD wrappers
    dry_run: bool = False

    @classmethod
    def all(cls, dry_run: bool = False) -> "RepairOptions":
        return cls(
            metadata=True,
            title=True,
            lang=True,
            th_scope=True,
            link_nesting=True,
            fix_tbody=True,
            dry_run=dry_run,
        )

    @property
    def any_selected(self) -> bool:
        return (
            self.metadata
            or self.title
            or self.lang
            or self.th_scope
            or self.link_nesting
            or self.fix_tbody
        )


@dataclass
class CheckOptions:
    """Which checks to run (report-only, no file written)."""

    alt_text: bool = False       # Figure elements missing /Alt
    fonts: bool = False          # unembedded / Type3 / missing ToUnicode
    suspects: bool = False       # /MarkInfo /Suspects flag

    @classmethod
    def all(cls) -> "CheckOptions":
        return cls(alt_text=True, fonts=True, suspects=True)

    @property
    def any_selected(self) -> bool:
        return self.alt_text or self.fonts or self.suspects
