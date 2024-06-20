import http from 'k6/http';
import { check, sleep } from 'k6';

export let options = {
    vus: 5,
    stages: [
      { duration: "30s", target: 1 },
      { duration: "30s", target: 3 },
      { duration: "30s", target: 5 },
      { duration: "30s", target: 5 },
      { duration: "30s", target: 4 },
      { duration: "30s", target: 2 },
      { duration: "30s", target: 0 },
    ],
    thresholds: {
      "RTT": ["avg<500"]
    },
    noConnectionReuse: true,
    noVUConnectionReuse: true,
    userAgent: "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/72.0.3626.121 Safari/537.36",
    // Don't save the bodies of HTTP responses by default, for improved performance
    // Can be overwritten by setting the `responseType` option to `text` or `binary` for individual requests
    discardResponseBodies: true,
    // ext: {
    //   loadimpact: {
    //     // Specify the distribution across load zones
    //     //
    //     // See https://docs.k6.io/docs/cloud-execution#section-cloud-execution-options
    //     //
    //     distribution: {
    //       loadZoneLabel1: { loadZone: "amazon:us:ashburn", percent: 50 },
    //       // Uncomment this and make sure percentage distribution adds up to 100 to use two load zones.
    //       loadZoneLabel2: { loadZone: "amazon:ie:dublin", percent: 50 }
    //     }
    //   }
    // }
  }

export default function () {
  let res = http.get('http://192.168.1.11:51878/api/v1/k8s-clusters');
  check(res, {
    'status is 200': (r) => r.status === 200
  });
  // console.log(res.body);
  sleep(1);
}

/*
# When using the `k6` docker image, you can't just give the script name since
# the script file will not be available to the container as it runs. Instead
# you must tell k6 to read `stdin` by passing the file name as `-`. Then you
# pipe the actual file into the container with `<` or equivalent. This will
# cause the file to be redirected into the container and be read by k6.

$ docker run -i loadimpact/k6 run - <get_all_clusters.js

$ docker run -i loadimpact/k6 run --vus 5 --duration 30s - <get_all_clusters.js

*/