import http from "k6/http";
import exec from "k6/execution";
import { check, group, sleep } from "k6";

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
            iterations: scaleVars.iteration,
            maxDuration: scaleVars.duration,
        },
    },
};



// These are still very much WIP and untested, but you can use them as is or write your own!
import {  textSummary } from 'https://jslib.k6.io/k6-summary/0.0.1/index.js';

export function handleSummary(data) {
  console.log('Preparing the end-of-test summary...');

  return {
    'stdout': textSummary(data, { indent: ' ', enableColors: true }), // Show the text summary to stdout...
    'example.json': JSON.stringify(data), // and a JSON with all the details...
    // And any other JS transformation of the data you can think of,
    // you can write your own JS helpers to transform the summary data however you like!
  };
}

export default function () {
    const execIteration = exec.scenario.iterationInTest;
    let timestamp = Math.floor(Date.now() / 1000);
    const protectionStoreName = `${vmPrefix}_${timestamp}_${execIteration}`;

    try {
      
        console.info(`============= Execution starts (${execIteration}) =============`);
        
        group(`Create Catalyst gateway VM`, () => {
            try {
                test_check(true);
                check(true, {"TestResult=> Create Catalyst gateway VM": (s) => s === true });
                console.info(`TestResult=> Iteration ${execIteration} => Protection store gateway VM created => PASS`);
                   

            }
            catch (err) {
                console.error(err)
                console.error(`TestResult=> Iteration ${execIteration} => Protection store gateway VM created => FAIL`)
                throw err;
            }
        })

        group("List Catalyst gateway VM", () => {
            try {
                test_check(false);

                check(true, { "TestResult=> List Catalyst gateway VM": (s) => s === true });
                console.info(`TestResult=> Iteration ${execIteration} => List VM completed => PASS`)
                
            }
            catch (err) {
                console.error(err);
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
        
        
    }
}


function test_check(testResult)
{
    check(testResult, { "Test check": (s) => s === true });

}