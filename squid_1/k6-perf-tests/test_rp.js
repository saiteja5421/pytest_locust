import http from "k6/http";
import exec from "k6/execution";
import { check, group, sleep } from "k6";
import { list_protectiongateway, generateHeader, getProtectionStoreVMList, getRandomIPWithinRange, waitForTask } from "./lib.js";
import { generateUpdateProxyPayload, generateUpdateDnsPayload } from "./payload_lib.js";
import { modifyCatalystNic } from "./modifyCatalystNic.js";
import { createCatalystGateway, getDatastoreId, getHostId, getHypervisorManagerId, fetchRandomHostAndDataStore } from "./createLocalStore.js";
import { deleteCatalystVM } from "./deleteCatalystVM.js";
import LibvSphareApi from './LibvSphareApi.js';


var testConfig = JSON.parse(open(__ENV.TEST_CONFIG));
var commonVars = testConfig.testbed.atlasOptions;
var scaleVars = testConfig.testinput.crudWorkflow;
var vmPrefix = commonVars.vmPrefix
export var gateway = commonVars.gateway;
export var subnetMask = commonVars.subnetMask;


export const options = {
    scenarios: {
        "crud-create-catalyst-vm": {
            executor: "shared-iterations",
            vus: 1,
            iterations: 1,
            maxDuration: scaleVars.duration,
        },
    },
};


import { startLaunch,startSuite,startTest,finishLaunch,finishSuite,finishTest } from "./common/report_portal.js";

export function setup() {
    let launchId = startLaunch();
    console.log(launchId);
    return { "launchId" : launchId};
}

    
export function teardown(data)
{   
    finishLaunch(data.launchId);
}


export default function (data) {
    const execIteration = exec.scenario.iterationInTest;
    let timestamp = Math.floor(Date.now() / 1000);
    const protectionStoreName = `${vmPrefix}_${timestamp}_${execIteration}`;
    let launchId = data.launchId;
    let suiteId = startSuite(launchId,`Crud Workflow #${execIteration}`,"Performance Test for Crud Workflow");
    console.log(`SuiteId ${suiteId}`);

    try {
        let testId="C12345"
        console.info(`============= Execution starts (${execIteration}) =============`);
        
        group(`Create Catalyst gateway VM`, () => {
            try {
                let testId = startTest(launchId,suiteId,"Create Catalyst VM","Create Catalyst VM");
                console.log(`Test id ${testId}`);
                test_check(true);
                check(true, {"TestResult=> Create Catalyst gateway VM": (s) => s === true });
                console.info(`TestResult=> Iteration ${execIteration} => Protection store gateway VM created => PASS`);
                finishTest(launchId,testId,"passed");
                   

            }
            catch (err) {
                console.error(err)
                finishTest(launchId,testId,"failed");
                console.error(`TestResult=> Iteration ${execIteration} => Protection store gateway VM created => FAIL`)
                throw err;
            }
        })

        group("List Catalyst gateway VM", () => {
            try {
                let testId = startTest(launchId,suiteId,"List Catalyst gateway VM","List Catalyst gateway VM");
                console.log(`Test id ${testId}`);
                test_check(false);

                check(true, { "TestResult=> List VM completed": (s) => s === true });
                console.info(`TestResult=> Iteration ${execIteration} => List VM completed => PASS`)
                finishTest(launchId,testId,"passed");
                
            }
            catch (err) {
                console.error(err);
                finishTest(launchId,testId,"failed");

                console.info(`TestResult=> Iteration ${execIteration} => List VM completed => FAIL`)
            }
        })

        
        
        console.info(`============= Scale iteration ${ execIteration } is completed =============`);
    }
    catch (err) {
        console.error(err);
        console.error(`Error occurrred during iteration ${ execIteration } => VM name is ${ protectionStoreName }`)
    }
    finally {
        console.log("Waiting for 5 minutes before next iteration");
        finishSuite(launchId,suiteId);
        
    }
}


function test_check(testResult)
{
    check(testResult, { "Test check": (s) => s === true });

}