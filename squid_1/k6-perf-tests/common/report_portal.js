import http from "k6/http";
var configFilePath= `../${__ENV.TEST_CONFIG}`
var testConfig = JSON.parse(open(configFilePath));
var reporterOptions = testConfig.testbed.reporterOptions;
var reportPortalUri = `${reporterOptions.endpoint}/${reporterOptions.project}`
var launchName = reporterOptions.launch;


export function startLaunch() {
    let payload = { "name": `${launchName}`, "description": "K6 load test report", "startTime": Date.now(), "mode": "DEFAULT", "attributes": [{ "key": "build", "value": "0.1" }, { "value": "test" }] }
    let response = http.post(`${reportPortalUri}/launch`, JSON.stringify(payload), getHeader());
    let body = JSON.parse(response.body);
    let launchId = body.id;
    return launchId;
}

export function startSuite(launchId, suiteName, suiteDescription) {
    let payload = {
        "name": `${suiteName}`, "startTime": Date.now(), "type": "suite", "launchUuid":
            `${launchId}`, "description": `${suiteDescription}`
    }
    let response = http.post(`${reportPortalUri}/item`, JSON.stringify(payload), getHeader());
    let body = JSON.parse(response.body);
    let suiteId = body.id;
    return suiteId;
}
export function startTest(launchId, suiteId, testcaseName, testDescription) {
    let payload = { "name": `${testcaseName}`, "startTime": Date.now(), "type": "test", "launchUuid": `${launchId}`, "description": `${testDescription}` }
    let response = http.post(`${reportPortalUri}/item/${suiteId}`, JSON.stringify(payload), getHeader());
    let body = JSON.parse(response.body);
    let testId = body.id;
    return testId;
}

export function startTestStep(launchId, testId, name, description) {
    let payload = { "name": `${name}`, "startTime": Date.now(), "type": "step", "hasStats": false, "launchUuid": `${launchId}`, "description": `${description}` }
    let response = http.post(`${reportPortalUri}/item/${testId}`, JSON.stringify(payload), getHeader());
    let body = JSON.parse(response.body);
    let testStepId = body.id;
    return testStepId;
}

export function finishTestStep(launchId, id, status, issueType, comment = "no comments") {

    let payload = {
        "endTime": Date.now(),
        "status": `${status}`,
        "launchUuid": `${launchId}`
    }
    if (issueType !== null) {
        payload["issue"] =
        {
            "issueType": `${issueType}`,
            "comment": `${comment}`
        }
    }
    let response = http.put(`${reportPortalUri}/item/${id}`, JSON.stringify(payload), getHeader());
    let body = JSON.parse(response.body);
    console.log(`[FinishTestStep] ${body.message}`);
}
export function finishTest(launchId, id, status) {
    let payload = {
        "status": status,
        "endTime": Date.now(),
        "launchUuid": `${launchId}`
    }
    let response = http.put(`${reportPortalUri}/item/${id}`, JSON.stringify(payload), getHeader());
    let body = JSON.parse(response.body);
    console.log(`[FinishTest]${body.message}`);

}
export function finishSuite(launchId, id) {
    let payload = {
        "endTime": Date.now(),
        "launchUuid": `${launchId}`
    }
    let response = http.put(`${reportPortalUri}/item/${id}`, JSON.stringify(payload), getHeader());
    let body = JSON.parse(response.body);
    console.log(`[FinishTestSuite] ${body.message}`);

}
export function finishLaunch(launchId) {
    let payload = {
        "endTime": Date.now()
    }
    let response = http.put(`${reportPortalUri}/launch/${launchId}/finish`, JSON.stringify(payload), getHeader());
    let body = JSON.parse(response.body);
    console.log(`[FinishLaunch] ${body.message}`);

}
function getHeader() {
    let token = "35cb5736-6602-4d54-898e-32dfaace21c2";
    var header = {
        headers: {
            "Content-Type": "application/json",
            authorization: `Bearer ${token}`,
        },
    };
    return header;
}
