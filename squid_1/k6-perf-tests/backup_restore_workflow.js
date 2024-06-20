import { sleep, check, group } from "k6";
import exec from "k6/execution";
import LibvSphereApi from './common/LibvSphereApi.js';
import { getSnapshotBackup } from "./common/backup_restore/backup_vm.js";
import { getProtectVmId, unprotectVm, getVMDetails } from "./common/backup_restore/protect_vm.js";
import { finishLaunch, finishSuite, startLaunch, startSuite } from "./common/report_portal_v2.js";
import RpClient from "./common/report_portal_v2.js";
import { BackupRestoreTest, getCopyPoolId } from "./common/backup_restore/backupRestore.js";

var testConfig = JSON.parse(open(__ENV.TEST_CONFIG));
var commonVars = testConfig.testbed;
var reporterOptions = testConfig.testbed.reporterOptions;
var testVars = testConfig.testinput.backupRestore;
export var baseUri = commonVars.atlasOptions.baseUri;
export let vcenterName = commonVars.vsphereOptions.vcenter;
var vsphereAuth = commonVars.vsphereOptions.vsphereAuth;
var api_host = `https://${vcenterName}`
// export var globalToken = undefined;

export const options = {
    scenarios: {
        "crud-create-catalyst-vm": {
            executor: "shared-iterations",
            vus: 1,
            iterations: testVars.iteration,
            maxDuration: testVars.duration
        },
    },
};

export function setup() {
    let launchId = startLaunch(reporterOptions);
    console.log(launchId);
    let suiteId = startSuite(launchId,"Backup and Restore Test Suite", `Total Iterations Executed: ${testVars.iteration}`,reporterOptions);
    console.log(`SuiteId ${suiteId}`);
    return { "launchId": launchId,"suiteId": suiteId }
}

