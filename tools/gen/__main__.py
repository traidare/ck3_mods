"""Run one generator on behalf of the Go core.

The core writes a JSON request on stdin and reads exactly one JSON result line
from stdout.  Anything the generator prints is captured and returned inside
that result, so the two never interleave.
"""

from __future__ import annotations

import importlib.util
import io
import json
import sys
import traceback
from collections.abc import Mapping
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path, PurePosixPath

from . import GenerationContext, GenerationError

SCHEMA_VERSION = 1


def load_entrypoint(module_path: Path, function_name: str):
    """Import a generator by path without leaving it in ``sys.modules``."""
    if not module_path.is_file():
        raise GenerationError(f"generator entrypoint not found: {module_path}")
    import_name = f"_ck3mm_generator_{module_path.stem}_{abs(hash(module_path))}"
    specification = importlib.util.spec_from_file_location(import_name, module_path)
    if specification is None or specification.loader is None:
        raise GenerationError(f"cannot load generator: {module_path}")
    module = importlib.util.module_from_spec(specification)
    sys.modules[import_name] = module
    try:
        specification.loader.exec_module(module)
    finally:
        sys.modules.pop(import_name, None)
    function = getattr(module, function_name, None)
    if not callable(function):
        raise GenerationError(
            f"generator entrypoint is not callable: {module_path.name}:{function_name}"
        )
    return function


def materialize(context: GenerationContext, value: object) -> None:
    """Stage a mapping of paths to content, for generators that return one."""
    if value is None:
        return
    if not isinstance(value, Mapping):
        raise GenerationError(
            "generator must return None or a mapping of relative paths to content"
        )
    for relative, content in value.items():
        if not isinstance(relative, (str, PurePosixPath)):
            raise GenerationError("generator output mapping keys must be paths")
        if isinstance(content, str):
            context.write_text(relative, content)
        elif isinstance(content, bytes):
            context.write_bytes(relative, content)
        else:
            raise GenerationError(
                f"generator output {relative} must contain text or bytes"
            )


def build_context(request: Mapping[str, object]) -> tuple[GenerationContext, Path, str]:
    version = request.get("schemaVersion")
    if version != SCHEMA_VERSION:
        raise GenerationError(f"unsupported request schema version: {version}")
    entrypoint = str(request["entrypoint"])
    module_name, _, function_name = entrypoint.partition(":")
    tooling_root = Path(str(request["toolingRoot"]))
    context = GenerationContext(
        mod_slug=str(request["modSlug"]),
        workspace_root=Path(str(request["workspaceRoot"])),
        mod_root=Path(str(request["modRoot"])),
        tooling_root=tooling_root,
        stage_dir=Path(str(request["stageDir"])),
        sources={
            name: Path(str(path))
            for name, path in dict(request.get("sources") or {}).items()
        },
        owned_outputs=tuple(request.get("ownedOutputs") or ()),
        owned_artifacts=tuple(request.get("ownedArtifacts") or ()),
        options=dict(request.get("options") or {}),
    )
    return context, tooling_root / module_name, function_name


def main() -> int:
    report = sys.stdout
    result: dict[str, object] = {"schemaVersion": SCHEMA_VERSION, "status": "ok"}
    captured_output = io.StringIO()
    captured_errors = io.StringIO()
    try:
        request = json.load(sys.stdin)
        context, module_path, function_name = build_context(request)
        with redirect_stdout(captured_output), redirect_stderr(captured_errors):
            generate = load_entrypoint(module_path, function_name)
            materialize(context, generate(context))
    except GenerationError as error:
        result["status"] = "error"
        result["error"] = str(error)
    except Exception as error:  # noqa: BLE001 - reported to the core verbatim
        result["status"] = "error"
        result["error"] = f"{type(error).__name__}: {error}"
        result["traceback"] = traceback.format_exc()
    result["stdout"] = captured_output.getvalue()
    result["stderr"] = captured_errors.getvalue()
    json.dump(result, report)
    report.write("\n")
    report.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
