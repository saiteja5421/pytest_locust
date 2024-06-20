import exec from "k6/execution";
import { sleep } from "k6";
import { SharedArray } from "k6/data";
import { createCatalystGateway,getDatastoreId, getHostId, getHypervisorManagerId, fetchRandomHostAndDataStore } from "./common/createLocalStore.js";
import { LabelElement } from "k6/html";
import LibvSphareApi from './LibvSphereApi.js';



// import { generateCreateCatalystPayload } from "./payload_lib.js"

// adding vuCount,iterationCount and etc outside so that it will be used in option as well default function

var testConfig = JSON.parse(open(__ENV.TEST_CONFIG));
var commonVars = testConfig.testbed;
var baseUri = commonVars.atlasOptions.baseUri;
var testVars = testConfig.testinput.createProtectionGateway;
var psgwOptions = testConfig.testinput.crudWorkflow.psgwOptions
var ipPrefix = psgwOptions.ipPrefix;
var ipMin = psgwOptions.ipMin;
var ipMax = psgwOptions.ipMax;
export var gateway = psgwOptions.gateway;
export var subnetMask = psgwOptions.subnetMask;
var dnsAddress = psgwOptions.dnsAddress;
var vmPrefix = psgwOptions.vmPrefix;
var vcenter = commonVars.vsphereOptions.vcenter;

var thinkingTime = testVars.thinkingTime;
var duration = testVars.duration;

var ipListAvailable = new SharedArray("Available Ip list", function () {
  let ipList = [];
  let numOfIP = parseInt(ipMax) - parseInt(ipMin);
  for (let i = 0; i <= numOfIP - 1; i++) {
    ipList[i] = ipPrefix + (parseInt(ipMin) + parseInt(i));
  }
  return ipList;
});

// Number of users should not exceed than the number of available PSGW (Protection Store gateway) available IP address. Otherwise IP range will exceed and fails. That's why vus are conditional.
var ipAvailableCount = ipListAvailable.length;
var protectionStoreVMCount = testConfig.testinput.crudWorkflow.iteration
const iterationCount = (ipAvailableCount < protectionStoreVMCount
  ? ipAvailableCount
  : protectionStoreVMCount);
export const options = {
  scenarios: {
    "create-catalyst-vm": {
      executor: "shared-iterations",
      vus: iterationCount,
      iterations: iterationCount,
      maxDuration: duration,
    },
  },
};
export function setup(){
  let hypervisorId = getHypervisorManagerId(baseUri,vcenter)
  console.log(`[setup] hypervisor id is => ${hypervisorId}`);
  let vcenterList = testConfig.testbed.vcenterList;
  console.log(`[setup] vcenterlist ${vcenterList}`);
  var vcenterObj = undefined;
  for (let vc of vcenterList) {
      if (vc.name === vcenter) {
          vcenterObj = vc;
      }
  }
  let networkName =vcenterObj.networkName

  let { datastoreName, hostName } = fetchRandomHostAndDataStore(vcenterObj);
  let datastoreId = getDatastoreId(baseUri,datastoreName)
  console.log(`[setup]=> Datastore id is ${datastoreId}`);
  let hostId = getHostId(baseUri,datastoreName,hostName)
  console.log(`[setup]=> host id is ${hostId}`);
  return { "hypervisorId": hypervisorId ,"datastoreId": datastoreId,"hostId":hostId, "networkName":networkName}
}
export default function (data) {
  console.log(exec.scenario.iterationInTest)
  let execIteration = exec.scenario.iterationInTest
  let timestamp = Math.floor(Date.now() / 1000);
  const protectionStoreName = `${vmPrefix}_${timestamp}_${execIteration}`;
  var vmCreationWaitTime = parseInt(commonVars.vsphereOptions.vmCreationTimeout);
  let nwAddress = ipListAvailable[execIteration];
  // TODO: Delete the content library
  var vSphareApi = new LibvSphareApi(testConfig);
  let contentLibraryList = vSphareApi.getContentLibraryIds();
  for (const _id in contentLibraryList) {
    let contentLibrary = vSphareApi.getLibraryDetail(contentLibraryList[_id]);
    if (vSphareApi.contentLibraryName == contentLibrary.name){
      console.log(`Delete Content Library Name: ${contentLibrary.name}`);
      vSphareApi.deleteContentLibrary(contentLibraryList[_id]);
    }
  }
  console.log("Wait for 120 seconds after content library deletion")
  sleep(120);
  let isVMDeployed = createCatalystGateway(data.networkName, protectionStoreName, nwAddress, dnsAddress, vmCreationWaitTime,data.hypervisorId,data.datastoreId,data.hostId,baseUri);
  // let isVMDeployed = createCatalystGateway(vcenterObj, protectionStoreName,nwAddress, dnsAddress, vmCreationWaitTime);
  if (isVMDeployed) {
    console.info(`Iteration => ${execIteration} => Protection store gateway vm ${protectionStoreName} is deployed`);
    console.log("Sleep for 120 seconds")
    sleep(120)
  }
  else {
    console.error(`Iteration => ${execIteration} => Protection store gateway vm ${protectionStoreName} is failed to deploy`);
    console.log("sleep 30 seconds")
    // sleep(30)
  }
  sleep(60);
  

  // After all the concurrentUsers executed once they will think for thinkingTime before
  // triggering next iteration till duration is over
  // if 5 concurrentUsers then they will complete in parallel then wait for
  // thinkingTime ,after thinkingTime again 5 concurrentUser execute.
  sleep(thinkingTime);
}
