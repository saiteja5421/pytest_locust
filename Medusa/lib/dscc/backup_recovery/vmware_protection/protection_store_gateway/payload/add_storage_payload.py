from json import dumps


class AddStoragePayload:
    payload = {}

    def __init__(
        self,
        datastore_info,
        total_size_tib,
    ):
        self.datastore_info = datastore_info
        self.total_size_tib = total_size_tib

    def create(self):
        datastoreList = []
        for datastore in self.datastore_info:
            datastoreList.append(datastore)
        self.payload = {"datastoreIds": datastoreList, "totalSizeTib": self.total_size_tib}
        return dumps(self.payload)
