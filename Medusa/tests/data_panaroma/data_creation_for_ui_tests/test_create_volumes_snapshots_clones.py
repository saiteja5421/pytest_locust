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


def test_create_volumes(nim_os_client: NimOSClient):
    for volume_name in volumes_name_list:
        logger.info(f"Creating volume {volume_name}")
        nim_os_client.volumes.create(
            volume_name,
            size="10240",  # 10 GB
            read_only="false",
        )

        volume = nim_os_client.volumes.get(name=volume_name)
        logger.info(f"Volume created with name {volume_name} is {volume.id}")


def test_create_snapshots(nim_os_client: NimOSClient):
    for volume_name, snapshot_name in zip(volumes_name_list, snapshots_name_list):
        logger.info(f"Fetching volume {volume_name}")
        volume = nim_os_client.volumes.get(name=volume_name)

        if volume:
            logger.info(f"Creating snapshot {snapshot_name}")
            nim_os_client.snapshots.create(
                name=snapshot_name,
                vol_id=volume.id,
                description=f"Snapshot for volume {volume_name}",
                online=False,
                writable=False,
            )

            snapshot = nim_os_client.snapshots.get(
                name=snapshot_name,
                vol_name=volume_name,
            )
            logger.info(f"Snapshot created with name {snapshot_name} is {snapshot.id}")
