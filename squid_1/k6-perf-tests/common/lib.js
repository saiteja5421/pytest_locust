import http from "k6/http";
import { check, sleep } from "k6";
import encoding from "k6/encoding";
// import {globalToken} from "./backup_restore_workflow.js";
var configFilePath = `../${__ENV.TEST_CONFIG}`;
var testConfig = JSON.parse(open(configFilePath));
var baseUri = testConfig.testbed.atlasOptions.baseUri;
var globalToken = undefined;
var tokenUri = testConfig.testbed.atlasOptions.tokenUri;
let accountObj = testConfig.testbed.accountOptions

/**
 * generateToken and store it in globalToken variable.
 * If expiryTime is over ,it will generate new token else send the old token again.
 * @param {number} expiryTime How long the token should be reused
 * @returns token
 */
function generateToken(account, expiryTime = 60) {
  try {
    if (globalToken == undefined) {
      globalToken = getToken(account);
    } else {
      //let token = getToken();
      const isTimesUp = isTokenTimeout(globalToken, expiryTime);
      if (isTimesUp) {
        console.log("Generate new token");
        globalToken = getToken(account);
      }
    }
    return globalToken;
  } catch (error) {
    console.error("Error occurred in generateToken");
    throw error;
  }
}

function isTokenTimeout(token, expiryTime) {
  let parsedToken = parseJwt(token);
  console.debug(JSON.stringify(parsedToken, undefined, 4));
  // let exp = JSON.parse(parsedToken)
  console.debug(`expiry time ${parsedToken.exp * 1000}`);
  console.debug(Date.now());
  let timediff = parsedToken.exp * 1000 - Date.now();
  let validity = timediff / 1000 / 60;
  const maxValidity = 120;
  let expectedValidity = maxValidity - expiryTime;
  const isTimesUp = validity < expectedValidity;
  return isTimesUp;
}

function generateAccountToken(account) {

  let token = newToken(account)
  return token;
}

function getToken(accountObj, retries = 3) {
  let retry = 1;
  let headers = {
    headers: {
      "content-type": "application/x-www-form-urlencoded",
    },
    params: {
      timeout: '120s',
    },
  };
  const tokenUri = "https://sso.common.cloud.hpe.com/as/token.oauth2";
  const requestBody = {
    grant_type: 'client_credentials',
    client_id: accountObj.clientId,
    client_secret: accountObj.clientSecret
  };
  var formRequestBody = [];
  for (var property in requestBody) {
    var encodedKey = encodeURIComponent(property);
    var encodedValue = encodeURIComponent(requestBody[property]);
    formRequestBody.push(encodedKey + "=" + encodedValue);
  }
  formRequestBody = formRequestBody.join("&");
  let token = undefined;
  while (true) {
    let token_response = http.post(
      tokenUri,
      formRequestBody,
      headers,
    ); //call to get the token

    console.debug(`Token response status => ${token_response.status}`);

    if (token_response.status === 200) {
      // @ts-ignore
      token = JSON.parse(token_response.body)["access_token"];
      if (token !== undefined) {
        check(token, { "Token is not empty": (t) => t !== undefined });
        return token;
      }
    }
    retry = retry + 1;
    if (retry > retries) {
      console.error(`Maximum retry attempts [${retries}] are over`);
      check(token, {
        "Failed to get token even after retries": (t) => t == undefined,
      });
      throw `Unable to get token after [${retries}] attempts`;
    }
    console.log("[getToken] => Wait 10 seconds and then retry");
    sleep(10);
  }
}

