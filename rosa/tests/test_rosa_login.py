import pytest
from rosa.cli import is_logged_in, NotLoggedInOrWrongEnvError


ROSA_ENV = "rosa_env"
AWS_REGION_STR = "us-east-1"
ROSA_CMD = "whoami"


@pytest.fixture
def mock_build_execute_command(mocker):
    return mocker.patch("rosa.cli.build_execute_command")


@pytest.fixture()
def allowed_commands():
    return [ROSA_CMD]


def test_is_logged_in_success(mock_build_execute_command, allowed_commands):
    mock_build_execute_command.return_value = {"out": {"OCM API": ROSA_ENV}, "err": None}

    is_logged_in(env=ROSA_ENV, aws_region=AWS_REGION_STR, allowed_commands=allowed_commands)

    mock_build_execute_command.assert_called_once_with(
        command=ROSA_CMD, aws_region=AWS_REGION_STR, allowed_commands=allowed_commands
    )


@pytest.mark.parametrize(
    "mock_command, expected",
    [
        (
            {"out": {"OCM API": "wrong_env"}, "err": None},
            f"User is logged in to OCM in wrong_env environment and not {ROSA_ENV} environment.",
        ),
        (
            {"out": "not_a_dict", "err": None},
            "Rosa `out` is not a dict': not_a_dict",
        ),
        (
            {"out": {}, "err": "some_error"},
            "Failed to execute 'rosa whoami': some_error",
        ),
    ],
)
def test_is_logged_in_error(mock_command, expected, mock_build_execute_command, allowed_commands):
    mock_build_execute_command.return_value = mock_command

    with pytest.raises(NotLoggedInOrWrongEnvError, match=expected):
        is_logged_in(env=ROSA_ENV, aws_region=AWS_REGION_STR, allowed_commands=allowed_commands)
