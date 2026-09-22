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


@dataclass
class RepairOptions:
    """Which repairs to run."""

    metadata: bool = False       # pdfuaid:part, DisplayDocTitle, MarkInfo
    th_scope: bool = False       # add /Scope to TH elements
    link_nesting: bool = False   # wrap orphaned Link annotations in <Link> struct elem
    fix_tbody: bool = False      # dissolve fake Table->TBody->TR->TD wrappers
    dry_run: bool = False

    @classmethod
    def all(cls, dry_run: bool = False) -> "RepairOptions":
        return cls(metadata=True, th_scope=True, link_nesting=True, fix_tbody=True, dry_run=dry_run)

    @property
    def any_selected(self) -> bool:
        return self.metadata or self.th_scope or self.link_nesting or self.fix_tbody
