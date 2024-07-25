import pytest
from rosa.cli import is_logged_in, NotLoggedInOrWrongEnvError


ROSA_ENV = "rosa_env"
AWS_REGION_STR = "us-east-1"


@pytest.fixture
def mock_build_execute_command(mocker):
    return mocker.patch("rosa.cli.build_execute_command")


@pytest.fixture()
def allowed_commands():
    return ["whoami"]


def test_is_logged_in_success(mock_build_execute_command, allowed_commands):
    mock_build_execute_command.return_value = {"out": {"OCM API": ROSA_ENV}, "err": None}

    is_logged_in(env=ROSA_ENV, aws_region=AWS_REGION_STR, allowed_commands=allowed_commands)

    mock_build_execute_command.assert_called_once_with(
        command="whoami", aws_region=AWS_REGION_STR, allowed_commands=allowed_commands
    )


def test_is_logged_in_with_wrong_env(mock_build_execute_command, allowed_commands):
    mock_response = {"out": {"OCM API": "wrong_env"}, "err": None}
    mock_build_execute_command.return_value = mock_response

    logged_in_ocm_env = mock_response["out"].get("OCM API")
    with pytest.raises(
        NotLoggedInOrWrongEnvError,
        match=f"User is logged in to OCM in {logged_in_ocm_env} environment and not {ROSA_ENV} environment.",
    ):
        is_logged_in(env=ROSA_ENV, aws_region=AWS_REGION_STR, allowed_commands=allowed_commands)


def test_is_logged_in_response_not_dict(mock_build_execute_command, allowed_commands):
    mock_response = {"out": "not_a_dict", "err": None}
    mock_build_execute_command.return_value = mock_response

    with pytest.raises(NotLoggedInOrWrongEnvError, match=f"Rosa `out` is not a dict': {mock_response['out']}"):
        is_logged_in(env=ROSA_ENV, aws_region=AWS_REGION_STR, allowed_commands=allowed_commands)


def test_is_logged_in_error_in_response(mock_build_execute_command, allowed_commands):
    mock_response = {"out": {}, "err": "some_error"}
    mock_build_execute_command.return_value = mock_response

    with pytest.raises(
        NotLoggedInOrWrongEnvError, match=f"Failed to execute 'rosa whoami': {mock_response.get('err')}"
    ):
        is_logged_in(env=ROSA_ENV, aws_region=AWS_REGION_STR, allowed_commands=allowed_commands)
