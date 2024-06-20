import http from "k6/http";
import { check, group, sleep } from "k6";
import exec from "k6/execution";

import { list_protectiongateway } from "./common/lib.js";
import { startLaunch, startSuite, startTest, startTestStep, finishLaunch, finishSuite, finishTest, finishTestStep } from "./common/report_portal.js";


var testConfig = JSON.parse(open(__ENV.TEST_CONFIG));
var baseUri = testConfig.testbed.atlasOptions.baseUri;
var testVars = testConfig.testinput.listProtectionGateway;
var concurrentUsers = testVars.virtualUsers; // Number of concurrent users
var duration = testVars.duration;
// users will not continuously retry some operation.
// They may think for few seconds then do . To simulate that thinkingTime
var thinkingTime = testVars.thinkingTime;

export const options = {
  scenarios: {
      "list-catalyst-vm": {
          executor: "shared-iterations",
          vus: concurrentUsers,
          iterations: testVars.iterations,
          maxDuration: `${duration}` ,
      },
  },
  
};

export function setup() {
  let launchId = startLaunch();
  console.log(launchId);
  return { "launchId": launchId };
}
export function teardown(data) {
  finishLaunch(data.launchId);
}

export default function (data) {
  let launchId = data.launchId;
  const execIteration = exec.scenario.iterationInTest;

  try {

    var suiteId = startSuite(launchId, `List Catalyst gateway VM #${execIteration+1}`, "Performance Test for List Catalyst gateway VM");
    console.log(`SuiteId ${suiteId}`);

    var testId = startTest(launchId, suiteId, "List Catalyst gateway VM", "List Catalyst gateway VM");
    console.log(`Test id ${testId}`);
    let response = list_protectiongateway();
    check(response, { "TestResult=> List Catalyst gateway VM": (r) => r.status === 200 });
    let body = JSON.parse(response.body);
    // console.log(JSON.stringify(body))
    body.items.forEach((element) => {
      if (element.datastoreIds.length != 0) {
        console.log(JSON.stringify(element));
        console.log(`Name of the gateway is ${element.name}`);
        console.log(
          `NIC of the gateway is ${JSON.stringify(element.network.nics)}`
        );
      }
    });
    let testResult = (response.status == 200)?"passed":"failed"
    finishTest(launchId,testId,testResult);
      
    sleep(thinkingTime);
  }
  catch (err) {
    console.error(err)
    finishTest(launchId, testId, "interrupted");
    console.error(`TestResult=> Iteration ${execIteration} => Protection store gateway VM created => FAIL`)
    throw err;
  }
  finally {
    console.log("Waiting for 5 minutes before next iteration");
    finishSuite(launchId,suiteId);
    
}
}