function newToken(accountObj, retries = 3) {
  let retry = 1;
  let headers = {
    headers: {
      "content-type": "application/x-www-form-urlencoded",
    },
  };
  const tokenUri = "https://sso.common.cloud.hpe.com/as/token.oauth2";
  const requestBody = {
    grant_type: 'client_credentials',
    client_id: accountObj.clientId,
    client_secret: accountObj.clientSecret
  };
  var formRequestBody = [];
  for (var property in requestBody) {
    var encodedKey = encodeURIComponent(property);
    var encodedValue = encodeURIComponent(requestBody[property]);
    formRequestBody.push(encodedKey + "=" + encodedValue);
  }
  formRequestBody = formRequestBody.join("&");
  let token = undefined;
  while (true) {
    let token_response = http.post(
      tokenUri,
      formRequestBody,
      headers
    ); //call to get the token

    console.debug(`Token response status => ${token_response.status}`);

    if (token_response.status === 200) {
      // @ts-ignore
      token = JSON.parse(token_response.body)["access_token"];
      if (token !== undefined) {
        check(token, { "Token is not empty": (t) => t !== undefined });
        return accountObj['token'] = token;
      }
    }
    retry = retry + 1;
    if (retry > retries) {
      console.error(`Maximum retry attempts [${retries}] are over`);
      check(token, {
        "Failed to get token even after retries": (t) => t == undefined,
      });
      throw `Unable to get token after [${retries}] attempts`;
    }
    console.log("[getToken] => Wait 10 seconds and then retry");
    sleep(10);
  }
}

function parseJwt(token) {
  try {
    console.debug(`[parseJwt]=> token is => ${token}`);
    var base64Url = token.split(".")[1];
    console.debug(`[parseJwt]=> ${base64Url}`);
    var jsonPayload = decodeURIComponent(
      encoding
        .b64decode(base64Url, "rawurl", "s")
        .split("")
        .map(function (c) {
          return "%" + ("00" + c.charCodeAt(0).toString(16)).slice(-2);
        })
        .join("")
    );

    return JSON.parse(jsonPayload);
  } catch (error) {
    console.error("Error occurred in parseJwt");
    throw error;
  }
}

export function list_protectiongateway() {
  // let token = getToken();
  // console.debug(`Bearer ${token.bearerToken}`);
  let atlasHeader = generateHeader();

  let response = httpGet(`${baseUri}/api/v1/protection-store-gateways`, atlasHeader);
  return response;
}

// Get protection store gateway with the given prefix
export function getProtectionStoreVMList(vmNamePrefix) {
  let res = list_protectiongateway();
  check(res, {
    "[func]lib.js => list protection store gateway => status was 200": (r) =>
      r.status === 200,
  });
  // console.log(JSON.stringify(res))
  // @ts-ignore
  let body = JSON.parse(res.body);
  console.log(JSON.stringify(body));
  console.log(`Number of gateway VMs available are ${body.items.length}`);
  let vmList = [];

  body.items.forEach((element) => {
    if (element.datastoreIds.length != 0) {
      if (element.name == vmNamePrefix) {
        vmList.push(element);
      }
    }
  });
  // console.log(`psgw List is ${psgwList}`)
  return vmList;
}

/**
 * generate header object with bearer token
 * @returns headers object with bearer token
 */
export function generateHeader(account = "HPE_Catalyst", expiryTime = 60) {
  account = accountObj[account]
  var header = generateHeaderByAccount(account, expiryTime);
  return header
}

export function generateHeaderByAccount(accountObj, expiryTime = 60) {
  try {
    var token = undefined
    if (accountObj['token'] == undefined) {
      token = generateAccountToken(accountObj);
      accountObj['token'] = token;
    }
    else if (isTokenTimeout(accountObj['token'], expiryTime)) {
      token = generateAccountToken(accountObj);
      accountObj['token'] = token;
    }
    else {
      token = accountObj['token']
    }
    var header = {
      headers: {
        "Content-Type": "application/json",
        authorization: `Bearer ${token}`,
      },
    };
    console.debug(`Header is ${JSON.stringify(header)}`);
    return header;
  }
  catch (error) {
    console.error("Error occured in generateHeaderByAccount");
    throw error;
  }
}

/**
 * http.get wrapper with retries option
 * @param {string} url
 * @param {object} params headers object
 * @param {number} retryCount number of times retries
 * @returns
 */
