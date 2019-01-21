#!/usr/bin/env python

import boto3
import time
import yaml
import passgen

dry_run = False

with open("create-config.yaml", "r") as yamlfile:
    config = yaml.load(yamlfile)

# Variable to Control Access
if "workshop_username" in config:
    workshop_username = config["workshop_username"]
else:
    workshop_username = "workshop"

if "role_name" in config:
    role_name = config["role_name"]
else:
    role_name = "OrganizationAccountAccessRole"

if "output_file_name" in config:
    output_file_name = config["output_file_name"]
else:
    output_file_name = "accounts.csv"

accounts_to_create = config["accounts_to_create"]
account_description_prefix = config["account_description_prefix"]
alias_prefix = config["alias_prefix"]
email_prefix = config["email_prefix"]
email_suffix = config["email_suffix"]

# workshop_username = "workshop"
# role_name = "OrganizationAccountAccessRole"
# accounts_to_create = 20

# Functions (Needs Refactoring)


def gen_password():
    try:
        if "workshop_password" in config:
            return config["workshop_password"]
        else:
            password = passgen.passgen()
            return password

    except Exception as error:
        print(error)


def create_alias_and_user(account, role_to_assume, username, password, alias):
    try:
        # Assume Role in Account
        print("Assuming Role: {} in Account: {}".format(role_to_assume, account))

        sts_client = boto3.client('sts')
        assumedRoleObject = sts_client.assume_role(
            RoleArn="arn:aws:iam::{}:role/{}".format(account, role_to_assume),
            RoleSessionName="CreateIAMUserSession"
        )

        credentials = assumedRoleObject['Credentials']

        client = boto3.client(
            'iam',
            aws_access_key_id=credentials['AccessKeyId'],
            aws_secret_access_key=credentials['SecretAccessKey'],
            aws_session_token=credentials['SessionToken'],
        )

        # Create Account Alias
        print("Creating Account Alias: {} in Account {}".format(alias, account))
        response = client.create_account_alias(
            AccountAlias=alias,
        )

        print("Alias Created: {}".format(response))

        # Create IAM User
        print("Creating User: {} in Account {}".format(username, account))
        response = client.create_user(
            UserName=username,
        )

        print("User Created: {}".format(response))

        # Create Login Profile for User
        print("Creating Login Profile for User: {} in Account {}".format(
            username, account))
        response = client.create_login_profile(
            UserName=username,
            Password=password,
            PasswordResetRequired=False
        )

        # Attach Administrator Policy to IAM User
        print("Attaching AdministratorAccess Policy to User: {} in Account {}".format(
            username, account))

        iam = boto3.resource(
            'iam',
            aws_access_key_id=credentials['AccessKeyId'],
            aws_secret_access_key=credentials['SecretAccessKey'],
            aws_session_token=credentials['SessionToken'],
        )

        user = iam.User(username)

        response = user.attach_policy(
            PolicyArn='arn:aws:iam::aws:policy/AdministratorAccess'
        )

        console_link = "https://{}.signin.aws.amazon.com/console".format(
            alias)

        print("User Created: {},{},{},{}".format(
            account, username, password, console_link))

        text_file = open(output_file_name, "a")
        text_file.write("{},{},{},{}\n".format(
            account, username, password, console_link))
        text_file.close()

    except Exception as error:
        print(error)

# Main


def main():

    try:
        for num in range(accounts_to_create):
            i = num + 1  # no one wants to be account number zero
            email = "{}{:02d}{}".format(
                email_prefix, i, email_suffix)
            name = "{}{:02d}".format(account_description_prefix, i)
            alias = "{}{:02d}".format(alias_prefix, i)
            user_password = gen_password()

            if dry_run:
                print("Would create account using email {} and name {} and role {}".format(
                    email, name, role_name))
                print("Then would name account using alias {}".format(alias))
                print("Then would create user {} with password {}".format(workshop_username,
                                                                          user_password))
            else:
                print("Attempting to create account Name: {} under email {}".format(
                    name, email))
                client = boto3.client('organizations')
                create_response = client.create_account(
                    Email=email,
                    AccountName=name,
                    RoleName=role_name
                )

                account_status = 'IN_PROGRESS'

                while account_status == 'IN_PROGRESS':
                    print("Waiting for account creation to finish...")
                    time.sleep(10)
                    create_account_status_response = client.describe_create_account_status(
                        CreateAccountRequestId=create_response.get('CreateAccountStatus').get('Id'))

                    # print("DEBUG: Create account status " +
                    #       str(create_account_status_response))
                    account_status = create_account_status_response.get(
                        'CreateAccountStatus').get('State')

                if account_status == 'SUCCEEDED':
                    account_id = create_account_status_response.get(
                        'CreateAccountStatus').get('AccountId')
                    print(
                        "Account creation SUCCEEDED for Account: {}".format(account_id))
                    create_alias_and_user(account_id, role_name,
                                          workshop_username, user_password, alias)

                elif account_status == 'FAILED':
                    failure_reason = create_account_status_response.get(
                        'CreateAccountStatus').get('FailureReason')
                    if failure_reason == "EMAIL_ALREADY_EXISTS":
                        print(
                            "Account already exists under email {}. Skipping...".format(email))
                    else:
                        print("Account creation failed: " + failure_reason)

    except Exception as error:
        print(error)


# Run Main
if __name__ == "__main__":
    main()
