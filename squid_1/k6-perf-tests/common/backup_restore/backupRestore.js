import { sleep, check, fail } from "k6";
import { generateHeader, getProtectionStoreVMList, httpGet } from "../lib.js";
import { getRestoreUrl, restoreToExistingVM, restoreSnapToNewVM, restoreLocalBackupToExistVM, restoreLocalBackupToNewVM, restoreCloudBackupToExistVM, restoreCloudBackupToNewVM } from "./restore_vm.js";
import { createSnapshotBackup, createLocalBackup, deleteLocalBackup, deleteAllLocalBackups, deleteAllCloudBackups, getBackupObj, deleteBackup, createCloudBackup, deleteAllSnapshots } from "./backup_vm.js";
import { getProtectVmId, unprotectVm } from "./protect_vm.js";
import { createProtectionPolicy, getProtectionPolicyTemplate, applyProtectionPolicy, deleteProtectionPolicy } from "./protectionPolicy.js";
import { vcenterName, baseUri } from "../../backup_restore_workflow.js";
import { resizePsgStorage } from "./resize_psg.js";


export class BackupRestoreTest {
    constructor(rpClient, testId, execIteration) {
        this.rpClient = rpClient;
        this.testId = testId;
        this.execIteration = execIteration;
    }

    createProtectionTemplate(policyName, localCopyPoolId, cloudCopyPoolId = null) {
        let testStepId = this.rpClient.startTestStep(this.testId, "Create protection policy template ", "Create protection policy template");
        try {
            let response = createProtectionPolicy(policyName, localCopyPoolId, cloudCopyPoolId);
            if (response.status == 200) {
                this.rpClient.finishTestStep(testStepId, "passed");
                console.log(`[Iteration ${this.execIteration}] =>Create protection policy ${JSON.stringify(response)}`);
            }
            else {
                this.rpClient.finishTestStep(testStepId, "failed", "pb001", "Create protection policy template failed");
                console.log(`[Iteration ${this.execIteration}] =>Create protection policy failed ${JSON.stringify(response)}`);
                fail(`[Iteration ${this.execIteration}] =>Create protection policy failed ${JSON.stringify(response)}`);
            }
        }
        catch (err) {
            console.error(err);
            this.rpClient.finishTestStep(testStepId, "interrupted", "pb001", err);
            console.error(`TestResult=> Iteration ${this.execIteration} =>  Create protection policy template failed`);
            throw err;
        }
    }

    protectVM(policyName, vmToProtect) {
        let testStepId = this.rpClient.startTestStep(this.testId, "Protect VM", "Protect VM by applying protection policy template");
        try {
            // Get Snapshot backup id ,local backup id and cloud backup id(if required)
            let isVmProtected = applyProtectionPolicy(policyName, vmToProtect, vcenterName);
            let testResult = (isVmProtected ? "PASS" : "FAIL");
            let testStatus = (testResult == "PASS") ? "passed" : "failed";
            this.rpClient.finishTestStep(testStepId, testStatus);
            console.log(`TestResult=> Iteration ${this.execIteration} => Protect VM => ${testResult}`);
        }
        catch (err) {
            console.error(err);
            this.rpClient.writeLog(testStepId, err);
            this.rpClient.finishTestStep(testStepId, "interrupted", "pb002", err);
            console.error(`TestResult=> Iteration ${this.execIteration} => Protect VM failed`);
            throw err;
        }
    }

    testCreateSnapshot(isSnapBackupCreated, vmId, snapName, snapStepId) {

        isSnapBackupCreated = createSnapshotBackup(vmId, snapName);
        check(isSnapBackupCreated, { "Snapshot Backup is created successfully": (i) => i == true });
        let testResult = (isSnapBackupCreated ? "PASS" : "FAIL");
        let testStatus = (testResult == "PASS") ? "passed" : "failed";
        this.rpClient.finishTestStep(snapStepId, testStatus);
        console.log(`TestResult=> Iteration ${this.execIteration} => Snapshot Backup Creation => ${testResult}`);
        return isSnapBackupCreated;
    }

