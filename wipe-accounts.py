#!/usr/bin/env python

import subprocess
import sys
import boto3
import csv
import yaml
import pexpect
import tempfile

if not (sys.version_info < (3, 0)):
    sys.exit("err: this script doesn't support Python 3+. Try again with Python 2")

dry_run = False
debug = False
force = True  # go non-interactive. no turning back!

configfile = "config.yaml"

with open(configfile, "r") as yamlfile:
    config = yaml.load(yamlfile)


# Required variables
for var in [
    "num_accounts",
    "alias_prefix",
    "iam_username",
    "account_description_prefix",
    "email_prefix",
    "email_suffix",
]:
    if not var in config:
        sys.exit("err: required variable {} not set in {}".format(var, configfile))

if not "role_name" in config:
    config["role_name"] = "OrganizationAccountAccessRole"

if not "output_file_name" in config:
    config["output_file_name"] = "{}.csv".format(config["alias_prefix"])

def main():
    # open csv file
    accounts = get_account_numbers()
    nuke_config_file = tempfile.NamedTemporaryFile(delete=False)
    create_nuke_config(accounts.keys(), nuke_config_file)  # the account numbers
    if debug:
        with open(nuke_config_file.name, "r") as f:
            print(f.read())
    for account_number in accounts:
        wipe_account(account_number, accounts[account_number], nuke_config_file.name)
    nuke_config_file.delete()


def get_account_numbers():
    account_numbers = []
    accounts = {}
    with open(config["output_file_name"], "r") as csvcontent:
        for row in csv.reader(csvcontent):
            account_number = row[0]
            alias = row[1]

            account_numbers.append(row[0])
            accounts[account_number] = alias
    return accounts


def get_credentials(role_to_assume, account):
    # Assume Role in Account
    print("Assuming Role: {} in Account: {}".format(role_to_assume, account))

    sts_client = boto3.client("sts")
    if debug:
        response = sts_client.get_caller_identity()
        print("DEBUG: get_caller_identity response: {}".format(response))

    assumedRoleObject = sts_client.assume_role(
        RoleArn="arn:aws:iam::{}:role/{}".format(account, role_to_assume),
        RoleSessionName="CreateIAMUserSession",
    )
    if debug:
        print("DEBUG: assume_role response: {}".format(assumedRoleObject))

    credentials = assumedRoleObject["Credentials"]
    return credentials


def create_nuke_config(account_numbers, nuke_config_file):
    sts_client = boto3.client("sts")
    response = sts_client.get_caller_identity()
    if debug:
        print("DEBUG: get_caller_identity response: {}".format(response))

    parent_account_number = response["Account"]

    nuke_config = {}
    nuke_config["regions"] = ["us-east-1", "us-west-2"]
    nuke_config["account-blacklist"] = [parent_account_number]
    nuke_config["accounts"] = {}
    for account_number in account_numbers:
        nuke_config["accounts"][account_number] = {}

    nuke_config_file.write(yaml.dump(nuke_config, default_flow_style=False))
    nuke_config_file.close()


def wipe_account(account_number, account_alias, nuke_config_file_name):
    credentials = get_credentials(config["role_name"], account_number)

    if dry_run:
        dry_run_toggle = ""
    else:
        dry_run_toggle = "--no-dry-run"

    if force:
        force_toggle = "--force"
    else:
        force_toggle = ""

    nuke_command = "/usr/local/bin/aws-nuke -c {} \
        --access-key-id {} \
        --secret-access-key {} \
        --session-token {} \
        --force-sleep 3 \
        {} \
        {} \
        ".format(
        nuke_config_file_name,
        credentials["AccessKeyId"],
        credentials["SecretAccessKey"],
        credentials["SessionToken"],
        dry_run_toggle,
        force_toggle,
    )

    if debug:
        print(nuke_command)

    process = pexpect.spawn(nuke_command, encoding="utf-8")
    process.interact()


if __name__ == "__main__":
    main()
