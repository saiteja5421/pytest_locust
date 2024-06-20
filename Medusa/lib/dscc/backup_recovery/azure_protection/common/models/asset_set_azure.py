from lib.common.enums.asset_info_types import AssetType


class AssetSetAzure:
    # 'virtual_machine' and 'disk' prefix for Azure IDs
    # 'csp' prefix for machine_instance and volume UUIDs

    def __init__(self):
        # Azure assets
        self.virtual_machine_1_id: str = None
        self.disk_1_id: str = None
        self.disk_2_id: str = None
        self.virtual_machine_id_list: list = []
        self.disk_id_list: list = []
        # DSCC assets
        self.csp_machine_instance_1_id: str = None
        self.csp_volume_1_id: str = None
        self.csp_volume_2_id: str = None
        self.csp_machine_instance_id_list: list = []
        self.csp_volume_id_list: list = []
        self.csp_machine_automatic_pg_id: str = None
        self.csp_machine_custom_pg_id: str = None
        self.csp_volume_automatic_pg_id: str = None
        self.csp_volume_custom_pg_id: str = None
        self.csp_tag_management_pg_id: str = None
        self.csp_pg_ids_list: list[str] = []

    def get_standard_assets(self):
        # call _update_id_list() function before calling get_standard_assets
        self._update_id_lists()

        standard_asset_id_list = []
        standard_asset_id_list.extend(self.csp_machine_instance_id_list)
        standard_asset_id_list.extend(self.csp_volume_id_list)
        standard_asset_id_list.extend(self.csp_pg_ids_list)

        standard_asset_type_list: list = [
            AssetType.CSP_MACHINE_INSTANCE,
            AssetType.CSP_VOLUME,
            AssetType.CSP_VOLUME,
            AssetType.CSP_PROTECTION_GROUP,
            AssetType.CSP_PROTECTION_GROUP,
            AssetType.CSP_PROTECTION_GROUP,
            AssetType.CSP_PROTECTION_GROUP,
            AssetType.CSP_PROTECTION_GROUP,
        ]

        return standard_asset_id_list, standard_asset_type_list

    def _update_id_lists(self):
        self.virtual_machine_id_list = [self.virtual_machine_1_id]
        self.disk_id_list = [self.disk_1_id, self.disk_2_id]

        self.csp_machine_instance_id_list = [self.csp_machine_instance_1_id]
        self.csp_volume_id_list = [self.csp_volume_1_id, self.csp_volume_2_id]
        self.csp_pg_ids_list = [
            self.csp_machine_automatic_pg_id,
            self.csp_volume_automatic_pg_id,
            self.csp_volume_automatic_pg_id,
            self.csp_volume_custom_pg_id,
            self.csp_tag_management_pg_id,
        ]
