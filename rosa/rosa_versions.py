import re
from typing import Dict, List
from functools import lru_cache

import rosa.cli
from ocm_python_wrapper.ocm_client import OCMPythonClient


@lru_cache
def get_rosa_versions(
    ocm_client: OCMPythonClient, aws_region: str, channel_group: str = "stable", hosted_cp: bool = False
) -> Dict[str, Dict[str, List[str]]]:
    """
    Get all rosa versions for specified channel group.

    Args:
        ocm_client: OCM client
        channel_group: Lists only versions from the specified channel group. Default is 'stable'
        aws_region: For using a specific AWS region
        hosted_cp: If True, lists only versions that are hosted-cp enabled

    Returns:
        dict: ROSA versions

    Examples:
        >>> get_rosa_versions(ocm_client=ocm_client, aws_region="us-east-1", channel_group='candidate')
        {'candidate': {'4.17': ['4.17.0-rc.0', '4.17.0-ec.3', '4.17.0-ec.2', '4.17.0-ec.1', '4.17.0-ec.0'],
                       '4.16': [4.16.3', '4.16.2', '4.16.1', '4.16.0', '4.16.0-rc.9', '4.16.0-rc.6'],
                       '4.15': ['4.15.32', '4.15.31', '4.15.30', '4.15.29', '4.15.28', '4.15.27']}}

    """
    rosa_base_available_versions_dict: Dict = {}
    base_available_versions = rosa.cli.execute(
        command=(f"list versions --channel-group={channel_group} {'--hosted-cp' if hosted_cp else ''}"),
        aws_region=aws_region,
        ocm_client=ocm_client,
    )["out"]
    _all_versions: List = [ver["raw_id"] for ver in base_available_versions]
    rosa_base_available_versions_dict[channel_group] = {}
    for _version in _all_versions:
        _version_key = re.findall(r"^\d+.\d+", _version)[0]
        rosa_base_available_versions_dict[channel_group].setdefault(_version_key, []).append(_version)

    return rosa_base_available_versions_dict
