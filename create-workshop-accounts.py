#!/usr/bin/env python

import sys
import boto3
import time
import yaml
import passgen

dry_run = False
debug = True

#### CONFIG ####
configfile = "create-config.yaml"

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

#### FUNCTIONS ####


def get_password():
    try:
        if "iam_password" in config:
            return config["iam_password"]
        else:
            password = passgen.passgen()
            return password

    except Exception as error:
        print(error)


def create_alias_and_user(
    account, role_to_assume, username, password, alias, output_file_name
):
    try:
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

        client = boto3.client(
            "iam",
            aws_access_key_id=credentials["AccessKeyId"],
            aws_secret_access_key=credentials["SecretAccessKey"],
            aws_session_token=credentials["SessionToken"],
        )

        # Create Account Alias
        print("Creating Account Alias: {} in Account {}".format(alias, account))

        response = client.create_account_alias(AccountAlias=alias)
        print("Alias Created.")
        if debug:
            print("DEBUG: create_account_alias response: {}".format(response))

        # Create IAM User
        print("Creating User: {} in Account {}".format(username, account))

        response = client.create_user(UserName=username)
        if debug:
            print("DEBUG: create_user response: {}".format(response))
        print("User Created.")

        # Create Login Profile for User
        print(
            "Creating Login Profile for User: {} in Account {}".format(
                username, account
            )
        )
        response = client.create_login_profile(
            UserName=username, Password=password, PasswordResetRequired=False
        )
        if debug:
            print("DEBUG: create_login_profile response: {}".format(response))

        # Attach Administrator Policy to IAM User
        print(
            "Attaching AdministratorAccess Policy to User: {} in Account {}".format(
                username, account
            )
        )

        iam = boto3.resource(
            "iam",
            aws_access_key_id=credentials["AccessKeyId"],
            aws_secret_access_key=credentials["SecretAccessKey"],
            aws_session_token=credentials["SessionToken"],
        )

        user = iam.User(username)

        response = user.attach_policy(
            PolicyArn="arn:aws:iam::aws:policy/AdministratorAccess"
        )

        console_link = "https://{}.signin.aws.amazon.com/console".format(alias)

        print(
            "User Created: {},{},{},{}".format(
                account, username, password, console_link
            )
        )

        text_file = open(output_file_name, "a")
        text_file.write(
            "{},{},{},{}\n".format(account, username, password, console_link)
        )
        text_file.close()

    except Exception as error:
        print(error)


#### MAIN ####


def main():

    try:
        for num in range(config["num_accounts"]):
            i = num + 1  # no one wants to be account number zero
            email = "{}{:02d}{}".format(
                config["email_prefix"], i, config["email_suffix"]
            )
            name = "{}{:02d}".format(config["account_description_prefix"], i)
            alias = "{}{:02d}".format(config["alias_prefix"], i)
            iam_password = get_password()
            iam_username = config["iam_username"]
            role_name = config["role_name"]
            output_file_name = config["output_file_name"]

            if dry_run:
                print(
                    "Would create account using email {} and name {} and role {}".format(
                        email, name, role_name
                    )
                )
                print("Then would name account using alias {}".format(alias))
                print(
                    "Then would create user {} with password {}".format(
                        iam_username, iam_password
                    )
                )
            else:
                print(
                    "Attempting to create account Name: {} under email {}".format(
                        name, email
                    )
                )
                client = boto3.client("organizations")
                create_response = client.create_account(
                    Email=email, AccountName=name, RoleName=role_name
                )

                account_status = "IN_PROGRESS"

                while account_status == "IN_PROGRESS":
                    print("Waiting for account creation to finish...")
                    time.sleep(10)
                    create_account_status_response = client.describe_create_account_status(
                        CreateAccountRequestId=create_response.get(
                            "CreateAccountStatus"
                        ).get("Id")
                    )

                    # print("DEBUG: Create account status " +
                    #       str(create_account_status_response))
                    account_status = create_account_status_response.get(
                        "CreateAccountStatus"
                    ).get("State")

                if account_status == "SUCCEEDED":
                    account_id = create_account_status_response.get(
                        "CreateAccountStatus"
                    ).get("AccountId")
                    print(
                        "Account creation SUCCEEDED for Account: {}".format(account_id)
                    )
                    create_alias_and_user(
                        account_id,
                        role_name,
                        iam_username,
                        iam_password,
                        alias,
                        output_file_name,
                    )

                elif account_status == "FAILED":
                    failure_reason = create_account_status_response.get(
                        "CreateAccountStatus"
                    ).get("FailureReason")
                    if failure_reason == "EMAIL_ALREADY_EXISTS":
                        print(
                            "Account already exists under email {}. Skipping...".format(
                                email
                            )
                        )
                    else:
                        print("Account creation failed: " + failure_reason)

    except Exception as error:
        print(error)


if __name__ == "__main__":
    main()
