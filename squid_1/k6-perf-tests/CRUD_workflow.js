import exec from "k6/execution";
import { check, group, sleep } from "k6";
import { list_protectiongateway, generateHeader, getProtectionStoreVMList, getRandomIPWithinRange, waitForTask, httpPatch } from "./common/lib.js";
import { generateUpdateProxyPayload, generateUpdateDnsPayload } from "./payload_lib.js";
import { modifyCatalystNic } from "./common/modifyCatalystNic.js";
import { createCatalystGateway, getDatastoreId, getHostId, getHypervisorManagerId, fetchRandomHostAndDataStore } from "./common/createLocalStore.js";
import { deleteCatalystVM } from "./common/deleteCatalystVM.js";
import LibvSphereApi from './common/LibvSphereApi.js';
import { startLaunch, finishLaunch, startSuite, finishSuite } from "./common/report_portal_v2.js";
import RpClient from "./common/report_portal_v2.js";
import { addCatalystNic } from "./common/AddCatalystNic.js";


var testConfig = JSON.parse(open(__ENV.TEST_CONFIG));
var commonVars = testConfig.testbed;
var reporterOptions = testConfig.testbed.reporterOptions;
var vsphereAuth = commonVars.vsphereOptions.vsphereAuth;
var scaleVars = testConfig.testinput.crudWorkflow;
var psgwOptions = testConfig.testinput.crudWorkflow.psgwOptions
var baseUri = commonVars.atlasOptions.baseUri;
var thinkTime = 5
var vmPrefix = psgwOptions.vmPrefix
var alternateDNS = psgwOptions.alternateDNS
var ipPrefix = psgwOptions.ipPrefix;
var ipMin = psgwOptions.ipMin;
var ipMax = psgwOptions.ipMax;
var data1IPAddress = psgwOptions.data1IP;
var data2IPAddress = psgwOptions.data2IP;
var dataSubnetMask = psgwOptions.dataSubnetMask;
var data1NetworkName = psgwOptions.network2;
var data2NetworkName = psgwOptions.network3;
var networkType = "STATIC"
var vcenter = commonVars.vsphereOptions.vcenter;
var dnsAddress = psgwOptions.dnsAddress;
export var gateway = psgwOptions.gateway;
export var subnetMask = psgwOptions.subnetMask;
var api_host = `https://${vcenter}`
// var globalToken = undefined;

// var vmCreationDuration = 900
// var modifyLocalStoreVars = testConfig.testinput.modifyLocalStore
// var concurrentUsers = testVars.virtualUsers
var thinkBeforeModifyDNS = scaleVars.thinkBeforeModifyDNS
var waitAfterModifyDNS = scaleVars.waitAfterModifyDNS
var thinkBeforeModifyProxy = scaleVars.thinkBeforeModifyProxy
var waitAfterModifyProxy = scaleVars.waitAfterModifyProxy


export const options = {
    scenarios: {
        "crud-create-catalyst-vm": {
            executor: "shared-iterations",
            vus: 1,
            iterations: scaleVars.iteration,
            maxDuration: scaleVars.duration,
        },
    },
};

var ipAddress = scaleVars.nwAddress

