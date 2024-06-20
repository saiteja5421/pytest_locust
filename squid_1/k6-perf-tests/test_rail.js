import http from "k6/http";
import { sleep, check } from "k6";
import encoding from "k6/encoding";
import exec from "k6/execution";
import {generateToken} from "./testlib.js";
import TestRail from "./LibTestrail.js";

// var globalToken = undefined;

export const options = {
    scenarios: {
        "crud-create-catalyst-vm": {
            executor: "shared-iterations",
            vus: 1,
            iterations: 1,
            maxDuration: "5m",
        },
    },
}; 

export default function () {
    console.log("Welcome")
    let baseUrl = 'https://testrail.eng.nimblestorage.com/index.php?/api/v2';
    const projectName = 'NimOS-SandBox';
    const milestoneName = 'Default';
    let emailId = 'SamSelvaPrabu.Jebaraj@nimblestorage.com';
    let apiKey = 'W/yWnjzZMhmIvy1LzVtG-y5UIGdV8HESHUt.b3nrQ';
    let testRailObj = new TestRail(baseUrl,emailId,apiKey,projectName,milestoneName)

    // let projectId = testRailObj.getProjectId();
    // console.log(`Project id is ${projectId}`);

    // let milestoneid = testRailObj.getMileStoneId('Default');
    // console.log(`Milestone id is ${milestoneid}`)

    let testplan =  testRailObj.createTestPlan('Atlas-Sample')
    console.log(testplan)
}



