#!/usr/bin/env python
# coding: utf-8

# This script requires an active AWS SSO session (aws sso login) since it searches for a cached access token under ~/.aws/cache

from argparse import ArgumentParser
import boto3
from configparser import ConfigParser
import json
from os.path import expanduser
from pathlib import Path
import sys
import yaml


aws_config_file = expanduser("~/.aws/config")
cache_dir = expanduser("~/.aws/sso/cache/")
default_util_config_file = Path(__file__).parent / "aws-sso-update-config.yaml"


def get_utility_config(util_config_file):
    with open(util_config_file) as f:
        return yaml.safe_load(f)


def get_aws_config(config_file):
    config = ConfigParser()
    if config_file:
        config.read(config_file)
    return config


def add_if_not_found(config, account_name, account_id, role, util_config):
    profile = f"profile {account_name}"
    if profile not in config:
        conf = util_config["default_config"].copy()
        conf["sso_account_id"] = account_id
        conf["sso_role_name"] = role
        config[profile] = conf
        return conf
    return None


def get_sso_accounts(cache_dir, util_config):
    sso_caches = list(
        Path(cache_dir).glob("????????????????????????????????????????.json")
    )
    access_token = None
    for sso_cache in sso_caches:
        try:
            with sso_cache.open() as f:
                access_token = json.load(f)["accessToken"]
        except KeyError:
            continue
    if not access_token:
        raise Exception(f"No SSO access token found in {cache_dir}")
    sso = boto3.client("sso", region_name=util_config["sso_region"])
    accounts = sso.list_accounts(maxResults=1000, accessToken=access_token)
    for account in accounts["accountList"]:
        roles = sso.list_account_roles(
            maxResults=100, accessToken=access_token, accountId=account["accountId"]
        )
        account["roles"] = [r["roleName"] for r in roles["roleList"]]
    return accounts["accountList"]


def normalise_account_name(name):
    name = name.lower().replace(" ", "-")
    return name


def generate_aws_config(replace, util_config):
    sso_role_names = util_config["sso_role_names"]
    if not sso_role_names:
        sso_role_names = [util_config["sso_role_name"]["sso_role_names"]]
    if replace:
        config_file = None
    else:
        config_file = aws_config_file
    config = get_aws_config(config_file)
    accounts = get_sso_accounts(cache_dir, util_config)

    for account in accounts:
        for role in sso_role_names:
            if role in account["roles"]:
                break
        else:
            raise ValueError(f"role {sso_role_names} not found in {account}")
        r = add_if_not_found(
            config,
            normalise_account_name(account["accountName"]),
            account["accountId"],
            role,
            util_config,
        )
        # if r:
        #     print(f"Added {account}")

    # Order alphabetically
    # WARNING: This relies on an internal ConfigParser implementation detail
    for section in config._sections:
        config._sections[section] = dict(
            sorted(config._sections[section].items(), key=lambda t: t[0])
        )
    config._sections = dict(sorted(config._sections.items(), key=lambda t: t[0]))

    # Add aliases
    for k, v in sorted(util_config.get("aliases", {}).items()):
        config[f"profile {v}"] = config[f"profile {k}"]

    config.write(sys.stdout)


def main():
    parser = ArgumentParser(
        description="""Generate an updated ~/.aws/config file with new SSO accounts.

Writes to stdout.

Requires an active SSO command line session (aws sso login)
"""
    )
    parser.add_argument(
        "--replace",
        action="store_true",
        help="Ignore existing entries in ~/.aws/config",
    )
    parser.add_argument(
        "--util-config",
        default=default_util_config_file,
        help="Utility configuration file",
    )
    args = parser.parse_args()

    util_config = get_utility_config(args.util_config)
    generate_aws_config(args.replace, util_config)


if __name__ == "__main__":
    main()
