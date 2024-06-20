import { check } from "k6";
import { generateHeader, httpDelete, httpGet, httpPost, waitForTask } from "./../lib.js";
import { baseUri } from "../../backup_restore_workflow.js";
import { getProtectVmId } from "./protect_vm.js";

// backup start
export function deleteBackup(resourceUri, waitTime = 120) {
    let header = generateHeader();
    let resp = httpDelete(`${baseUri}${resourceUri}`, null, header);
    console.log(`[deleteBackup]=> Delete backup response is ${JSON.stringify(resp, undefined, 4)}`);
    check(resp, { "Delete backup -> status 202": (r) => r.status === 202 });
    // @ts-ignore
    let body = JSON.parse(resp.body);
    let taskUri = body.taskUri;
    let fullTaskUri = `${baseUri}${taskUri}`;
    let isBackupDeleted = waitForTask(fullTaskUri, waitTime, header);
    return isBackupDeleted;
}

export function deleteAllSnapshots(vmToProtect, vcenterName, waitTime = 300) {
    let vmId = getProtectVmId(vmToProtect, vcenterName);
    let localBackupUri = `${baseUri}/api/v1/virtual-machines/${vmId}/snapshots?limit=1000`;
    let isLocalBackupDeleted = deleteAllObjects(localBackupUri, 'Snapshot', waitTime);
    return isLocalBackupDeleted;
}

export function deleteAllLocalBackups(vmToProtect, vcenterName, waitTime = 300) {
    let vmId = getProtectVmId(vmToProtect, vcenterName);
    let localBackupUri = `${baseUri}/api/v1/virtual-machines/${vmId}/backups?limit=1000`;
    let isLocalBackupDeleted = deleteAllObjects(localBackupUri, 'BACKUP', waitTime);
    return isLocalBackupDeleted;
}

export function deleteAllCloudBackups(vmToProtect, vcenterName, waitTime = 300) {
    let vmId = getProtectVmId(vmToProtect, vcenterName);
    let cloudBackupUri = `${baseUri}/api/v1/virtual-machines/${vmId}/backups?limit=1000`;
    let isCloudBackupDeleted = deleteAllObjects(cloudBackupUri, 'CLOUD_BACKUP', waitTime);
    return isCloudBackupDeleted;
}

export function deleteAllObjects(backupUri, backupType = 'Backup', waitTime = 300) {
    // let backupUri = `${baseUri}/api/v1/virtual-machines/${vmId}/backups`;
    let header = generateHeader();
    let resp = httpGet(backupUri, header);
    console.log(`Backup response is ${JSON.stringify(resp, undefined, 4)}`);
    // @ts-ignore
    let status = true;
    let body = JSON.parse(resp.body);
    for (let item of body.items) {
        if (backupType != 'Snapshot') {
            if (backupType != item.backupType) {
                continue;
            }
        }
        console.log(`Resource Uri is -> ${item.resourceUri}`);
        let isDeleted = deleteBackup(item.resourceUri, waitTime);
        if (isDeleted != true) {
            status = false;
        }
    }
    if (status) {
        console.log("[deleteAllObjects] All backups are removed successfully..");
        return status;
    } else {
        throw `[deleteAllObjects] [throw] => Backup for vm ${backupUri} is not found.`;
    }
}

export function deleteLocalBackup(vmToProtect, vcenterName, waitTime = 120) {
    let vmId = getProtectVmId(vmToProtect, vcenterName);
    let localBackupUri = `${baseUri}/api/v1/virtual-machines/${vmId}/backups?limit=1000`;
    let backupObj = getBackupObj(localBackupUri);
    let isLocalBackupDeleted = deleteBackup(backupObj.resourceUri, waitTime);
    return isLocalBackupDeleted;
}

export function deleteCloudBackup(vmToProtect, vcenterName, waitTime = 120) {
    let vmId = getProtectVmId(vmToProtect, vcenterName);
    let cloudBackupUri = `${baseUri}/api/v1/virtual-machines/${vmId}/backups?limit=1000`;
    let backupObj = getBackupObj(cloudBackupUri);
    let isCloudBackupDeleted = deleteBackup(backupObj.resourceUri, waitTime);
    return isCloudBackupDeleted;
}

