import { startLaunch,finishLaunch } from "./common/report_portal_v2.js";
import exec from "k6/execution";
import RpClient from "./common/report_portal_v2.js";

var configFilePath = `./${__ENV.TEST_CONFIG}`
var testConfig = JSON.parse(open(configFilePath));
var reporterOptions = testConfig.testbed.reporterOptions;

export const options = {
    scenarios: {
        "crud-create-catalyst-vm": {
            executor: "shared-iterations",
            vus: 1,
            iterations: 3,
            maxDuration: "10m",
        },
    },
};

export function setup()
{

    let launchId = startLaunch(reporterOptions);
    console.log(launchId);
    return {"launchId": launchId}
}
export default function(data)
{
    const execIteration = exec.scenario.iterationInTest;
    let launchId = data.launchId
    let rpClient = new RpClient(launchId,reporterOptions);
    let suiteId =rpClient.startSuite(`Crud Workflow #${execIteration+1}`,"Performance Test for Crud Workflow");
    console.log(suiteId);
    let testId =rpClient.startTest(suiteId,"Create Catalyst VM","Create Catalyst VM");
    console.log(testId);
    let testStepId =rpClient.startTestStep(testId,"Get catalyst VM name ","Get catalyst VM name");
    console.log(testStepId);
    //finishTestStep(testStepId,"passed");
    rpClient.finishTestStep(testStepId,"failed","ab001","Create Catalyst VM Failed");
    rpClient.finishTest(testId,"failed");
    rpClient.finishSuite(suiteId);
    //finishLaunch();
}
export function teardown(data) {
   finishLaunch(data.launchId,reporterOptions);
}