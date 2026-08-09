"""The unified CK3MM command-line interface."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Callable, Sequence
from pathlib import Path

from . import __version__
from .config import (
    KNOWN_VARIABLES,
    Config,
    ConfigError,
    load_config,
    validate_config,
)
from .conflicts import ConflictAnalysisError
from .cultures import CultureToolError
from .descriptors import DescriptorError, load_descriptor, validate_native_descriptor
from .diagnostics import DiagnosticError
from .generation import (
    GenerationError,
    run_generator,
    source_lock_path,
    verify_source_locks,
    write_source_locks,
)
from .heightmap import HeightmapError
from .install import InstallError
from .launcher import LauncherError
from .preservation import PreservationError
from .references import ReferenceSyncError
from .workspace import Mod, Workspace, WorkspaceError

Handler = Callable[[argparse.Namespace, Workspace, Config], int]


class CommandUnavailable(RuntimeError):
    """Raised for command groups that are being migrated into CK3MM."""


def _add_subcommands(parser: argparse.ArgumentParser) -> argparse._SubParsersAction:
    return parser.add_subparsers(dest=f"{parser.prog}_command", required=True)


def _set_handler(parser: argparse.ArgumentParser, handler: Handler) -> None:
    parser.set_defaults(_handler=handler)


def _unavailable(name: str) -> Handler:
    def handler(
        _args: argparse.Namespace, _workspace: Workspace, _config: Config
    ) -> int:
        raise CommandUnavailable(f"{name} has not been migrated to CK3MM yet")

    return handler


def _config_check(
    args: argparse.Namespace, _workspace: Workspace, config: Config
) -> int:
    validate_config(config)
    values = config.environment()
    if args.json:
        print(json.dumps(values, indent=2, sort_keys=True))
    else:
        for variable in KNOWN_VARIABLES:
            value = values.get(variable)
            print(f"{variable}={value if value is not None else '<unset>'}")
    return 0


def _mod_list(args: argparse.Namespace, workspace: Workspace, _config: Config) -> int:
    mods = workspace.mods()
    if args.json:
        print(
            json.dumps(
                [
                    {
                        "slug": mod.slug,
                        "descriptor": mod.descriptor_path.is_file(),
                        "manifest": mod.manifest is not None,
                        "generator": bool(
                            mod.manifest and mod.manifest.generator is not None
                        ),
                    }
                    for mod in mods
                ],
                indent=2,
                sort_keys=True,
            )
        )
    else:
        for mod in mods:
            features = []
            if mod.manifest:
                features.append("manifest")
            if mod.manifest and mod.manifest.generator:
                features.append("generator")
            suffix = f" ({', '.join(features)})" if features else ""
            print(mod.slug + suffix)
    return 0


def _selected_generator_mods(
    workspace: Workspace, slugs: Sequence[str]
) -> tuple[Mod, ...]:
    if slugs:
        return tuple(workspace.get_mod(slug) for slug in slugs)
    return tuple(
        mod
        for mod in workspace.iter_mods()
        if mod.manifest is not None and mod.manifest.generator is not None
    )


def _mod_generation(
    args: argparse.Namespace, workspace: Workspace, config: Config
) -> int:
    check = args.mod_action == "check"
    stale = False
    failed = False
    options = _generator_options(args.option)
    for mod in _selected_generator_mods(workspace, args.mods):
        try:
            result = run_generator(workspace, mod, config, check=check, options=options)
        except (ConfigError, GenerationError, WorkspaceError) as error:
            failed = True
            print(f"{mod.slug}: error: {error}", file=sys.stderr)
            continue
        if result.stdout:
            print(result.stdout, end="")
        if result.stderr:
            print(result.stderr, end="", file=sys.stderr)
        if result.current:
            print(f"{mod.slug}: current")
            continue
        stale = True
        action = "would update" if check else "updated"
        paths = sorted((*result.changed_files, *result.stale_files))
        print(f"{mod.slug}: {action} {len(paths)} file(s)")
        for path in paths:
            print(f"  {path}")
    return int(failed or (check and stale))


def _generator_options(values: Sequence[str]) -> dict[str, object]:
    options: dict[str, object] = {}
    for raw in values:
        key, separator, value = raw.partition("=")
        if not key.isidentifier():
            raise GenerationError(f"invalid generator option name: {key!r}")
        if not separator:
            options[key] = True
            continue
        try:
            options[key] = json.loads(value)
        except json.JSONDecodeError:
            options[key] = value
    return options


def _mod_audit(args: argparse.Namespace, workspace: Workspace, _config: Config) -> int:
    selected = (
        tuple(workspace.get_mod(slug) for slug in args.mods)
        if args.mods
        else workspace.mods()
    )
    invalid = False
    for mod in selected:
        if not mod.descriptor_path.is_file():
            invalid = True
            print(f"{mod.slug}: missing {workspace.settings.descriptor}")
            continue
        try:
            validate_native_descriptor(load_descriptor(mod.descriptor_path))
        except DescriptorError as error:
            invalid = True
            print(f"{mod.slug}: {error}")
        else:
            print(f"{mod.slug}: descriptor valid")
    return int(invalid)


def _mod_sources(args: argparse.Namespace, workspace: Workspace, config: Config) -> int:
    failed = False
    for mod in _selected_generator_mods(workspace, args.mods):
        assert mod.manifest is not None
        try:
            sources = workspace.resolve_sources(mod.manifest, config)
            if args.sources_action == "check":
                if not source_lock_path(mod.manifest).is_file():
                    print(f"{mod.slug}: no source locks recorded")
                    continue
                verify_source_locks(mod.manifest, sources)
                print(f"{mod.slug}: sources accepted")
                continue
            preview = write_source_locks(mod.manifest, sources, apply=args.apply)
            if args.apply:
                print(f"{mod.slug}: source locks updated")
            else:
                print(f"{mod.slug}: source-lock preview")
                print(preview, end="")
        except (ConfigError, GenerationError, WorkspaceError) as error:
            failed = True
            print(f"{mod.slug}: error: {error}", file=sys.stderr)
    return int(failed)


def _launcher_database(config: Config) -> Path:
    config.require("CK3_PARADOX_DIR")
    assert config.launcher_db is not None
    return config.launcher_db


def _load_live_playset(config: Config, name: str | None):
    from .playsets import load_live_playset

    return load_live_playset(
        _launcher_database(config),
        name=name,
        configured_name=config.playset_name,
    )


def _playset_command(
    args: argparse.Namespace, _workspace: Workspace, config: Config
) -> int:
    from .playsets import (
        apply_import,
        diff_playsets,
        dump_playset,
        load_playset_file,
        plan_import,
        playset_summary,
    )

    if args.playset_action == "summary":
        summary = playset_summary(_load_live_playset(config, args.name))
        if args.json:
            print(json.dumps(summary, indent=2, sort_keys=True))
        else:
            print(f"Playset: {summary['name']}")
            print(f"Selection: {summary['selectionSource']}")
            print(f"Mods: {summary['enabled']} enabled / {summary['total']} total")
            print(f"Local: {summary['local']}")
            print(f"Workshop: {summary['workshop']}")
        return 0

    if args.playset_action == "export":
        content = dump_playset(_load_live_playset(config, args.name), path=args.output)
        if args.output is None:
            print(content, end="")
        else:
            print(f"exported playset to {args.output}")
        return 0

    if args.playset_action == "import":
        playset = load_playset_file(args.file)
        database = _launcher_database(config)
        plan = (
            apply_import(database, playset, allow_missing=args.allow_missing)
            if args.apply
            else plan_import(database, playset)
        )
        print(json.dumps(plan.to_dict(), indent=2, sort_keys=True))
        return 0

    if args.playset_action == "diff":
        result = diff_playsets(
            load_playset_file(args.before),
            load_playset_file(args.after),
        )
        if args.json:
            print(json.dumps(result.to_dict(), indent=2, sort_keys=True))
        else:
            print(f"Playsets: {result.before_name} -> {result.after_name}")
            for label, mods in (
                ("Added", result.added),
                ("Removed", result.removed),
            ):
                print(f"{label}: {len(mods)}")
                for mod in mods:
                    print(f"  {mod.stable_id} ({mod.display_name})")
            print(f"Changed: {len(result.changed)}")
            for change in result.changed:
                print(f"  {change.stable_id} ({change.after.display_name})")
        return int(not result.current)

    raise CommandUnavailable(f"playset {args.playset_action} is not migrated")


def _conflicts_command(
    args: argparse.Namespace, _workspace: Workspace, config: Config
) -> int:
    from .conflicts import (
        analyze_conflicts,
        failure_exit_code,
        filter_report,
    )
    from .discovery import discover_playset
    from .playsets import load_playset_file
    from .report import render_text

    if args.playset_file is not None and args.playset is not None:
        raise LauncherError("choose either a playset name or --playset-file, not both")
    config.require("CK3_PARADOX_DIR", "CK3_WORKSHOP_DIR")
    assert config.paradox_dir is not None
    assert config.workshop_dir is not None
    playset = (
        load_playset_file(args.playset_file)
        if args.playset_file is not None
        else _load_live_playset(config, args.playset)
    )
    discovery = discover_playset(
        playset,
        workshop_dir=config.workshop_dir,
        paradox_dir=config.paradox_dir,
    )
    report = analyze_conflicts(
        discovery.providers,
        playset=discovery.playset,
        warnings=discovery.warnings,
        include_all=args.all_files,
    )
    report = filter_report(
        report,
        involving=args.involving or "",
        include_prefixes=args.include_prefix,
        exclude_prefixes=args.exclude_prefix,
        conflicts_only=not args.all_files,
        summary_only=args.summary_only,
    )
    debug_paths = {
        provider.stable_id: str(provider.root.resolve(strict=False))
        for provider in discovery.providers
    }
    if args.format == "json":
        if args.debug_paths:
            payload = report.to_dict()
            payload["debugPaths"] = debug_paths
            output = json.dumps(payload, indent=2, sort_keys=True) + "\n"
        else:
            output = report.to_json()
    else:
        output = render_text(report)
        if args.debug_paths:
            output += "\nDebug paths\n"
            output += "".join(
                f"  {stable_id}: {path}\n"
                for stable_id, path in sorted(debug_paths.items())
            )
    print(output, end="")
    return failure_exit_code(report, args.fail_on)


def _cultures_command(
    args: argparse.Namespace, _workspace: Workspace, config: Config
) -> int:
    from . import cultures

    return cultures.main(args.arguments, config=config)


def _preserve_command(
    args: argparse.Namespace, _workspace: Workspace, config: Config
) -> int:
    from .preservation import apply_preservation, plan_preservation

    config.require("CK3_PARADOX_DIR", "CK3_WORKSHOP_DIR")
    assert config.paradox_dir is not None
    assert config.workshop_dir is not None
    plan = plan_preservation(
        _launcher_database(config),
        config.paradox_dir / "mod",
        workshop_directory=config.workshop_dir,
        playset_name=args.name,
        configured_name=config.playset_name,
        snapshot_name=args.snapshot_name,
    )
    print(json.dumps(plan.to_dict(), indent=2, sort_keys=True))
    if args.apply:
        apply_preservation(plan)
    return 0


def _install_command(
    args: argparse.Namespace, workspace: Workspace, config: Config
) -> int:
    from .install import apply_install, plan_install

    config.require("CK3_PARADOX_DIR")
    assert config.paradox_dir is not None
    plan = plan_install(workspace, config.paradox_dir / "mod", mod_slugs=args.mods)
    if args.apply:
        apply_install(plan)
    state = "applied" if args.apply else "preview"
    print(f"Install {state}")
    print(f"  Mods: {len(plan.mod_slugs)}")
    print(f"  Payload files: {len(plan.files)}")
    print(f"  Launcher descriptors: {len(plan.descriptors)}")
    print(f"  Removals: {len(plan.removals)}")
    return 0


def _validate_command(
    args: argparse.Namespace, workspace: Workspace, config: Config
) -> int:
    from .validation import validate_mods

    selected: Sequence[Mod | str] = args.mods or workspace.mods()
    results = validate_mods(workspace, selected, config)
    if args.json:
        print(
            json.dumps(
                [result.to_dict() for result in results],
                indent=2,
                sort_keys=True,
            )
        )
    else:
        for result in results:
            print(f"{result.mod_slug}: {result.status.value}")
            for check in result.checks:
                print(f"  {check.step.value}: {check.status.value} - {check.message}")
                if check.command:
                    print("    command: " + " ".join(check.command))
                for detail in check.details:
                    print(f"    {detail}")
                for label, output in (
                    ("stdout", check.stdout),
                    ("stderr", check.stderr),
                ):
                    if output:
                        print(f"    {label}:")
                        for line in output.rstrip().splitlines():
                            print(f"      {line}")
    return int(any(not result.ok for result in results))


def _references_command(
    args: argparse.Namespace, workspace: Workspace, config: Config
) -> int:
    from .references import (
        apply_reference_sync,
        check_references,
        plan_reference_sync,
    )

    config.require("CK3_GAME_DIR", "CK3_PARADOX_DIR")
    assert config.game_dir is not None
    assert config.paradox_dir is not None
    cache_root = workspace.root / "references" / "generated"
    if args.check:
        result = check_references(config.game_dir, config.paradox_dir, cache_root)
    else:
        plan = plan_reference_sync(config.game_dir, config.paradox_dir, cache_root)
        result = apply_reference_sync(plan)
    print(f"Info files: {result.info_files}")
    print(f"Script-doc logs: {result.script_doc_logs}")
    for label, values in (
        ("Missing", result.missing),
        ("Stale", result.stale),
        ("Unexpected", result.unexpected),
        ("Manifest errors", result.manifest_errors),
    ):
        if values:
            print(f"{label}:")
            for value in values:
                print(f"  {value}")
    print("References are current" if result.current else "References need refresh")
    return int(not result.current)


def _diagnose_live_command(
    args: argparse.Namespace, _workspace: Workspace, config: Config
) -> int:
    from .diagnostics import collect_live_diagnostics, write_diagnostic_report

    config.require("CK3_PARADOX_DIR")
    assert config.paradox_dir is not None
    steam_log = args.steam_log
    if steam_log is None and config.steam_log_dir is not None:
        steam_log = config.steam_log_dir / "gameprocess_log.txt"
    report = collect_live_diagnostics(
        paradox_dir=config.paradox_dir,
        proc_root=args.proc_root,
        pids=args.pid,
        steam_log_path=steam_log,
        capture_backtrace=args.backtrace,
        sample_count=args.sample_count,
        sample_interval=args.sample_interval,
    )
    if args.output is None:
        print(report.text, end="")
    else:
        write_diagnostic_report(report, args.output)
        print(f"wrote diagnostic report to {args.output}")
    return 0


def _heightmap_plan_dict(plan) -> dict[str, object]:
    return {
        "operation": plan.operation,
        "stage": str(plan.stage),
        "copies": [
            {"source": str(copy.source), "destination": str(copy.destination)}
            for copy in plan.copies
        ],
        "writes": [str(write.destination) for write in plan.writes],
        "backups": [
            {"source": str(copy.source), "destination": str(copy.destination)}
            for copy in plan.backups
        ],
        "moves": [
            {"source": str(move.source), "destination": str(move.destination)}
            for move in plan.moves
        ],
    }


def _heightmap_command(
    args: argparse.Namespace, _workspace: Workspace, _config: Config
) -> int:
    from .heightmap import (
        apply_heightmap_plan,
        minimal_editor_playset,
        plan_prepare,
        plan_promote,
        plan_unregister,
        verify_heightmap,
    )

    action = args.heightmap_action
    if action == "import-playset":
        playset = minimal_editor_playset()
        content = (
            playset.decode("utf-8")
            if isinstance(playset, bytes)
            else json.dumps(playset, indent=2, sort_keys=True) + "\n"
        )
        if args.output is not None and args.apply:
            args.output.write_text(content, encoding="utf-8")
            print(f"wrote editor playset to {args.output}")
        else:
            print(content, end="")
        return 0
    if action == "verify":
        result = verify_heightmap(args.stage)
        print(
            json.dumps(
                {
                    "stage": str(result.stage),
                    "sourceReencoded": result.source_reencoded,
                    "packedHashChanged": result.packed_hash_changed,
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 0
    if action == "prepare":
        plan = plan_prepare(
            source_mod=args.source_mod,
            source_heightmap=args.source_heightmap,
            essos_expanded_root=args.essos_expanded_root,
            stage=args.stage,
            playset_path=args.playset_path,
            launcher_descriptor=args.launcher_descriptor,
            launcher_mod_path=args.launcher_mod_path,
        )
    elif action == "promote":
        plan = plan_promote(
            stage=args.stage,
            target_map_data=args.target_map_data,
            backup_dir=args.backup_dir,
        )
    elif action == "unregister":
        plan = plan_unregister(
            stage=args.stage,
            launcher_descriptor=args.launcher_descriptor,
            destination=args.destination,
        )
    else:  # pragma: no cover - argparse constrains the command set.
        raise CommandUnavailable(f"map heightmap {action}")
    print(json.dumps(_heightmap_plan_dict(plan), indent=2, sort_keys=True))
    if args.apply:
        apply_heightmap_plan(plan)
    return 0


def _build_config_commands(subcommands: argparse._SubParsersAction) -> None:
    config_parser = subcommands.add_parser("config", help="inspect local configuration")
    actions = _add_subcommands(config_parser)
    check = actions.add_parser("check", help="validate required CK3 paths")
    check.add_argument("--json", action="store_true", help="emit a JSON object")
    _set_handler(check, _config_check)


def _build_mod_commands(subcommands: argparse._SubParsersAction) -> None:
    mod_parser = subcommands.add_parser("mod", help="work with local mods")
    actions = mod_parser.add_subparsers(dest="mod_action", required=True)

    list_parser = actions.add_parser("list", help="list repository mods")
    list_parser.add_argument("--json", action="store_true")
    _set_handler(list_parser, _mod_list)

    for action, help_text in (
        ("generate", "stage and promote generated outputs"),
        ("check", "check generated outputs without changing them"),
    ):
        parser = actions.add_parser(action, help=help_text)
        parser.add_argument("mods", nargs="*", metavar="MOD")
        parser.add_argument(
            "--option",
            action="append",
            default=[],
            metavar="NAME[=VALUE]",
            help="pass a generator-specific option; repeatable",
        )
        _set_handler(parser, _mod_generation)

    audit = actions.add_parser("audit", help="audit canonical mod descriptors")
    audit.add_argument("mods", nargs="*", metavar="MOD")
    _set_handler(audit, _mod_audit)

    validate = actions.add_parser("validate", help="run complete mod validation")
    validate.add_argument("mods", nargs="*", metavar="MOD")
    validate.add_argument("--json", action="store_true")
    _set_handler(validate, _validate_command)

    install = actions.add_parser("install", help="preview or install local mods")
    install.add_argument("mods", nargs="*", metavar="MOD")
    install.add_argument("--apply", action="store_true")
    _set_handler(install, _install_command)

    sources = actions.add_parser("sources", help="work with generator source locks")
    source_actions = sources.add_subparsers(dest="sources_action", required=True)
    source_check = source_actions.add_parser("check", help="verify accepted hashes")
    source_check.add_argument("mods", nargs="*", metavar="MOD")
    _set_handler(source_check, _mod_sources)
    source_accept = source_actions.add_parser("accept", help="accept current hashes")
    source_accept.add_argument("mods", nargs="*", metavar="MOD")
    source_accept.add_argument("--apply", action="store_true")
    _set_handler(source_accept, _mod_sources)


def _build_playset_commands(subcommands: argparse._SubParsersAction) -> None:
    playset = subcommands.add_parser("playset", help="inspect or mutate playsets")
    actions = playset.add_subparsers(dest="playset_action", required=True)
    summary = actions.add_parser("summary")
    summary.add_argument("name", nargs="?")
    summary.add_argument("--json", action="store_true")
    _set_handler(summary, _playset_command)

    export = actions.add_parser("export")
    export.add_argument("name", nargs="?")
    export.add_argument("--output", type=Path)
    _set_handler(export, _playset_command)

    import_parser = actions.add_parser("import")
    import_parser.add_argument("file", type=Path)
    import_parser.add_argument("--allow-missing", action="store_true")
    import_parser.add_argument("--apply", action="store_true")
    _set_handler(import_parser, _playset_command)

    diff = actions.add_parser("diff")
    diff.add_argument("before", type=Path)
    diff.add_argument("after", type=Path)
    diff.add_argument("--json", action="store_true")
    _set_handler(diff, _playset_command)

    preserve = actions.add_parser("preserve")
    preserve.add_argument("name", nargs="?")
    preserve.add_argument("--snapshot-name")
    preserve.add_argument("--apply", action="store_true")
    _set_handler(preserve, _preserve_command)


def _build_conflict_command(subcommands: argparse._SubParsersAction) -> None:
    parser = subcommands.add_parser("conflicts", help="analyze playset file conflicts")
    parser.add_argument("playset", nargs="?")
    parser.add_argument("--playset-file", type=Path)
    parser.add_argument("--involving", default="")
    parser.add_argument("--include-prefix", action="append", default=[])
    parser.add_argument("--exclude-prefix", action="append", default=[])
    parser.add_argument("--summary-only", action="store_true")
    parser.add_argument("--all-files", action="store_true")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    parser.add_argument(
        "--fail-on", choices=("divergent", "any", "missing"), default=None
    )
    parser.add_argument("--debug-paths", action="store_true")
    _set_handler(parser, _conflicts_command)


def _build_remaining_commands(subcommands: argparse._SubParsersAction) -> None:
    refs = subcommands.add_parser("refs", help="synchronize local references")
    refs_actions = refs.add_subparsers(dest="refs_action", required=True)
    refs_sync = refs_actions.add_parser("sync")
    refs_sync.add_argument("--check", action="store_true")
    _set_handler(refs_sync, _references_command)

    cultures = subcommands.add_parser("cultures", help="inspect culture data")
    cultures.add_argument("arguments", nargs=argparse.REMAINDER)
    _set_handler(cultures, _cultures_command)

    diagnose = subcommands.add_parser("diagnose", help="collect diagnostics")
    diagnose_actions = diagnose.add_subparsers(dest="diagnose_action", required=True)
    diagnose_live = diagnose_actions.add_parser("live")
    diagnose_live.add_argument("--pid", action="append", type=int, default=[])
    diagnose_live.add_argument("--sample-count", type=int, default=2)
    diagnose_live.add_argument("--sample-interval", type=float, default=5.0)
    diagnose_live.add_argument("--backtrace", action="store_true")
    diagnose_live.add_argument("--proc-root", type=Path, default=Path("/proc"))
    diagnose_live.add_argument("--steam-log", type=Path)
    diagnose_live.add_argument("--output", type=Path)
    _set_handler(diagnose_live, _diagnose_live_command)

    map_parser = subcommands.add_parser("map", help="work with map-editor artifacts")
    map_actions = map_parser.add_subparsers(dest="map_action", required=True)
    heightmap = map_actions.add_parser("heightmap")
    heightmap_actions = heightmap.add_subparsers(dest="heightmap_action", required=True)
    prepare = heightmap_actions.add_parser("prepare")
    prepare.add_argument("--source-mod", type=Path, required=True)
    prepare.add_argument("--source-heightmap", type=Path, required=True)
    prepare.add_argument("--essos-expanded-root", type=Path, required=True)
    prepare.add_argument("--stage", type=Path, required=True)
    prepare.add_argument("--playset-path", type=Path, required=True)
    prepare.add_argument("--launcher-descriptor", type=Path)
    prepare.add_argument(
        "--launcher-mod-path", default="mod/agot_heightmap_repack_staging"
    )
    prepare.add_argument("--apply", action="store_true")
    _set_handler(prepare, _heightmap_command)

    verify = heightmap_actions.add_parser("verify")
    verify.add_argument("stage", type=Path)
    _set_handler(verify, _heightmap_command)

    promote = heightmap_actions.add_parser("promote")
    promote.add_argument("--stage", type=Path, required=True)
    promote.add_argument("--target-map-data", type=Path, required=True)
    promote.add_argument("--backup-dir", type=Path, required=True)
    promote.add_argument("--apply", action="store_true")
    _set_handler(promote, _heightmap_command)

    import_playset = heightmap_actions.add_parser("import-playset")
    import_playset.add_argument("--output", type=Path)
    import_playset.add_argument("--apply", action="store_true")
    _set_handler(import_playset, _heightmap_command)

    unregister = heightmap_actions.add_parser("unregister")
    unregister.add_argument("--stage", type=Path, required=True)
    unregister.add_argument("--launcher-descriptor", type=Path, required=True)
    unregister.add_argument("--destination", type=Path, required=True)
    unregister.add_argument("--apply", action="store_true")
    _set_handler(unregister, _heightmap_command)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ck3mm", description="Manage this CK3 mod workspace"
    )
    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {__version__}"
    )
    parser.add_argument(
        "--root", type=Path, help="workspace path (defaults to discovery from cwd)"
    )
    parser.add_argument("--game-dir", type=Path, default=None)
    parser.add_argument("--paradox-dir", type=Path, default=None)
    parser.add_argument("--workshop-dir", type=Path, default=None)
    parser.add_argument("--playset", dest="playset_name", default=None)
    parser.add_argument("--steam-log-dir", type=Path, default=None)
    subcommands = parser.add_subparsers(dest="command", required=True)
    _build_config_commands(subcommands)
    _build_playset_commands(subcommands)
    _build_conflict_command(subcommands)
    _build_mod_commands(subcommands)
    _build_remaining_commands(subcommands)
    return parser


def _config_overrides(args: argparse.Namespace) -> dict[str, object]:
    result: dict[str, object] = {}
    for name in (
        "game_dir",
        "paradox_dir",
        "workshop_dir",
        "playset_name",
        "steam_log_dir",
    ):
        value = getattr(args, name, None)
        if value is not None:
            result[name] = value
    return result


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        workspace = Workspace.from_path(args.root)
        config = load_config(workspace.root, overrides=_config_overrides(args))
        handler: Handler = args._handler
        return handler(args, workspace, config)
    except (
        CommandUnavailable,
        ConfigError,
        ConflictAnalysisError,
        CultureToolError,
        DescriptorError,
        DiagnosticError,
        GenerationError,
        HeightmapError,
        InstallError,
        LauncherError,
        PreservationError,
        ReferenceSyncError,
        WorkspaceError,
    ) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
