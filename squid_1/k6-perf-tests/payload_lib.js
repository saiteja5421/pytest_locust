import { getToken, getHypervisorManagerId, getDatastoreId, getHostId } from "./common/lib.js";
import http from "k6/http";

export function generateUpdateDnsPayload(newDNS) {
    return {
        "dns": [
            {
                "networkAddress": `${newDNS}`
            }
        ]
    };
}

export function generateUpdateProxyPayload(port) {
    return {
        "proxy": {
            "networkAddress": "http://web-proxy.corp.hpecorp.net",
            "port": port
        }
    }
}

// UpdateNic Payload will be generated 
export function generateUpdateNicPayload(gatewayVM, networkAddress) {
    console.debug(gatewayVM.network.nics[0])
    // Update the network address of the first NIC from list
    return {
        nic: {
            'gateway': gatewayVM.network.nics[0].gateway,
            'id': gatewayVM.network.nics[0].id,
            'networkAddress': networkAddress,
            'networkType': gatewayVM.network.nics[0].networkType,
            'subnetMask': gatewayVM.network.nics[0].subnetMask,
        },
    };
}

// AddNic Payload will be generated
  
export function generateAddNicPayload(networkAddress,networkType,subnetMask,networkName) {
    // Add Data Network Interfaces of Catalyst VM
    return {
        nic: {
            'networkAddress': networkAddress,
            'networkName': networkName,
            'networkType':networkType,
            'subnetMask': subnetMask,
        },
    };
}

