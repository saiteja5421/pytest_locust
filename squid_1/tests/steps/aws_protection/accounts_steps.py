from lib.dscc.backup_recovery.aws_protection.accounts.inventory import Accounts


def refresh_account_inventory(account_config, account_type: str = "EC2") -> None:
    csp_account_name = account_config["name"]
    account = Accounts(csp_account_name)
    account.refresh_inventory(account_type=account_type)
