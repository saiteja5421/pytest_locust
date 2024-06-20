import exec from "k6/execution";
import { sleep, check, group, fail } from "k6";
import { generateHeader, httpGet } from "./common/lib.js"
import RpClient, { finishLaunch, finishSuite, startLaunch, startSuite } from "./common/report_portal_v2.js";



var testConfig = JSON.parse(open(__ENV.TEST_CONFIG));
var commonVars = testConfig.testbed.atlasOptions;
var reporterOptions = testConfig.testbed.reporterOptions;
var testVars = testConfig.testinput.backupRestore;
export var baseUri = commonVars.baseUri;

export const options = {
    scenarios: {
        "crud-create-catalyst-vm": {
            executor: "shared-iterations",
            vus: testVars.virtualUsers,
            iterations: testVars.iteration,
            maxDuration: testVars.duration,
            // startVUs: 0,
            // stages: [
            //   { duration: '2m', target: 5 },
            //   { duration: '5m', target: 10 },
            //   { duration: '2m',target: 0}
            // ],
            // gracefulRampDown: '0s',
        },
    },
};
export function setup() {
    let launchId = startLaunch(reporterOptions);
    console.log(launchId);
    let suiteId = startSuite(launchId, "Monitor Health page Test Suite", `Total Iterations Executed: ${testVars.iteration}`, reporterOptions);
    console.log(`SuiteId ${suiteId}`);
    return { "launchId": launchId, "suiteId": suiteId }
}

export function teardown(data) {
    finishSuite(data.suiteId, data.launchId, reporterOptions);
    finishLaunch(data.launchId, reporterOptions);
}
export default function (data) {
    let execIteration = exec.scenario.iterationInTest;
    let launchId = data.launchId
    let rpClient = new RpClient(launchId, reporterOptions);
    let suiteId = data.suiteId;
    let testId = rpClient.startTest(suiteId, `Monitor Health page #${execIteration + 1}`, "Monitor Health page");
    let isMonitorHealthPageCompleted = false;
    try {
        console.log(`Monitor health page -> Iteration#${execIteration + 1} Started`);
        group("Monitor Health Page", () => {
            let isBackupUsageNotNull = null, isRecoveryPointNotNull = null, isInventorySummaryNotNull = null, isProtectionJobSummaryNotNull = null, isProtectionPoliciesSummaryNotNull = null;
            group("Monitor Backup usage summary", () => {
                let testStepId = rpClient.startTestStep(testId, "Monitor Backup usage summary", "Monitor Backup usage summary");
                isBackupUsageNotNull = get_backup_usage_summary();
                check(isBackupUsageNotNull, { "Backup usage summary check completed ": (i) => i == true });
                let testResult = (isBackupUsageNotNull ? "PASS" : "FAIL");
                let testStatus = (testResult == "PASS") ? "passed" : "failed"
                rpClient.finishTestStep(testStepId, testStatus);
                console.log(`TestResult=> Iteration ${execIteration} => Monitor Backup usage summary => ${testResult}`)
            });

            group("Monitor Recovery point", () => {
                let testStepId = rpClient.startTestStep(testId, "Monitor Recovery point check", "Monitor Recovery point check");
                isRecoveryPointNotNull = get_recovery_point_details();
                check(isRecoveryPointNotNull, { "Recovery point check completed ": (i) => i == true });
                let testResult = (isRecoveryPointNotNull ? "PASS" : "FAIL");
                let testStatus = (testResult == "PASS") ? "passed" : "failed"
                rpClient.finishTestStep(testStepId, testStatus);
                console.log(`TestResult=> Iteration ${execIteration} => Monitor Recovery point => ${testResult}`)
            });
            group("Monitor Inventory summary", () => {
                let testStepId = rpClient.startTestStep(testId, "Monitor Inventory summary", "Monitor Inventory summary");
                isInventorySummaryNotNull = get_inventory_summary();
                check(isInventorySummaryNotNull, { "Inventory summary check completed ": (i) => i == true });
                let testResult = (isInventorySummaryNotNull ? "PASS" : "FAIL");
                let testStatus = (testResult == "PASS") ? "passed" : "failed"
                rpClient.finishTestStep(testStepId, testStatus);
                console.log(`TestResult=> Iteration ${execIteration} => Monitor Inventory summary => ${testResult}`)
            });
            group("Monitor Protection job summary", () => {
                let testStepId = rpClient.startTestStep(testId, "Monitor Protection job summary", "Monitor Protection job summary");
                isProtectionJobSummaryNotNull = get_protection_job_summary();
                check(isProtectionJobSummaryNotNull, { "Protection job summary check completed ": (i) => i == true });
                let testResult = (isProtectionJobSummaryNotNull ? "PASS" : "FAIL");
                let testStatus = (testResult == "PASS") ? "passed" : "failed"
                rpClient.finishTestStep(testStepId, testStatus);
                console.log(`TestResult=> Iteration ${execIteration} => Monitor Protection job summary => ${testResult}`)
            });
            group("Monitor Protection policies summary", () => {
                let testStepId = rpClient.startTestStep(testId, "Monitor Protection policies summary", "Monitor Protection policies summary");
                isProtectionPoliciesSummaryNotNull = get_protection_policies_summary();
                check(isProtectionPoliciesSummaryNotNull, { "Protection policies summary check completed ": (i) => i == true });
                let testResult = (isProtectionPoliciesSummaryNotNull ? "PASS" : "FAIL");
                let testStatus = (testResult == "PASS") ? "passed" : "failed"
                rpClient.finishTestStep(testStepId, testStatus);
                console.log(`TestResult=> Iteration ${execIteration} => Monitor Protection policies summary => ${testResult}`)
            });

            isMonitorHealthPageCompleted = isBackupUsageNotNull && isRecoveryPointNotNull && isInventorySummaryNotNull && isProtectionJobSummaryNotNull && isProtectionPoliciesSummaryNotNull;


            if (isMonitorHealthPageCompleted) {
                rpClient.finishTest(testId, "passed");
            }
            else {
                rpClient.finishTest(testId, "failed");
            }
        });

    }
    catch (err) {
        console.error(err);
        console.error(`[Monitor Health page] Exception occurrred during iteration ${execIteration} `)
        rpClient.writeLog(testId, err);
        rpClient.finishTest(testId, "interrupted");

    }
    finally {
        check(isMonitorHealthPageCompleted, { "TestResult=> Monitor Health Page": (i) => i == true });
        sleep(30);
    }

}
export function get_backup_usage_summary() {
    let header = generateHeader();
    let backup_url = `${baseUri}/app-data-management/v1/dashboard/backup-capacity-usage-summary`;
    let response = httpGet(backup_url, header);
    let responseBody = JSON.parse(response.body);
    console.log(`Response is ${JSON.stringify(responseBody, undefined, 4)}`);
    if (response.status === 200 && responseBody !== null) {
        console.log("Backup usage summary succeeded")
        return true
    }
    return false
}

