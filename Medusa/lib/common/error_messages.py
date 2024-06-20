ERROR_MESSAGE_GET_ALL_WITH_LIMIT = "^Request failed.*$"
ERROR_MESSAGE_CLUSTER_NOT_FOUND = "Cluster with specified ID not found"
ERROR_MESSAGE_INVALID_ARGUMENT = "Invalid argument passed in request"
ERROR_MESSAGE_VALUE_CANNOT_BE_EMPTY = ".*value cannot be empty$"
ERROR_MESSAGE_NAME_NOT_UNIQUE = "name is not unique"
ERROR_MESSAGE_PROTECTION_NAME_EXISTS = "Protection policy with same name"
ERROR_MESSAGE_PROTECTION_POLICY_NOT_FOUND = (
    "Created protection policy is not found in the list of protection policies retrieved from the cluster"
)
ERROR_MESSAGE_VM_MANAGER_FAILED = "error virtualization manager failed"
ERROR_MESSAGE_FEATURE_NOT_READY = "feature not ready for implementation"
ERROR_MESSAGE_CREATE_PSG_VM_EXISTS = "Protection Store Gateway name is not unique"
ERROR_MESSAGE_DISK_SIZE_ABOVE_MAX_ALLOWED = "disk size above maximum value"
UNREGISTER_OPE_FOUND_ASSOCIATED_PSG = (
    "Found associated Protection Store Gateway VMs.     Cannot proceed with unregistration."
)
ERROR_MESSAGE_FAILED_TO_DELETE_PRIMARY_NIC = "Error:  attempt to delete primary management network blocked"
ERROR_MESSAGE_NOT_VALID_NETWORK_DETAILS = (
    "Error:  validation of network config "
    "information failed: gateway address supplied is either not a valid ip "
    "address or is not in the same network as that of the ip address ("
    "determined using subnet mask and ip address)"
)
ERROR_MESSAGE_CANNOT_ADD_ANOTHER_NIC = (
    "all Protection Store Gateway networks are already configured - cannot add another"
)
ERROR_MESSAGE_CANNOT_CONFIGURE_NIC = "failed to configure VMWare network adapter to requested network"

# Modify NIC with duplicate IP
ERROR_MESSAGE_MODIFY_NIC_WITH_DUPLICATE_IP = (
    "failed to validate provided NIC information: duplicate network address provided"
)

