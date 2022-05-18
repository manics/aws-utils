#!/usr/bin/env python

import argparse
from configparser import ConfigParser
from os.path import expanduser
import boto3
import pytz
from datetime import datetime
from sys import exit
from time import sleep


p = argparse.ArgumentParser("aws-mfa-login")
p.add_argument("--profile", help="AWS profile with login credentials", required=True)
p.add_argument(
    "--output-profile",
    help="AWS profile in credentials file to be updated with new tokens",
    required=True,
)
p.add_argument(
    "--mfa-serial-number",
    help="MFA serial number, e.g. arn:aws:iam::<ACCOUNT>:mfa/<USERNAME>",
    required=True,
)
p.add_argument("--mfa-token", help="MFA token", required=True)
p.add_argument("--assume-role-account", help="AWS Account ID to be assumed")
p.add_argument("--assume-role-name", help="AWS role name to be assumed")
p.add_argument(
    "--refresh",
    action="store_true",
    help="Keep running and auto refresh token half-way to expriry",
)


def update_session_token(token, account_id, role_name):
    session = boto3.session.Session(
        aws_access_key_id=token["Credentials"]["AccessKeyId"],
        aws_secret_access_key=token["Credentials"]["SecretAccessKey"],
        aws_session_token=token["Credentials"]["SessionToken"],
    )
    sts = session.client("sts")
    token = sts.assume_role(
        RoleArn=f"arn:aws:iam::{account_id}:role/{role_name}",
        RoleSessionName=f"nccid-{account_id}",
    )
    return token


def update_aws_credentials(profile_name, token):
    credentials_file = expanduser("~/.aws/credentials")
    credentials = ConfigParser()
    credentials.read(credentials_file)
    credentials[profile_name] = dict(
        aws_access_key_id=token["Credentials"]["AccessKeyId"],
        aws_secret_access_key=token["Credentials"]["SecretAccessKey"],
        aws_session_token=token["Credentials"]["SessionToken"],
    )
    with open(credentials_file, "w") as cfg:
        credentials.write(cfg)


def _check_arg_non_empty_string(args, name):
    s = getattr(args, name.replace("-", "_"))
    if not s:
        raise ValueError(f"{name}: Expected non-empty string")


args = p.parse_args()
for name in (
    "profile",
    "output-profile",
    "mfa-serial-number",
    "mfa-token",
    # "assume-role-account",
    # "assume-role-name",
):
    _check_arg_non_empty_string(args, name)
if bool(args.assume_role_account) != bool(args.assume_role_name):
    raise Exception("assume-role-account and assume-role-name must be used together")

session1 = boto3.session.Session(profile_name=args.profile)
sts1 = session1.client("sts")
print(args.mfa_token)
token1 = sts1.get_session_token(
    SerialNumber=args.mfa_serial_number, TokenCode=args.mfa_token
)
if not args.assume_role_account:
    update_aws_credentials(args.output_profile, token1)
    exit(0)

delay = 0
while True:
    sleep(delay)
    token2 = update_session_token(
        token1, args.assume_role_account, args.assume_role_name
    )
    exp = token2["Credentials"]["Expiration"]
    update_aws_credentials(args.output_profile, token2)
    print(f"Updated AWS profile [{args.output_profile}]")
    print(f'  arn={token2["AssumedRoleUser"]["Arn"]}')
    print(f"  expiration={exp.isoformat()}")
    if args.refresh > 0:
        delay = (exp - datetime.utcnow().replace(tzinfo=pytz.utc)).seconds * 0.5
    else:
        break