    testRestoreSnapToExistingVM(vmToProtect, isSnapBackupRestoredToExistingVM, snapBackupObj) {
        let header = generateHeader();
        let stepId = this.rpClient.startTestStep(this.testId, "Restore Snapshot to existing VM ", "Restore Snapshot to existing VM");
        try {
            console.log(`[Iteration${this.execIteration}] => TestStep => Restore Snapshot to existing VM`);
            let restoreUrl = getRestoreUrl(vmToProtect, vcenterName);
            isSnapBackupRestoredToExistingVM = restoreToExistingVM(restoreUrl, header, snapBackupObj.id);
            check(isSnapBackupRestoredToExistingVM, { "Snapshot Backup restored to existing VM successfully": (i) => i == true });
            let testResult = (isSnapBackupRestoredToExistingVM ? "PASS" : "FAIL");
            let testStatus = (testResult == "PASS") ? "passed" : "failed";
            this.rpClient.finishTestStep(stepId, testStatus);
            console.log(`TestResult=> Iteration ${this.execIteration} => Restore Snapshot to existing VM => ${testResult}`);
            let vmId = getProtectVmId(vmToProtect, vcenterName);
            console.log(`[Restore Snapshot to existing VM] => vmId of ${vmToProtect} after restoring snapshot to existing vm is ${vmId}`);
        }
        catch (err) {
            console.error(err);
            this.rpClient.writeLog(stepId, err);
            this.rpClient.finishTestStep(stepId, "interrupted", "pb003", err);
            console.error(`TestResult=> Iteration ${this.execIteration} => Restore snapshot to New VM failed`);
            throw err;
        }

        return isSnapBackupRestoredToExistingVM;
    }

    testRestoreSnapToNewVM(restoreSnapVm, isSnapBackupRestoredToNewVM, vmToProtect, snapName) {
        let header = generateHeader();
        let stepId = this.rpClient.startTestStep(this.testId, "Restore Snapshot to New VM", "Restore Snapshot to New VM");
        try {
            console.log(`[Iteration ${this.execIteration}] => TestStep => Restore Snapshot to New VM ${restoreSnapVm}`);
            // After restoring vm,vm id will change so getting restoreUrl with latest vmid
            isSnapBackupRestoredToNewVM = restoreSnapToNewVM(vmToProtect, vcenterName, snapName, restoreSnapVm, header);

            check(isSnapBackupRestoredToNewVM, { "Snapshot Backup restored to New VM successfully": (i) => i == true });
            console.log(`[Iteration ${this.execIteration}] => Snapshot Backup restored to New VM ${restoreSnapVm} successfully ${isSnapBackupRestoredToNewVM}`);
            let testResult = (isSnapBackupRestoredToNewVM ? "PASS" : "FAIL");
            let testStatus = (testResult == "PASS") ? "passed" : "failed";
            this.rpClient.finishTestStep(stepId, testStatus);
            console.log(`TestResult=> Iteration ${this.execIteration} => Restore Snapshot to New VM => ${testResult}`);
        }
        catch (err) {
            console.error(err);
            this.rpClient.writeLog(stepId, err);
            this.rpClient.finishTestStep(stepId, "interrupted", "pb004", err);
            console.error(`TestResult=> Iteration ${this.execIteration} => Restore snapshot to New VM failed`);
            throw err;
        }
        return isSnapBackupRestoredToNewVM;
    }

