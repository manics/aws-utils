# AWS Utilities

## [`awsutils/aws-login-mfa.py`](awsutils/aws-login-mfa.py)

Helper for using MFA logins with AWS Command line login.

## [`awsutils/aws-sso-update-config.py`](awsutils/aws-sso-update-config.py)

Update or replace the `~/.aws/config` file with new SSO accounts.
Requires:

- an active SSO session (`aws sso login`)
- a configuration file for this utility (`cp awsutils/aws-sso-update-config.yaml.template awsutils/aws-sso-update-config.yaml`, edit)
