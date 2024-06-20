import exec from "k6/execution";
import { group } from 'k6';
import { check, sleep } from "k6";
import { generateHeader, getProtectionStoreVMList, httpPatch, waitForTask } from "./common/lib.js";
import { generateUpdateProxyPayload, generateUpdateDnsPayload } from "./payload_lib.js"


var testConfig = JSON.parse(open(__ENV.TEST_CONFIG));
var commonVars = testConfig.testbed.atlasOptions;
var baseUri = commonVars.baseUri;
var vmCount = testConfig.testinput.crudWorkflow.iteration;
var vmPrefix = commonVars.vmPrefix
var alternateDNS = commonVars.alternateDNS

var testVars = testConfig.testinput.modifyLocalStore
var concurrentUsers = testVars.virtualUsers
var thinkBeforeModifyDNS = testVars.thinkBeforeModifyDNS
var waitAfterModifyDNS = testVars.waitAfterModifyDNS
var thinkBeforeModifyProxy = testVars.thinkBeforeModifyProxy
var waitAfterModifyProxy = testVars.waitAfterModifyProxy

export var options = {
  scenarios: {
    "modify-local-store": {
      executor: "shared-iterations",
      vus: vmCount < concurrentUsers ? vmCount : concurrentUsers,
      iterations: vmCount, // No of VM to be deleted will not be more than number of user
    },
  },
};

export function setup() {
  let protectionStoreList = getProtectionStoreVMList(vmPrefix);
  console.debug(JSON.stringify(protectionStoreList))
  return { psgwList: protectionStoreList };
}


export default function (data) {

  let psgwList = data.psgwList;
  const psgwToBeModified = psgwList[exec.scenario.iterationInTest];
  console.log(`VM to be modified is ${JSON.stringify(psgwToBeModified)}`)
  console.log(psgwToBeModified.name)
  let resourceUri = psgwToBeModified.resourceUri
  let Uri = `${baseUri}${resourceUri}`
  console.log(`resource URI ${resourceUri}`)


  group('Modify DNS', function () {
    sleep(thinkBeforeModifyDNS)

    let body = generateUpdateDnsPayload(alternateDNS)
    let header = generateHeader();

    console.debug(`${Uri}`)
    console.debug(JSON.stringify(body))
    let resDnsChange = httpPatch(`${Uri}`, JSON.stringify(body), header)
    console.log(`response of DNS change ${JSON.stringify(resDnsChange, undefined, 4)}`);
    check(resDnsChange, { "Modify DNS is initiated successfully": (r) => r.status === 202 })
    // let body = JSON.parse(resDnsChange)
    // console.log(`resource URi is `)
    let responseBody = JSON.parse(resDnsChange.body)
    let taskUri = responseBody.taskUri
    console.debug(taskUri)

    const taskUrl = `${baseUri}${taskUri}`;
    let isSucceed = waitForTask(taskUrl, 120)
    console.log(`Task status is ${isSucceed}`)
    check(isSucceed, { "Modify DNS is completed successfully": (s) => s === true })

    sleep(waitAfterModifyDNS);
  });

  group("Modify Proxy", function () {
    sleep(thinkBeforeModifyProxy);

    let body = generateUpdateProxyPayload()
    let header = generateHeader();
    console.debug(`${Uri}`)
    console.debug(JSON.stringify(body))
    let proxyChangeResponse = httpPatch(`${Uri}`, JSON.stringify(body), header)
    console.log(JSON.stringify(proxyChangeResponse))
    check(proxyChangeResponse, { "Proxy change is initiated": (r) => r.status === 202 })

    let responseBody = JSON.parse(proxyChangeResponse.body)
    let taskUri = responseBody.taskUri
    console.debug(taskUri)

    const taskUrl = `${baseUri}${taskUri}`;
    let isSucceed = waitForTask(taskUrl, 120)
    console.log(`Task status is ${isSucceed}`)
    check(isSucceed, { "Proxy change is completed successfully": (s) => s === true })

    sleep(waitAfterModifyProxy)
  });
}