    testCreateLocalBackup(isLocalBackupCreated, vmToProtect, snapName, copyPoolId, localBackupName, localStepId) {

        isLocalBackupCreated = createLocalBackup(vmToProtect, vcenterName, snapName, copyPoolId, localBackupName);
        check(isLocalBackupCreated, { "Local Backup is created successfully": (i) => i == true });
        console.log(`[Iteration ${this.execIteration}] => Local Backup ${localBackupName} is created successfully ${isLocalBackupCreated}`);
        let testResult = (isLocalBackupCreated ? "PASS" : "FAIL");
        let testStatus = (testResult == "PASS") ? "passed" : "failed";
        this.rpClient.finishTestStep(localStepId, testStatus);
        console.log(`TestResult=> Iteration ${this.execIteration} => Create Local Backup => ${testResult}`);
        return isLocalBackupCreated;
    }

    testRestoreLocalToExistingVM(isLocalBackupRestoredToExistingVM, vmToProtect, localBackupName) {
        let header = generateHeader();
        let stepId = this.rpClient.startTestStep(this.testId, "Restore Local Backup to existing VM ", "Restore Local Backup to existing VM");
        try {
            console.log(`[Iteration ${this.execIteration}] => TestStep => Restore Local Backup to existing VM`);
            isLocalBackupRestoredToExistingVM = restoreLocalBackupToExistVM(vmToProtect, vcenterName, localBackupName, header, "Backup");
            check(isLocalBackupRestoredToExistingVM, { "Local Backup restored to existing VM successfully": (i) => i == true });
            if (!isLocalBackupRestoredToExistingVM) {
                console.error(`VM ${vmToProtect} fail to take backup ${localBackupName}`);
            }
            console.log(`[Iteration ${this.execIteration}] => Local Backup restored to existing VM successfully ${isLocalBackupRestoredToExistingVM}`);
            let testResult = (isLocalBackupRestoredToExistingVM ? "PASS" : "FAIL");
            let testStatus = (testResult == "PASS") ? "passed" : "failed";
            this.rpClient.finishTestStep(stepId, testStatus);
            console.log(`TestResult=> Iteration ${this.execIteration} => Restore Local Backup to existing VM => ${testResult}`);
            let vmId = getProtectVmId(vmToProtect, vcenterName);
            console.log(`[Iteration ${this.execIteration}] => vmId after restoring Local Backup to existing vm is ${vmId}`);
        }
        catch (err) {
            console.error(err);
            this.rpClient.writeLog(stepId, err);
            this.rpClient.finishTestStep(stepId, "interrupted", "pb006", err);
            console.error(`TestResult=> Iteration ${this.execIteration} => Restore Local Backup to existing VM failed`);
            throw err;
        }
        return isLocalBackupRestoredToExistingVM;
    }

    testRestoreLocalToNewVM(isLocalBackupRestoredToNewVM, vmToProtect, localBackupName, restoreVmName) {
        let header = generateHeader();
        let stepId = this.rpClient.startTestStep(this.testId, "Restore Local Backup to New VM ", "Restore Local Backup to New VM");
        try {
            console.log(`[Iteration ${this.execIteration}] => TestStep => Restore Local Backup to New VM`);
            // After restoring vm,vm id will change so getting restoreUrl with latest vmid
            isLocalBackupRestoredToNewVM = restoreLocalBackupToNewVM(vmToProtect, vcenterName, localBackupName, restoreVmName, header, "Backup");
            check(isLocalBackupRestoredToNewVM, { "Local Backup restored to New VM successfully": (i) => i == true });
            console.log(`[Iteration ${this.execIteration}] => Local Backup restored to New VM successfully ${isLocalBackupRestoredToNewVM}`);
            let testResult = (isLocalBackupRestoredToNewVM ? "PASS" : "FAIL");
            let testStatus = (testResult == "PASS") ? "passed" : "failed";
            this.rpClient.finishTestStep(stepId, testStatus);
            console.log(`TestResult=> Iteration ${this.execIteration} => Local Backup restored to New VM => ${testResult}`);
        }
        catch (err) {
            console.error(err);
            this.rpClient.writeLog(stepId, err);
            this.rpClient.finishTestStep(stepId, "interrupted", "pb007", err);
            console.error(`TestResult=> Iteration ${this.execIteration} => Restore Local Backup to New VM failed`);
            throw err;
        }
        return isLocalBackupRestoredToNewVM;
    }

