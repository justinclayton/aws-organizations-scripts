# Using Organizations For Workshops

## Creating Accounts

1. Make sure you have a working python environment with `boto3` installed. If you don't have a clean setup, you can run something like this:

```
virtualenv mypythonenv
source ./mypythonenv/bin/activate
pip install boto3
```

2. Edit the included `create-config.yaml` file to meet your needs.
3. Run `./create-workshop-accounts.py`

## Wiping Accounts

1. Download the `aws-nuke` binary from https://github.com/rebuy-de/aws-nuke/releases
2. Put it somewhere in your PATH and make it executable.
3. Edit the included `nuke-config.yaml` file to meet your needs.
4. Run `./wipe-workshop-accounts.sh <account_number>`