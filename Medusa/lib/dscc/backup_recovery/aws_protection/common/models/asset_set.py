from lib.common.enums.asset_info_types import AssetType


class AssetSet:
    # ec2 and ebs prefix for aws ids
    # csp prefix for backup and recovery uuids
    # all protection group is backup and recovery uuids

    def __init__(self):
        # AWS assets
        self.ec2_instance_id: str = None
        self.ebs_volume_1_id: str = None
        self.ebs_volume_2_id: str = None
        self.ec2_automatic_pg_id: str = None
        self.ec2_custom_pg_id: str = None
        self.ebs_automatic_pg_id: str = None
        self.ebs_custom_pg_id: str = None
        self.ec2_instance_id_list: list = []
        self.ebs_volume_id_list: list = []
        self.csp_machine_instance_id_list: list = [None]
        self.csp_volume_id_list: list = [None, None]
        self.auto_pg_id_list: list = []
        self.custom_pg_id_list: list = []
        self.standard_pg_id_list: list = []
        self.attached_ebs_volume_id_list = []
        self.csp_attached_ebs_volume_id_list: list = []
        self.attached_ebs_root_id = None

    def get_standard_assets(self):
        # call update_id_list() function before calling get_standard_assets.
        standard_asset_id_list = []
        standard_asset_id_list.extend(self.csp_machine_instance_id_list)
        standard_asset_id_list.extend(self.csp_volume_id_list)
        standard_asset_id_list.append(self.ec2_automatic_pg_id)
        standard_asset_id_list.append(self.ec2_custom_pg_id)
        standard_asset_id_list.append(self.ebs_automatic_pg_id)
        standard_asset_id_list.append(self.ebs_custom_pg_id)

        standard_asset_type_list: list = [
            AssetType.CSP_MACHINE_INSTANCE,
            AssetType.CSP_VOLUME,
            AssetType.CSP_VOLUME,
            AssetType.CSP_PROTECTION_GROUP,
            AssetType.CSP_PROTECTION_GROUP,
            AssetType.CSP_PROTECTION_GROUP,
            AssetType.CSP_PROTECTION_GROUP,
        ]

        return standard_asset_id_list, standard_asset_type_list

    def update_id_lists(self):
        self.ec2_instance_id_list = [self.ec2_instance_id]
        self.ebs_volume_id_list = [
            self.ebs_volume_1_id,
            self.ebs_volume_2_id,
        ]
        self.auto_pg_id_list = [self.ec2_automatic_pg_id, self.ebs_automatic_pg_id]
        self.custom_pg_id_list = [self.ec2_custom_pg_id, self.ebs_custom_pg_id]
        self.standard_pg_id_list = self.auto_pg_id_list + self.custom_pg_id_list
