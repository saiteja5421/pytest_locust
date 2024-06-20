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
    console.log("After all the backups are taken wait for 30 minutes")
    sleep(1800);

    // getSummaryReport(accountObj.BRIM1,5);
    // sleep(10);
    // getSummaryReport(accountObj.BRIM2,5);
}

// https://scint-app.qa.cds.hpe.com/api/v1/app-data-management-jobs/901c02a6-3392-4c8a-9294-b42b9f605f97
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
