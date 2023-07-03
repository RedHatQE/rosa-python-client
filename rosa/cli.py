import contextlib
import functools
import json
import os
import re
import shlex
import subprocess

from benedict import benedict
from clouds.aws.aws_utils import set_and_verify_aws_credentials
from simple_logger.logger import get_logger


LOGGER = get_logger(__name__)
TIMEOUT_5MIN = 5 * 60


class MissingAWSCredentials(Exception):
    pass


class CommandExecuteError(Exception):
    pass


class NotLoggedInError(Exception):
    pass


@contextlib.contextmanager
def rosa_login_logout(env, token, aws_region, allowed_commands=None):
    _allowed_commands = allowed_commands or parse_help()
    build_execute_command(
        command=f"login {f'--env={env}' if env else ''} --token={token}",
        allowed_commands=_allowed_commands,
        aws_region=aws_region,
    )
    if not is_logged_in(allowed_commands=_allowed_commands, aws_region=aws_region):
        raise NotLoggedInError("Failed to login to AWS.")

    yield
    build_execute_command(command="logout", allowed_commands=_allowed_commands)


@contextlib.contextmanager
def change_home_environment():
    current_home = os.environ.get("HOME")
    os.environ["HOME"] = "/tmp/"
    yield
    os.environ["HOME"] = current_home


def is_logged_in(aws_region=None, allowed_commands=None):
    _allowed_commands = allowed_commands or parse_help()
    try:
        res = build_execute_command(
            command="whoami", aws_region=aws_region, allowed_commands=_allowed_commands
        )
        return "User is not logged in to OCM" not in res["err"]
    except CommandExecuteError:
        return False


def execute_command(command, wait_timeout=TIMEOUT_5MIN):
    joined_command = " ".join(command)
    LOGGER.info(
        f"Executing command: {re.sub(r'(--token=.* |--token=.*)', '--token=hashed-token', joined_command)}, "
        f"waiting for {wait_timeout} seconds."
    )
    res = subprocess.run(command, capture_output=True, text=True, timeout=wait_timeout)
    if res.returncode != 0:
        raise CommandExecuteError(f"Failed to execute: {res.stderr}")

    return parse_json_response(response=res)


def check_flag_in_flags(command_list, flag_str):
    available_flags = get_available_flags(command=command_list)
    for flag in available_flags:
        if flag_str in flag:
            return True
    return False


def build_command(command, allowed_commands=None, aws_region=None):
    _allowed_commands = allowed_commands or parse_help()
    _user_command = shlex.split(command)
    command = ["rosa"]
    command.extend(_user_command)
    commands_to_process = [_cmd for _cmd in _user_command if not _cmd.startswith("--")]
    commands_dict = benedict(_allowed_commands, keypath_separator=" ")
    _output = commands_dict[commands_to_process]

    if _output.get("json_output") is True:
        command.append("-ojson")

    if _output.get("auto_answer_yes") is True:
        command.append("--yes")

    if _output.get("auto_mode") is True:
        command.append("--mode=auto")

    if _output.get("region") is True and aws_region:
        command.append(f"--region={aws_region}")

    return command


def get_available_commands(command):
    __available_commands = []
    command.append("--help")
    res = subprocess.run(command, capture_output=True, check=True, text=True)
    available_commands = re.findall(
        r"Available Commands:(.*)\nFlags:", res.stdout, re.DOTALL
    )
    if available_commands:
        available_commands = available_commands[0]
        available_commands = available_commands.strip()
        for _command in available_commands.splitlines():
            if _command:
                _command = _command.split()[0]
                _command = _command.strip()
                __available_commands.append(_command)
    return __available_commands


def get_available_flags(command):
    command.append("--help")
    available_flags = subprocess.run(
        command, capture_output=True, check=True, text=True
    )
    available_flags = re.findall(
        r"Flags:(.*)Global Flags:(.*)", available_flags.stdout, re.DOTALL
    )
    if available_flags:
        available_flags = " ".join([flags for flags in available_flags[0]])
        available_flags = available_flags.strip()
        return available_flags.splitlines()
    return []


