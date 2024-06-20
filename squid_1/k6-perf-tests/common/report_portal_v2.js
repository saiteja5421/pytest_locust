import http from "k6/http";

/**
 * This will create launch in our reportportal project
 * @param {object} reporterOptions 
 * @returns 
 */
export function startLaunch(reporterOptions) {
    if (!reporterOptions.publishResult){
        return null
    }
    let reportPortalUri = `${reporterOptions.endpoint}/${reporterOptions.project}`
    let launchName = reporterOptions.launch;
    let payload = { "name": `${launchName}`, "description": `${reporterOptions.description}`, "startTime": Date.now(), "mode": "DEFAULT", "attributes": [{ "key": "build", "value": "0.1" }, { "value": "test" }] }
    let response = http.post(`${reportPortalUri}/launch`, JSON.stringify(payload), getHeader(reporterOptions.token));
    let body = JSON.parse(response.body);
    let launchId = body.id;
    return launchId;
}

/**
 * This will finish launch created by startLaunch
 * @param {string} launchId 
 * @param {*} reporterOptions 
 */
export function finishLaunch(launchId,reporterOptions) {
    if (!reporterOptions.publishResult){
        return null
    }
    let reportPortalUri = `${reporterOptions.endpoint}/${reporterOptions.project}`
    let payload = {
        "endTime": Date.now()
    }
    let response = http.put(`${reportPortalUri}/launch/${launchId}/finish`, JSON.stringify(payload), getHeader(reporterOptions.token));
    let body = JSON.parse(response.body);
    console.log(`[FinishLaunch] ${body.message}`);

}
/**
     * This method will start suite
     * @param {*} suiteName 
     * @param {*} suiteDescription 
     * @returns 
     */
 export function startSuite(launchId,suiteName, suiteDescription,reporterOptions) {
    if (!reporterOptions.publishResult){
        return null
    }
    let reportPortalUri = `${reporterOptions.endpoint}/${reporterOptions.project}`
    let payload = {
        "name": `${suiteName}`, "startTime": Date.now(), "type": "suite", "launchUuid":
            `${launchId}`, "description": `${suiteDescription}`
    }
    console.log(payload);
    let response = http.post(`${reportPortalUri}/item`, JSON.stringify(payload), getHeader(reporterOptions.token));
    let body = JSON.parse(response.body);
    let suiteId = body.id;
    return suiteId;
}
/**
     * This method will finish suite created by startSuite
     * @param {*} id - suite id
     * @returns 
     */
 export function finishSuite(id,launchId,reporterOptions) {
    if (!reporterOptions.publishResult){
        return null
    }
    let reportPortalUri = `${reporterOptions.endpoint}/${reporterOptions.project}`
    let payload = {
        "endTime": Date.now(),
        "launchUuid": `${launchId}`
    }
    let response = http.put(`${reportPortalUri}/item/${id}`, JSON.stringify(payload), getHeader(reporterOptions.token));
    let body = JSON.parse(response.body);
    console.log(`[FinishTestSuite] ${body.message}`);
}
/**
 * This will create header with authorization token.
 * @param {token} token 
 * @returns 
 */
function getHeader(token) {
    var header = {
        headers: {
            "Content-Type": "application/json",
            authorization: `Bearer ${token}`,
        },
    };
    return header;
}


/**
 * ReportPortal Client Class
 */
