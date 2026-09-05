"""Resolved source roots and staging paths for one compatch run.

Every stage reads the same parent stack, so the Workshop identifiers, the shared
Workshop parent directory, and the missing-module check live here once instead of
being restated per stage.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from gen import GenerationContext

# Every Workshop parent this module reads, by the short label the stages use.
# `RC` is the Legacy of Valyria AGOT bridge; `BRIDGE` is the Essos Expanded
# TempLoV/NOW compatch.
WORKSHOP_IDS = {
    "AGOT": "2962333032",
    "NOW": "3664900993",
    "LOV": "3403938445",
    "RC": "3719888822",
    "EE": "3682802751",
    "EEP": "3768149491",
    "BRIDGE": "3773608127",
}

# The manifest source name for each label, so the shared Workshop parent can be
# resolved through the core rather than assumed.
SOURCE_NAMES = {
    "AGOT": "agot",
    "NOW": "now",
    "LOV": "legacy-of-valyria",
    "RC": "legacy-of-valyria-bridge",
    "EE": "essos-expanded",
    "EEP": "essos-expanded-bridge",
    "BRIDGE": "essos-compatch",
}


@dataclass(frozen=True, slots=True)
class RunInputs:
    """Portable roots one compatch run reads from and stages into."""

    context: GenerationContext
    workshop_root: Path
    workshop: dict[str, Path]
    root: Path
    output: Path
    assets: Path
    references: dict[str, Path]

    @classmethod
    def from_context(cls, context: GenerationContext) -> RunInputs:
        workshop_root = context.workshop_root(*SOURCE_NAMES.values())
        workshop = {
            label: workshop_root / item_id for label, item_id in WORKSHOP_IDS.items()
        }
        missing = [
            f"{label}:{path}" for label, path in workshop.items() if not path.is_dir()
        ]
        if missing:
            raise FileNotFoundError(f"missing Workshop modules: {missing}")
        references = {
            "detailed": context.source("known-world-detailed"),
            "google": context.source("known-world-google"),
        }
        missing_references = [
            path.as_posix() for path in references.values() if not path.is_file()
        ]
        if missing_references:
            raise FileNotFoundError(
                f"missing lore reference maps: {missing_references}"
            )
        return cls(
            context=context,
            workshop_root=workshop_root,
            workshop=workshop,
            root=context.workspace_root,
            output=context.output_root,
            assets=context.assets_dir,
            references=references,
        )

    def __getitem__(self, label: str) -> Path:
        return self.workshop[label]

    def current_map_source(self, relative: str) -> Path:
        """Return Further East's file, falling back to its Essos Expanded parent."""
        for label in ("EEP", "EE"):
            candidate = self.workshop[label] / relative
            if candidate.is_file():
                return candidate
        raise FileNotFoundError(f"Further East supplies no {relative}")

    def write(self, relative: str, text: str, *, encoding: str = "utf-8-sig") -> None:
        self.context.output_path(relative).write_text(
            text, encoding=encoding, newline="\n"
        )