export function httpGet(url, params, retryCount = 10) {
  var res;
  for (var retries = retryCount; retries > 0; retries--) {
    res = http.get(url, params);
    // Status 0 will be returned for Connection reset by peer or for request timeout
    // As of now it seems as proxy issue, so we are doing retries.
    if (res.status == 0) {
      // connection reset and request timeout will return status 0
      console.log("Response is 0");
      console.warn(`Response status is ${res.error}`);
      console.warn(`Response is ${JSON.stringify(res)}`);
    } else {
      return res;
    }
    console.warn(
      `Iteration -> ${retries - 1
      } pending. As request is failed wait for 30 seconds and retry`
    );
    sleep(30);
  }
  return res;
}

/**
 * http.get wrapper with retries option
 * @param {string} url
 * @param {string} body JSON string
 * @param {object} params headers object
 * @param {number} retryCount number of times retries
 * @returns
 */
export function httpPost(url, body, params, retryCount = 10) {
  var res;
  for (var retries = retryCount; retries > 0; retries--) {
    res = http.post(url, body, params);
    // Status 0 will be returned for Connection reset by peer or for request timeout
    // As of now it seems as proxy issue, so we are doing retries.
    if (res.status == 0) {
      // connection reset and request timeout will return status 0
      console.log("Response is 0");
      console.warn(`Response status is ${res.error}`);
      console.warn(`Response is ${JSON.stringify(res)}`);
    } else {
      return res;
    }
    console.warn(
      `Iteration -> ${retries - 1
      } pending. As request is failed wait for 30 seconds and retry`
    );
    sleep(30);
  }
  return res;
}


/**
 * http.del wrapper with retries option
 * @param {string} url
 * @param {string} body JSON string [Optional]
 * @param {object} params headers object [Optional]
 * @param {number} retryCount number of times retries [Optional]
 * @returns
 */
export function httpDelete(url, body, params, retryCount = 10) {
  var res;
  for (var retries = retryCount; retries > 0; retries--) {
    res = http.del(url, body, params);
    // Status 0 will be returned for Connection reset by peer or for request timeout
    // As of now it seems as proxy issue, so we are doing retries.
    if (res.status == 0) {
      // connection reset and request timeout will return status 0
      console.log("Response is 0");
      console.warn(`Response status is ${res.error}`);
      console.warn(`Response is ${JSON.stringify(res)}`);
    } else {
      return res;
    }
    console.warn(
      `Iteration -> ${retries - 1
      } pending. As request is failed wait for 30 seconds and retry`
    );
    sleep(30);
  }
  return res;
}


/**
 * http.patch wrapper with retries option
 * @param {string} url
 * @param {string} body JSON string
 * @param {object} params headers object
 * @param {number} retryCount number of times retries
 * @returns
 */
export function httpPatch(url, body, params, retryCount = 10) {
  var res;
  for (var retries = retryCount; retries > 0; retries--) {
    res = http.patch(url, body, params);
    // Status 0 will be returned for Connection reset by peer or for request timeout
    // As of now it seems as proxy issue, so we are doing retries.
    if (res.status == 0) {
      // connection reset and request timeout will return status 0
      console.log("Response is 0");
      console.warn(`Response status is ${res.error}`);
      console.warn(`Response is ${JSON.stringify(res)}`);
    } else {
      return res;
    }
    console.warn(
      `Iteration -> ${retries - 1
      } pending. As request is failed wait for 30 seconds and retry`
    );
    sleep(30);
  }
  return res;
}


/**
 * There are static ip within the range ipMin and ipMax.
 * Pick one of them randomly
 */
export function getRandomIPWithinRange(ipPrefix, ipMin, ipMax) {
  let ipMaxLastDigit = Number.parseInt(ipMax);
  let ipMinLastDigit = Number.parseInt(ipMin);
  let randomIP =
    Math.floor(Math.random() * (ipMaxLastDigit - ipMinLastDigit)) +
    ipMinLastDigit;
  // let vuSequence=__VU + __ITER *concurrentUsers -1
  let ipAddress = `${ipPrefix}${randomIP}`;
  console.log(`New IP address is ${ipAddress}`);
  return ipAddress;
}

