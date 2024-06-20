import { check } from "k6";
import { generateHeader, httpDelete, waitForTask } from "./lib.js";
// import { baseUri } from "./delete_protectiongateway";


/**
 * delete protection store gateway from Atlas UI. It will wait till the delete task is completed 
 * @param {string} baseUri -Atlas application base Url
 * @param {object} vmObj - VM to be deleted object
 * @param {number} vmDeletionWaitTime - wait time for vm to be deleted
 * @returns {boolean}
 */
export function deleteCatalystVM(baseUri, vmObj, header, vmDeletionWaitTime = 500) {
    if (header == null) {
        var header = generateHeader();
    }
    console.debug(`header is ${JSON.stringify(header)}`);

    let delResponse = httpDelete(`${baseUri}/api/v1/catalyst-gateways/${vmObj.id}`, null, header);
    console.log(`Delete VM response ${JSON.stringify(delResponse)}`);
    check(delResponse, { "Protection Store gateway VM Deletion is initiated- Status 202 received": (r) => r.status === 202 });
    let responseBody = JSON.parse(delResponse.body);
    let taskUri = responseBody.taskUri;
    console.debug(taskUri);

    const taskUrl = `${baseUri}${taskUri}`;
    let isVMDeleteTask = waitForTask(taskUrl, vmDeletionWaitTime);
    console.log(`Task status is ${isVMDeleteTask}`);
    check(isVMDeleteTask, { "Protection store gateway VM delete Task status": (s) => s === true });
    return isVMDeleteTask 
}


