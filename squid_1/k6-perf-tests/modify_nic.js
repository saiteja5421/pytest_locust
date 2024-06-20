import { check, sleep } from "k6";
import { list_protectiongateway, getProtectionStoreVMList, getRandomIPWithinRange } from "./lib.js";
import exec from "k6/execution";
import { group } from "k6";
import { modifyCatalystNic } from "./modifyCatalystNic.js";

// Read test inputs from json
var testConfig = JSON.parse(open(__ENV.TEST_CONFIG));
var commonVars = testConfig.testbed.atlasOptions;
var baseUri = commonVars.baseUri;
var vmCount = testConfig.testinput.crudWorkflow.iteration;
var ipPrefix = commonVars.ipPrefix;
var ipMin = commonVars.ipMin;
var ipMax = commonVars.ipMax;
var psgwPrefix = commonVars.vmPrefix;

var testVars = testConfig.testinput.modifyNic;
var concurrentUsers = testVars.virtualUsers;
var duration = testVars.duration;
var waitAfterModify = testVars.waitAfterModify;
var thinkBeforeModify = testVars.thinkBeforeModify;

// Number of concurrent users will do delete operation for duration (after one iteration they will wait)

export var options = {
  scenarios: {
    "modify-catalyst-vm": {
      executor: "shared-iterations",
      vus: vmCount < concurrentUsers ? vmCount : concurrentUsers,
      iterations: vmCount, // No of VM to be deleted will not be more than number of user
      maxDuration: duration,
    },
  },
};

// As setup will run only once ,getting protction store gateway with the prefix is done here.
export function setup() {
  let protectionStoreList = getProtectionStoreVMList(psgwPrefix);
  return { psgwList: protectionStoreList };
}

/*
Each user will fetch gateway vm using get call then filter the VM with given prefix
then modify Network interface in it. After modifying it they will wait some time (thinking time)
then do the next iteration.
*/
export default function (data) {

  group("User browse through the list of protection gateway Vm", () => {

    let response = list_protectiongateway();
    check(response, { "list protection store gateway status was 200": (r) => r.status === 200 });

  })

  group("User Modifies the NIC", function () {
    // User is thinking sometime before modify
    sleep(thinkBeforeModify);

    // Protection store gateway with the given prefix is already done in setup and the result is stored in
    // data.psgwList
    let psgwList = data.psgwList;
    console.debug(`vm list ${JSON.stringify(psgwList)}`);
    console.debug(
      `Number of gateway VMs with the prefix ${psgwPrefix} are ${psgwList.length}`
    );

    // User select the VM to be modified
    const psgwToBeModified = psgwList[exec.scenario.iterationInTest];
    console.debug(JSON.stringify(psgwToBeModified))
    console.log(
      `VM to be modified is ${JSON.stringify(psgwToBeModified.name)}, ${psgwToBeModified.id
      }, ${JSON.stringify(psgwToBeModified.network.nics[0])}`
    );

    // Create payload
    while (true) {
      var randomNetAddress = getRandomIPWithinRange(ipPrefix, ipMin, ipMax);
      if (randomNetAddress !== psgwToBeModified.network.nics[0].networkAddress) {
        break;
      }
    }
    modifyCatalystNic(baseUri, psgwToBeModified, randomNetAddress);

    // // Each user modify a gateway VM and wait some time before doing next iteration
    sleep(waitAfterModify);
  });
}