export function setup() {
    let hypervisorId = getHypervisorManagerId(baseUri, vcenter)
    console.log(`[setup] hypervisor id is => ${hypervisorId}`);
    let vcenterList = testConfig.testbed.vcenterList;
    console.log(`[setup] vcenterlist ${JSON.stringify(vcenterList)}`);
    let vcenterObj = undefined;
    for (let vc of vcenterList) {
        if (vc.name === vcenter) {
            vcenterObj = vc;
        }
    }
    let networkName = vcenterObj.networkName
    console.log(`network name is ${networkName}`);
    let { datastoreName, hostName } = fetchRandomHostAndDataStore(vcenterObj);
    let datastoreId = getDatastoreId(baseUri, datastoreName)
    console.log(`[setup]=> Datastore id is ${datastoreId}`);
    let hostId = getHostId(baseUri, datastoreName, hostName);
    console.log(`[setup]=> host id is ${hostId}`);
    let launchId = startLaunch(reporterOptions);
    console.log(launchId);
    let suiteId = startSuite(launchId, "CRUD Workflow Test Suite", `Total Iterations Executed: ${scaleVars.iteration}`, reporterOptions);
    console.log(`SuiteId ${suiteId}`);
    return { "hypervisorId": hypervisorId, "datastoreId": datastoreId, "hostId": hostId, "networkName": networkName, "launchId": launchId, "suiteId": suiteId }
}
export function teardown(data) {
    finishSuite(data.suiteId, data.launchId, reporterOptions);
    finishLaunch(data.launchId, reporterOptions);
}
export default function (data) {
    const execIteration = exec.scenario.iterationInTest;
    let timestamp = Math.floor(Date.now() / 1000);
    const protectionStoreName = `${vmPrefix}_${timestamp}_${execIteration + 1}`;

    var launchId = data.launchId;
    var rpClient = new RpClient(launchId, reporterOptions);
    var suiteId = data.suiteId;


    let testId = rpClient.startTest(suiteId, `Catalyst gateway VM creation Iteration #${execIteration + 1}`, "Catalyst gateway VM creation");
    let crudTestObj = new CrudTest(rpClient, testId, execIteration);
    let isCatalystGatewayCompleted = false;
    let isCatalystVmCreated = false, isCatalystVmslisted = false, isCatalystVmModified = false, isNetworkInterfacesAdded, isCatalystVmDeleted = false;
    try {

        console.info(`============= Execution starts (${execIteration}) =============`);
        isCatalystVmCreated = crudTestObj.createCatalystGateway(data, protectionStoreName);

        isCatalystVmslisted = crudTestObj.listCatalystGateway();

        // let catalystVMList = data.psgwList;
        try {
            var catalystVMList = getProtectionStoreVMList(protectionStoreName);
            console.log(`Catalyst VM list ${JSON.stringify(catalystVMList)}`)
            var vmToBeModifiedObj = catalystVMList[0]; // As exact vm name is given to getProtectionStoreVMList, it will have only one object.
            let vmName = vmToBeModifiedObj.name;
            console.log(`VM to be modified is ${vmName}`);
            var resourceUri = vmToBeModifiedObj.resourceUri
            var modifyUri = `${baseUri}${resourceUri}`
            console.log(`resource URI ${resourceUri}`)
        }
        catch (err) {
            console.error("Error while fetching VM to be modified");
            throw err;
        }

        isCatalystVmModified = crudTestObj.modifyCatalystGateway(modifyUri, vmToBeModifiedObj);

        isNetworkInterfacesAdded = crudTestObj.addDataNetworkInterace(baseUri, vmToBeModifiedObj)

        console.info(`============= Scale iteration ${execIteration} is completed =============`);
    }
    catch (err) {
        console.error(err.message);
        console.error(`Error occurrred during iteration ${execIteration} => VM name is ${protectionStoreName}`)
    }
    try {
        var psg = getProtectionStoreVMList(protectionStoreName);
        console.log(`PSG: ${JSON.stringify(psg)}`)
        isCatalystVmDeleted = crudTestObj.deleteCatalystGateway(psg[0]);
    }
    catch (err) {
        console.error(err.message);
        console.error(`Error occurrred during iteration ${execIteration} => VM name is ${protectionStoreName}`)
    }
    finally {
        isCatalystGatewayCompleted = isCatalystVmCreated && isCatalystVmslisted && isCatalystVmModified && isCatalystVmDeleted
        let testStatus = isCatalystGatewayCompleted ? "passed" : "failed";
        rpClient.finishTest(testId, testStatus);
        // Sleep 5 minutes as a cooling time
        console.log("Waiting for 5 minutes before next iteration");
        sleep(300);
    }


}
class CrudTest {
    constructor(rpClient, testId, execIteration) {
        this.rpClient = rpClient;
        this.testId = testId;
        this.execIteration = execIteration;
    }
    createCatalystGateway(data, protectionStoreName) {
        // this.deleteContentLibrary();
        let isVMDeployed = false;
        group("Create Catalyst gateway VM", () => {
            let stepId = this.rpClient.startTestStep(this.testId, "Create Catalyst gateway VM", "Create Protection store gateway VM using Rest API");
            try {
                console.info(`[TestStep] => Iteration ${this.execIteration} => Create VM started =============`);
                var vmCreationWaitTime = parseInt(commonVars.vsphereOptions.vmCreationTimeout);
                console.info(`[TestStep] => Iteration ${this.execIteration} => Create VM started with following values: protectionStoreName, ipAddress, dnsAddress, vmCreationWaitTime, data.hypervisorId, data.datastoreId, data.hostId, baseUri, gateway, subnetMask: ${protectionStoreName}, ${ipAddress}, ${dnsAddress}, ${vmCreationWaitTime}, ${data.hypervisorId}, ${data.datastoreId}, ${data.hostId}, ${baseUri}, ${gateway}, ${subnetMask} =============`);
                isVMDeployed = createCatalystGateway(data.networkName, protectionStoreName, ipAddress, dnsAddress, vmCreationWaitTime, data.hypervisorId, data.datastoreId, data.hostId, baseUri, gateway, subnetMask);
                // check(isVMDeployed, { "TestResult=> Create Catalyst gateway VM": (s) => s === true });
                if (isVMDeployed) {
                    console.info(`Iteration => ${this.execIteration} => Protection store gateway vm ${protectionStoreName} is deployed`);
                    this.rpClient.finishTestStep(stepId, "passed", null);
                    console.log(`TestResult=> Iteration ${this.execIteration} => Protection store gateway VM created => PASS`);
                    console.log("Sleep for 120 seconds");
                    sleep(120);
                }
                else {
                    this.rpClient.finishTestStep(stepId, "failed", "pb002", `Protection store gateway vm ${protectionStoreName} is failed to deploy`);
                    console.error(`Iteration => ${this.execIteration} => Protection store gateway vm ${protectionStoreName} is failed to deploy`);
                    console.log("sleep 30 seconds");
                    sleep(30);
                    throw "Catalyst VM failed to deploy";
                }

            }
            catch (err) {
                console.error(err.message);
                this.rpClient.writeLog(stepId, err);
                this.rpClient.finishTestStep(stepId, "interupted", "pb002", err);
                console.error(`TestResult=> Iteration ${this.execIteration} => Protection store gateway VM created => FAIL`);
                throw err;
            }
            finally {
                sleep(60);
                check(isVMDeployed, { "TestResult=> Create Catalyst gateway VM": (s) => s === true });
            }
        });
        return isVMDeployed
    }
    deleteContentLibrary() {
        group("Delete content libray", () => {
            let stepId = this.rpClient.startTestStep(this.testId, "Delete content library", "Delete content library in Vsphere");
            try {
                console.info(`[TestStep] => Iteration ${this.execIteration} => Delete content library started =============`);
                var vSphareApi = new LibvSphereApi(testConfig);
                let contentLibraryList = vSphareApi.getContentLibraryIds();
                for (const _id in contentLibraryList) {
                    let contentLibrary = vSphareApi.getLibraryDetail(contentLibraryList[_id]);
                    if (vSphareApi.contentLibraryName == contentLibrary.name) {
                        console.log(`Delete Content Library Name: ${contentLibrary.name}`);
                        var deletecontentRes = vSphareApi.deleteContentLibrary(contentLibraryList[_id]);
                    }
                }
                console.log("Wait for 120 seconds after content library deletion");
                sleep(120);
                let testStatus = deletecontentRes ? "passed" : "failed";
                this.rpClient.finishTestStep(stepId, testStatus, null);
                console.info(`[TestStep] => Iteration ${this.execIteration} => Delete content library completed =============`);
            }
            catch (err) {
                console.error(err.message);
                this.rpClient.writeLog(stepId, err);
                this.rpClient.finishTestStep(stepId, "interupted", "pb001", err);
                console.error(`TestResult=> Iteration ${this.execIteration} =>  Delete content library failed`);
                throw err;
            }

        });
    }
    listCatalystGateway() {
        let isListCatalystVMCompleted = false;
        group("List Catalyst gateway VM", () => {
            let listVMTestId = this.rpClient.startTestStep(this.testId, "List Catalyst gateway VM", "List gateway VM");
            try {
                console.info(`[TestStep] => Iteration ${this.execIteration} => List VM started =============`);
                sleep(thinkTime);

                let response = list_protectiongateway();
                check(response, { "TestResult=> List Catalyst gateway VM": (r) => r.status === 200 });

                sleep(thinkTime);
                if (response.status === 200) {
                    isListCatalystVMCompleted = true
                    this.rpClient.finishTestStep(listVMTestId, "passed");
                    console.info(`TestResult=> Iteration ${this.execIteration} => List VM completed => PASS`);
                }
                else {
                    throw "Failed to list protection gateway VM";
                }
            }
            catch (err) {
                console.error(err.message);
                this.rpClient.writeLog(listVMTestId, err);
                this.rpClient.finishTestStep(listVMTestId, "failed", null);
                console.info(`TestResult=> Iteration ${this.execIteration} => List VM completed => FAIL`);
            }
        });
        return isListCatalystVMCompleted;
    }
    modifyCatalystGateway(modifyUri, vmToBeModifiedObj) {
        let header = generateHeader();
        let isCatalystGatewayModified = false;
        let isProxyModified = false;
        let isIpAddressModified = false;
        let isDNSmodified = false;
        console.log("Update Catalyst gateway VM parameters such as DNS address, proxy and new IP address");
        group('Modify DNS', () => {
            let testId = this.rpClient.startTestStep(this.testId, "Modify DNS", "Modify DNS of catalyst gateway");
            try {
                console.info(`[TestStep] => Modify DNS starts => Iteration ${this.execIteration}====================`);
                sleep(thinkBeforeModifyDNS);

                isDNSmodified = modifyDNSAddress(modifyUri, alternateDNS, header);
                console.log(`Task status is ${isDNSmodified}`);
                // check(isSucceed, { "TestResult=> Modify DNS": (s) => s === true });

                sleep(waitAfterModifyDNS);
                if (isDNSmodified) {
                    this.rpClient.finishTestStep(testId, "passed", null);
                    console.info(`TestResult=> Iteration ${this.execIteration} Modify DNS completed => PASS`);
                }
                else {
                    throw "Failed to modify DNS";
                }
            }
            catch (err) {
                console.error(err);
                this.rpClient.writeLog(testId, err);
                this.rpClient.finishTestStep(testId, "failed", null);
                console.error(`TestResult=> Iteration ${this.execIteration} Modify DNS completed => FAIL`);
            }
            finally {
                check(isDNSmodified, { "TestResult=> Modify DNS": (s) => s === true });
            }
        });

        group("Modify Proxy", () => {
            let testId = this.rpClient.startTestStep(this.testId, "Modify Proxy", "Modify Proxy of catalyst VM");
            try {
                console.info(`[TestStep] => Modify Proxy starts => Iteration ${this.execIteration} ====================`);
                sleep(thinkBeforeModifyProxy);

                isProxyModified = modifyProxy(modifyUri, 8082, header);
                console.log(`Task status is ${isProxyModified}`);
                // check(isProxyModified, { "TestResult=> Modify Proxy": (s) => s === true });

                sleep(waitAfterModifyProxy);
                if (isProxyModified) {
                    this.rpClient.finishTestStep(testId, "passed", null);
                    console.log(`TestResult=> Iteration ${this.execIteration} Modify Proxy completed => PASS`);
                }
                else {
                    throw "Failed to modify Proxy";
                }

            }
            catch (err) {
                console.error(err);
                this.rpClient.writeLog(testId, err);
                this.rpClient.finishTestStep(testId, "failed", null);
                console.error(`TestResult=> Iteration ${this.execIteration} Modify Proxy => FAIL`);
            }
            finally {
                check(isProxyModified, { "TestResult=> Modify Proxy": (s) => s === true });
                sleep(60);
                let isSucceed = modifyProxy(modifyUri, 8080, header); //reverting proxy back
                console.log(`Task status is ${isSucceed}`);
                if (isSucceed) {
                    console.info("============= Modify Proxy is reversed ====================");
                }
                check(isSucceed, { "Proxy change is reverted again successfully": (s) => s === true });
            }
        });

        group("Modify new IP address", () => {
            let testId = this.rpClient.startTestStep(this.testId, "Modify new IP address", "Modify new IP address");
            try {
                console.info(`TestStep => Modify IP address starts => Iteration ${this.execIteration}====================`);
                sleep(thinkTime);
                // Create payload
                var oldIpAddress = vmToBeModifiedObj.network.nics[0].networkAddress;
                var newIpAddress;
                while (true) {
                    newIpAddress = getRandomIPWithinRange(ipPrefix, ipMin, ipMax);
                    if (newIpAddress !== oldIpAddress) {
                        break;
                    }
                }
                isIpAddressModified = modifyIPAddress(vmToBeModifiedObj, newIpAddress, header, 800);
                console.log(`Task status is ${isIpAddressModified}`);
                // check(isIpAddressModified, { "TestResult=> Modify IP address": (s) => s === true });
                if (isIpAddressModified) {
                    this.rpClient.finishTestStep(testId, "passed", null);
                    console.info(`Old IP address ${oldIpAddress} is modified to new address ${newIpAddress} successfully. Wait for 2 minutes `);
                    console.log(`TestResult=> Iteration ${this.execIteration} Modify IP address ${oldIpAddress}-> ${newIpAddress} completed => PASS`);
                    console.log("Wait for 2 minutes before next task.");
                    sleep(120);
                }
                else {
                    console.info(`Iteration ${this.execIteration} => IP address modification failed.`);
                    throw "Failed to modify IP address";
                }
                console.info("============= Modify IP address completed ====================");
            }
            catch (err) {
                console.error(err);
                this.rpClient.writeLog(testId, err);
                this.rpClient.finishTestStep(testId, "failed", null);
                console.error(`TestResult=> Iteration ${this.execIteration} Modify IP address [${oldIpAddress} => ${newIpAddress}] => FAIL`);
            }
            finally {
                check(isIpAddressModified, { "TestResult=> Modify IP address": (s) => s === true });
            }
        });
        isCatalystGatewayModified = isDNSmodified && isProxyModified && isIpAddressModified
        return isCatalystGatewayModified

    }

