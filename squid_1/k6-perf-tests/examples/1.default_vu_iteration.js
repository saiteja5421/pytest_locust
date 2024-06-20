// Example of default virtual user and iterations.
import exec from "k6/execution";
import { check, group } from "k6";
import { generateHeader } from "../common/lib.js";
import http from "k6/http";

let baseUri = "https://scdev01-app.qa.cds.hpe.com"
export default function () {
    let atlasHeader = generateHeader();
    let response = http.get(`${baseUri}/api/v1/catalyst-gateways`, atlasHeader);
    check(response, { "List catalyst VM": (r) => r.status == 200 })
    //console.log(JSON.stringify(response,undefined,4));
    // @ts-ignore
    let body = JSON.parse(response.body)
    for (const b of body.items) {
        console.log(`Protection store gateway VM name => ${b.name}`);
    }
}