    testCreateCloudBackup(isCloudBackupCreated, vmToProtect, localBackupName, policyTemplateId, cloudBackupName) {
        let stepId = this.rpClient.startTestStep(this.testId, "Create Cloud Backup and Restore", "Create Cloud Backup and Restore");
        isCloudBackupCreated = createCloudBackup(vmToProtect, policyTemplateId);
        check(isCloudBackupCreated, { "Cloud Backup is created successfully": (i) => i == true });
        console.log(`[Iteration ${this.execIteration}] => Cloud Backup ${cloudBackupName} is created successfully ${isCloudBackupCreated}`);
        let testResult = (isCloudBackupCreated ? "PASS" : "FAIL");
        let testStatus = (testResult == "PASS") ? "passed" : "failed";
        this.rpClient.finishTestStep(stepId, testStatus);
        console.log(`TestResult=> Iteration ${this.execIteration} => Create Cloud Backup => ${testResult}`);
        return isCloudBackupCreated;
    }

    testRestoreCloudToExistingVM(isCloudBackupRestoredToExistingVM, vmToProtect, cloudBackupName) {
        let header = generateHeader();
        let stepId = this.rpClient.startTestStep(this.testId, "Restore Cloud Backup to existing VM", "Restore Cloud Backup to existing VM");
        try {
            isCloudBackupRestoredToExistingVM = restoreCloudBackupToExistVM(vmToProtect, vcenterName, cloudBackupName, header, "CLOUD_BACKUP");
            check(isCloudBackupRestoredToExistingVM, { "Cloud Backup restored to existing VM successfully": (i) => i == true });
            if (!isCloudBackupRestoredToExistingVM) {
                console.error(`VM ${vmToProtect} fail to take backup ${cloudBackupName}`);
            }
            console.log(`[Iteration ${this.execIteration}] => Cloud Backup restored to existing VM successfully ${isCloudBackupRestoredToExistingVM}`);
            let testResult = (isCloudBackupRestoredToExistingVM ? "PASS" : "FAIL");
            let testStatus = (testResult == "PASS") ? "passed" : "failed";
            this.rpClient.finishTestStep(stepId, testStatus);
            console.log(`TestResult=> Iteration ${this.execIteration} => Restore Cloud Backup to existing VM => ${testResult}`);
            let vmId = getProtectVmId(vmToProtect, vcenterName);
            console.log(`[Iteration ${this.execIteration}] => vmId after restoring Cloud Backup to existing vm is ${vmId}`);
        }
        catch (err) {
            console.error(err);
            this.rpClient.writeLog(stepId, err);
            this.rpClient.finishTestStep(stepId, "interrupted", "pb006", err);
            console.error(`TestResult=> Iteration ${this.execIteration} => Restore Cloud Backup to existing VM failed`);
            throw err;
        }
        return isCloudBackupRestoredToExistingVM;
    }