/**
 * wait for task to be completed. IF the task status is SUCCEEDED ,it will return as true.
 * For other states it will return as false.
 * @param {string} taskUrl task url
 * @param {number} waitTime wait time for task to complete
 * @returns
 */
export function waitForTask(taskUrl, waitTime, header) {
  if (taskUrl.endsWith("undefined")) {
    throw `WaitForTask => Task Url ${taskUrl} is invalid`
  }
  if (header == undefined) {
    var header = generateHeader();
  }
  let startTime = new Date();
  let durationTaken = 0;
  let retryCount = 0;
  while (true) {
    console.log(`Waiting for task ${taskUrl}`);
    let taskRes = httpGet(taskUrl, header);
    console.log(`WaitForTask => Task status is ${taskRes.status}`);
    if (taskRes.status === 200) {
      // @ts-ignore
      var body = JSON.parse(taskRes.body);
      const taskState = body.state;
      console.log(`WaitForTask => Task state is ${taskState}`);
      if (taskState === "SUCCEEDED") {
        console.log(`Task is completed. Time taken is ${durationTaken}`);
        return true;
      } else if (taskState === "FAILED") {
        console.error(
          `WaitForTask => Task ${taskUrl} is failed . status is ${taskState}. Duration taken is ${durationTaken}`
        );
        console.error(`${JSON.stringify(body.error)} ${JSON.stringify(body.error)}`);
        console.error(`[WaitForTask] => ${JSON.stringify(body.logMessages)}`);
        // return false;
        throw `[WaitForTask] => ${JSON.stringify(body.logMessages)}`
      } else if (taskState === "RUNNING" || taskState === "INITIALIZED") {
        if (durationTaken > waitTime) {
          console.log(
            `[waitForTask]=> Times up -> duration taken is ${durationTaken} greater than wait time ${waitTime}. task state is ${taskState}`
          );
          // return false;
          throw `Times up -> duration taken is ${durationTaken} greater than wait time ${waitTime}. task state is ${taskState}`
        }
      } else {
        console.log(
          `[waitForTask]-> duration taken is ${durationTaken} and state is ${taskState}`
        );
        continue;
      }
    } else if (taskRes.status === 403) {
      // To skip forbidden issue which sometimes occurs.
      console.warn(`[waitForTask]-> Task status is ${taskRes.status}`);
      continue;
    } else if (taskRes.status === 500) {
      // Run intermittently experiancing 500 error with INTERNAL_ERROR code. Defect: SC-8356
      // As a workaround added here retry for couple of times.
      var res_content = JSON.parse(taskRes.body);
      if (retryCount < 20 && res_content.errorCode === 'INTERNAL_ERROR') {
        retryCount++;
        console.error(`Known issue: SC-8356; Retrying[${retryCount}]..`);
        sleep(10);
        continue;
      } else {
        throw `WaitForTask => Task status is ${taskRes.status} => Task response content ${JSON.stringify(res_content)}`;
      }
    } else {
      console.error(`WaitForTask => Task status is ${taskRes.status} => Task Log message ${JSON.stringify(body.logMessages)}`);
      throw `WaitForTask => Task status is ${taskRes.status} => Task Log message ${JSON.stringify(body.logMessages)}`;
    }
    durationTaken = parseInt(new Date() - startTime) / 1000;
    console.log("[waitForTask]-> Sleep 30 seconds before continue");
    sleep(30);
  }
}

// List datastores
export function list_datastore() {
  let genHeader = generateHeader();
  let response = http.get(`${baseUri}/api/v1/datastores?limit=1000`, genHeader);
  console.log(`Datastore List: ${JSON.stringify(response)}`);
  return response;
}