export function get_recovery_point_details() {
    let header = generateHeader();
    let backup_url = `${baseUri}/app-data-management/v1/dashboard/copies-summary`;
    let response = httpGet(backup_url, header);
    let responseBody = JSON.parse(response.body);
    console.log(`Response is ${JSON.stringify(responseBody, undefined, 4)}`);
    if (response.status === 200 && responseBody !== null) {
        console.log("Recovery point summary succeeded")
        return true
    }
    return false
}
export function get_inventory_summary() {
    let header = generateHeader();
    let backup_url = `${baseUri}/app-data-management/v1/dashboard/inventory-summary`;
    let response = httpGet(backup_url, header);
    let responseBody = JSON.parse(response.body);
    console.log(`Response is ${JSON.stringify(responseBody, undefined, 4)}`);
    if (response.status === 200 && responseBody !== null) {
        console.log("Inventory summary succeeded")
        return true
    }
    return false
}
export function get_protection_job_summary() {
    let header = generateHeader();
    let backup_url = `${baseUri}/app-data-management/v1/dashboard/job-execution-status-summary`;
    let response = httpGet(backup_url, header);
    let responseBody = JSON.parse(response.body);
    console.log(`Response is ${JSON.stringify(responseBody, undefined, 4)}`);
    if (response.status === 200 && responseBody !== null) {
        console.log("Protection job summary succeeded")
        return true
    }
    return false
}
export function get_protection_policies_summary() {
    let header = generateHeader();
    let backup_url = `${baseUri}/app-data-management/v1/dashboard/templates-summary`;
    let response = httpGet(backup_url, header);
    let responseBody = JSON.parse(response.body);
    console.log(`Response is ${JSON.stringify(responseBody, undefined, 4)}`);
    if (response.status === 200 && responseBody !== null) {
        console.log("Protection policies summary succeeded")
        return true
    }
    return false
}