# When PSG deployment is in-progress if we do Action operations we get below messages (E.g. Shutdown, powerON, etc.)
ERROR_MESSAGE_DEPLOY_PSGW_PERFORM_SHUTDOWN = (
    "Operation 'shutdown Protection Store Gateway' failed.*?Protection Store Gateway state is not 'OK'"
)
ERROR_MESSAGE_DEPLOY_PSGW_PERFORM_POWER_ON = (
    "Operation 'power on Protection Store Gateway' failed.*?Protection Store Gateway state is not 'OFF'"
)
ERROR_MESSAGE_DEPLOY_PSGW_PERFORM_RESTART = "Operation 'restart Protection Store Gateway' failed because of a bad \
request.*?Protection Store Gateway state is not 'OK'"
ERROR_MESSAGE_DEPLOY_PSGW_PERFORM_REMOTE_SUPPORT = (
    "Operation 'set Protection Store Gateway remote support' failed.*?gateway is not connected"
)
ERROR_MESSAGE_DEPLOY_PSGW_PERFORM_SUPPORT_BUNDLE = (
    "Operation 'generate Protection Store Gateway support bundle' failed.*?gateway is not connected"
)
ERROR_MESSAGE_DEPLOY_PSGW_PERFORM_CONSOLE_USER = "An internal error occurred"
ERROR_MESSAGE_ACTIVATION_OF_DUPLICATE_DATA_INTERFACE = "failed because it is already active on a system"
ERROR_MESSAGE_DURING_DEPLOYMENT = "Failed to register Protection Store Gateway."
# When PSGW VM already deleted from vcenter if we do Action operations we get below messages (E.g. Shutdown, powerON, \
# etc.)
ERROR_MESSAGE_RESTART_PSGW_AFTER_DELETED_FROM_VCENTER = (
    "Operation 'restart Protection Store Gateway' failed.*?Protection Store Gateway state is not 'OK'"
)
ERROR_MESSAGE_SHUTDOWN_PSGW_AFTER_DELETED_FROM_VCENTER = (
    "Operation 'shutdown Protection Store Gateway' failed.*?Protection Store Gateway state is not 'OK'"
)
ERROR_MESSAGE_DEPLOY_PSG_ALL_HOSTID_CLUSTERID_RESOURCEPOOLID = "failed to validate create Protection Store Gateway request: Json validation error: only one of HostID, ClusterID or resourcePool can be supplied"
ERROR_MESSAGE_DEPLOY_PSG_WITH_INVALD_CLUSTER_ID = "Cluster not found: error getting hypervisor cluster:"
ERROR_MESSAGE_DEPLOY_PSG_WITH_INVALD_RESOURCE_POOL_ID = (
    "Resource pool not found: error getting hypervisor resource pool:"
)
ERROR_MESSAGE_DEPLOY_PSG_WITH_INVALD_CONTENT_LIB_DATASTORE_ID = (
    "Content library not found: unexpected error calling grpc GetDatastore:"
)
ERROR_MESSAGE_DEPLOY_PSG_WITH_INVALD_FOLDER_ID = "Folder not found: error getting hypervisor folder: rpc error:"
# Deleting PSGW contains cloud backup data
ERROR_MESSAGE_DELETING_PSGW_CONTAINS_CLOUD_BACKUP = "Cannot delete store.*?as it contains data"
ERROR_MESSAGE_RECOVER_PSGW_WITH_INVALID_IP = "validation of network config information failed: gateway address \
supplied is not valid"
# inventory_manager
ERROR_MESSAGE_PROTECTION_GROUP_NOT_FOUND = "csp-protection-group was not found with ID:"
ERROR_MESSAGE_PROTECTION_GROUP_CONFLICT = (
    "operation not possible due to current state: protection group is associated with protection policy"
)

# backup
ERROR_MESSAGE_BACKUP = "backup finished with error. Do not know exact message."
ERROR_MESSAGE_FAILED_TO_CREATE_BACKUPS = "Cloud Service Provider Backup(s) creation failed"

# PSGW resize
ERROR_MESSAGE_EQUAL_SIZE = "new size must be larger than the existing"
ERROR_MESSAGE_MAX_PSGW_SIZE = "size must not be larger than 500 Tib"
ERROR_MESSAGE_RESCAN_FAILED = "Rescan failed."
ERROR_MESSAGE_CANNOT_RESIZE_PSGW_VM = "Expand storage failed"

# Size protection store gateway
ERROR_MESSAGE_CLOUD_DAILY_PROTECTED_DATA = "max daily protected in cloud data must be between 1 and 30"
ERROR_MESSAGE_INVALID_CLOUD_PRTCTD_DATA_FIELD_STRING = (
    "invalid type in input field maxInCloudDailyProtectedDataInTiB. Expected type float64, got type string"
)
ERROR_MESSAGE_CLOUD_RETENTION_DAYS = "max cloud retention days must be between 1 and 3650 inclusive"
ERROR_MESSAGE_INVALID_CLOUD_RTN_FIELD_STRING = (
    "invalid type in input field maxInCloudRetentionDays. Expected type int, got type string"
)
ERROR_MESSAGE_INVALID_CLOUD_RTN_FIELD_FLOAT = (
    "invalid type in input field maxInCloudRetentionDays. Expected type int, got type number"
)
ERROR_MESSAGE_ONPREM_DAILY_PROTECTED_DATA = "max daily protected on prem data must be between 1 and 100"
ERROR_MESSAGE_INVALID_ONPREM_PRTCTD_DATA_FIELD_STRING = (
    "invalid type in input field maxOnPremDailyProtectedDataInTiB. Expected type float64, got type string"
)
ERROR_MESSAGE_ONPREM_RETENTION_DAYS = "max on prem retention days must be between 1 and 2555 inclusive"
ERROR_MESSAGE_INVALID_ONPREM_RTN_FIELD_STRING = (
    "invalid type in input field maxOnPremRetentionDays. Expected type int, got type string"
)
ERROR_MESSAGE_INVALID_ONPREM_RTN_FIELD_FLOAT = (
    "invalid type in input field maxOnPremRetentionDays. Expected type int, got type number"
)