export function getBackupObj(backupUri) {
    // let backupUri = `${baseUri}/api/v1/virtual-machines/${vmId}/backups`;
    let header = generateHeader();
    let resp = httpGet(backupUri, header);
    console.log(`Backup response is ${JSON.stringify(resp, undefined, 4)}`);
    // @ts-ignore
    let body = JSON.parse(resp.body);
    for (let i of body.items) {
        console.log(`Resource Uri is -> ${i.resourceUri}`);
        return i;
    }
    throw `[getBackupObj] [throw] => Local backup for vm ${backupUri} is not found.`;
}

export function createLocalBackup(vmToProtect, vcenterName, snapName, copyPoolId, localBackupName) {
    let vmId = getProtectVmId(vmToProtect, vcenterName);
    let snapBackupObj = getSnapshotBackup(vmId, snapName);
    // console.log(`[Iteration ${execIteration}] => Snapshot backup object is ${snapBackupObj.id}`);
    // console.log(`[Iteration ${execIteration}] => VM Id after restore is ${vmId}`);
    let backupUri = `${baseUri}/api/v1/virtual-machines/${vmId}/backups?limit=1000`;
    let isLocalBackupCreated = httpCreateLocalBackup(backupUri, copyPoolId, localBackupName, snapBackupObj.id);
    return isLocalBackupCreated;
}

export function createCloudBackup(vmToProtect, policyTemplateId) {
    // let vmId = getProtectVmId(vmToProtect, vcenterName);
    // let localBackupObj = getLocalBackup(vmId, localBackupName);
    // console.log(`[Iteration ${execIteration}] => Snapshot backup object is ${snapBackupObj.id}`);
    let job = getProtectionJobId(vmToProtect);
    console.log(`Job Id ${job}`);
    let backupUri = `${baseUri}/api/v1/protection-jobs/${job}/run`;
    let isCloudBackupCreated = httpCreateCloudBackup(backupUri);
    return isCloudBackupCreated;
}

function httpCreateLocalBackup(backupUri, copyPoolId, localBackupName, snapBackupId, waitTime = 1200) {
    let header = generateHeader();
    let payload = {
        "backupType": "BACKUP",
        "storagePoolId": `${copyPoolId}`,
        "name": `${localBackupName}`,
        "sourceCopyInfo": {
            "id": `${snapBackupId}`,
            "type": "SNAPSHOT"
        }
    };
    let resp = httpPost(backupUri, JSON.stringify(payload), header);
    console.log(`[httpCreateLocalBackup] => Create Local backup response -> ${JSON.stringify(resp, undefined, 4)}`);
    // @ts-ignore
    let body = JSON.parse(resp.body);
    let taskUri = body.taskUri;
    let fullTaskUri = `${baseUri}${taskUri}`;
    let isLocalBackupCreated = waitForTask(fullTaskUri, waitTime, header);
    return isLocalBackupCreated;

}

function httpCreateCloudBackup(backupUri, copyPoolId, cloudBackupName, localBackupId, waitTime = 1800) {
    let header = generateHeader();
    let payload = {
        "scheduleIds": [3, 1]
    };
    let resp = httpPost(backupUri, JSON.stringify(payload), header);
    console.log(`[httpCreateCloudBackup] => Create Cloud backup response -> ${JSON.stringify(resp, undefined, 4)}`);
    // @ts-ignore
    let body = JSON.parse(resp.body);
    let taskUri = body.taskUri;
    let fullTaskUri = `${baseUri}${taskUri}`;
    let isCloudBackupCreated = waitForTask(fullTaskUri, waitTime, header);
    return isCloudBackupCreated;

}

export function getSnapshotBackup(vmId, snapName) {
    let header = generateHeader();
    let snapBackupUrl = `${baseUri}/api/v1/virtual-machines/${vmId}/snapshots?limit=1000`;
    let resp = httpGet(snapBackupUrl, header);
    console.log(`response is ${JSON.stringify(resp, undefined, 4)}`);
    // @ts-ignore
    let snapBody = JSON.parse(resp.body);

    for (let snapBackup of snapBody.items) {
        if (snapBackup.name === snapName) {
            return snapBackup;
        }
    }
    throw `[getSnapshotBackup] [throw]=> Failed to get snapshot ${snapName} details for VM id ${vmId}`;
}

