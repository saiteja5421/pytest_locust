import json
from requests import Response

from lib.common.common import get
from lib.common.users.user import ApiHeader

from lib.dscc.data_panorama.app_lineage.models.app_lineage import (
    ApplicationList,
    VolumesDetail,
    SnapshotsDetail,
    ClonesDetail,
)

from tests.e2e.data_panorama.panorama_context_models import PanoramaAPI


class AppLineageInfo:
    api_header: ApiHeader
    url: str
    systems: str
    applications: str
    application_snapshots: str
    application_clones: str
    application_volumes: str

    def __init__(self, url: str, api_header: ApiHeader):
        self.api_header = api_header
        self.url = url
        self.systems = PanoramaAPI.systems
        self.applications = PanoramaAPI.applications
        self.application_snapshots = PanoramaAPI.application_snapshots
        self.application_clones = PanoramaAPI.application_clones
        self.application_volumes = PanoramaAPI.application_volumes

    # function to get applications REST API /data-observability/v1alpha1/applications

    def get_applications(self, r="", **params) -> ApplicationList:
        """
        Function to get list of available applications
        Query Parameters:
            limit (O): int
            offset (O): int

        Return: ApplicationList object with list of Applications or respone error code
        """
        path: str = f"{self.applications}?{r}limit=1000"
        response: Response = get(self.url, path, params=params, headers=self.api_header.authentication_header)
        assert response.status_code == 200, f"API call failed with {response.status_code}"
        return ApplicationList(**json.loads(response.text))

    # function to get the volume list for specific application REST API /data-observability/v1alpha1/applications/{id}/volumes
    def get_application_volumes_detail(self, **params) -> VolumesDetail:
        """
        Function to get list of volume details for the specific application

        Path Arguments:
            app id(R) : str  id of the application
            system id (R) : str id of system
        Query Parameters:
            limit (O): int
            offset (O): int
        Return: VolumesDetail object with list of volumes or respone error code
        """
        # path: str = self.application_volumes_detail
        system_id = params["system_id"]
        app_id = params["app_id"]
        params.pop("system_id")
        params.pop("app_id")
        path: str = f"{self.systems}/{system_id}/{self.applications}/{app_id}/{self.application_volumes}?limit=1000"
        response: Response = get(self.url, path, params=params, headers=self.api_header.authentication_header)
        assert response.status_code == 200, f"API call failed with {response.status_code}"
        return VolumesDetail(**json.loads(response.text))

    # function to get list of snapshot for a specific volume REST API /data-observability/v1alpha1/systems/{system-id}/volumes/{volume-id}/snapshots
    def get_application_snapshots_detail(self, **params) -> SnapshotsDetail:
        """
        Function to get list of snapshot details for the specific volume in an application

        Path Arguments from params:
            system_id (R) : str id of system
            volume_uuid(R) : str id of volume
        Query Parameters from params:
            limit (O): int
            offset (O): int
        Return: SnapshotsDetail object with list of Snapshots and information or respone error code
        """
        system_id = params["system_id"]
        volume_uuid = params["volume_uuid"]
        params.pop("system_id")
        params.pop("volume_uuid")
        path: str = f"{self.systems}/{system_id}/{self.application_volumes}/{volume_uuid}/{self.application_snapshots}?limit=1000"
        response: Response = get(self.url, path, params=params, headers=self.api_header.authentication_header)
        assert response.status_code == 200, f"API call failed with {response.status_code}"
        return SnapshotsDetail(**json.loads(response.text))

    # function to get list of snapshot for a specific volume REST API /data-observability/v1alpha1/systems/{system-id}/volumes/{volume-id}/clones
    def get_application_clones_detail(self, **params) -> ClonesDetail:
        """
        Function to get list of clone details for the specific snapshot in an application
        Path Arguments from params:
            system_id (R) : str id of system
            snapshot_id(R) : str id of volume
        Query Parameters from params:
            limit (O): int
            offset (O): int
        Return: ClonesDetail object with list of Clones information or respone error code

        """
        system_id = params["system_id"]
        snapshot_id = params["snapshot_id"]
        params.pop("system_id")
        params.pop("snapshot_id")
        path: str = f"{self.systems}/{system_id}/{self.application_snapshots}/{snapshot_id}/{self.application_clones}"
        response: Response = get(self.url, path, params=params, headers=self.api_header.authentication_header)
        assert response.status_code == 200, f"API call failed with {response.status_code}"
        return ClonesDetail(**json.loads(response.text))
