# Using Organizations For Workshops

## Creating Accounts

1. Make sure you have a working python environment with `boto3` installed. If you don't have a clean setup, you can run something like this:

```
virtualenv mypythonenv
source ./mypythonenv/bin/activate
pip install -r requirements.txt
```

2. Copy the included `config.example.yaml` file to `config.yaml` and edit to meet your needs.
3. Run `./create-workshop-accounts.py`

## Wiping Accounts

1. Download the `aws-nuke` binary from https://github.com/rebuy-de/aws-nuke/releases
2. Put it in /usr/local/bin and make it executable.
3. Run `./wipe-accounts.py`
