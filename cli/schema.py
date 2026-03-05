"""lr schema -- command schema introspection."""
import click
from cli.output import OutputFormatter


@click.command("schema")
@click.argument("path", required=False, default=None)
@click.pass_context
def schema_cmd(ctx, path):
    """Introspect command schemas.

    Usage:
      lr schema                    -- list all groups
      lr schema develop            -- list commands in group
      lr schema develop.set        -- show command detail
    """
    from lightroom_sdk.schema import get_all_schemas, get_schemas_by_group
    fmt = ctx.obj.get("output", "text") if ctx.obj else "text"

    if path is None:
        schemas = get_all_schemas()
        groups: dict[str, dict] = {}
        for cmd_name, schema in schemas.items():
            group = cmd_name.split(".")[0]
            if group not in groups:
                groups[group] = {"name": group, "commands": 0, "mutating": 0}
            groups[group]["commands"] += 1
            if schema.mutating:
                groups[group]["mutating"] += 1
        click.echo(OutputFormatter.format(list(groups.values()), fmt))

    elif "." not in path:
        schemas = get_schemas_by_group(path)
        if not schemas:
            click.echo(OutputFormatter.format_error(f"Unknown group: {path}", fmt))
            return
        summary = [
            {
                "command": s.cli_path,
                "description": s.description,
                "mutating": s.mutating,
                "params": len(s.params),
            }
            for s in schemas.values()
        ]
        click.echo(OutputFormatter.format(summary, fmt))

    else:
        schemas = get_all_schemas()
        target = None
        for s in schemas.values():
            if s.cli_path == path or s.command == path:
                target = s
                break
        if target is None:
            click.echo(OutputFormatter.format_error(f"Unknown command: {path}", fmt))
            return
        detail = {
            "command": target.cli_path,
            "bridge_command": target.command,
            "description": target.description,
            "mutating": target.mutating,
            "timeout": target.timeout,
            "params": [
                {
                    "name": p.name,
                    "type": p.type.value,
                    "required": p.required,
                    "description": p.description,
                    **({"default": p.default} if p.default is not None else {}),
                    **({"enum_values": p.enum_values} if p.enum_values else {}),
                }
                for p in target.params
            ],
            "response_fields": target.response_fields,
        }
        click.echo(OutputFormatter.format(detail, fmt))
