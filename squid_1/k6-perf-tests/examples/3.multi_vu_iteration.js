// Example of Multiple virtual user and iterations.
import { generateHeader } from "../common/lib.js";
import http from "k6/http";
import { sleep } from "k6";

let baseUri = "https://scdev01-app.qa.cds.hpe.com"

export const options = {
    scenarios: {
        "multi_vu_iteration": {
            executor: "shared-iterations",
            vus: 2,
            iterations: 5,
            maxDuration: "10m",
        },
    },
};

let thinkTime = 3
export default function () {
    let atlasHeader = generateHeader();
    let response = http.get(`${baseUri}/api/v1/catalyst-gateways`, atlasHeader);
    //console.log(JSON.stringify(response,undefined,4));
    // @ts-ignore
    let body = JSON.parse(response.body);
    console.log(`Iteration [${__ITER}] => Virtual user [${__VU}]`);
    for (const b of body.items) {
        console.log(`Protection store gateway VM name => ${b.name}`);
    }
    sleep(thinkTime)
}


