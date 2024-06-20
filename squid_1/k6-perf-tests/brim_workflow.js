import { sleep, check, group } from "k6";
import http from "k6/http";
import exec from "k6/execution";
import { generateHeader, generateHeaderByAccount, waitForTask } from "./common/lib.js";

var configFilePath = `${__ENV.TEST_CONFIG}`;
var testConfig = JSON.parse(open(configFilePath));
var backupObj = testConfig.testinput.brimBackup
let accountObj = testConfig.testbed.accountOptions

export const options = {
    scenarios: {
        "crud-create-catalyst-vm": {
            executor: "shared-iterations",
            vus: 1,
            iterations: 1,
            maxDuration: "2h"
        },
    },
};

export default function () {
    
    for (const i of backupObj) {
        runBackupNow(accountObj[i.account], i.protectionJobId, i.waitTime);
    }
    console.log("After all the backups are taken wait for 10 minutes")
    sleep(600);

    // getSummaryReport(accountObj.BRIM1,5);
    // sleep(10);
    // getSummaryReport(accountObj.BRIM2,5);
}

function getSummaryReport(account, waitTime = 30) {
    getCloudStoreUsage(account);
    
    sleep(waitTime)
    
    let vmProtectedSummary = getVMProtectedSummary(account);
    console.debug(`VM Protected summary ${JSON.stringify(vmProtectedSummary, undefined, 4)}`);
    // if(vmProtectedSummary.status == )
    var vmBody = JSON.parse(vmProtectedSummary.body);
    let protectedVMCount = vmBody.hypervisorManagers.totalProtected
    console.log(`Total VMs protected are ${protectedVMCount}`);
}

function getCloudStoreUsage(account) {
    let backupSummary = getBackupSummary(account);
    console.log(JSON.stringify(backupSummary, undefined, 4));
    let backupResp = JSON.parse(backupSummary.body);
    let summaryList = backupResp.protectionStoresSummary;
    let cloudSizeBytes = 0;
    for (const summary of summaryList) {
        for (const cloudStore of summary.cloudStores) {
            console.log(`cloudStore usage is ${JSON.stringify(cloudStore)}`);
            cloudSizeBytes = cloudSizeBytes + parseInt(cloudStore.totalDiskBytes);

        }
        // console.log(`Backup summary are ${JSON.stringify(i.,undefined,4)}`);
    }

    console.log(`Acccount ${account} Cloud Store size byte is ${cloudSizeBytes}`);
    let cloudSize = formatBytes(cloudSizeBytes)
    console.log(`Acccount ${account} Cloud Store size is ${cloudSize}`);
}

function getBackupSummary(account) {
    let header = generateHeaderByAccount(account);
    let uri = "https://scint-app.qa.cds.hpe.com/app-data-management/v1/dashboard/backup-capacity-usage-summary";
    let resp = http.get(uri, header);
    console.log(JSON.stringify(resp, undefined, 4))
    check(resp, { "Get backup summary is initated": (r) => r.status === 200 });
    return resp;
}

/**
 * 
 * @param {object} account - account Object
 * @param {string} protectionJobId - Job id to take backup
 * @param {number} waitTime -Amount of time to wait for backup to be completed
 * @returns 
 */
function runBackupNow(account,protectionJobId, waitTime) {
    let baseUri = "https://scint-app.qa.cds.hpe.com"
    let uri = `${baseUri}/api/v1/protection-jobs/${protectionJobId}/run`;
    let header = generateHeaderByAccount(account);
    console.log(JSON.stringify(header));
    let payload = {
        "scheduleIds": [
            3,
            1,
            2
        ]
    };
    let resp = http.post(uri, JSON.stringify(payload), header);
    console.log(`Backup VM using PSG ${JSON.stringify(resp, undefined, 4)}`);
    check(resp, { "Run backup is initated": (r) => r.status === 202 });
    // @ts-ignore
    let respBody = JSON.parse(resp.body);
    let taskUri = respBody.taskUri;
    console.debug(taskUri);
    sleep(30);
    const taskUrl = `${baseUri}${taskUri}`;
    let isSucceed = waitForTask(taskUrl, waitTime, header);
    return isSucceed;
}

function getVMProtectedSummary(account) {
    let header = generateHeaderByAccount(account);
    let uri = "https://scint-app.qa.cds.hpe.com/app-data-management/v1/dashboard/protections-summary";
    let resp = http.get(uri, header);
    console.log(JSON.stringify(resp, undefined, 4))
    check(resp, { "Get Number of VMs protected is initated": (r) => r.status === 200 });
    return resp;
}

function formatBytes(bytes, decimals = 2) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const dm = decimals < 0 ? 0 : decimals;
    const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
}
