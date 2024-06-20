import { sleep, check } from "k6";
import { generateHeader, httpDelete, httpGet, httpPost } from "./../lib.js";
import { getProtectVmId, generateProtectVMPayload, protectVm } from "./protect_vm.js";
import { baseUri } from "../../backup_restore_workflow.js";

// Protecion policy
export function createProtectionPolicy(protectionPolicyName, localCopyPoolId = null, cloudCopyPoolId = null) {
    let snapProtection = generateSnapBackupPayload();
    let localBackup = null;
    let cloudBackup = null;
    if (localCopyPoolId != null) {
        localBackup = generateLocalBackupPayload(localCopyPoolId);
    }
    if (cloudCopyPoolId != null) {
        cloudBackup = generateCloudBackupPayload(cloudCopyPoolId);
    }
    // let timestamp = Math.floor(Date.now() / 1000);
    // let timestamp = Math.floor(Date.now() / 1000);
    // let backupName = `${backupPrefix}-${timestamp}`;
    let payload = genProtectionTemplatePayload(protectionPolicyName, snapProtection, localBackup, cloudBackup);
    console.log(`Protection template ${JSON.stringify(payload, undefined, 1)}`);
    let response = postCreateProtectionPolicy(payload);
    return response;
}
export function getProtectionPolicyTemplate(policyName) {
    let uri = `${baseUri}/api/v1/protection-policies?limit=1000`;
    let header = generateHeader();
    header['timeout'] = "60s";
    console.log(JSON.stringify(header));
    let res = httpGet(uri, header);

    let body = JSON.parse(res.body);
    //console.log(`body is ${JSON.stringify(body, undefined, 4)}`);

    for (let policy of body.items) {
        if (policy.name === policyName) {
            console.log(`policy name is ${policy.name} -> id ${policy.id}`);
            return policy;
        }
    }
    throw `Policy template ${policyName} is not found`;
}
/**
 * Delete protection policy template
 * @param {string} policyTemplateId Protection policy template id
 * @returns boolean
 */
export function deleteProtectionPolicy(policyTemplateId) {
    let header = generateHeader();
    let resp = httpDelete(`${baseUri}/api/v1/protection-policies/${policyTemplateId}`, null, header);
    console.log(`Delete template response -> ${JSON.stringify(resp, undefined, 4)}`);
    check(resp, { "[deleteProtectionPolicy]-> Delete protection policy template -> status 204 received": (r) => r.status === 204 });
    return (resp.status === 204);
}
export function applyProtectionPolicy(policyName, vmToProtect, vcenterName) {
    let policy = getProtectionPolicyTemplate(policyName);
    let snapshotBackupId = policy.protections[0].id;
    let localBackupId = policy.protections[1].id;
    let policyTemplateId = policy.id;
    let vmId = getProtectVmId(vmToProtect, vcenterName);
    console.log(`[applyProtectionPolicy] => Snapshot id -> ${snapshotBackupId} -> local backup id ${localBackupId} -> policy Id ${policyTemplateId}`);
    let payload = generateProtectVMPayload(vmToProtect, vmId, policyTemplateId, snapshotBackupId);

    // Step 2.2 -> Protect VM -> Apply protection to the VM using protection policy
    console.log(`[applyProtectionPolicy] => payload is ${JSON.stringify(payload, undefined, 4)}`);
    let isVmProtected = protectVm(payload);
    console.log("Sleeping 300 sec to complete default snapshot backup");
    sleep(300);
    return isVmProtected;
}
function postCreateProtectionPolicy(payload) {
    let protectionTemplateUrl = `${baseUri}/api/v1/protection-policies?limit=1000`;
    let header = generateHeader();
    let response = httpPost(protectionTemplateUrl, JSON.stringify(payload), header);
    check(response, { "Protection policy is created": (r) => r.status === 200 });
    console.log(`protection template response is ${JSON.stringify(response, undefined, 4)}`);
    return response;
}
function generateLocalBackupPayload(copyPoolId) {
    return {
        "type": "BACKUP",
        "applicationType": "VMWARE",
        "schedules": [
            {
                "id": 2,
                "name": "Local_Backup_2",
                "namePattern": {
                    "format": "Local_Backup_{DateFormat}"
                },
                "expireAfter": {
                    "unit": "WEEKS",
                    "value": 1
                },
                "schedule": {
                    "recurrence": "WEEKLY",
                    "repeatInterval": {
                        "every": 1,
                        "on": [
                            2
                        ]
                    }
                },
                "sourceProtectionScheduleId": 1
            }
        ],
        "protectionStoreId": copyPoolId
    };
}
function genProtectionTemplatePayload(backupName, snapBackup, localBackup, cloudBackup) {
    let protectionList = [];
    protectionList.push(snapBackup);
    if (localBackup != undefined || localBackup != null) {
        protectionList.push(localBackup);
    }
    if (cloudBackup != undefined || cloudBackup != null) {
        protectionList.push(cloudBackup);
    }
    let payload = {
        // "appType": "VMware",
        "name": backupName,
        "protections": protectionList
    };
    return payload;
}


function generateSnapBackupPayload() {
    let timestamp = Math.floor(Date.now() / 1000);
    return {
        "type": "SNAPSHOT",
        "applicationType": "VMWARE",
        "schedules": [
            {
                "id": 1,
                "name": "Snapshot_1",
                "namePattern": {
                    "format": "Snapshot_{DateFormat}"
                },
                "expireAfter": {
                    "unit": "DAYS",
                    "value": 1
                },
                "schedule": {
                    "recurrence": "DAILY",
                    "repeatInterval": {
                        "every": 1
                    }
                }
            }
        ]
    }
}

function generateCloudBackupPayload(poolId) {
    return {
        "type": "CLOUD_BACKUP",
        "applicationType": "VMWARE",
        "schedules": [
            {
                "id": 3,
                "name": "Cloud_Backup_3",
                "namePattern": {
                    "format": "Cloud_Backup_{DateFormat}"
                },
                "expireAfter": {
                    "unit": "MONTHS",
                    "value": 1
                },
                "schedule": {
                    "recurrence": "MONTHLY",
                    "repeatInterval": {
                        "every": 1,
                        "on": [
                            6
                        ]
                    }
                },
                "sourceProtectionScheduleId": 2
            }
        ],
        "protectionStoreId": poolId
    }
}