    addDataNetworkInterace(baseUri, vmToBeModifiedObj) {
        let header = generateHeader();
        let isData1NetworkAdded = false;
        let isData2NetworkAdded = false;

        group('Add Data1 Network Interface', () => {

            let testId = this.rpClient.startTestStep(this.testId, "Add Data1 Network Interface", "Add Data1 Network Interface of catalyst gateway");
            try {
                console.info(`[TestStep] => Add Data1 Network inteface => Iteration ${this.execIteration}====================`);
                sleep(thinkTime);

                var networkAddress = data1IPAddress;

                isData1NetworkAdded = AddNetworkInterface(baseUri, vmToBeModifiedObj, networkAddress, networkType, dataSubnetMask, data1NetworkName, header);
                console.log(`Task status is ${isData1NetworkAdded}`);
                // check(isSucceed, { "TestResult=> Modify DNS": (s) => s === true });

                sleep(waitAfterModifyDNS);
                if (isData1NetworkAdded) {
                    this.rpClient.finishTestStep(testId, "passed", null);
                    console.info(`TestResult=> Iteration ${this.execIteration} Add Data1 Network Interface completed => PASS`);
                    sleep(120);
                }
                else {
                    throw "Failed to Add Data1 Network Interface";
                }
            }
            catch (err) {
                console.error(err);
                this.rpClient.writeLog(testId, err);
                this.rpClient.finishTestStep(testId, "failed", null);
                console.error(`TestResult=> Iteration ${this.execIteration} Add Data1 Network Interface => FAIL`);
            }
            finally {
                check(isData1NetworkAdded, { "TestResult=> Add Data1 Network Interface": (s) => s === true });
            }

        });
        group('Add Data2 Network Interface', () => {
            let testId = this.rpClient.startTestStep(this.testId, "Add Data2 Network Interface", "Add Data2 Network Interface of catalyst gateway");
            try {
                console.info(`[TestStep] => Add Data2 Network inteface => Iteration ${this.execIteration}====================`);
                sleep(thinkTime);

                var networkAddress = data2IPAddress;

                isData2NetworkAdded = AddNetworkInterface(baseUri, vmToBeModifiedObj, networkAddress, networkType, dataSubnetMask, data2NetworkName, header, 600);
                console.log(`Task status is ${isData2NetworkAdded}`);
                // check(isSucceed, { "TestResult=> Modify DNS": (s) => s === true });

                sleep(120);
                if (isData2NetworkAdded) {
                    this.rpClient.finishTestStep(testId, "passed", null);
                    console.info(`TestResult=> Iteration ${this.execIteration} Add Data2 Network Interface completed => PASS`);
                }
                else {
                    throw "Failed to Add Data2 Network Interface";
                }
            }
            catch (err) {
                console.error(err);
                this.rpClient.writeLog(testId, err);
                this.rpClient.finishTestStep(testId, "failed", null);
                console.error(`TestResult=> Iteration ${this.execIteration} Add Data2 Network Interface => FAIL`);

            }
            finally {
                check(isData2NetworkAdded, { "TestResult=> Add Data2 Network Interface": (s) => s === true });
            }

        });
    }

