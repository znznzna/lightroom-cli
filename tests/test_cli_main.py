import pytest
from click.testing import CliRunner
from cli.main import cli


@pytest.fixture
def runner():
    return CliRunner()


def test_cli_help(runner):
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "Lightroom Classic CLI" in result.output


def test_cli_output_option(runner):
    result = runner.invoke(cli, ["--help"])
    assert "--output" in result.output or "-o" in result.output


def test_cli_verbose_option(runner):
    result = runner.invoke(cli, ["--help"])
    assert "--verbose" in result.output or "-v" in result.output


def test_cli_timeout_option(runner):
    result = runner.invoke(cli, ["--help"])
    assert "--timeout" in result.output or "-t" in result.output


def test_cli_version(runner):
    result = runner.invoke(cli, ["--version"])
    assert result.exit_code == 0
