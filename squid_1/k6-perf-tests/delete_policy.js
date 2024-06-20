import { deleteProtectionPolicy } from "./common/backup_restore/protectionPolicy.js";
import { generateHeader, httpGet } from "./common/lib.js";

var testConfig = JSON.parse(open(__ENV.TEST_CONFIG));
var commonVars = testConfig.testbed;
export var baseUri = commonVars.atlasOptions.baseUri;
// delete all protection policy that includes "Perf" in protection policy name
export default function () {
    console.log(`Delete protection template`);
    let uri = `${baseUri}/api/v1/protection-policies?limit=1000`;
    let header = generateHeader();
    header['timeout'] = "60s";
    console.log(JSON.stringify(header));
    let res = httpGet(uri, header);
    let body = JSON.parse(res.body);
    console.log(`body is ${JSON.stringify(body, undefined, 4)}`);

    for (let policy of body.items) {
        if (policy.name.includes('Perf')) {
            console.log(`policy name is ${policy.name} -> id ${policy.id}`);
            const isProtectionTemplateDeleted = deleteProtectionPolicy(policy.id);
            console.log(isProtectionTemplateDeleted);
        }
    }

}