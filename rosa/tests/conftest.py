from rosa.cli import parse_help


def path_from_dict(_dict, _path=""):
    aws_region_str = "aws_region"
    end_values = ["json_output", "auto_answer_yes", "auto_mode", "region"]

    for key, val in _dict.items():
        if all([True if _key in end_values else False for _key in val.keys()]):
            yield {
                "command": f"{_path}{key}",
                aws_region_str: aws_region_str if val["region"] else None,
            }
        else:
            yield from path_from_dict(_dict=val, _path=f"{key} ")


def pytest_generate_tests(metafunc):
    if "rosa_commands" in metafunc.fixturenames:
        parametrized = list(path_from_dict(_dict=parse_help()))
        metafunc.parametrize("rosa_commands", parametrized, indirect=True)
