from lib.dscc.backup_recovery.aws_protection.common.models.rds_common_objects import RDSDBConnection


class RDSAssetSet:
    # rds prefix for aws ids
    def __init__(self):
        # RDS assets
        self.rds_db_connection_list: list[RDSDBConnection] = []

    def get_standard_rds_assets(self):
        standard_rds_asset_connection_list: list[RDSDBConnection] = []
        standard_rds_asset_connection_list.extend(self.rds_db_connection_list)
        return standard_rds_asset_connection_list