export function getLocalBackup(vmId, backupName) {
    let header = generateHeader();
    let localBackupUrl = `${baseUri}/api/v1/virtual-machines/${vmId}/backups?limit=1000`;
    let resp = httpGet(localBackupUrl, header);
    console.log(`response is ${JSON.stringify(resp, undefined, 4)}`);
    // @ts-ignore
    let localBackupBody = JSON.parse(resp.body);

    for (let localBackup of localBackupBody.items) {
        if (localBackup.name === backupName) {
            return localBackup;
        }
    }
    throw `Failed to get Local backup ${backupName} details for VM id ${vmId}`;

}

export function getCloudBackup(vmId, backupName) {
    let header = generateHeader();
    let cloudBackupUrl = `${baseUri}/api/v1/virtual-machines/${vmId}/backups?limit=1000`;
    let resp = httpGet(cloudBackupUrl, header);
    console.log(`response is ${JSON.stringify(resp, undefined, 4)}`);
    // @ts-ignore
    let cloudBackupBody = JSON.parse(resp.body);

    for (let cloudBackup of cloudBackupBody.items) {
        if (cloudBackup.name.includes("Cloud_Backup")) {
            console.log(`returning cloudBackup: ${cloudBackup}`);
            return cloudBackup;
        }
    }
    throw `Failed to get Cloud backup ${backupName} details for VM id ${vmId}`;

}

export function createSnapshotBackup(vmId, snapName) {
    let header = generateHeader();
    let snapBackupUrl = `${baseUri}/api/v1/virtual-machines/${vmId}/snapshots`;
    let payload = {
        "name": snapName,
        "snapshotType": "SNAPSHOT"
    };
    let resp = httpPost(snapBackupUrl, JSON.stringify(payload), header);
    console.log(`Snapshot backup ${JSON.stringify(resp, undefined, 4)}`);
    // @ts-ignore
    let body = JSON.parse(resp.body);
    let taskUri = body.taskUri;
    let fullTaskUri = `${baseUri}${taskUri}`;
    let isSnapBackupCreated = waitForTask(fullTaskUri, 300, header);
    return isSnapBackupCreated;

}

// @ts-ignore
function runBackupNow(vmToProtect) {
    let header = generateHeader();
    let localBackupPayload = {
        "scheduleIds": [
            3,
            1,
            2
        ]
    };
    // @ts-ignore
    let job = getProtectionJob(vmToProtect);
    let resp = httpPost(`${baseUri}/api/v1/protection-jobs/${job.id}/run`, JSON.stringify(localBackupPayload), header);
    console.log(`Local backup Response is ${JSON.stringify(resp, undefined, 4)}`);
    // @ts-ignore
    let body = JSON.parse(resp.body);
    let taskUri = body.taskUri; let
        fullTaskUri = `${baseUri}${taskUri}`;
    let isProtected = waitForTask(fullTaskUri, 120, header);
    check(isProtected, { "Backup is created successfully": (i) => i == true });
    return isProtected;
}

export function getProtectionJobId(vmName) {
    let header = generateHeader();
    let resp = httpGet(`${baseUri}/api/v1/protection-jobs?limit=1000`, header);
    check(resp, { "[unprotectVm]-> Get data management job -> status 200 received": (r) => r.status === 200 });
    // console.log(`Get job -> ${JSON.stringify(resp, undefined, 4)}`);
    let jobBody = JSON.parse(resp.body);
    let resourceUri = undefined;
    let jobId1 = undefined
    for (let job of jobBody.items) {
        if (job.assetInfo.displayName === vmName) {
            resourceUri = job.resourceUri;
            jobId1 = job.id
            console.log(`Resource Uri of app management Jobs Id ${resourceUri}`);
            console.log(`Resource Uri of app management Jobs Id ${jobId1}`);
            return jobId1;
        }
    }
    throw `Failed to get Protection Job for VM ${vmName}`;
}
