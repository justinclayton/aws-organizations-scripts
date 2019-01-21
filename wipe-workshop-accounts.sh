#!/usr/bin/env bash

account_number=$1
dry_run_toggle=""
configfile="nuke-config.yaml"

if [[ $2 == "-f" ]]; then
  dry_run_toggle="--no-dry-run"
fi

newcreds=$(aws sts assume-role --role-session-name prepare-to-nuke --role-arn arn:aws:iam::${account_number}:role/OrganizationAccountAccessRole)
aws_access_key_id=$(echo ${newcreds} | jq -r .Credentials.AccessKeyId)
aws_secret_access_key=$(echo ${newcreds} | jq -r .Credentials.SecretAccessKey)
aws_session_token=$(echo ${newcreds} | jq -r .Credentials.SessionToken)

aws-nuke \
  -c $configfile \
  --access-key-id $aws_access_key_id \
  --secret-access-key $aws_secret_access_key \
  --session-token $aws_session_token \
  ${dry_run_toggle}