    testRestoreCloudToNewVM(isCloudBackupRestoredToNewVM, vmToProtect, cloudBackupName, restoreVmName) {
        let header = generateHeader();
        let stepId = this.rpClient.startTestStep(this.testId, "Restore Cloud Backup to New VM", "Restore Cloud Backup to New VM");
        try {
            // After restoring vm,vm id will change so getting restoreUrl with latest vmid
            isCloudBackupRestoredToNewVM = restoreCloudBackupToNewVM(vmToProtect, vcenterName, cloudBackupName, restoreVmName, header, "CLOUD_BACKUP");
            check(isCloudBackupRestoredToNewVM, { "Cloud Backup restored to New VM successfully": (i) => i == true });
            console.log(`[Iteration ${this.execIteration}] => Cloud Backup restored to New VM successfully ${isCloudBackupRestoredToNewVM}`);
            let testResult = (isCloudBackupRestoredToNewVM ? "PASS" : "FAIL");
            let testStatus = (testResult == "PASS") ? "passed" : "failed";
            this.rpClient.finishTestStep(stepId, testStatus);
            console.log(`TestResult=> Iteration ${this.execIteration} => Cloud Backup restored to New VM => ${testResult}`);
        }
        catch (err) {
            console.error(err);
            this.rpClient.writeLog(stepId, err);
            this.rpClient.finishTestStep(stepId, "interrupted", "pb007", err);
            console.error(`TestResult=> Iteration ${this.execIteration} => Restore Cloud Backup to New VM failed`);
            throw err;
        }
        return isCloudBackupRestoredToNewVM;
    }

    deleteLocalBackupandRestoredVM(vmToProtect, restoreVmName, vSphereApi) {
        let teststepId = this.rpClient.startTestStep(this.testId, "Delete the Local backup and restored VM", "Delete the Local backup and restored VM");
        try {
            const waitTimeToDeleteBackup = 600; // 10 Minutes 
            let isLocalBackupDeleted = deleteLocalBackup(vmToProtect, vcenterName, waitTimeToDeleteBackup);
            check(isLocalBackupDeleted, { "Local backup is deleted": (d) => d == true });
            let testResult = (isLocalBackupDeleted ? "PASS" : "FAIL");
            let testStatus = (testResult == "PASS") ? "passed" : "failed";
            this.rpClient.finishTestStep(teststepId, testStatus);
            console.log(`TestResult=> Iteration ${this.execIteration} => Delete Local Backup => ${testResult}`);
            console.log("Sleep 30 seconds after local backup is deleted");
            sleep(30);

            console.log(`[Iteration ${this.execIteration}] => Before deleting the VM restored from local backup ${restoreVmName}, wait for 60 seconds`);
            sleep(60);

            vSphereApi.cleanupVm(restoreVmName);
            console.log(`[Iteration ${this.execIteration}] => After deleting the VM restored from local backup ${restoreVmName}, wait for another 60 seconds.`);
            sleep(60);
        }
        catch (err) {
            console.error(err);
            this.rpClient.writeLog(teststepId, err);
            this.rpClient.finishTestStep(teststepId, "interrupted", "pb010", err);
            console.error(`TestResult=> Iteration ${this.execIteration} => Delete the Local backup and restored VM failed`);
            throw err;
        }
    }

    deleteSnapBackupandRestoredVM(vmToProtect, restoreSnapVm, vSphereApi) {
        let teststepId = this.rpClient.startTestStep(this.testId, "Delete the Snap backup and restored VM", "Delete the Local backup and restored VM");
        try {
            let vmId = getProtectVmId(vmToProtect, vcenterName);
            let vmUrl = `${baseUri}/api/v1/virtual-machines/${vmId}?limit=1000`;
            let headers = generateHeader();
            let resp = httpGet(vmUrl, headers);
            console.log(`[Step 7] VM response of ${vmToProtect} -> VM Id [${vmId}] is ${JSON.stringify(resp)}`);
            if (resp.status != 200) {
                console.log(`[Failure] VM response ${JSON.stringify(resp)}`);
                throw `Failed to get specific vM with the url ${vmUrl} for vm ${vmToProtect}`;
            }
            let snapBackupUri = `${baseUri}/api/v1/virtual-machines/${vmId}/snapshots?limit=1000`;
            let snapBackupObj = getBackupObj(snapBackupUri);
            // const resourceUri = snapBackupObj.resourceUri;
            let isSnapBackupDeleted = deleteBackup(snapBackupObj.resourceUri);
            check(isSnapBackupDeleted, { "Snapshot backup is deleted": (d) => d == true });
            let testResult = (isSnapBackupDeleted ? "PASS" : "FAIL");
            let testStatus = (testResult == "PASS") ? "passed" : "failed";
            this.rpClient.finishTestStep(teststepId, testStatus);
            console.log(`TestResult=> Iteration ${this.execIteration} => Delete the snap backup and restored VM => ${testResult}`);

            console.log(`[Iteration ${this.execIteration}] => Before deleting the VM restored from snapshot ${restoreSnapVm}, wait for 60 seconds`);
            sleep(60);
            vSphereApi.cleanupVm(restoreSnapVm);
            console.log(`[Iteration ${this.execIteration}] => After deleting the VM restored from snapshot ${restoreSnapVm}, wait for another 60 seconds.`);
            sleep(60);
        }
        catch (err) {
            console.error(err);
            this.rpClient.writeLog(teststepId, err);
            this.rpClient.finishTestStep(teststepId, "interrupted", "pb010", err);
            console.error(`TestResult=> Iteration ${this.execIteration} => Delete the Snap backup and restored VM failed`);
            throw err;
        }
    }

