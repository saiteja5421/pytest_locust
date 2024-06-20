import http from "k6/http";
import exec from "k6/execution";
import encoding from "k6/encoding";

export default class TestRail {

    constructor(baseUrl, emailId, apiKey, projectName, milestoneName) {
        this.baseUrl = baseUrl
        this.projectName = projectName
        this.milestoneName = milestoneName
        this.encodedAuthentication = encoding.b64encode(`${emailId}:${apiKey}`);
        this.projectId = this.getProjectId();
        this.milestoneId = this.getMileStoneId();
    }

    getProjectId() {
        let url = `${this.baseUrl}/get_projects`;
        let projectId = this.getObjectId(url, this.projectName)
        if (projectId != null) {
            return projectId
        }
        throw `project ${this.projectName} is not found`
    }

    getObjectId(url, name) {
        let headers = this.generateHeader();
        let resp = http.get(url, headers);
        if (resp.status <= 201) {
            console.debug(`milestones are ${JSON.stringify(resp, undefined, 4)}`);
        }
        //console.log(JSON.stringify(resp, undefined, 4));
        // @ts-ignore
        let body = JSON.parse(resp.body);
        for (const b of body) {

            if (b.name === name) {
                return b.id;
            }
        }
        return null;
    }
    generateHeader() {
        return {
            headers: {
                "content-type": "application/json",
                Authorization: `Basic ${this.encodedAuthentication}`
            },
        };
    }

    getMileStoneId() {
        let url = `${this.baseUrl}/get_milestones/${this.projectId}`;
        let milestoneId = this.getObjectId(url, this.milestoneName)
        if (milestoneId != null) {
            return milestoneId
        }
        throw `milestone ${this.milestoneName} is not found`
    }

    getTestPlanId(planName) {
        let url = `${this.baseUrl}/get_plans/${this.projectId}`;
        return this.getObjectId(url, planName)
    }

    createTestPlan(testplanName) {
        let body = {
            "name": testplanName,
            "milestone_id": this.milestoneId
        };
        let url = `${this.baseUrl}/add_plan/${this.projectId}`;
        let header = this.generateHeader();
        let resp = http.post(url, JSON.stringify(body), header);
        // @ts-ignore
        let responseBody = JSON.parse(resp.body)
        return responseBody["id"]
    }

    addTestPlanEntry(testrunName){
        let runs =[]
        runs.push({
            "include_all": false,
            "case_ids": run_result["case_ids"],
            "config_ids": run_result["configs"] 
        })
        let plan_entry = {
            // "case_ids": list(set(all_case_ids)),
            // "config_ids": list(set(all_config_ids)),
            // TODO: test suite to be fetched
            "suite_id": testrailsuite_id,
            "name": testrun,
            "include_all": false,
            "runs": runs
        }
    testplan = api_request("POST", "/add_plan_entry/" + str(testplan_id), api_details, data=plan_entry)
        let url =`${this.baseUrl}/add_plan_entry/`;

        if "entries" in testplan.keys():

            for testrail_plan_entry in testplan["entries"]:

                if plan_entry["name"] == testrail_plan_entry["name"]:

                    testplanentry_id = testrail_plan_entry["id"]

                    return testplanentry_id

        else:

            testplanentry_id = testplan["id"]

            return testplanentry_id
    }
}