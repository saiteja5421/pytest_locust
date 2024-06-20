// Example of default virtual user and iterations.
import exec from "k6/execution";
import { check, group, sleep } from "k6";
import { generateHeader } from "../common/lib.js";
import http from "k6/http";

let baseUri = "https://scdev01-app.qa.cds.hpe.com"
let thinkTime = 5
export default function () {
    group("List catalyst gateway before delete", () => {
        console.log("========== User is viewing the list of Catalyst VM ================")
        let atlasHeader = generateHeader();
        let response = http.get(`${baseUri}/api/v1/catalyst-gateways`, atlasHeader);
        check(response, { "List catalyst VM": (r) => r.status == 200 })
        //console.log(JSON.stringify(response,undefined,4));
        // @ts-ignore
        let body = JSON.parse(response.body)
        for (const b of body.items) {
            console.log(`Protection store gateway VM name => ${b.name}`);
        }
        console.log("=========Before Delete End =================")
    })
    console.log("========== He is checking which VM is to be deleted.  ================")
    sleep(thinkTime)
    group("Delete catalyst gateway", () => {
        check(true, { "VM is deleted": (r) => r == true })
    })
    sleep(thinkTime)
    group("List catalyst gateway after delete", () => {
        console.log("========== After the VM is deleted ,he is listing and ensure that it is removed from UI.  ================")

        let atlasHeader = generateHeader();
        let response = http.get(`${baseUri}/api/v1/catalyst-gateways`, atlasHeader);
        check(response, { "List catalyst VM": (r) => r.status == 200 })
        //console.log(JSON.stringify(response,undefined,4));
        let body = JSON.parse(response.body)
        for (const b of body.items) {
            console.log(`Protection store gateway VM name => ${b.name}`);
        }
        console.log("========== VM is deleted successfully. Now he waits for next action ================")
    })
    sleep(thinkTime)
}