export default class RpClient {
    /**
     * 
     * @param {*} launchId 
     * @param {*} reporterOptions - object which contains Reportal portal URI,tokenid,project details and publishResult flag 
     * If publishResult flag is set to false,the results will not be push to
     * reportportal[During development time,set this flag as false]
     */
    constructor(launchId,reporterOptions){
        this.launchId = launchId
        this.reportPortalUri = `${reporterOptions.endpoint}/${reporterOptions.project}`
        this.token = reporterOptions.token
        this.publishResult = reporterOptions.publishResult
        this.projectName = reporterOptions.project;


    }
    /**
     * This method will start suite
     * @param {*} suiteName 
     * @param {*} suiteDescription 
     * @returns 
     */
    startSuite(suiteName, suiteDescription) {
        if (!this.publishResult){
            return null
        }
        let payload = {
            "name": `${suiteName}`, "startTime": Date.now(), "type": "suite", "launchUuid":
                `${this.launchId}`, "description": `${suiteDescription}`
        }
        let response = http.post(`${this.reportPortalUri}/item`, JSON.stringify(payload), getHeader(this.token));
        let body = JSON.parse(response.body);
        let suiteId = body.id;
        return suiteId;
    }
    /**
     * This method will start the testcase
     * @param {*} suiteId - suite id
     * @param {*} testcaseName 
     * @param {*} testDescription 
     * @returns
     */
    startTest( suiteId, testcaseName, testDescription) {
        if (!this.publishResult){
            return null
        }
        let payload = { "name": `${testcaseName}`, "startTime": Date.now(), "type": "test", "launchUuid": `${this.launchId}`, "description": `${testDescription}` }
        let response = http.post(`${this.reportPortalUri}/item/${suiteId}`, JSON.stringify(payload), getHeader(this.token));
        let body = JSON.parse(response.body);
        let testId = body.id;
        return testId;
    }
    /**
     * This method will start test step
     * @param {*} testId - testcase id
     * @param {*} name - test step name
     * @param {*} description - test step description
     * @returns 
     */
    startTestStep( testId, name, description) {
        if (!this.publishResult){
            return null
        }
        let payload = { "name": `${name}`, "startTime": Date.now(), "type": "step", "hasStats": false, "launchUuid": `${this.launchId}`, "description": `${description}` }
        let response = http.post(`${this.reportPortalUri}/item/${testId}`, JSON.stringify(payload), getHeader(this.token));
        let body = JSON.parse(response.body);
        let testStepId = body.id;
        return testStepId;
    }
    /**
     * This method will finish test step created by startTestStep
     * @param {*} id - test step id
     * @param {*} status - test step status
     * @param {*} issueType -issue type
     * @param {*} comment - comment
     * @returns 
     */
    finishTestStep(id, status, issueType, comment = "no comments") {
        if (!this.publishResult){
            return null
        }
        let payload = {
            "endTime": Date.now(),
            "status": `${status}`,
            "launchUuid": `${this.launchId}`
        }
        if (issueType !== null) {
            payload["issue"] =
            {
                "issueType": `${issueType}`,
                "comment": `${comment}`
            }
        }
        let response = http.put(`${this.reportPortalUri}/item/${id}`, JSON.stringify(payload), getHeader(this.token));
        let body = JSON.parse(response.body);
        console.log(`[FinishTestStep] ${body.message}`);
    }
    /**
     * This method will finish testcase created by startTest
     * @param {*} id - testcase id
     * @param {*} status - test status (passed/failed/interrupted)
     * @returns 
     */
    finishTest( id, status) {
        if (!this.publishResult){
            return null
        }
        let payload = {
            "status": status,
            "endTime": Date.now(),
            "launchUuid": `${this.launchId}`
        }
        let response = http.put(`${this.reportPortalUri}/item/${id}`, JSON.stringify(payload), getHeader(this.token));
        let body = JSON.parse(response.body);
        console.log(`[FinishTest]${body.message}`);

    }
    /**
     * This method will finish suite created by startSuite
     * @param {*} id - suite id
     * @returns 
     */
    finishSuite(id) {
        if (!this.publishResult){
            return null
        }
        let payload = {
            "endTime": Date.now(),
            "launchUuid": `${this.launchId}`
        }
        let response = http.put(`${this.reportPortalUri}/item/${id}`, JSON.stringify(payload), getHeader(this.token));
        let body = JSON.parse(response.body);
        console.log(`[FinishTestSuite] ${body.message}`);
    }
    /**
     * This method will write log messages to report portal under parent item
     * @param {*} id - id of the parent item
     * @param {*} message - Log message
     * @returns 
     */
    writeLog(id,message){
        if (!this.publishResult){
            return null
        }
        let payload =  {
            "launchUuid": this.launchId,
            "itemUuid": id,
            "time": Date.now(),
            "message": message,
            "level": "error"
        }
        let response = http.post(`${this.reportPortalUri}/log`, JSON.stringify(payload), getHeader(this.token));
        let body = JSON.parse(response.body);
        console.log(`[writeLog] ${body.id}`);
        console.log(`[writeLog] ${message}`)
    }
}

