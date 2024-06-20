import { check, sleep } from "k6";
import { gateway, subnetMask } from "../CRUD_workflow.js";
import { generateHeader, waitForTask, httpGet, httpPost } from "./lib.js";

export function httpCreateLocalStore(baseUri, catalystId) {

    let copyPoolUrl = `${baseUri}/api/v1/protection-stores`;
    //Post copy pools with the payload to create localstore
    let localstorePayload = {
        "protectionStoreId": catalystId
    };
    console.debug(JSON.stringify(localstorePayload));
    let header = generateHeader();
    let localstoreResponse = httpPost(copyPoolUrl, JSON.stringify(localstorePayload), header);
    check(localstoreResponse, { "Local store creation is successful- Status 202 received": (r) => r.status === 202 });

    console.debug(`Local store response is ${JSON.stringify(localstoreResponse, undefined, 4)}`);
}
export function httpCreateCloudStore(baseUri, catalystId, region) {

    let copyPoolUrl = `${baseUri}/api/v1/protection-stores`;
    //Post copy pools with the payload to create localstore
    let cloudstorePayload = {
        "protectionStoreGatewayId": catalystId,
        "region": region
    };
    console.debug(JSON.stringify(cloudstorePayload));
    let header = generateHeader();
    let cloudstoreResponse = httpPost(copyPoolUrl, JSON.stringify(cloudstorePayload), header);
    check(cloudstoreResponse, { "Cloud store creation is successful- Status 202 received": (r) => r.status === 202 });

    console.debug(`Cloud store response is ${JSON.stringify(cloudstoreResponse, undefined, 4)}`);
}
export function getCalalystIdFromTask(taskUrl) {

    let header = generateHeader();
    let response = httpGet(taskUrl, header);
    console.log(`response is ${JSON.stringify(response, undefined, 4)}`);
    let taskResBody = JSON.parse(response.body);

    // From the resourceUri ,get catalyst gateway id
    console.debug(`resourceUri full - ${taskResBody.sourceResource.resourceUri}`);
    let resourceUri = taskResBody.sourceResource.resourceUri.split("/");
    let catalystId = resourceUri[resourceUri.length - 1];
    console.debug(`Catalyst gateway id is ${catalystId}`);
    return catalystId;
}

export function getCalalystVMStateFromTask(taskUrl) {

    let header = generateHeader();
    let response = httpGet(taskUrl, header);
    console.log(`response is ${JSON.stringify(response, undefined, 4)}`);
    let taskResBody = JSON.parse(response.body);

    // From the resourceUri ,get catalyst gateway id
    console.log(`Task state - ${taskResBody.state}`);

}

export function httpCreateProtectionGateway(networkName, protectionStoreName, nwAddress, dnsAddress, hypervisorId, datastoreId, hostId, baseUri, gateway, subnetMask ) {
    try {
        // Pick random datastore name in the given vcenter 
        // let { datastoreName, hostName } = fetchRandomHostAndDataStore(vcenterObj);

        // let networkName = vcenterObj.networkName;

        let payload = generateCreateCatalystPayload(protectionStoreName, hypervisorId, datastoreId, hostId, nwAddress, networkName, dnsAddress, gateway, subnetMask);
        console.log(`Create catalyst payload ${JSON.stringify(payload, undefined, 4)}`);

        // create Protection store gateway
        var header = generateHeader();
        const url = `${baseUri}/api/v1/protection-store-gateways`;
        let response = httpPost(url, JSON.stringify(payload), header);

        check(response, { "Protection Store VM  creation is successful- Status 201 received": (r) => r.status === 201 });
        console.log(`Create protection store ${protectionStoreName} response is ${JSON.stringify(response, undefined, 4)}`);
        return response;
    }
    catch (err) {
        console.error(err.message)
        console.error("Exception occurred in httpCreateProtectionGateway");
        throw err;
    }
}

export function fetchRandomHostAndDataStore(vcenterObj) {
    let randomDatastoreIndex = Math.floor(
        Math.random() * (vcenterObj.datastoreList.length - 1)
    );
    let datastoreName = vcenterObj.datastoreList[randomDatastoreIndex];

    // Pick random host name in the given vcenter
    let randomHostNameIndex = Math.floor(Math.random() * (vcenterObj.hostList.length - 1));
    let hostName = vcenterObj.hostList[randomHostNameIndex];
    return { datastoreName, hostName };
}

