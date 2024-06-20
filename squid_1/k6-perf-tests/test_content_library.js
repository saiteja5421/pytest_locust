import LibvSphareApi from './LibvSphareApi.js';

var testConfig = JSON.parse(open(__ENV.TEST_CONFIG));

export const options = {
  scenarios: {
    "create-catalyst-vm": {
      executor: "shared-iterations",
      vus: 2,
      iterations: 5,
      maxDuration: "10m",
    },
  },
};

export default function () {
  var vSphareApi = new LibvSphareApi(testConfig);
  let contentLibraryList = vSphareApi.getContentLibraryIds();
  for (const _id in contentLibraryList) {
    let contentLibrary = vSphareApi.getLibraryDetail(contentLibraryList[_id]);
    if (vSphareApi.contentLibraryName == contentLibrary.name){
      console.log(`Delete Content Library Name: ${contentLibrary.name}`);
      // vSphareApi.deleteContentLibrary(contentLibraryList[_id]);
    }
  }
}