    deleteCatalystGateway(vmToBeModifiedObj) {
        let header = generateHeader();
        let isVmDeleted = false;
        group("Delete Catalyst gateway VM", () => {
            let stepId = this.rpClient.startTestStep(this.testId, "Delete Catalyst gateway VM", "Delete Catalyst gateway VM");
            try {
                console.log(`[TestStep] => Deleting VM start => Iteration ${this.execIteration} =============`);
                // Think or scroll before deleteing a catalyst gateway VM
                sleep(thinkTime);
                // const vsphereAuth = 'administrator@vsphere.local:Nim123Boli#';
                isVmDeleted = deleteCatalystVM(baseUri, vmToBeModifiedObj, header);
                // check(isVmDeleted, { "TestResult=> Delete Catalyst gateway VM": (s) => s === true });

                if (isVmDeleted) {
                    this.rpClient.finishTestStep(stepId, "passed", null);
                    console.log(`============= Deleting VM completed => Iteration ${this.execIteration} =============`);
                    console.log(`TestResult => Iteration ${this.execIteration} =>Deleting VM => PASS`);
                }
                else {
                    this.rpClient.finishTestStep(stepId, "failed", null);
                    console.error(`TestResult => Iteration ${this.execIteration} =>Deleting VM => FAIL`);
                    console.log(`VM deleted status is ${isVmDeleted}`);
                }

            }
            catch (err) {
                console.error(err);
                this.rpClient.writeLog(stepId, err);
                this.rpClient.finishTestStep(stepId, "interrupted", null);
                console.error(`Iteration ${this.execIteration} => Exception occurred during Delete catalyst gateway VM`);
                console.error(`TestResult => Iteration ${this.execIteration} => Deleting VM => FAIL`);
                throw err;
            }
            finally {
                check(isVmDeleted, { "TestResult=> Delete Catalyst gateway VM": (s) => s === true });
            }
        });
        return isVmDeleted;
    }    
}