// Create protection store VM payload
export function generateCreateCatalystPayload(protectionStoreName, hypervisorId, datastoreId, hostId, nwAddress, networkName, dnsAddress, gateway, subnetMask) {
    try {
        // let timestamp = Math.floor(Date.now() /1000);
            console.log(`Generating create catalyst with protectionStoreName, hypervisorId, datastoreId, hostId, nwAddress, networkName, dnsAddress, gateway::: ${protectionStoreName}, ${hypervisorId}, ${datastoreId}, ${hostId}, ${nwAddress}, ${networkName}, ${dnsAddress}, ${gateway}, ${subnetMask}`);
        return {
            "hypervisorManagerId": hypervisorId,
            "name": protectionStoreName,
            "vmConfig": {
                "datastoreIds": [
                    {
                        "datastoreId": datastoreId,
                    },
                ],
                "maxInCloudDailyProtectedDataTiB": 2,
                "maxInCloudRetentionDays": 100,
                "maxOnPremDailyProtectedDataTiB": 2,
                "maxOnPremRetentionDays": 100,
                "hostId": hostId,
                "network": {
                    "dns": [
                        {
                            "networkAddress": dnsAddress
                        }
                    ],
                    "gateway": gateway,
                    "networkAddress": nwAddress,
                    "networkType": "STATIC",
                    "subnetMask": subnetMask,
                    "name": networkName
                },
            },
        };
    }
    catch (err) {
        console.error(err.message)
        console.error("Exception occurred in generateCreateCatalystPayload");
        throw err;
    }
}

export function getDatastoreId(baseUri, datastoreName) {
    try {
        //let vcenterName = "vcsa67-02.vlab.nimblestorage.com"
        // let token = getToken();
        // console.debug(`Bearer ${token.bearerToken}`);
        let atlasHeader = generateHeader();
        console.log(`Header response is ${atlasHeader}`);
        let response = httpGet(`${baseUri}/api/v1/datastores?limit=1000`, atlasHeader);
        check(response, { "getDatastoreId -> Get datastore list -> status was 200": (r) => r.status === 200 });
        let datastoreList = JSON.parse(response.body);

        for (let datastore of datastoreList.items) {
            if (datastore.name === datastoreName) {
                // console.log(vcenter.id)
                return datastore.id;
            }
        }
        console.debug(`no datastore is present with the name ${datastoreName}`);
        throw `datastore ${datastoreName} is not found`;
    }
    catch (err) {
        console.error("Exception occurred in getDatastoreId");
        throw err;
    }
}

export function getHostId(baseUri, datastoreName, hostName) {
    try {
        //let vcenterName = "vcsa67-02.vlab.nimblestorage.com"
        //let token = getToken();
        console.log(`datastore ${datastoreName} `);
        let atlasHeader = generateHeader();

        let response = httpGet(`${baseUri}/api/v1/datastores?limit=1000`, atlasHeader);
        check(response, { "[func]getHostId -> Get data store list -> status was 200": (r) => r.status === 200 });
        let datastoreList = JSON.parse(response.body);

        for (let datastore of datastoreList.items) {
            if (datastore.name === datastoreName) {
                // console.log(vcenter.id)
                let hostList = datastore.hostsInfo;
                for (let host of hostList) {
                    if (host.name === hostName) {
                        return host.id;
                    }
                }
            }
        }
        throw `host ${hostName} is not found`;
    }
    catch (err) {
        console.error("Some exception occurred in getHostId")
        throw err;
    }
}

export function getHypervisorManagerId(baseUri, vcenterName) {
    try {
        //let vcenterName = "vcsa67-02.vlab.nimblestorage.com"
        // let token = getToken();
        console.log(`vcenter name is  ${vcenterName}`);
        let atlasHeader = generateHeader();

        let response = httpGet(`${baseUri}/api/v1/hypervisor-managers`, atlasHeader);
        check(response, { "[script] createLocalStore -> [func]getHypervisorManagerId -> get hypervisor list -> status was 200": (r) => r.status === 200 });
        let vcenterList = JSON.parse(response.body);
        console.log(`vcenter manager response is ${JSON.stringify(response)}`);
        for (let vcenter of vcenterList.items) {
            if (vcenter.name === vcenterName) {
                // console.log(vcenter.id)
                return vcenter.id;
            }
        }
        throw `vcenter ${vcenterName} is not found.`;
    }
    catch (err) {
        console.error("Exception occurred in getHypervisorManagerId");
        throw err;
    }
}
export function getCalalystIdByName(baseUri, catalystVmName) {

    let header = generateHeader();
    let url = `${baseUri}/api/v1/protection-store-gateways`;
    let response = httpGet(url, header);
    console.log(`response is ${JSON.stringify(response, undefined, 4)}`);
    let responseBody = JSON.parse(response.body);
    for (let vm of responseBody.items) {
        if (catalystVmName === vm.name) {
            let catalystVmId = vm.id;
            return catalystVmId;
        }
    }

}
export function getCatalystVmState(catalystUrl) {
    try {
        let atlasHeader = generateHeader();
        let catalystRes = httpGet(catalystUrl, atlasHeader);
        //"state": "CG_STATE_ERROR"
        console.log(`Catalyst gateway response is ${JSON.stringify(catalystRes)}`);
        let responseBody = JSON.parse(catalystRes.body);
        let vmState = responseBody.state;
        let vmStatus = responseBody.health.status;
        let vmName = responseBody.name
        return { vmName, vmState, vmStatus };
    }
    catch (err) {
        console.error("Exception occurred in getCatalystVmState");
        throw err;
    }
}