@functools.cache
def parse_help(rosa_cmd="rosa"):
    commands_dict = benedict()

    def _fill_commands_dict_with_support_flags(flag_key_path):
        support_commands = {
            "json_output": "-o, --output",
            "auto_answer_yes": "-y, --yes",
            "auto_mode": "-m, --mode",
            "region": "--region",
        }
        for cli_flag, flag_value in support_commands.items():
            commands_dict[flag_key_path][cli_flag] = check_flag_in_flags(
                command_list=["rosa"] + flag_key_path,
                flag_str=flag_value,
            )

    _commands = get_available_commands(command=[rosa_cmd])

    for command in _commands:
        commands_dict.setdefault(command, {})

    for top_command in commands_dict.keys():
        sub_commands = get_available_commands(command=["rosa", top_command])

        if sub_commands:
            # If top command has sub command
            for command in sub_commands:
                sub_search_path = [top_command, command]
                commands_dict[sub_search_path] = {}
                complementary_sub_commands = get_available_commands(
                    command=["rosa"] + sub_search_path
                )
                if complementary_sub_commands:
                    # If sub command has sub command
                    for _command in complementary_sub_commands:
                        complementary_search_path = [top_command, command, _command]
                        commands_dict[complementary_search_path] = {}
                        _fill_commands_dict_with_support_flags(
                            flag_key_path=complementary_search_path
                        )
                else:
                    # If sub command doesn't have sub command
                    _fill_commands_dict_with_support_flags(
                        flag_key_path=sub_search_path
                    )
        else:
            # If top command doesn't have sub command
            _fill_commands_dict_with_support_flags(flag_key_path=[top_command])

    return commands_dict


@functools.cache
def parse_help_1(rosa_cmd="rosa"):
    commands_dict = benedict()

    def _fill_commands_dict_with_support_flags(flag_key_path):
        support_commands = {
            "json_output": "-o, --output",
            "auto_answer_yes": "-y, --yes",
            "auto_mode": "-m, --mode",
            "region": "--region",
        }
        for cli_flag, flag_value in support_commands.items():
            commands_dict[flag_key_path][cli_flag] = check_flag_in_flags(
                command_list=["rosa"] + flag_key_path,
                flag_str=flag_value,
            )

    def _build_command_tree(commands_search_path):
        sub_commands = get_available_commands(command=["rosa"] + commands_search_path)
        if not sub_commands:
            return _fill_commands_dict_with_support_flags(
                flag_key_path=commands_search_path
            )
        for sub_command in sub_commands:
            commands_dict[commands_search_path, sub_command] = {}
            _build_command_tree(commands_search_path + [sub_command])

    _build_command_tree([])

    return commands_dict


def parse_json_response(response):
    def _try_json_load(arg):
        try:
            return json.loads(arg)
        except json.decoder.JSONDecodeError:
            return arg

    return {
        "out": _try_json_load(response.stdout),
        "err": _try_json_load(response.stderr),
    }


def build_execute_command(command, allowed_commands=None, aws_region=None):
    _allowed_commands = allowed_commands or parse_help()
    command = build_command(
        command=command, allowed_commands=_allowed_commands, aws_region=aws_region
    )
    return execute_command(command=command)


def execute(
    command,
    allowed_commands=None,
    ocm_env="production",
    token=None,
    ocm_client=None,
    aws_region=None,
):
    """
    Support commands and execute with ROSA cli

    If 'token' or 'ocm_client' is passed, log in to rosa execute the command and then logout.

    Args:
        command (str): ROSA cli command to execute.
        allowed_commands (dict): Commands dict of dicts with following
            options for each entry.
        ocm_env (str): OCM env to log in into.
        token (str): Access or refresh token generated from https://console.redhat.com/openshift/token/rosa.
        ocm_client (OCMPythonClient): OCM client to use for log in.
        aws_region (str): AWS region to use for ROSA commands.

    Example:
        allowed_commands = {'create':
            {'account-roles': {'json_output': False, 'auto_answer_yes': True,
                'auto_mode': True, 'billing_model': False},
            'admin': {'json_output': True, 'auto_answer_yes': True, 'auto_mode': False, 'billing_model': False},
            'cluster': {'json_output': True, 'auto_answer_yes': True, 'auto_mode': True, 'billing_model': False}
            }}

    Returns:
        dict: {'out': res.stdout, 'err': res.stderr}
            res.stdout/stderr will be parsed as json if possible, else str
    """
    _allowed_commands = allowed_commands or parse_help()

    if token or ocm_client:
        set_and_verify_aws_credentials()

        if ocm_client:
            ocm_env = ocm_client.api_client.configuration.host
            token = ocm_client.api_client.token

        with change_home_environment(), rosa_login_logout(
            env=ocm_env,
            token=token,
            aws_region=aws_region,
            allowed_commands=_allowed_commands,
        ):
            return build_execute_command(
                command=command,
                allowed_commands=_allowed_commands,
                aws_region=aws_region,
            )
    else:
        if not is_logged_in(allowed_commands=_allowed_commands, aws_region=aws_region):
            raise NotLoggedInError(
                "Not logged in to OCM, either pass 'token' or log in before running."
            )

        return build_execute_command(
            command=command, allowed_commands=_allowed_commands, aws_region=aws_region
        )


if __name__ == "__main__":
    """
    for local debugging.
    """
