import http from "k6/http";
import { check, fail, sleep } from "k6";
import encoding from 'k6/encoding';

export default class LibvSphereApi {
  constructor(testconfig) {
    
    if (LibvSphereApi._instance) {
      
      return LibvSphereApi._instance
    }
    
    LibvSphereApi._instance = this;
    this.vsphereAuth = testconfig.testbed.vsphereOptions.vsphereAuth;
    this.vcenter = testconfig.testbed.vsphereOptions.vcenter;
    this.contentLibraryName = testconfig.testbed.vsphereOptions.content_library;
    this.host = `https://${this.vcenter}`
    this.headers = this.getHeaders()
  }


  /**
   * Get Vsphere rest API session token
   * @returns session token
   */
  getVmSessionToken() {
    const encodedAuthentication = encoding.b64encode(this.vsphereAuth);
    const url = `${this.host}/rest/com/vmware/cis/session`;
    const header = {
      headers: {
        Authorization: `Basic ${encodedAuthentication}`
      }
    };
    console.log(`getVMSessionToken => header is ${JSON.stringify(header)}`)
    const res = http.post(url, null, header);
    check(res,{"VM session token is fetched successfully": (r)=> r.status === 200})
    if(res.status !== 200){
      fail("Failed to get VMware session token")
    }
    console.log(`VM session token response is ${JSON.stringify(res, undefined, 4)}`);
    
    let body = JSON.parse(res.body);
    const sessionToken = body.value;
    console.log(`Session id is ${sessionToken}`);
    return sessionToken;
  }

  getHeaders(){
    let sessionToken = this.getVmSessionToken();
    const sessionHeader = {
        headers: {
            'vmware-api-session-id': sessionToken
        }
    };
    return sessionHeader
  }

  shutdownVM(vmName, waitTime=120) {
    let vmUrl = `${this.host}/rest/vcenter/vm`;
    var vmObj = this.getVM(vmUrl, vmName);

    let shutdownUrl = `${this.host}/rest/vcenter/vm/${vmObj.vm}/guest/power?action=shutdown`;
    // let delUrl = `${api_host}/rest/vcenter/vm/${vmId}`;
    let resp = http.post(shutdownUrl, null, this.headers);
    console.log(JSON.stringify(resp, undefined, 4));

    check(resp, { "VM shutdown successfully": (r) => r.status === 200 });
    let startTime = new Date();
    let durationTaken = 0;
    while (true) {

        let vmObj = this.getVM(vmUrl, vmName);
        if (vmObj.power_state === 'POWERED_OFF') {
            return true;
        }
        else if (durationTaken > waitTime) {
            // sleep(15)
          return false;
        }
        
        durationTaken = parseInt(new Date() - startTime) / 1000;
        console.log("[shutdownVM]-> Sleep 10 seconds before continue")
        sleep(10);
    }
  }

  /**
   * shutdown and delete the VM from vcenter
   * @param {string} vmName 
   */
  cleanupVm(vmName) {
    let vmState = this.shutdownVM(vmName);
    if (vmState) {
        this.deleteVM(vmName);
    }
    else {
        console.error(`Unable to shutdown VM ${vmName}`)
        throw `Unable to shutdown VM ${vmName}`;
    }
  }

  /**
   * Get virtual machine Id using Vsphere rest API
   * @param {string} vmUrl vcenter url
   * @param {string} vmName 
   * @returns virtual machine id
   */
  getVM(vmUrl, vmName) {

    console.log(JSON.stringify(this.headers, undefined, 4));
    let getRes = http.get(vmUrl, this.headers);
    console.log(JSON.stringify(getRes, undefined, 4));
    
    // @ts-ignore
    let body = JSON.parse(getRes.body);
    console.log(JSON.stringify(body, undefined, 4));
    let vmObj = undefined;
    for (let b of body.value) {
      if (b.name === vmName) {
        vmObj = b;
        console.log(vmObj);
        // vm
        return vmObj;
      }
    }
    throw `[getVM] =>  ${vmName} is not found`
  }

    /**
   * delete VM from vcenter side
   * @param {string} vmName 
   */
  deleteVM(vmName) {
    let vmUrl = `${this.host}/rest/vcenter/vm`;
    var vmObj = this.getVM(vmUrl,vmName);

    let delUrl = `${this.host}/rest/vcenter/vm/${vmObj.vm}`;
    let delRes = http.del(delUrl, null, this.headers);
    console.log(JSON.stringify(delRes, undefined, 4));
    check(delRes, { "VM deleted from vcenter successfully ": (r) => r.status === 200 })
    if (delRes.status === 200) {
        console.info(`VM ${vmName} deleted successfully`);
        return true;
    }
    console.error(`VM deletion status code is ${delRes.status}`);
    throw(`VM ${vmName} is failed to be deleted.`);
  }

  getContentLibraryIds() {
    const url = `${this.host}/api/content/local-library`;

    let response = http.get(url, this.headers);
    console.log(`getContentLibraryIDs from vSphare api=> response => ${JSON.stringify(response, undefined, 4)}`);
    
    let responseStatus = JSON.parse(response.status);
    
    let responseBody = JSON.parse(response.body);
    check(responseStatus,{"get Content Library Id request (200)" : (t) => t == 200})  
    check(responseBody,{"ContentLibraryId is not empty" : (t) => t !== undefined})  
    console.log(`getContentLibraryIDs=> ${responseBody}`);
    return responseBody;
  }

  getLibraryDetail(contentLibraryId) {
    console.log(`getting content library details for id: ${contentLibraryId}`);
    const url = `${this.host}/api/content/local-library/${contentLibraryId}`;

    let response = http.get(url, this.headers);
    console.log(`getLibraryDetail from vSphare api response => ${JSON.stringify(response, undefined, 4)}}`);
    
    let responseBody = JSON.parse(response.body);
    
    // @ts-ignore
    let responseStatus = JSON.parse(response.status);
    check(responseStatus,{"get Content Library Detail request (200)" : (t) => t == 200})  
    check(responseBody,{"ContentLibraryDetail is not empty" : (t) => t !== undefined})  
    console.log(`getLibraryDetail=> ${JSON.stringify(responseBody, undefined, 4)}`);
    return responseBody;
  }

  deleteContentLibrary(contentLibraryId) {
    console.log(`deleting content library id: ${contentLibraryId}`);
    const url = `${this.host}/api/content/local-library/${contentLibraryId}`;

    let response = http.del(url,null, this.headers);
    console.log(`deleteContentLibrary from vSphare api response => ${JSON.stringify(response, undefined, 4)}}`);
    
    let responseStatus = JSON.parse(response.status);
    check(responseStatus,{"delete Content Library request (204)" : (t) => t == 204}) 
    return (responseStatus == 204)
  }

}
