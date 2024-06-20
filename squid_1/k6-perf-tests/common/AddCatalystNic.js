import { check } from "k6";
import { httpPost } from "./lib.js";
import { generateAddNicPayload } from "../payload_lib.js";

export function addCatalystNic(baseUri, catalystVM, networkAddress, networkType, subnetMask, networkName, header) {
  const nwInterfacePayload = generateAddNicPayload(networkAddress, networkType, subnetMask, networkName);

  console.debug(`header is ${JSON.stringify(header)}`);

  const url = `${baseUri}/api/v1/catalyst-gateways`;
  const AddNicUrl = `${url}/${catalystVM.id}/createNic`;
  let response = httpPost(
    AddNicUrl,
    JSON.stringify(nwInterfacePayload),
    header
  );
  console.log(`Add ${networkName} Nic response -> ${JSON.stringify(response, undefined, 4)}`);
  check(response, { "Data Network Interface is added": (r) => r.status === 202 });

  // In case of failure display the status message and status code.
  let responseBody = JSON.parse(response.body);
  if (response.status !== 202) {
    console.log(`StatusMessage is "${responseBody.StatusMessage}"`);
    console.log(response.status);
  }
  return response;
}