ERROR_MESSAGE_RECOVER_OK_CONNECTED_PSG = "Protection Store Gateway must be disconnected: Protection Store Gateway \
connection status must be disconnected before recover option is allowed."
# PSG Recover
ERROR_MESSAGE_DEPLOY_PSGW_PERFORM_RECOVER = "Operation 'Protection Store Gateway creation' failed because of a bad \
request.*? at least one cloud store must be fully configured for restore to be permitted"

# DEPLOY PSG WITH DATA NIC ONLY
ERROR_MESSAGE_DEPLOY_PSG_WITH_DATA_NIC_ONLY = "Operation 'Protection Store Gateway creation' failed because of a \
bad request.*?Error:  validation of network config information failed: gateway address supplied is not valid"

# override
ERROR_MESSAGE_OVERRIDE_CPU = "CPU must be between 2 and 48"
ERROR_MESSAGE_OVERRIDE_RAM = "RAM must be between 16 and 500"
ERROR_MESSAGE_OVERRIDE_STORAGE = "storage must be between 1 and 500"
ERROR_MESSAGE_ISUFFICIENT_DATASTORE_SPACE = (
    "create Protection Store Gateway request: Json validation error: not enough storage space"
)

# PSG Resize
ERROR_RESIZE_PSGW_EQUAL_STORAGE = "Error:  no change to PSG"
ERROR_RESIZE_PSGW_LESSER_STORAGE = "override storage must be larger or equal to the current size"

# StoreOnce error messages
ERROR_MESSAGE_INCORRECT_FORMAT_FOR_STOREONCE_USERNAME = (
    "Invalid fields [username: Incorrect format for StoreOnce username]"
)
ERROR_MESSAGE_STOREONCE_HAS_NO_VALID_LICENSE = "StoreOnce doesn't have valid encryption license"
ERROR_MESSAGE_STOREONCE_WITH_INVALID_SERIAL_NUMBER = (
    "Provided serial number doesn't match with the actual serial number"
)
ERROR_MESSAGE_STOREONCE_WITH_INVALID_PASSWORD = "Wrong password provided for DSCCAdmin user"
ERROR_MESSAGE_STOREONCE_WITH_INVALID_IPADDRESS_OR_FQDN = (
    "Couldn't find Data Orchestrator capable of establishing connection with StoreOnce"
)
ERROR_MESSAGE_STOREONCE_WITH_INVALID_UUID = "Couldn't find"
ERROR_MESSAGE_UNREGISTRING_STOREONCE_WITH_BACKUP = "while attempting to delete stores"
ERROR_MESSAGE_UNREGISTRING_STOREONCE_WITH_DUALAUTH = "Dual Auth enabled"


# Insufficient Previlage Error Messages
ERROR_MESSAGE_UNABLE_TO_UPDATE_VCENTER = "Unable to perform specified operation on vCenter server. Invalid user \
permissions. Details: Unable to update vCenter server. User .*? doesn't have the required permissions."
ERROR_MESSAGE_UNABLE_TO_REGISTER_VCENTER = "Unable to perform specified operation on vCenter server. Invalid user \
permissions. Details: Unable to register vCenter server. User .*? doesn't have the required permissions."
ERROR_MESSAGE_FOR_INSUFFICIENT_PREVILEGES_TASK = "User .*? doesn't have required privileges to manage Hypervisor."

