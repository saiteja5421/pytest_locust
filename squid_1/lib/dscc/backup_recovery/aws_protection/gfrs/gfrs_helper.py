import logging
import json
from common.error_messages import ERROR_MESSAGE_POST_INDEX_FILE
from tests.aws.config import GFRSPaths
from common import helpers
from lib.dscc.backup_recovery.aws_protection.gfrs.payload.file_system_info import (
    PostCSPFileSystemInfo,
    PostRestoreCSPFileSystemInfo,
)
from lib.dscc.backup_recovery.aws_protection.gfrs.models.csp_indexed_file_system_info import (
    CSPIndexedFileSystemInfoList,
)
import requests
import time
import locust_plugins

logger = logging.getLogger(__name__)
v1_beta_1_api, v1_beta_2_api = helpers.get_v1_beta_api_prefix()


def post_index_guest_files_on_csp_machine_instance_and_volume_backup(
    self,
    csp_asset_id: str,
    csp_asset_backup_id: str,
    csp_path_type: GFRSPaths = GFRSPaths.CSP_MACHINE_INSTANCES_BACKUPS,
    post_file_system_info: PostCSPFileSystemInfo = "{}",
    expecting_error: bool = False,
):
    """Post index guest files on CSP Machine Instance and CSP Volume Backups simultaneously
    NOTE: self -> uses client, proxies, headers, & environment
    """
    # POST /v1beta1/csp-machine-instances/{id}/backups/{backupId}/index-files
    # POST /v1beta1/csp-volumes/{id}/backups/{backupId}/index-files
    try:
        payload = post_file_system_info
        path = (
            f"{helpers.get_locust_host()}{v1_beta_1_api}/{csp_path_type}/{csp_asset_backup_id}/{GFRSPaths.INDEX_FILES}"
        )
        logger.info(f"Post Index path: {path}")
        with self.client.post(
            path,
            data=payload,
            proxies=self.proxies,
            headers=self.headers.authentication_header,
            catch_response=True,
            name=f"POST Index Guest Files on {csp_path_type} Backups",
        ) as response:
            try:
                logger.info(
                    f"POST Index Guest Files on {csp_path_type}: {csp_asset_id}, Backup {csp_asset_backup_id} -> Response code {response.status_code}"
                )
                logger.info(
                    f"POST Index Guest Files on {csp_path_type}: {csp_asset_id}, Backup {csp_asset_backup_id} -> Response text {response.text}"
                )
                if response.status_code == requests.codes.accepted:
                    logger.info(f"Response Headers = {response.headers}")
                    task_uri = response.headers["location"]
                    task_status = helpers.wait_for_task(task_uri=task_uri, api_header=self.headers, timeout_minutes=30)
                    if task_status == helpers.TaskStatus.success:
                        logger.info("POST Index Guest Files success")
                    elif task_status == helpers.TaskStatus.timeout:
                        raise Exception("POST Index Guest Files failed with timeout error")
                    elif task_status == helpers.TaskStatus.failure:
                        if expecting_error == True:
                            err_msg = helpers.get_error_message_from_task_response(task_uri,api_header=self.headers)
                            if err_msg == ERROR_MESSAGE_POST_INDEX_FILE:
                               logger.info(f"POST Index Guest Files failed with expected error {err_msg}")
                            else:
                                raise Exception(f"POST Index Guest Files failed with unexpected error {err_msg}")
                        else:
                            raise Exception("POST Index Guest Files failed with status'FAILED' error")
                    else:
                        raise Exception("POST Index Guest Files failed with unknown error")
                else:
                    logger.info(
                        f"POST Index Guest Files on {csp_path_type}: {csp_asset_id}, Backup {csp_asset_backup_id} -> Response code {response.status_code}"
                    )
                    logger.info(
                        f"POST Index Guest Files on {csp_path_type}: {csp_asset_id}, Backup {csp_asset_backup_id} -> Response text {response.text}"
                    )

                    response.failure(
                        f"POST Index Guest Files on {csp_path_type}: {csp_asset_id}, Backup {csp_asset_backup_id} -> Response code is {response.status_code}\n Response text {response.text}"
                    )
            except Exception as e:
                response.failure(f"Exception during POST Index Guest Files {e}")
                raise
    except Exception as e:
        helpers.custom_locust_response(
            self.environment, name="post_index_guest_files_on_csp_machine_instance_and_volume_backup", exception=e
        )


