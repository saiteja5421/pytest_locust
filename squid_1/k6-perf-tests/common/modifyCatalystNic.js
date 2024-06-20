import { check } from "k6";
import { httpPost } from "./lib.js";
import { generateUpdateNicPayload } from "../payload_lib.js";

export function modifyCatalystNic(baseUri, catalystVM, newIpAddress, header) {
  const nwInterfacePayload = generateUpdateNicPayload(catalystVM, newIpAddress);

  console.debug(`header is ${JSON.stringify(header)}`);

  const url = `${baseUri}/api/v1/catalyst-gateways`;
  const modifyNicUrl = `${url}/${catalystVM.id}/updateNic`;
  let response = httpPost(
    modifyNicUrl,
    JSON.stringify(nwInterfacePayload),
    header
  );
  console.log(`Update Nic response -> ${JSON.stringify(response, undefined, 4)}`);
  check(response, { "IP is modified": (r) => r.status === 202 });

  // In case of failure display the status message and status code.
  let responseBody = JSON.parse(response.body);
  if (response.status !== 202) {
    console.log(`StatusMessage is "${responseBody.StatusMessage}"`);
    console.log(response.status);
  }
  return response;
}