    testDeleteCloudBackups(vmToProtect, restoreVmName, vSphereApi) {
        let teststepId = this.rpClient.startTestStep(this.testId, "Delete the Cloud backup and restored VM", "Delete the Cloud backup and restored VM");
        try {
            const waitTimeToDeleteBackup = 600; // 10 Minutes 
            let isCloudBackupDeleted = deleteAllCloudBackups(vmToProtect, vcenterName, waitTimeToDeleteBackup);
            check(isCloudBackupDeleted, { "Cloud backup is deleted": (d) => d == true });
            let testResult = (isCloudBackupDeleted ? "PASS" : "FAIL");
            let testStatus = (testResult == "PASS") ? "passed" : "failed";
            this.rpClient.finishTestStep(teststepId, testStatus);
            console.log(`TestResult=> Iteration ${this.execIteration} => Delete Cloud Backup => ${testResult}`);
            console.log("Sleep 30 seconds after cloud backup is deleted");
            sleep(30);

            console.log(`[Iteration ${this.execIteration}] => Before deleting the VM restored from Cloud backup ${restoreVmName}, wait for 60 seconds`);
            sleep(60);

            vSphereApi.cleanupVm(restoreVmName);
            console.log(`[Iteration ${this.execIteration}] => After deleting the VM restored from cloud backup ${restoreVmName}, wait for another 60 seconds.`);
            sleep(60);
        }
        catch (err) {
            console.error(err);
            this.rpClient.writeLog(teststepId, err);
            this.rpClient.finishTestStep(teststepId, "interrupted", "pb010", err);
            console.error(`TestResult=> Iteration ${this.execIteration} => Delete the Cloud backup and restored VM failed`);
            throw err;
        }
    }

    testDeleteLocalBackups(vmToProtect) {
        let teststepId = this.rpClient.startTestStep(this.testId, "Delete the Local backup", "Delete the Local backup ");
        try {
            const waitTimeToDeleteBackup = 600; // 10 Minutes 
            let isLocalBackupDeleted = deleteAllLocalBackups(vmToProtect, vcenterName, waitTimeToDeleteBackup);
            check(isLocalBackupDeleted, { "Local backup is deleted": (d) => d == true });
            let testResult = (isLocalBackupDeleted ? "PASS" : "FAIL");
            let testStatus = (testResult == "PASS") ? "passed" : "failed";
            this.rpClient.finishTestStep(teststepId, testStatus);
            console.log(`TestResult=> Iteration ${this.execIteration} => Delete Local Backup => ${testResult}`);
            console.log("Sleep 30 seconds after local backup is deleted");
            sleep(30);
        }
        catch (err) {
            console.error(err);
            this.rpClient.writeLog(teststepId, err);
            this.rpClient.finishTestStep(teststepId, "interrupted", "pb010", err);
            console.error(`TestResult=> Iteration ${this.execIteration} => Delete the Local backup failed`);
            throw err;
        }
    }