# Update vCenter with invalid passowrd Error Message
ERROR_MESSAGE_UNABLE_TO_UPDATE_VCENTER_PASSWORD = "Unable to perform specified operation on vCenter server. Invalid vCenter \
credentials. Details: Unable to login to the vCenter server while performing update vCenter with the network address .*? using specified credentials."
ERROR_MESSAGE_FOR_TASK_TO_UPDATE_VCENTER_PASSWORD = (
    "Cannot complete vCenter login due to an incorrect user name or password."
)
ERROR_MESSAGE_GENERATE_SUPPORT_BUNDLE_WHEN_ALREADY_INPROGRESS = (
    "A log collection operation is already in progress. Please wait for the operation to complete and try again."
)
ERROR_MESSAGE_BACKUP_ON_PSG_AND_VM_ON_SAME_DATASTORE = (
    "The virtual machine is residing on a datastore which is having Protection Store Gateway."
)

# Protection store related
ERROR_MESSAGE_DELETE_PROTECTION_STORE_WITHOUT_PROTECTION_POLICY = "Failed to delete Protection Store. \
The Protection Store is a backup destination for one or more protection policies."
ERROR_MESSAGE_UPDATE_PROTECTION_STORE_WITH_SAME_NAME = (
    "Failed to update Protection Store. Protection Store .* already exists."
)
ERROR_MESSAGE_DELETE_PROTECTION_STORE_WITH_BACKUP_WITHOUT_USING_FORCE = "Unable to delete Protection Store without \
force. Protection Store contains user data. or Failed to delete Protection Store: Cannot delete store (cloud true) ?* contains user data (requires force option)"

# PSGW deployment with OVA upload
ERROR_MESSAGE_DEPLOY_PSGW_WHEN_UPLOAD_TO_CONTENT_LIBRARY_IS_ALREADY_IN_PROGRESS = "There is already a process \
downloading the file:.* Please re-try OVA deployment after sometime."

# PSG tooling connectivity
ERROR_MESSAGE_VALIDATING_PSGW_TOOLING_CONNECTIVITY_TO_INVALID_ADDRESS_TASK_FAILURE = (
    "Network debug result was not successful"
)
ERROR_MESSAGE_VALIDATING_PSGW_TOOLING_CONNECTIVITY_WHEN_PSGW_IS_IN_OFFLINE_STATE = (
    "Protection Store Gateway not connected"
)
ERROR_MESSAGE_VALIDATING_PSGW_TOOLING_CONNECTIVITY_TO_INVALID_ADDRESS_WITH_BAD_REQUEST = "invalid address"

# Backup job failed
ERROR_MESSAGE_VALIDATING_EXPIREAFTER_NOT_MORE_THAN_5_YEARS_WITH_lOCKFOR_VALUE_100_YEARS = "Failed to create or update snapshot. \
Invalid value for the input parameter. Details: The 'expireAfter' parameter can not exceed .*? days."

ERROR_MESSAGE_VALIDATING_EXPIREAFTER_5_YEARS_WITH_lOCKFOR_VALUE_100_YEARS = "Error in request body validation: Failed to perform specified operation.\
The parameter 'expireAfter': .*? cannot be less than the parameter 'lockFor': .*?. in body"

ERROR_MESSAGE_CREATE_CLOUD_STORAGE_LOCATION_ID = (
    "Failed to create Cloud Protection Store. Invalid value specified for 'storageLocationId'*?."
)
ERROR_MESSAGE_CREATE_CLOUD_STORAGE_LOCATION_ID_AS_EMPTY = "Failed to Create Cloud Protection Store. \
Required parameter 'region' or  'storageLocationId' is missing in the request body."
