import { httpPost, waitForTask } from "./../lib.js";
import { baseUri } from "../../backup_restore_workflow.js";
import { getProtectVmId, getVMDetails } from "./protect_vm.js";
import { getCloudBackup, getLocalBackup, getSnapshotBackup } from "./backup_vm.js";
import { sleep } from "k6";

export function restoreCloudBackupToExistVM(vmToProtect, vcenterName, cloudBackupName, header, backupType = "BACKUP") {
    let restoreUrl = getRestoreUrl(vmToProtect, vcenterName);
    console.log(`[restoreBackupToExistVM] => Resoure URL after restore is ${restoreUrl}`);
    let vmId = getProtectVmId(vmToProtect, vcenterName);
    let cloudBackupObj = getCloudBackup(vmId, cloudBackupName);
    let isCloudBackupRestored = restoreToExistingVM(restoreUrl, header, cloudBackupObj.id, backupType);
    return isCloudBackupRestored;
}
// restore Start
export function restoreLocalBackupToExistVM(vmToProtect, vcenterName, localBackupName, header, backupType = "BACKUP") {
    let restoreUrl = getRestoreUrl(vmToProtect, vcenterName);
    console.log(`[restoreBackupToExistVM] => Resoure URL after restore is ${restoreUrl}`);
    let vmId = getProtectVmId(vmToProtect, vcenterName);
    let localBackupObj = getLocalBackup(vmId, localBackupName);
    let isLocalBackupRestored = restoreToExistingVM(restoreUrl, header, localBackupObj.id, backupType);
    return isLocalBackupRestored;
}
export function restoreSnapToNewVM(vmToProtect, vcenterName, snapName, restoreSnapVm, header) {
    let vm_response = getVMDetails(vmToProtect, vcenterName);
    let vmId = vm_response.id;
    console.log(`[restoreSnapToNewVM] => vmId of ${vmToProtect} before restoring Snapshot to New vm is ${vmId}`)

    let snapBackupObj = getSnapshotBackup(vmId, snapName);
    let restoreUrl = getRestoreUrl(vmToProtect, vcenterName);
    console.log(`[RestoreSnapToNewVM] => Resoure URL after restore is ${restoreUrl}`);
    let hostId = vm_response.hostInfo.id;
    let datastoreId = vm_response.appInfo.vmware.datastoresInfo[0].id;
    let payload = restoreNewVMPayload(snapBackupObj.id, restoreSnapVm, hostId, datastoreId, "SNAPSHOT");
    let isSnapBackupRestored = restoreBackup(restoreUrl, payload, header);
    sleep(60);
    vmId = getProtectVmId(vmToProtect, vcenterName);
    console.log(`[restoreSnapToNewVM] => vmId of ${vmToProtect} after restoring Snapshot to New vm is ${vmId}`)
    vmId = getProtectVmId(restoreSnapVm, vcenterName);
    console.log(`[restoreSnapToNewVM] => vmId of ${restoreSnapVm} after restoring Snapshot Backup to New vm is ${vmId}`)
    return isSnapBackupRestored;
}
export function restoreLocalBackupToNewVM(vmToProtect, vcenterName, backupName, restoreVmName, header, backupType = "BACKUP") {
    let restoreUrl = getRestoreUrl(vmToProtect, vcenterName);
    console.log(`[restoreBackupToNewVM] => Resoure URL is ${restoreUrl}`);
    let vmId = getProtectVmId(vmToProtect, vcenterName);
    console.log(`[restoreBackupToNewVM] => vmId of ${vmToProtect} before restoring Local Backup to New vm is ${vmId}`)

    let localBackupObj = getLocalBackup(vmId, backupName);

    let vm_response = getVMDetails(vmToProtect, vcenterName);
    let hostId = vm_response.hostInfo.id;
    let datastoreId = vm_response.appInfo.vmware.datastoresInfo[0].id;
    // const backupType = "Backup";
    let payload = restoreNewVMPayload(localBackupObj.id, restoreVmName, hostId, datastoreId, backupType);
    let isLocalBackupRestored = restoreBackup(restoreUrl, payload, header);
    vmId = getProtectVmId(vmToProtect, vcenterName);
    console.log(`[restoreBackupToNewVM] => vmId of ${vmToProtect} after restoring Local Backup to New vm is ${vmId}`)
    vmId = getProtectVmId(restoreVmName, vcenterName);
    console.log(`[restoreBackupToNewVM] => vmId of ${restoreVmName} after restoring Local Backup to New vm is ${vmId}`)
    return isLocalBackupRestored;
}
export function restoreCloudBackupToNewVM(vmToProtect, vcenterName, backupName, restoreVmName, header, backupType = "CLOUD_BACKUP") {
    let restoreUrl = getRestoreUrl(vmToProtect, vcenterName);
    console.log(`[restoreCloudBackupToNewVM] => Resoure URL is ${restoreUrl}`);
    let vmId = getProtectVmId(vmToProtect, vcenterName);
    console.log(`[restoreCloudBackupToNewVM] => vmId of ${vmToProtect} before restoring Cloud Backup to New vm is ${vmId}`);

    let cloudBackupObj = getCloudBackup(vmId, backupName);

    let vm_response = getVMDetails(vmToProtect, vcenterName);
    let hostId = vm_response.hostInfo.id;
    let datastoreId = vm_response.appInfo.vmware.datastoresInfo[0].id;
    // const backupType = "Backup";
    let payload = restoreNewVMPayload(cloudBackupObj.id, restoreVmName, hostId, datastoreId, backupType);
    let isCloudBackupRestored = restoreBackup(restoreUrl, payload, header);
    vmId = getProtectVmId(vmToProtect, vcenterName);
    console.log(`[restoreCloudBackupToNewVM] => vmId of ${vmToProtect} after restoring Cloud Backup to New vm is ${vmId}`);
    console.log(`[restoreCloudBackupToNewVM] Giving 60s breathing time before attempting to find VM - ${restoreVmName}`);
    sleep(60);
    vmId = getProtectVmId(restoreVmName, vcenterName);
    console.log(`[restoreCloudBackupToNewVM] => vmId of ${restoreVmName} after restoring Cloud Backup to New vm is ${vmId}`);
    return isCloudBackupRestored;
}
export function restoreToExistingVM(restoreUrl, header, backupId, backupType = "SNAPSHOT") {
    let payload = {
        "restoreType": "PARENT"
    };
    if (backupType === "SNAPSHOT") {
        payload["snapshotId"] = backupId;
    }
    if (backupType === "BACKUP") {
        payload["backupId"] = backupId;
    }
    if (backupType === "CLOUD_BACKUP") {
        payload["backupId"] = backupId;
    }
    let isBackupRestored = restoreBackup(restoreUrl, payload, header);
    return isBackupRestored;

}
function restoreBackup(restoreSnapshotUrl, payload, header, waitTime = 1800) {
    let resp = httpPost(restoreSnapshotUrl, JSON.stringify(payload), header);
    console.log(`Snapshot restore ${JSON.stringify(resp, undefined, 4)}`);
    let body = JSON.parse(resp.body);
    let taskUri = body.taskUri;
    let fullTaskUri = `${baseUri}${taskUri}`;
    let isBackupRestored = waitForTask(fullTaskUri, waitTime, header);
    return isBackupRestored;
}
function restoreNewVMPayload(backupId, vmName, hostId, datastoreId, backupType = "SNAPSHOT") {

    let backupPayload = {
        "restoreType": "ALTERNATE",
        "targetVMInfo": {
            "name": vmName,
            "hostId": hostId,
            "powerOn": true,
            "appInfo": {
                "vmware": {
                    "datastoreId": datastoreId
                }
            }
        }
    };
    if (backupType === "SNAPSHOT") {
        backupPayload["snapshotId"] = backupId;
    }
    if (backupType === "BACKUP") {
        backupPayload["backupId"] = backupId;
    }
    if (backupType === "CLOUD_BACKUP") {
        backupPayload["backupId"] = backupId;
    }
    return backupPayload;
}
export function getRestoreUrl(vmName, vcenterName) {
    let vmId = getProtectVmId(vmName, vcenterName);
    let restoreUrl = `${baseUri}/api/v1/virtual-machines/${vmId}/restore?limit=1000`;
    return restoreUrl;
}
