import logging

from lib.common.enums.inventory_type import InventoryType
from lib.dscc.backup_recovery.aws_protection.accounts.domain_models.csp_account_model import CSPAccountModel
import tests.steps.aws_protection.cloud_account_manager_steps as CAMS


from tests.e2e.aws_protection.context import Context

logger = logging.getLogger()


def get_csp_account_rds_refresh_status(context: Context, csp_account_id: str) -> str:
    """Get CSP account RDS refresh status

    Args:
        context (Context): Test context
        csp_account_id (str): csp account id

    Returns:
        str: Function returns refresh status for the RDS inventory.
        Possible values Ok | Warning | Unknown | Error
    """
    rds_status: str = ""
    csp_account: CSPAccountModel = CAMS.get_csp_account_by_csp_id(context=context, csp_account_id=csp_account_id)

    if csp_account:
        for refresh_info in csp_account.inventory_refresh_info:
            if refresh_info.inventory_type == InventoryType.RDS:
                rds_status = refresh_info.status.value

    return rds_status
