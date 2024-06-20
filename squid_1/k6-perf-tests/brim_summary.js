import { sleep, check, group } from "k6";
import http from "k6/http";
import { generateHeaderByAccount } from "./common/lib.js";
import RpClient, { finishLaunch, finishSuite, startLaunch, startSuite } from "./common/report_portal_v2.js";

var configFilePath = `${__ENV.TEST_CONFIG}`;
var testConfig = JSON.parse(open(configFilePath));
var backupObj = testConfig.testinput.brimBackup
let accountObj = testConfig.testbed.accountOptions;
var reporterOptions = testConfig.testbed.reporterOptions;

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

export function setup() {
    let launchId = startLaunch(reporterOptions);
    console.log(launchId);
    let suiteId = startSuite(launchId, "BRIM Backup Metrics", 'BRIM Protected VM and Cloud backup size metrics for all BRIM accounts', reporterOptions);
    console.log(`SuiteId ${suiteId}`);
    return { "launchId": launchId, "suiteId": suiteId }
}

export default function (data) {
    let launchId = data.launchId
    let rpClient = new RpClient(launchId, reporterOptions);
    let suiteId = data.suiteId;
    let testId = rpClient.startTest(suiteId, 'BRIM Metrics', "Metrics of BRIM account");
    try {
        let brim1Summary = getSummaryReport(accountObj['INGRAM MICRO ASIA TEST'], 5);
        rpClient.writeLog(testId, `INGRAM MICRO ASIA TEST -> Used cloud size -> ${brim1Summary.cloudSize}`);
        rpClient.writeLog(testId, `INGRAM MICRO ASIA TEST -> No of VMs Protected -> ${brim1Summary.vmCount}`);

        let brim2Summary = getSummaryReport(accountObj.BRIM2, 5);
        rpClient.writeLog(testId, `BRIM2 -> Used cloud size -> ${brim2Summary.cloudSize}`);
        rpClient.writeLog(testId, `BRIM2 -> No of VMs Protected -> ${brim2Summary.vmCount}`);
        rpClient.finishTest(testId, "passed");
        
    }
    catch (err) {
        console.error(err);
        rpClient.writeLog(testId, err);
        rpClient.finishTest(testId, "failed");
    }
    sleep(10);

    // let testId2 = rpClient.startTest(suiteId, 'BRIM2 Metrics', "Metrics of BRIM1 account");
    // try {
    //     let brim2Summary = getSummaryReport(accountObj.BRIM2, 5);
    //     rpClient.writeLog(testId2, `BRIM2 -> Used cloud size -> ${brim2Summary.cloudSize}`);
    //     rpClient.writeLog(testId2, `BRIM2 -> No of VMs Protected -> ${brim2Summary.vmCount}`);
    //     rpClient.finishTest(testId2, "passed");
    // }
    // catch (err) {
    //     console.error(err);
    //     rpClient.writeLog(testId2, err);
    //     rpClient.finishTest(testId2, "failed");
    // }
}

export function teardown(data) {
    console.log("Teardown to complete the report portal")
    finishSuite(data.suiteId, data.launchId, reporterOptions);
    finishLaunch(data.launchId, reporterOptions);
}
/////////////////////////////////////// Lib Area ///////////////////////////////////////

function getSummaryReport(account, waitTime = 30) {
    let cloudSizeBytes = getCloudStoreUsage(account);
    console.log(`Acccount ${account.name} Cloud Store size byte is ${cloudSizeBytes}`);
    let cloudSize = formatBytes(cloudSizeBytes)
    console.log(`Acccount ${account.name} Cloud Store size is ${cloudSize}`);

    sleep(waitTime)

    let vmProtectedSummary = getVMProtectedSummary(account);
    console.debug(`VM Protected summary ${JSON.stringify(vmProtectedSummary, undefined, 4)}`);
    // if(vmProtectedSummary.status == )
    var vmBody = JSON.parse(vmProtectedSummary.body);
    let protectedVMCount = vmBody.hypervisorManagers.totalProtected
    console.log(`Total VMs protected are ${protectedVMCount}`);
    return { "cloudSize": cloudSize, "vmCount": protectedVMCount }
}

function getCloudStoreUsage(account) {
    let backupSummary = getBackupSummary(account);
    console.log(JSON.stringify(backupSummary, undefined, 4));
    let backupResp = JSON.parse(backupSummary.body);
    let summaryList = backupResp.protectionStoresSummary;
    let cloudSizeBytes = 0;
    for (const summary of summaryList) {
        for (const cloudStore of summary.cloudStores) {
            // console.log(`cloudStore usage is ${JSON.stringify(cloudStore)}`);
            cloudSizeBytes = cloudSizeBytes + parseInt(cloudStore.totalDiskBytes);

        }
        // console.log(`Backup summary are ${JSON.stringify(i.,undefined,4)}`);
    }
    return cloudSizeBytes

}

function getBackupSummary(account) {
    let header = generateHeaderByAccount(account);
    let uri = "https://scint-app.qa.cds.hpe.com/app-data-management/v1/dashboard/backup-capacity-usage-summary";
    let resp = http.get(uri, header);
    console.log(JSON.stringify(resp, undefined, 4))
    check(resp, { "Get backup summary is initated": (r) => r.status === 200 });
    if (resp.status !== 200) {
        throw `Backup summary for ${account.name} account is failed `
    }
    return resp;
}

function getVMProtectedSummary(account) {
    let header = generateHeaderByAccount(account);
    let uri = "https://scint-app.qa.cds.hpe.com/app-data-management/v1/dashboard/protections-summary";
    let resp = http.get(uri, header);
    console.log(JSON.stringify(resp, undefined, 4))
    check(resp, { "Get Number of VMs protected is initated": (r) => r.status === 200 });
    if (resp.status !== 200) {
        throw `VM Protected summary for ${account.name} account is failed `
    }
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