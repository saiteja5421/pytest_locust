import { sleep, check, group } from "k6";
import exec from "k6/execution";
import LibvSphereApi from './common/LibvSphereApi.js';
import { getProtectVmId, getVMDetails, unprotectVm } from "./common/backup_restore/protect_vm.js";
import { finishLaunch, finishSuite, startLaunch, startSuite } from "./common/report_portal_v2.js";
import RpClient from "./common/report_portal_v2.js";
import { createCatalystGateway, getCalalystIdByName, httpCreateCloudStore, getDatastoreId, getHostId, getHypervisorManagerId, fetchRandomHostAndDataStore } from "./common/createLocalStore.js";
import { BackupRestoreTest, getCloudCopyPoolId, getCopyPoolId } from "./common/backup_restore/backupRestore.js";
import { getProtectionPolicyTemplate } from "./common/backup_restore/protectionPolicy.js";
import { getProtectionStoreVMList, generateHeader, waitForTask } from "./common/lib.js";
import { deleteCatalystVM } from "./common/deleteCatalystVM.js";
import { addCatalystNic } from "./common/AddCatalystNic.js";

var testConfig = JSON.parse(open(__ENV.TEST_CONFIG));
var commonVars = testConfig.testbed;
var reporterOptions = testConfig.testbed.reporterOptions;
var testVars = testConfig.testinput.backupRestore;
export var baseUri = commonVars.atlasOptions.baseUri;
let vcenterName = commonVars.vsphereOptions.vcenter;
var psgwOptions = testVars.psgwOptions;
var vmPrefix = psgwOptions.vmPrefix;
export var gateway = psgwOptions.gateway;
export var subnetMask = psgwOptions.subnetMask;
var data1IPAddress = psgwOptions.data1IP;
var dataSubnetMask = psgwOptions.dataSubnetMask;
var data1NetworkName = psgwOptions.network2;
var networkType = "STATIC";

export const options = {
    scenarios: {
        "backup-and-restore": {
            executor: "shared-iterations",
            vus: 1,
            iterations: testVars.iteration,
            maxDuration: testVars.duration
        },
    },
    insecureSkipTLSVerify: true,
    setupTimeout: `${parseInt(commonVars.vsphereOptions.vmCreationTimeout)}s`,
    teardownTimeout: '500s',
};

export function setup() {
    let launchId = startLaunch(reporterOptions);
    console.log(launchId);
    let suiteId = startSuite(launchId, "Cloud Backup and Restore Test Suite", `Total Iterations Executed: ${testVars.iteration}`, reporterOptions);
    console.log(`SuiteId ${suiteId}`);

    // Define PSG name
    let protectionStoreName = `${vmPrefix}_${Math.floor(Date.now() / 1000)}`;

    // Read PSG management IPv4 address
    var ipAddress = testVars.nwAddress;

    // Fetch vCenter object UUID from DSCC
    let hypervisorId = getHypervisorManagerId(baseUri, vcenterName)
    console.log(`[setup] hypervisor id is => ${hypervisorId}`);

    // Read VCSA info from datafile
    let vcenterList = testConfig.testbed.vcenterList;
    console.log(`[setup] vcenterlist ${JSON.stringify(vcenterList)}`);
    let vcenterObj = undefined;
    for (let vc of vcenterList) {
        if (vc.name === vcenterName) {
            vcenterObj = vc;
        }
    }
    // Read management network moref string from data file
    let networkName = vcenterObj.networkName
    console.log(`network name is ${networkName}`);

    // Read datastore and esxi hostname info from datafile
    let { datastoreName, hostName } = fetchRandomHostAndDataStore(vcenterObj);
    console.log(`[setup]=> Datastore name: ${datastoreName} and hostname: ${hostName}`);

    // Fetch Datastore object ID from DSCC for PSG deployment
    let datastoreId = getDatastoreId(baseUri, datastoreName)
    console.log(`[setup]=> Datastore id is ${datastoreId}`);

    // Fetch ESXi host object ID from DSCC for PSG deployment
    let hostId = getHostId(baseUri, datastoreName, hostName);
    console.log(`[setup]=> host id is ${hostId}`);

    var dnsAddress = psgwOptions.dnsAddress;
    var vmCreationWaitTime = parseInt(commonVars.vsphereOptions.vmCreationTimeout);

    // Deploy PSG
    try {
        let isVMDeployed = createCatalystGateway(networkName, protectionStoreName, ipAddress, dnsAddress, vmCreationWaitTime, hypervisorId, datastoreId, hostId, baseUri, gateway, subnetMask);
        if (isVMDeployed) {
            console.info(`Protection store gateway VM ${protectionStoreName} is deployed`);
            console.log("Sleep for 5 minutes to complete local protection store creation");
            sleep(300);
        }
        else {
            console.log("sleep 30 seconds");
            sleep(30);
            throw `Protection store gateway VM ${protectionStoreName} is failed to deploy`;
        }

        // Add additional DATA interface
        var catalystVMList = getProtectionStoreVMList(protectionStoreName);
        console.log(`Catalyst VM list ${JSON.stringify(catalystVMList)}`)
        var vmToBeModifiedObj = catalystVMList[0]
        let header = generateHeader();
        let isData1NetworkAdded = AddNetworkInterface(baseUri, vmToBeModifiedObj, data1IPAddress, networkType, dataSubnetMask, data1NetworkName, header);

        if (isData1NetworkAdded != true) {
            console.error("Failed to add additional DATA interface.")
        }
    } catch (err) {
        console.error(err.message);
        console.error(`setup() failed to deploy PSG`)
        var psg = getProtectionStoreVMList(protectionStoreName);
        console.log(`PSG: ${JSON.stringify(psg)}`)
        deleteCatalystVM(baseUri, psg[0], null);
    }
    return { "launchId": launchId, "suiteId": suiteId, "protectionStoreName": protectionStoreName }
}

