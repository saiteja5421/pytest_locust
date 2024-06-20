from nimbleclient.v1 import NimOSClient
import logging
from pytest import fixture
from tests.e2e.data_panorama.panorama_context import Context
from tests.data_panaroma.data_creation_for_ui_tests.common_test_data import volumes_name_list, snapshots_name_list

logger = logging.getLogger()


@fixture(scope="module")
def nim_os_client():
    context = Context(cxo_29_array=True)
    nimble_api: NimOSClient = NimOSClient(
        context.cxo_array.array_ip,
        context.cxo_array.username,
        context.cxo_array.password,
    )
    return nimble_api


def test_delete_snapshots(nim_os_client: NimOSClient):
    for volume_name, snapshot_name in zip(volumes_name_list, snapshots_name_list):
        print(f"Fetching snapshot {snapshot_name}")
        snapshot = nim_os_client.snapshots.get(
            name=snapshot_name,
            vol_name=volume_name,
        )

        if snapshot:
            print(f"Deleting snapshot {snapshot_name}, {snapshot.id}")
            snapshot_response = nim_os_client.snapshots.delete(id=snapshot.id)
            print(f"Deleted snapshot{snapshot_name}, {snapshot_response}")


def test_delete_volumes(nim_os_client: NimOSClient):
    for volume_name in volumes_name_list:
        print(f"Fetching volume {volume_name}")
        volume = nim_os_client.volumes.get(name=volume_name)

        if volume:
            print(f"Setting state of volume {volume_name}, {volume.id} to 'Offline'")
            nim_os_client.volumes.offline(volume.id)

            print(f"Deleting volume {volume_name}, {volume.id}")
            vol_resp = nim_os_client.volumes.delete(volume.id)
            print(f"Volume deleted {volume_name}, {vol_resp}")