    testDeleteSnapshots(vmToProtect) {
        let teststepId = this.rpClient.startTestStep(this.testId, "Delete the Snapshot backup", "Delete the Snapshot backup ");
        try {
            const waitTimeToDeleteBackup = 600; // 10 Minutes 
            let isDeleted = deleteAllSnapshots(vmToProtect, vcenterName, waitTimeToDeleteBackup);
            check(isDeleted, { "Snapshot backup is deleted": (d) => d == true });
            let testResult = (isDeleted ? "PASS" : "FAIL");
            let testStatus = (testResult == "PASS") ? "passed" : "failed";
            this.rpClient.finishTestStep(teststepId, testStatus);
            console.log(`TestResult=> Iteration ${this.execIteration} => Delete Snapshot Backup => ${testResult}`);
            console.log("Sleep 30 seconds after snapshot backup is deleted");
            sleep(30);
        }
        catch (err) {
            console.error(err);
            this.rpClient.writeLog(teststepId, err);
            this.rpClient.finishTestStep(teststepId, "interrupted", "pb010", err);
            console.error(`TestResult=> Iteration ${this.execIteration} => Delete the snapshot backup failed`);
            throw err;
        }
    }

    unprotectVM(vmToProtect) {
        let teststepId = this.rpClient.startTestStep(this.testId, "Unprotect VM", "Unprotect VM");
        try {
            let isVmUnprotected = unprotectVm(vmToProtect);
            console.log(`[Iteration ${this.execIteration}] => VM is unprotected ${isVmUnprotected}`);
            let testResult = (isVmUnprotected ? "PASS" : "FAIL");
            let testStatus = (testResult == "PASS") ? "passed" : "failed";
            this.rpClient.finishTestStep(teststepId, testStatus);
            console.log(`TestResult=> Iteration ${this.execIteration} => Unprotect VM => ${testResult}`);
        }
        catch (err) {
            console.error(err);
            this.rpClient.writeLog(teststepId, err);
            this.rpClient.finishTestStep(teststepId, "interrupted", "pb009", err);
            console.error(`TestResult=> Iteration ${this.execIteration} => Unprotect VM failed`);
            throw err;
        }
    }

    deleteProtectionTemplate(policyName) {
        let teststepId = this.rpClient.startTestStep(this.testId, "Delete protection template");
        try {
            let policy = getProtectionPolicyTemplate(policyName);
            let policyTemplateId = policy.id;
            const isProtectionTemplateDeleted = deleteProtectionPolicy(policyTemplateId);
            console.log(`[Iteration ${this.execIteration}] => isProtection template deleted ${isProtectionTemplateDeleted}`);
            let testResult = (isProtectionTemplateDeleted ? "PASS" : "FAIL");
            let testStatus = (testResult == "PASS") ? "passed" : "failed";
            this.rpClient.finishTestStep(teststepId, testStatus);
            console.log(`TestResult=> Iteration ${this.execIteration} => Delete protection template => ${testResult}`);
        }
        catch (err) {
            console.error(err);
            this.rpClient.writeLog(teststepId, err);
            this.rpClient.finishTestStep(teststepId, "interrupted", "pb011", err);
            console.error(`TestResult=> Iteration ${this.execIteration} => Delete protection template failed`);
            throw err;
        }
    }