export function teardown(data) {
    var psg = getProtectionStoreVMList(data.protectionStoreName);
    console.log(`PSG: ${JSON.stringify(psg)}`)
    deleteCatalystVM(baseUri, psg[0], null);

    finishSuite(data.suiteId, data.launchId, reporterOptions);
    finishLaunch(data.launchId, reporterOptions);
}

export default function (data) {
    let execIteration = exec.scenario.iterationInTest;
    let launchId = data.launchId;
    let rpClient = new RpClient(launchId, reporterOptions);
    let suiteId = data.suiteId;
    let testId = rpClient.startTest(suiteId, `Cloud Backup and Restore VM Test #${execIteration + 1}`, "Cloud Backup and Restore VM");
    let vmToProtect = testVars.vmToProtect;
    let backupTestObj = new BackupRestoreTest(rpClient, testId, execIteration);
    let timestamp = Math.floor(Date.now() / 1000);
    let policyName = `PerfCloudBackup-${timestamp}`;
    try {
        let catalystVmName = data.protectionStoreName;
        let updatePsgDsName = testVars.updateDsName;
        let updatePsgSize1 = testVars.updatePsgSize1;
        let updatePsgSize2 = testVars.updatePsgSize2;
        let catalystGatewayId = getCalalystIdByName(baseUri, catalystVmName);
        let localCopyPoolId = getCopyPoolId(baseUri, catalystVmName, "ON_PREMISES");
        let region = 'USA, North Virginia';
        let cloudCopyPoolId = getCloudCopyPoolId(baseUri, catalystVmName, region);
        console.log(cloudCopyPoolId);
        if (cloudCopyPoolId === null) {
            httpCreateCloudStore(baseUri, catalystGatewayId, region);
            cloudCopyPoolId = getCloudCopyPoolId(baseUri, catalystVmName, region);
        }
        let snapName = `PerfSnapBackup-${timestamp}`;

        var vSphereApi = new LibvSphereApi(testConfig);
        vSphereApi.headers = vSphereApi.getHeaders();

        // Step 1 -> Create protection Policy
        group("Step 1 -> Create protection policy template", () => {
            console.log(`[Iteration${execIteration}] => TestStep => Step 1 -> Create protection policy template`);
            backupTestObj.createProtectionTemplate(policyName, localCopyPoolId, cloudCopyPoolId);
        });
        console.log(`[Iteration ${execIteration}] => wait 10 seconds after protection policy ${policyName} is created`);
        sleep(10);

        group("Step 2-> Protect VM", () => {
            console.log(`[Iteration${execIteration}] => TestStep => Step 2 -> Protect VM`);
            backupTestObj.protectVM(policyName, vmToProtect);
        });
        console.log("wait 120 seconds after VM is protected");
        sleep(600);

        // group("Step 3-> Create Snapshot backup", () => {
        //     let stepId = rpClient.startTestStep(testId, "Create Snapshot backup", "Create Snapshot backup");
        //     let isSnapBackupCreated = null;
        //     try {
        //         console.log(`[Iteration${execIteration}] => TestStep => Step 3 -> Create Snapshot Backup`);
        //         let vmId = getProtectVmId(vmToProtect, vcenterName);
        //         isSnapBackupCreated = backupTestObj.testCreateSnapshot(isSnapBackupCreated, vmId, snapName, stepId);
        //         check(isSnapBackupCreated, { "Snapshot Backup is created successfully": (i) => i == true });
        //         let testResult = (isSnapBackupCreated ? "PASS" : "FAIL");
        //         let testStatus = (testResult == "PASS") ? "passed" : "failed";
        //         rpClient.finishTestStep(stepId, testStatus);
        //         console.log(`TestResult=> Iteration ${execIteration} => Snapshot Backup Creation => ${testResult}`);
        //     }
        //     catch (err) {
        //         console.error(err);
        //         rpClient.writeLog(stepId, err);
        //         rpClient.finishTestStep(stepId, "interrupted", "pb005", err);
        //         console.error(`TestResult=> Iteration ${execIteration} => Create  Snapshot backup failed`);
        //         throw err;
        //     }
        // })
        // console.log("wait 60 seconds after taking Snapshot");
        // sleep(60);

        let localBackupName = `PerfLocalBackup-${timestamp}`;
        // // let localBackupName ="Snapshot_2021-12-21-23:23:55"
        // group("Step 4 -> Create Local Backup", () => {
        //     let stepId = rpClient.startTestStep(testId, "Create Local Backup", "Create Local Backup");
        //     let isLocalBackupCreated = null;
        //     try {
        //         console.log(`[Iteration${execIteration}] => TestStep => Step 4 -> Create Local Backup`);
        //         isLocalBackupCreated = backupTestObj.testCreateLocalBackup(isLocalBackupCreated, vmToProtect, snapName, localCopyPoolId, localBackupName, stepId);

        //         check(isLocalBackupCreated, { "Local Backup is created successfully": (i) => i == true });
        //         console.log(`[Iteration ${execIteration}] => Local Backup ${localBackupName} is created successfully ${isLocalBackupCreated}`);
        //         let testResult = (isLocalBackupCreated ? "PASS" : "FAIL");
        //         let testStatus = (testResult == "PASS") ? "passed" : "failed";
        //         rpClient.finishTestStep(stepId, testStatus);
        //         console.log(`TestResult=> Iteration ${execIteration} => Create Local Backup => ${testResult}`);
        //         console.log("Sleep 30 seconds after Local Backup is created");
        //         sleep(30);
        //     }
        //     catch (err) {
        //         console.error(err);
        //         rpClient.writeLog(stepId, err);
        //         rpClient.finishTestStep(stepId, "interrupted", "pb006", err);
        //         console.error(`TestResult=> Iteration ${execIteration} => Create Local Backup failed`);
        //         throw err;
        //     }
        // })
        // console.log("Sleep 120 seconds after Creating Local backup");
        // sleep(120);

        let restoreVmName = `RestoreCloud-${vmToProtect}-${timestamp}`;
        group("Step 5 -> Create Cloud Backup and Restore", () => {
            let isCloudBackupCreated = null, isCloudBackupRestoredToExistingVM = null, isCloudBackupRestoredToNewVM = null;
            let isCloudBackupCompleted = false;
            try {
                console.log(`[Iteration${execIteration}] => TestStep => Step 5 -> Create Cloud Backup and Restore`);
                //let cloudBackupName = `PerfCloudBackup-${timestamp}`;
                let policy = getProtectionPolicyTemplate(policyName);
                let policyTemplateId = policy.id;
                isCloudBackupCreated = backupTestObj.testCreateCloudBackup(isCloudBackupCreated, vmToProtect, localBackupName, policyTemplateId, policyName);
                console.log("Sleep 30 seconds after Cloud Backup is created");
                sleep(600);

                group("Restore Cloud Backup to existing VM", () => {
                    console.log(`[Iteration ${execIteration}] => TestStep => Restore Cloud Backup to existing VM`);
                    isCloudBackupRestoredToExistingVM = backupTestObj.testRestoreCloudToExistingVM(isCloudBackupRestoredToExistingVM, vmToProtect, policyName);
                })
                console.log("Sleep 60 seconds after Cloud Backup restored to existing VM");
                sleep(60);

                group("Restore Cloud Backup to New VM", () => {
                    console.log(`[Iteration ${execIteration}] => TestStep => Restore Cloud Backup to New VM`);
                    isCloudBackupRestoredToNewVM = backupTestObj.testRestoreCloudToNewVM(isCloudBackupRestoredToNewVM, vmToProtect, policyName, restoreVmName);
                })
                isCloudBackupCompleted = isCloudBackupCreated && isCloudBackupRestoredToExistingVM && isCloudBackupRestoredToNewVM;
            }
            catch (err) {
                console.error(err.message)
                console.error(`TestResult=> Iteration ${execIteration} => Create Cloud Backup and Restore failed`)
                throw err;
            }
            finally {
                check(isCloudBackupCompleted, { "TestResult=> Cloud Backup and Restore": (i) => i == true });
            }
        })

        group("Step 6 -> Unprotect VM", () => {
            console.log(`[Iteration${execIteration}] => TestStep => Step 6 -> Unprotect VM`);
            backupTestObj.unprotectVM(vmToProtect);
        });
        console.log("Sleep 30 seconds after unprotect VM");
        sleep(30);

        group("Step 7 -> Delete the Cloud backup and restored VM", () => {
            console.log(`[Iteration${execIteration}] => TestStep => Step 7 -> Delete the Cloud backup and restored VM`);
            backupTestObj.testDeleteCloudBackups(vmToProtect, restoreVmName, vSphereApi);

        })

        group("Step 8 -> Delete local Backup", () => {
            console.log(`Iteration ${execIteration} => TestStep => Step 8 -> Delete the Local backup`);
            backupTestObj.testDeleteLocalBackups(vmToProtect);
        })

        group("Step 9 -> Delete the snap backup", () => {
            console.log(`Iteration ${execIteration} => TestStep => Step 9 -> Delete the snap backup`);
            backupTestObj.testDeleteSnapshots(vmToProtect);

        })

        group("Step 10-> Delete protection template", () => {
            console.log(`[Iteration${execIteration}] => TestStep => Step 10 -> Delete protection template`);
            backupTestObj.deleteProtectionTemplate(policyName);
        });
        console.log("Sleep 30 seconds after deleting protection template");
        sleep(30);

        group("Step 11-> Resize PSG storage capacity", () => {
            let updatePsgSize = 2;
            if (execIteration % 2 === 0) {
                updatePsgSize = updatePsgSize1;
            }
            else {
                updatePsgSize = updatePsgSize2;
            }
            console.log(`[Iteration${execIteration}] => TestStep => Step 11 -> Resize PSG storage capacity`);
            backupTestObj.resizePsg(catalystVmName, updatePsgDsName, updatePsgSize);
        });
        rpClient.finishTest(testId, "passed");
    }
    catch (err) {
        console.error(err.message);
        rpClient.writeLog(testId, err);
        console.error(`Exception occurrred during iteration ${execIteration} `);
        rpClient.finishTest(testId, "failed");
    }
    finally {
        // Unprotect VM
        try {
            let vm_detail = getVMDetails(vmToProtect, vcenterName);
            if (vm_detail.protectionJobInfo.id) {
                console.log("VM is in protected state. Unprotect the vm before continuing for next iteration");
                let isVmUnprotected = unprotectVm(vmToProtect);
                console.log(`[Iteration ${execIteration}] => VM is unprotected ${isVmUnprotected}`);
            }
            else {
                console.log("VM is already in unprotected state.");
            }
        }
        catch (err) {
            console.error(err.message);
        }

        // Delete protection policy
        try {
            let policy = getProtectionPolicyTemplate(policyName);
            if (policy) {
                console.log(`DELETE Protection policy - ${policyName}`);
                backupTestObj.deleteProtectionTemplate(policyName);
            }
        }
        catch (err) {
            console.error(err.message);
        }

        // Wait for 60s before next iteration
        sleep(60)
    }
}



function AddNetworkInterface(baseUri, vmToBeModified, networkAddress, networkType, subnetMask, networkName, header, waitTime = 300) {
    // Add additional Data network interface
    let networkInterfaceResponse = addCatalystNic(baseUri, vmToBeModified, networkAddress, networkType, subnetMask, networkName, header);
    let responseBody = JSON.parse(networkInterfaceResponse.body);
    let taskUri = responseBody.taskUri;
    console.debug(taskUri);

    const taskUrl = `${baseUri}${taskUri}`;
    let isSucceed = waitForTask(taskUrl, waitTime);
    return isSucceed;
}