def get_indexed_file_system_info_for_backup(
    self, csp_asset_id: str, csp_asset_backup_id: str, csp_asset_type: GFRSPaths = GFRSPaths.GET_VOLUME_INDEXED_FILE
) -> CSPIndexedFileSystemInfoList:
    """Get indexed files/folders for Backup"""
    # GET /v1beta1/indexed-filesystems

    url = f"{helpers.get_locust_host()}{v1_beta_2_api}/{GFRSPaths.INDEXED_FILESYSTEMS}?asset-type={csp_asset_type}&asset-id={csp_asset_id}&backup-id={csp_asset_backup_id}"
    logger.info(url)

    response = requests.request("GET", url, headers=self.headers.authentication_header)
    logger.info(response)
    logger.info(response.text)

    if response.status_code == requests.codes.ok:
        response_data = CSPIndexedFileSystemInfoList.from_json(response.text)
        logger.info(f"Response data::{response_data}")
        return response_data
    else:
        logger.error(response.text)


def restore_csp_instance_or_volume_files_folders(
    self,
    csp_asset_id: str,
    csp_asset_backup_id: str,
    payload,
    csp_asset_type: GFRSPaths = GFRSPaths.CSP_MACHINE_INSTANCES_BACKUPS,
    expecting_error: bool = False,
):
    """
    Restores CSP Instance or CSP Volume provided files and folders for a CSP Instance/Volume's Backup
    and waits for restore task to complete
    """
    # POST /v1beta1/csp-machine-instances/{id}/backups/{backupId}/restore-files
    # POST /v1beta1/csp-volumes/{id}/backups/{backupId}/restore-files
    logger.info(f"payload: {payload}")
    path = (
        f"{helpers.get_locust_host()}{v1_beta_1_api}/{csp_asset_type}/{csp_asset_backup_id}/{GFRSPaths.RESTORE_FILES}"
    )
    logger.info(f"path: {path}")
    with self.client.post(
        url=path,
        data=json.dumps(payload),
        proxies=self.proxies,
        headers=self.headers.authentication_header,
        catch_response=True,
        name=f"POST GFRS Restore CSP {csp_asset_type}",
    ) as response:
        # TODO: Add parameter check for expecting Error for Negative Test Cases (when files already indexed / index already in progress)
        logger.info(f"Response text: {response.text}")
        if response.status_code == requests.codes.accepted:
            logger.info(f"Response with StatusCode: {response.status_code} with response {response.text}")
            task_uri = response.headers["location"]
            task_status = helpers.wait_for_task(task_uri=task_uri, api_header=self.headers)
            if task_status == helpers.TaskStatus.success:
                logger.info(f"Restore for CSP {csp_asset_type} was successful")
            else:
                response.failure(
                    f"Restore from local backup failed in wait_for_task, taskuri: {task_uri} , taskstatus: {task_status}"
                )
        else:
            response.failure(
                f"Failed to to restore , StatusCode: {str(response.status_code)} with response {response.text}"
            )


def delete_indexed_files_from_csp_backup(
    self, csp_asset_id: str, csp_backup_id: str, csp_asset_type: GFRSPaths = GFRSPaths.GET_INSTANCE_INDEXED_FILE
):
    # INTERNAL API to delete Index-File data for a given Backup
    # https://github.hpe.com/nimble-dcs/hybridcloud-file-index-search#internal-delete-api
    #
    # DELETE /test/v1/nb-rest.fiss/indexed-files
    logger.info(
        f"calling delete indexed-files endpoint: asset_type: {csp_asset_type}, asset_id: {csp_asset_id}, backup_id: {csp_backup_id}"
    )
    path = f"{helpers.get_locust_host()}/test/v1/nb-rest.fiss/indexed-files?asset-type={csp_asset_type}&asset-id={csp_asset_id}&backup-id={csp_backup_id}"
    logger.info(f"path: {path}")
    with self.client.delete(
        path,
        proxies=self.proxies,
        headers=self.headers.authentication_header,
        catch_response=True,
        name=f"DELETE Indexed Files from CSP {csp_asset_type}",
    ) as response:
        # response: Response = delete(url, path, headers=self.user.authentication_header)
        # There is no "task_id" returned for this Internal Call - much like "copy2cloud".
        # we'll need to look for the Task by name and wait for it to complete
        #
        # response.status_code == 404 if there is no Index-Files found for the Backup
        logger.info(f"Response: {response.text}")
        logger.info(f"Response Status Code: {response.status_code}")
        if response.status_code == requests.codes.ok:
            logger.info("delete Indexed-Files for Backup started")

            # TODO: Wait for task to complete.
            # Temporarily wait 5 min
            time.sleep(300)

        else:
            logger.info("No Indexed-Files found for Backup")

        # find and wait for all tasks for this asset id
