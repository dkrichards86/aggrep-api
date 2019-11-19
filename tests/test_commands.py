"""CLI tests."""
from aggrep.commands import test


def test_test_command():
    """Test the 'flask test' command."""
    ctx1 = test.make_context("test", [])
    assert ctx1.command.name == "test"
    assert ctx1.params["show_missing"] is False
    assert ctx1.params["verbose"] is False

    ctx2 = test.make_context("test", ["--show-missing"])
    assert ctx2.params["show_missing"] is True
    assert ctx2.params["verbose"] is False

    ctx3 = test.make_context("test", ["--verbose"])
    assert ctx3.params["show_missing"] is False
    assert ctx3.params["verbose"] is True

    ctx4 = test.make_context("test", ["--show-missing", "--verbose"])
    assert ctx4.params["show_missing"] is True
    assert ctx4.params["verbose"] is True
