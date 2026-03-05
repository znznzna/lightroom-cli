"""catalog set-rating の 0-5 範囲バリデーションテスト"""

from click.testing import CliRunner

from cli.main import cli


class TestSetRatingRange:
    def test_rating_below_0_rejected(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["catalog", "set-rating", "photo123", "-1"])
        assert result.exit_code != 0

    def test_rating_above_5_rejected(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["catalog", "set-rating", "photo123", "9"])
        assert result.exit_code != 0

    def test_rating_0_accepted(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["catalog", "set-rating", "photo123", "0", "--dry-run"])
        assert result.exit_code == 0

    def test_rating_5_accepted(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["catalog", "set-rating", "photo123", "5", "--dry-run"])
        assert result.exit_code == 0