    resizePsg(catalystVmName, updatePsgDsName, updatePsgSize) {
        let teststepId = this.rpClient.startTestStep(this.testId, "Resize PSG", "Resize PSG");
        try {
            let isPsgResized = resizePsgStorage(catalystVmName, updatePsgDsName, updatePsgSize);
            console.log(`[Iteration ${this.execIteration}] => PSG Resized ${isPsgResized}`);
            let testResult = (isPsgResized ? "PASS" : "FAIL");
            let testStatus = (testResult == "PASS") ? "passed" : "failed";
            this.rpClient.finishTestStep(teststepId, testStatus);
            console.log(`TestResult=> Iteration ${this.execIteration} => Resize PSG => ${testResult}`);
        }
        catch (err) {
            console.error(err);
            this.rpClient.writeLog(teststepId, err);
            this.rpClient.finishTestStep(teststepId, "interrupted", "pb009", err);
            console.error(`TestResult=> Iteration ${this.execIteration} => Resize PSG failed`);
            throw err;
        }
    }
}

export function getCopyPoolId(baseUri, catalystVmName, copyPoolType = "ON_PREMISES") {
    let vmList = getProtectionStoreVMList(catalystVmName);
    // console.log(`VM list is ${JSON.stringify(vmList,undefined,4)}`)
    let catalystVmId = vmList[0].id

    let copyPoolUrl = `${baseUri}/api/v1/protection-stores`;
    console.log(copyPoolUrl);
    // sleep(20)
    let header = generateHeader();
    let response = httpGet(copyPoolUrl, header)
    // @ts-ignore 
    let responseBody = JSON.parse(response.body);
    // console.log(`Response is ${JSON.stringify(response,undefined,4)}`);
    console.log(`Response is ${JSON.stringify(responseBody, undefined, 4)}`);
    for (let copyPool of responseBody.items) {
        const storageSystemId = copyPool.storageSystemInfo.id;
        console.log(`storage system id is ${storageSystemId}`);
        console.log(`Catalyst VM id is ${catalystVmId}`)
        sleep(5);
        if (storageSystemId === catalystVmId && copyPoolType === copyPool.protectionStoreType) {
            console.log("Id matches")
            //   copyPoolId = copyPool.id
            console.log(`Copy pool is ${JSON.stringify(copyPool)}`);
            console.log(copyPool.id)
            return copyPool.id
        }
        else {
            console.debug(`Catalyst gateway VM Id ${catalystVmId} does not match with ${storageSystemId}`)
        }
    }

    console.debug(`Copy pool is not found for ${catalystVmName} with id ${catalystVmId}`)
    // throw "copy pool is not found"
    throw `Copy Pool is not found for VM ${catalystVmName} with id ${catalystVmId}`
}

export function getCloudCopyPoolId(baseUri, catalystVmName, region) {
    let vmList = getProtectionStoreVMList(catalystVmName);
    // console.log(`VM list is ${JSON.stringify(vmList,undefined,4)}`)
    let catalystVmId = vmList[0].id
    let copyPoolType = "CLOUD"
    let copyPoolUrl = `${baseUri}/api/v1/protection-stores`;
    console.log(copyPoolUrl);
    // sleep(20)
    let header = generateHeader();
    let response = httpGet(copyPoolUrl, header)
    // @ts-ignore 
    let responseBody = JSON.parse(response.body);
    // console.log(`Response is ${JSON.stringify(response,undefined,4)}`);
    console.log(`Response is ${JSON.stringify(responseBody, undefined, 4)}`);
    for (let copyPool of responseBody.items) {

        const storageSystemId = copyPool.storageSystemInfo.id;
        console.log(`storage system id is ${storageSystemId}`);
        console.log(`Catalyst VM id is ${catalystVmId}`)
        sleep(5);
        if (storageSystemId === catalystVmId && copyPool.protectionStoreType == copyPoolType) {
            if (region === copyPool.region) {
                console.log("Id matches")
                //   copyPoolId = copyPool.id
                console.log(`Copy pool is ${JSON.stringify(copyPool)}`);
                console.log(copyPool.id)
                return copyPool.id
            }
        }

    }
    console.warn(`Copy pool is not found for ${catalystVmName} with id ${catalystVmId}`)
    // throw "copy pool is not found"
    // throw `Copy Pool is not found for VM ${catalystVmName} with id ${catalystVmId}`
    return null


}