import http from "k6/http";
import { check, sleep } from "k6";
import { list_protectiongateway, getToken, getProtectionStoreVMList, generateHeader, waitForTask } from "./common/lib.js";
import { deleteCatalystVM } from "./common/deleteCatalystVM.js";
import exec from "k6/execution";

// Read test inputs from json
var testConfig = JSON.parse(open(__ENV.TEST_CONFIG));
var commonVars = testConfig.testbed.atlasOptions;
var baseUri = commonVars.baseUri;
var psgwPrefix = commonVars.vmPrefix;
var vmCount = testConfig.testinput.crudWorkflow.iteration

var testVars = testConfig.testinput.deleteProtectionGateway;
var concurrentUsers = testVars.virtualUsers;
var duration = testVars.duration;
var waitAfterDelete = testVars.waitAfterDelete;
var thinkBeforeDelete = testVars.thinkBeforeDelete;

// Number of concurrent users will do delete operation for duration (after one iteration they will wait)

export var options = {
    scenarios: {
        "delete-catalyst-vm": {
            executor: "shared-iterations",
            vus: (vmCount < concurrentUsers ? vmCount : concurrentUsers),
            iterations: vmCount, // No of VM to be deleted will not be more than number of user
            maxDuration: duration,
        },
    },
};

export function setup() {
    let protectionStoreList = getProtectionStoreVMList(psgwPrefix);

    return { "psgwList": protectionStoreList }
}

/* 
Each user will fetch gateway vm using get call
then delete it. After deleting it they will wait some time (thinking time)
then do the next iteration
*/
export default function (data) {
    // User browse through the list of protection gateway Vm
    let res = list_protectiongateway();
    check(res, { "[Function]delete_protectiongateway => list protectiongateway => status was 200": (r) => r.status === 200 });

    // User is thinking sometime before delete
    sleep(thinkBeforeDelete);

    let psgwList = data.psgwList;
    console.debug(JSON.stringify(psgwList))
    console.debug(
        `Number of gateway VMs with the prefix ${psgwPrefix} are ${psgwList.length}`
    );

    // User select the VM to be deleted
    let token = getToken();
    const psgwToBeDeleted = psgwList[exec.scenario.iterationInTest]
    console.log(
        `VM to be deleted is ${JSON.stringify(
            psgwToBeDeleted.name
        )}, ${psgwToBeDeleted.id}`
    );

    const vsphereAuth = 'administrator@vsphere.local:Nim123Boli#';
    deleteCatalystVM(baseUri, psgwToBeDeleted, vsphereAuth);
    // var header = generateHeader();
    // console.debug(`header is ${JSON.stringify(header)}`);

    // let delResponse = http.del(`${baseUri}/api/v1/catalyst-gateways/${psgwToBeDeleted.id}`, null, header)
    // console.log(`Delete response is ${JSON.stringify(delResponse)}`)
    // check(delResponse, { "Protection Store gateway VM Deletion is initiated- Status 202 received": (r) => r.status === 202 })
    // let responseBody = JSON.parse(delResponse.body);
    // let taskUri = responseBody.taskUri;
    // console.debug(taskUri);

    // const taskUrl = `${baseUri}${taskUri}`;
    // let vmDeletionWaitTime = 120
    // let isVMDeleteTask = waitForTask(taskUrl, vmDeletionWaitTime);
    // console.log(`Task status is ${isVMDeleteTask}`);
    // check(isVMDeleteTask, { "Protection store gateway VM delete Task status": (s) => s === true });
    // // // Each user delete a gateway VM and wait some time before doing next iteration
    sleep(waitAfterDelete);
}

