import click

from cli.decorators import json_input_options
from cli.helpers import execute_command


@click.group()
def selection():
    """Selection commands (flag, unflag, reject, next, previous, color-label)"""
    pass


@selection.command("flag")
@click.option("--dry-run", is_flag=True, default=False, help="Preview without executing")
@json_input_options
@click.pass_context
def flag_as_pick(ctx, dry_run, **kwargs):
    """Flag selected photo(s) as Pick"""
    execute_command(ctx, "selection.flagAsPick", {})


@selection.command("reject")
@click.option("--dry-run", is_flag=True, default=False, help="Preview without executing")
@json_input_options
@click.pass_context
def flag_as_reject(ctx, dry_run, **kwargs):
    """Flag selected photo(s) as Reject"""
    execute_command(ctx, "selection.flagAsReject", {})


@selection.command("unflag")
@click.option("--dry-run", is_flag=True, default=False, help="Preview without executing")
@json_input_options
@click.pass_context
def remove_flag(ctx, dry_run, **kwargs):
    """Remove flag from selected photo(s)"""
    execute_command(ctx, "selection.removeFlag", {})


@selection.command("next")
@json_input_options
@click.pass_context
def next_photo(ctx, **kwargs):
    """Move to next photo"""
    execute_command(ctx, "selection.nextPhoto", {})


@selection.command("previous")
@json_input_options
@click.pass_context
def previous_photo(ctx, **kwargs):
    """Move to previous photo"""
    execute_command(ctx, "selection.previousPhoto", {})


@selection.command("color-label")
@click.argument("label", type=click.Choice(["red", "yellow", "green", "blue", "purple", "none"]))
@click.option("--dry-run", is_flag=True, default=False, help="Preview without executing")
@json_input_options
@click.pass_context
def set_color_label(ctx, label, dry_run, **kwargs):
    """Set color label for selected photo(s)"""
    execute_command(ctx, "selection.setColorLabel", {"label": label})


@selection.command("select-all")
@click.option("--dry-run", is_flag=True, default=False, help="Preview without executing")
@json_input_options
@click.pass_context
def select_all(ctx, dry_run, **kwargs):
    """Select all photos"""
    execute_command(ctx, "selection.selectAll", {})


@selection.command("select-none")
@click.option("--dry-run", is_flag=True, default=False, help="Preview without executing")
@json_input_options
@click.pass_context
def select_none(ctx, dry_run, **kwargs):
    """Deselect all photos"""
    execute_command(ctx, "selection.selectNone", {})


@selection.command("select-inverse")
@click.option("--dry-run", is_flag=True, default=False, help="Preview without executing")
@json_input_options
@click.pass_context
def select_inverse(ctx, dry_run, **kwargs):
    """Invert the current selection"""
    execute_command(ctx, "selection.selectInverse", {})


@selection.command("increase-rating")
@click.option("--dry-run", is_flag=True, default=False, help="Preview without executing")
@json_input_options
@click.pass_context
def increase_rating(ctx, dry_run, **kwargs):
    """Increase rating of selected photo(s) by 1"""
    execute_command(ctx, "selection.increaseRating", {})


@selection.command("decrease-rating")
@click.option("--dry-run", is_flag=True, default=False, help="Preview without executing")
@json_input_options
@click.pass_context
def decrease_rating(ctx, dry_run, **kwargs):
    """Decrease rating of selected photo(s) by 1"""
    execute_command(ctx, "selection.decreaseRating", {})


TOGGLE_LABEL_COMMANDS = {
    "red": "selection.toggleRedLabel",
    "yellow": "selection.toggleYellowLabel",
    "green": "selection.toggleGreenLabel",
    "blue": "selection.toggleBlueLabel",
    "purple": "selection.togglePurpleLabel",
}


@selection.command("toggle-label")
@click.argument("color", type=click.Choice(["red", "yellow", "green", "blue", "purple"]))
@click.option("--dry-run", is_flag=True, default=False, help="Preview without executing")
@json_input_options
@click.pass_context
def toggle_label(ctx, color, dry_run, **kwargs):
    """Toggle color label for selected photo(s)"""
    cmd = TOGGLE_LABEL_COMMANDS[color]
    execute_command(ctx, cmd, {})


@selection.command("extend")
@click.option("--direction", default="right", type=click.Choice(["left", "right"]))
@click.option("--amount", default=1, type=int)
@click.option("--dry-run", is_flag=True, default=False, help="Preview without executing")
@json_input_options
@click.pass_context
def extend_selection(ctx, direction, amount, dry_run, **kwargs):
    """Extend selection in a direction"""
    execute_command(ctx, "selection.extendSelection", {"direction": direction, "amount": amount})


@selection.command("deselect-active")
@click.option("--dry-run", is_flag=True, default=False, help="Preview without executing")
@json_input_options
@click.pass_context
def deselect_active(ctx, dry_run, **kwargs):
    """Deselect the active photo"""
    execute_command(ctx, "selection.deselectActive", {})


@selection.command("deselect-others")
@click.option("--dry-run", is_flag=True, default=False, help="Preview without executing")
@json_input_options
@click.pass_context
def deselect_others(ctx, dry_run, **kwargs):
    """Deselect all except active photo"""
    execute_command(ctx, "selection.deselectOthers", {})


@selection.command("get-flag")
@json_input_options
@click.pass_context
def get_flag(ctx, **kwargs):
    """Get flag status of selected photo"""
    execute_command(ctx, "selection.getFlag", {})


@selection.command("get-rating")
@json_input_options
@click.pass_context
def get_rating(ctx, **kwargs):
    """Get rating of selected photo"""
    execute_command(ctx, "selection.getRating", {})


@selection.command("set-rating")
@click.argument("rating", type=click.IntRange(0, 5))
@click.option("--dry-run", is_flag=True, default=False, help="Preview without executing")
@json_input_options
@click.pass_context
def set_rating(ctx, rating, dry_run, **kwargs):
    """Set rating for selected photo (0-5)"""
    execute_command(ctx, "selection.setRating", {"rating": rating})


@selection.command("get-color-label")
@json_input_options
@click.pass_context
def get_color_label(ctx, **kwargs):
    """Get color label of selected photo"""
    execute_command(ctx, "selection.getColorLabel", {})
