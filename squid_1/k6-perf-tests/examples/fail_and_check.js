// Example of Single virtual user and Multi iterations.
import { generateHeader } from "../common/lib.js";
import http from "k6/http";
import { check, fail, sleep } from "k6";

let baseUri = "https://scdev01-app.qa.cds.hpe.com"

export const options = {
    scenarios: {
        "single_vu_multiiteration": {
            executor: "shared-iterations",
            vus: 1,
            iterations: 2,
            maxDuration: "10m",
        },
    },
    insecureSkipTLSVerify: true
};
let thinkTime = 5
export default function () {
    let atlasHeader = generateHeader();
    let response = http.get(`${baseUri}/api/v1/catalyst-gateways`, atlasHeader);
    //console.log(JSON.stringify(response,undefined,4));
    // @ts-ignore
    let body = JSON.parse(response.body)
    console.log(`Iteration [${__ITER}] => Virtual user [${__VU}]`)
    for (const b of body.items) {
        console.log(`Protection store gateway VM name => ${b.name}`);
    }
    check(response, {
        "Protection store gateway response is 200": (r) => r.status == 200,
        "VM PerfTest-PSG-076 is there": (r) => r.body.includes("PerfTest-PSG-076")
    })
    // User is thinking before doing next round of action.
    if (response.status != 201) {
        fail("Failed to get VM")
    }
    console.log("Fail is crossed")
    sleep(thinkTime)
}