export function isCatalystVMDeployed(catalystUrl, vmCreationDuration) {
    let startTime = new Date();
    let durationTaken = 0;
    while (true) {
        let { vmName, vmState, vmStatus } = getCatalystVmState(catalystUrl);
        console.log(`VM ${vmName} state is ${vmState} and VM status is ${vmStatus}`)
        if (vmState === 'CG_STATE_OK' && vmStatus === 'CG_HEALTH_STATUS_CONNECTED') {
            console.log(`VM ${vmName} is deployed completely`);
            return true;
        }
        else if (vmState === 'CG_STATE_ERROR' || durationTaken > vmCreationDuration) {
            console.error(`VM ${vmName} is not created yet. vm state is ${vmState} and duration taken is  ${durationTaken} is more than ${vmCreationDuration}`);
            return false;
        }
        else {
            // vmCreationDuration = vmCreationDuration - 10;
            sleep(10);
            // let {vmState, vmStatus} = getCatalystVmState(catalystUrl);
            durationTaken = parseInt(new Date() - startTime) / 1000
            console.log(`Time taken is ${durationTaken} seconds. VM state is ${vmState}. VM status is ${vmStatus}`)
        }
    }
}

/**
 * Catalyst gateway VM creation(rest api call),wait for VM to reach OK and connected state.
 * Also check whether the task is completed or not
 * @param {object} vcenterObj vcenter object mentioned in testconfig json.
 * @param {string} protectionStoreName 
 * @param {string} ipAddress 
 * @param {string} dnsAddress 
 * @param {number} vmCreationWaitTime wait time in seconds for creating VM
 * @returns boolean
 */
export function createCatalystGateway(networkName, protectionStoreName, ipAddress, dnsAddress, vmCreationWaitTime, hypervisorId, datastoreId, hostId, baseUri, gateway, subnetMask) {
    try {
        // var vcenterObj = vcenterList.filter(vc => vc.name === vcenter)
        // console.log(JSON.stringify(vcenterObj, undefined, 4));
        let response = httpCreateProtectionGateway(networkName, protectionStoreName, ipAddress, dnsAddress, hypervisorId, datastoreId, hostId, baseUri, gateway, subnetMask);

        let isProtectionStoreInitiated = (response.status === 201);
        var isVMDeployed = undefined
        if (isProtectionStoreInitiated) {
            // From task fetch the catalyst Id
            let responseBody = JSON.parse(response.body);
            let taskUri = responseBody.taskUri;
            console.debug(taskUri);

            const taskUrl = `${baseUri}${taskUri}`;
            let catalystId = getCalalystIdFromTask(taskUrl);
            getCalalystVMStateFromTask(taskUrl);

            sleep(10);
            const catalystUrl = `${baseUri}/api/v1/protection-store-gateways/${catalystId}`;

            // Check the status in Task
            let isVMDeployTaskCompleted = waitForTask(taskUrl, vmCreationWaitTime);
            console.log(`[createCatalystGateway]=> VM creation Task status is ${isVMDeployTaskCompleted}`);
            check(isVMDeployTaskCompleted, { "Protection store gateway VM deployment Task status": (s) => s === true });

            isVMDeployed = isCatalystVMDeployed(catalystUrl, 120);
            check(isVMDeployed, { "Protection store gateway VM deployment status": (s) => s === true });
            // Wait 5 mins to trigger local store creation task
            sleep(300);
        }
        return isVMDeployed;
    }
    catch (err) {
        console.error(error.message)
        console.error("Exception occurred in createCatalystGateway");
        throw err
    }
}