function modifyDNSAddress(modifyUri, alternateDNS, header) {
    let body = generateUpdateDnsPayload(alternateDNS);
    // let header = generateHeader();

    console.debug(`${modifyUri}`);
    console.debug(JSON.stringify(body));
    let resDnsChange = httpPatch(`${modifyUri}`, JSON.stringify(body), header);
    console.log(JSON.stringify(resDnsChange));
    check(resDnsChange, { "Modify DNS is initated": (r) => r.status === 202 });
    // @ts-ignore
    let responseBody = JSON.parse(resDnsChange.body);
    let taskUri = responseBody.taskUri;
    console.debug(taskUri);

    const taskUrl = `${baseUri}${taskUri}`;
    let isSucceed = waitForTask(taskUrl, 120);
    return isSucceed;
}

function modifyIPAddress(vmToBeModified, newIPAddress, header, waitTime = 300) {
    let ipModifyResponse = modifyCatalystNic(baseUri, vmToBeModified, newIPAddress, header);
    // @ts-ignore
    let responseBody = JSON.parse(ipModifyResponse.body);
    let taskUri = responseBody.taskUri;
    console.debug(taskUri);

    const taskUrl = `${baseUri}${taskUri}`;
    let isSucceed = waitForTask(taskUrl, waitTime);
    return isSucceed;
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

function modifyProxy(modifyUri, proxyPort, header) {
    let body = generateUpdateProxyPayload(proxyPort);
    // let header = generateHeader();
    console.debug(`${modifyUri}`);
    console.debug(JSON.stringify(body));
    let proxyChangeResponse = httpPatch(`${modifyUri}`, JSON.stringify(body), header);
    console.log(JSON.stringify(proxyChangeResponse));
    check(proxyChangeResponse, { "Proxy change is initiated": (r) => r.status === 202 });

    // @ts-ignore
    let responseBody = JSON.parse(proxyChangeResponse.body);
    let taskUri = responseBody.taskUri;
    console.debug(taskUri);

    const taskUrl = `${baseUri}${taskUri}`;
    let isSucceed = waitForTask(taskUrl, 300);
    return isSucceed;
}
