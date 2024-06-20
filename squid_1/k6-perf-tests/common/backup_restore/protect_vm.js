import { check } from "k6";
import { generateHeader, httpDelete, httpGet, httpPost, waitForTask } from "./../lib.js";
import { baseUri } from "../../backup_restore_workflow.js";

/**
 * unprotect VM
 * @param {string} vmName vm name
 * @returns boolean
 */
export function unprotectVm(vmName, waitTime = 300) {
    let job = getProtectionJob(vmName);
    // job.resourceUri
    let header = generateHeader();
    let deleteJob = httpDelete(`${baseUri}${job.resourceUri}`, null, header);
    check(deleteJob, { "[unprotectVm]-> UnprotectVm is successful -> status 202 received": (r) => r.status === 202 });
    console.log(`unprotect VM ${vmName} response -> ${JSON.stringify(deleteJob, undefined, 4)}`);
    let body = JSON.parse(deleteJob.body);
    if (deleteJob.status === 202) {
        const isVmUnprotected = waitForTask(`${baseUri}${body.taskUri}`, waitTime, header);
        return isVmUnprotected;
    }
    console.error(`[unprotectVm] => Failed to unprotect => ${body.error}`);
    throw `[unprotectVm] => Failed to unprotect vm ${vmName}`;
}
export function getProtectionJob(vmName) {
    let header = generateHeader();
    let resp = httpGet(`${baseUri}/api/v1/protection-jobs?limit=1000`, header);
    check(resp, { "[unprotectVm]-> Get data management job -> status 200 received": (r) => r.status === 200 });
    //console.log(`Get job -> ${JSON.stringify(resp, undefined, 4)}`);
    let jobBody = JSON.parse(resp.body);
    let resourceUri = undefined;
    for (let job of jobBody.items) {
        if (job.assetInfo.displayName === vmName) {
            resourceUri = job.resourceUri;
            console.log(`Resource Uri of app management Jobs Id ${resourceUri}`);
            return job;
        }
    }
    throw `Failed to get Protection Job for VM ${vmName}`;
}
export function protectVm(payload) {
    let header = generateHeader();
    let resp = httpPost(`${baseUri}/api/v1/protection-jobs`, JSON.stringify(payload), header);
    console.log(`Protect VM response is ${JSON.stringify(resp, undefined, 4)}`);
    let body = JSON.parse(resp.body);
    check(resp, { "Apply Protection to VM": (r) => r.status === 202 });
    if (resp.status === 202) {
        let isProtectionApplied = waitForTask(`${baseUri}${body.taskUri}`, 300, header);
        return isProtectionApplied;
    }
    console.error(`${body.error}`);
    throw `[protectVM] => failed to protect VM ${payload.assetInfo.displayName} => ${body.error}`;
}

export function getProtectVmId(vmName, vcenterName) {
    let vmObj = getVMDetails(vmName, vcenterName);
    console.log(`vm id of ${vmName} is ${vmObj.id}`);
    return vmObj.id;
    // throw `VM Name ${vmName} is not found in ${vcenterName}`
}
export function generateProtectVMPayload(vmName, vmId, protectionTemplateId, snapProtectionId, localProtectionId, cloudProtectionId) {
    let protectionList = [];
    protectionList.push(
        {
            "id": snapProtectionId,
            "schedules": [
                {
                    "id": 1,
                    "consistency": "CRASH_CONSISTENT_ON_FAILURE"
                }
            ]
        }
    );
    if (localProtectionId != undefined) {
        protectionList.push({
            "id": localProtectionId,
            "schedules": [
                {
                    "id": 2,
                    "consistency": "CRASH_CONSISTENT_ON_FAILURE"
                }
            ]
        });
    }
    if (cloudProtectionId != undefined) {
        protectionList.push({
            "id": cloudProtectionId,
            "schedules": [
                {
                    "id": 3,
                    "consistency": "CRASH_CONSISTENT_ON_FAILURE"
                }
            ]
        });
    }

    return {
        "assetInfo": {
            "id": vmId,
            "type": "VIRTUAL_MACHINE",
            "name": vmName
        },
        "protectionPolicyId": protectionTemplateId,
        "overrides": {
            "protections": protectionList
        },
        // "runOnce": false
    };
}

export function getVMDetails(vmName, vcenterName) {
    let header = generateHeader();
    let vmUri = `${baseUri}/api/v1/virtual-machines?limit=1000`;
    let res = httpGet(vmUri, header);
    let respBody = null;
    try {
        // We often get "SyntaxError: invalid character 'o' in literal null (expecting 'u')". Enabled try-catch to safely fail the test.
        respBody = JSON.parse(res.body);
    } catch (err) {
        console.error(`VM list ${JSON.stringify(res, undefined, 4)}`);
        throw `ERROR: ${err}`;
    }

    for (let vm of respBody.items) {
        if (vm.name === vmName) {
            console.log(`[getVMDetails] => VM ${vmName} is present`);
            if (vm.hypervisorManagerInfo.name === vcenterName) {
                console.log(`VM ${vmName} is present in ${vcenterName}. VM Object is ${vm.id}. `);
                return vm
            }
        }
    }
    throw `VM Name ${vmName} is not found in ${vcenterName}`
}
