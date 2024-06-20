import { check } from "k6";
import { generateHeader, waitForTask, list_datastore, getProtectionStoreVMList, httpPost } from "./../lib.js";
import { baseUri } from "../../cloud_backup_restore_workflow.js";

export function resizePsgStorage(catalystVmName, updatePsgDsName, updatePsgSize) {
  // Get the gateway VM to resize
  var catalystVMList = getProtectionStoreVMList(catalystVmName);
  //console.log(`Catalyst VM list ${JSON.stringify(catalystVMList)}`)
  var vmToBeResizeObj = catalystVMList[0]; // As exact vm name is given to getProtectionStoreVMList, it will have only one object.
  let psgName = vmToBeResizeObj.name;
  let psgId = vmToBeResizeObj.id;

  // Existing PSG datastore/s
  let psgDataStore = existingPsgDataStore(vmToBeResizeObj);
  let psgSize = existingPsgSize(vmToBeResizeObj);
  console.log(`Existing PSG Details: PSG Name: ${psgName} PSG ID: ${psgId} PSG Size: ${psgSize} PSG Datastore ID/s: ${JSON.stringify(psgDataStore)}`);
  let totalPsgSize = parseInt(psgSize) + parseInt(updatePsgSize);
  console.log(`Total PSG size: ${totalPsgSize}`);
  let resizeUri = `${baseUri}/api/v1/catalyst-gateways/${psgId}/resize`;

  // Additional datastores to resize PSG
  // let dsList = getDatastoreIds(updatePsgDsName);
  // if (dsList == undefined) {
  //   throw `Datastore list to add additional disk is empty`
  // }
  // Resize PSG requiers existing datastores to resize
  //let resizeDs = getresizeDataStores(dsList, psgDataStore);
  // if (resizeDs == undefined) {
  //   throw `List of datastores to resize PSG is empty`
  // }
  let payload = generateResizePayload(psgDataStore, updatePsgSize, psgSize);
  let isPsgResized = httpResizePsg(resizeUri, payload);
  return isPsgResized;
}

// Get existing PSG datastores
export function existingPsgDataStore(vmToBeResizeObj) {
  let dsList = [];
  let datastoreIds = vmToBeResizeObj.datastoreIds;
  for (let i = 0; i < datastoreIds.length; i++) {
    let dsId = datastoreIds[i].datastoreId;
    dsList.push(dsId);
  }
  console.log(`Existing PSG datastores: ${JSON.stringify(dsList)}`);
  return dsList;
}

// Get Existing PSG size
export function existingPsgSize(vmToBeResizeObj) {
  let existingDsInfo = vmToBeResizeObj.datastoresInfo;
  let existingPsgSize = 0;
  for (let i = 0; i < existingDsInfo.length; i++) {
    let dsSize = existingDsInfo[i].totalProvisionedDiskTiB;
    existingPsgSize = existingPsgSize + dsSize;
  }
  console.log(`Existing PSG size: ${existingPsgSize}`);
  return existingPsgSize;
}

// Get addtional datastore/s to resize
export function getDatastoreIds(updatePsgDsName) {
  let response = list_datastore();
  console.log(`[ListDatastores] => List Datastore response is ${JSON.stringify(response, undefined, 4)}`);
  check(response, { "List Datastore => ": (r) => r.status === 200 });
  let body = JSON.parse(response.body);
  console.debug(JSON.stringify(body));
  let dsList = [];
  body.items.forEach((element) => {
    let dsName = element.name;
    if (dsName.match(updatePsgDsName)) {
      dsList.push(element.id);
    }
  });
  console.log(`Datastore List to add additional disk: ${JSON.stringify(dsList)}`);
  return dsList;
}

// Get list of datastores to resize PSG, list should contain existing + new ds
export function getresizeDataStores(dsList, psgDataStore) {
  let datastoreIdsList = [];
  for (let i = 0; i < dsList.length; i++) {
    for (let j = 0; j < psgDataStore.length; j++) {
      if (dsList[i] == psgDataStore[j]) {
        datastoreIdsList.push(dsList[i]);
        dsList.splice(i, 1);
      }
    }
  }
  var dataStoreList = datastoreIdsList.concat(dsList);
  console.log(`Datastore List to resize PSG: ${JSON.stringify(dataStoreList)}`);
  return dataStoreList;
}

// resize API  call
export function httpResizePsg(resizeUri, payload, waitTime = 600) {
  let header = generateHeader();
  let resp = httpPost(resizeUri, JSON.stringify(payload), header);
  console.log(`[httpsResizePsg] => Create Resize PSG response -> ${JSON.stringify(resp, undefined, 4)}`);
  let body = JSON.parse(resp.body);
  check(resp, { "Resize PSG": (r) => r.status === 202 });
  if (resp.status === 202) {
    let isPsgResized = waitForTask(`${baseUri}${body.taskUri}`, waitTime, header);
    return isPsgResized;
  }
  console.error(`${body.error}`);
  throw `[httpResizePsg] => failed to resize PSG VM => ${body.error}`;
}

//generate resize PSG payload
export function generateResizePayload(resizeDs, updatePsgSize, psgSize) {
  console.log(`Total datastores available to resize is: ${resizeDs.length}`);
  if (psgSize == updatePsgSize) {
    updatePsgSize = (updatePsgSize + 2)
  }
  let datastoreList = [];
  let dsPayload = {};
  for (let i = 0; i < resizeDs.length; i++) {
    datastoreList.push({ datastoreId: dsPayload.datastoreId = resizeDs[i] });
  }
  let payload = {
    "datastoreIds": datastoreList,
    "maxInCloudDailyProtectedDataTiB": updatePsgSize,
    "maxInCloudRetentionDays": 100,
    "maxOnPremDailyProtectedDataTiB": 3,
    "maxOnPremRetentionDays": 100
  };
  console.log(`Resize PSG Payload: ${JSON.stringify(payload)}`);
  return payload;
}