export function teardown(data) {
    finishSuite(data.suiteId,data.launchId,reporterOptions);
    finishLaunch(data.launchId, reporterOptions);
}
export default function (data) {

    let execIteration = exec.scenario.iterationInTest
    let launchId = data.launchId
    let rpClient = new RpClient(launchId, reporterOptions);
    let suiteId= data.suiteId;
    let testId = rpClient.startTest(suiteId, `Backup and Restore VM Iteration Test #${execIteration + 1}`, "Backup and Restore VM");
    let vmToProtect = testVars.vmToProtect;
    let backupTestObj = new BackupRestoreTest(rpClient,testId,execIteration);
    try {
        let timestamp = Math.floor(Date.now() / 1000);
        let policyName = `PerfLocalBackup-${timestamp}`;
        let catalystVmName = testVars.catalystVm;
        let copyPoolType = "ON_PREMISES";
        let copyPoolId = getCopyPoolId(baseUri, catalystVmName, copyPoolType);
        let snapName = `PerfSnapBackup-${timestamp}`;
        let restoreSnapVm = `RestoreSnap-${vmToProtect}-${timestamp}`

        var vSphereApi = new LibvSphereApi(testConfig);
        vSphereApi.headers = vSphereApi.getHeaders();


        // Step 1 -> Create protection Policy
        group("Step 1 -> Create protection policy template", () => {
            console.log(`[Iteration${execIteration}] => TestStep => Step 1 -> Create protection policy template`);
            backupTestObj.createProtectionTemplate(policyName, copyPoolId);
        });
        
        console.log(`[Iteration ${execIteration}] => wait 10 seconds after protection policy ${policyName} is created`)
        sleep(10)
        group("Step 2-> Protect VM", () => {
            console.log(`[Iteration${execIteration}] => TestStep => Step 2 -> Protect VM`);
            backupTestObj.protectVM(policyName, vmToProtect);
        });
        console.log("wait 120 seconds after VM is protected")
        sleep(120)

        // // It will create snapshot immediately so wait for few mins
        // Step 3 -> create local backup
        group("Step3 -> Create Snapshot backup and Restore", () => {
            let isSnapBackupCreated = null,isSnapBackupRestoredToExistingVM=null,isSnapBackupRestoredToNewVM=null;
            let isSnapBackupCompleted = false;
            let snapStepId = rpClient.startTestStep(testId, "Create Snapshot backup", "Create Snapshot backup");
            try {
                let vmId = getProtectVmId(vmToProtect, vcenterName);
                console.log(`[Iteration${execIteration}] => TestStep => Step 3 -> Create Snapshot backup and Restore`);
                isSnapBackupCreated = backupTestObj.testCreateSnapshot(isSnapBackupCreated, vmId, snapName,snapStepId);
                let snapBackupObj = getSnapshotBackup(vmId, snapName);
                console.log(`[Iteration ${execIteration}] => Snapshot backup object is ${snapBackupObj.id}`);

                group("Restore Snapshot to existing VM", () => {
                    isSnapBackupRestoredToExistingVM = backupTestObj.testRestoreSnapToExistingVM(vmToProtect,isSnapBackupRestoredToExistingVM,snapBackupObj);
                });

                console.log(`Waiting for 60 seconds after snapshot restored to existing VM ${vmToProtect}`);
                sleep(60);

                group("Restore Snapshot to New VM", () => {
                    isSnapBackupRestoredToNewVM = backupTestObj.testRestoreSnapToNewVM(restoreSnapVm, isSnapBackupRestoredToNewVM, vmToProtect,snapName);
                });

                isSnapBackupCompleted = isSnapBackupCreated && isSnapBackupRestoredToExistingVM && isSnapBackupRestoredToNewVM;

            }
            catch (err) {
                console.error(err)
                rpClient.writeLog(snapStepId,err);
                rpClient.finishTestStep(snapStepId, "interrupted", "pb005", err);
                console.error(`TestResult=> Iteration ${execIteration} => Backup and restore snapshot failed`)
                throw err;
            }
            finally{
                check(isSnapBackupCompleted, { "TestResult=> Snapshot Backup and Restore": (i) => i == true });
            }
        })

        console.log("Sleep 30 seconds after snapshot restored to New VM")
        sleep(60);
        let restoreVmName = `RestoreLocal-${vmToProtect}-${timestamp}`;
        group("Step4 -> Create Local Backup and Restore", () => {
            let isLocalBackupCreated= null,isLocalBackupRestoredToExistingVM=null,isLocalBackupRestoredToNewVM=null;
            let isLocalBackupCompleted = false;
            let localStepId = rpClient.startTestStep(testId, "Create Local Backup", "Create Local Backup");
            try {
                let localBackupName = `PerfLocalBackup-${timestamp}`
                console.log(`[Iteration${execIteration}] => TestStep => Step 4 -> Create Local Backup and Restore`);
                isLocalBackupCreated = backupTestObj.testCreateLocalBackup(isLocalBackupCreated, vmToProtect,snapName, copyPoolId, localBackupName,localStepId);

                console.log("Sleep 30 seconds after Local Backup is created")
                sleep(30);

                group("Restore Local Backup to existing VM", () => {
                    isLocalBackupRestoredToExistingVM = backupTestObj.testRestoreLocalToExistingVM(isLocalBackupRestoredToExistingVM, vmToProtect,localBackupName);
                });

                console.log("Sleep 60 seconds after Local Backup restored to existing VM")
                sleep(60)

                group("Restore Local Backup to New VM", () => {
                    isLocalBackupRestoredToNewVM = backupTestObj.testRestoreLocalToNewVM(isLocalBackupRestoredToNewVM, vmToProtect,localBackupName, restoreVmName);
                });

                isLocalBackupCompleted = isLocalBackupCreated && isLocalBackupRestoredToExistingVM && isLocalBackupRestoredToNewVM;
            }
            catch (err) {
                console.error(err)
                rpClient.writeLog(localStepId,err);
                rpClient.finishTestStep(localStepId, "interrupted", "pb008", err);
                console.error(`TestResult=> Iteration ${execIteration} => Create Local Backup and Restore failed`)
                throw err;
            }
            finally{
                check(isLocalBackupCompleted, { "TestResult=> Local Backup and Restore": (i) => i == true });

            }
        })
        console.log("Sleep 60 seconds after Local Backup restored to New VM")
        sleep(60)
        // Step -> Unprotect VM
        group("Step 5 -> Unprotect VM", () => {
            console.log(`[Iteration${execIteration}] => TestStep => Step 5 -> Unprotect VM`);
            backupTestObj.unprotectVM(vmToProtect);
        });
        console.log("Sleep 30 seconds after unprotect VM")
        sleep(30);
        // Step -> Delete backup.
        group("Step 6 -> Delete the Local backup and restored VM", () => {
            console.log(`[Iteration${execIteration}] => TestStep => Step 6 -> Delete the Local backup and restored VM`);
            backupTestObj.deleteLocalBackupandRestoredVM(vmToProtect, restoreVmName, vSphereApi);
        });
        group("Step 7 -> Delete the snap backup and restored VM ", () => {
            console.log(`Iteration ${execIteration} => TestStep => Delete the snap backup and restored VM`);
            backupTestObj.deleteSnapBackupandRestoredVM(vmToProtect, restoreSnapVm, vSphereApi);
        });

        console.log("Sleep 30 seconds after snap backups are deleted")

        // Finally delete the protection policy
        group("Step 8-> Delete protection template", () => {
            console.log(`[Iteration${execIteration}] => TestStep => Step 7 -> Delete protection template`);
            backupTestObj.deleteProtectionTemplate(policyName);
        });
        rpClient.finishTest(testId, "passed");
    }
    catch (err) {
        console.error(err);
        rpClient.writeLog(testId,err);
        console.error(`[Backup Restore] Exception occurrred during iteration ${execIteration} `)
        rpClient.finishTest(testId, "failed");
    }
    finally {
        // Unprotect VM
        let vm_detail = getVMDetails(vmToProtect,vcenterName);
        if (vm_detail.protectionJobInfo !== undefined){
            console.log("VM is in protected state.Unprotect vm before continuing next iteration");
            let isVmUnprotected = unprotectVm(vmToProtect);
            console.log(`[Iteration ${execIteration}] => VM is unprotected ${isVmUnprotected}`)
        }
        else{
            console.log("VM is already in protected state.Continuing next iteration");
        }
        sleep(60)
    }

}


