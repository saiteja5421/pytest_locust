## Users in tests

- USER-ONE is treated as the default user

- USER-TWO is a user working on the same vCenter as USER-ONE

- USER-THREE is a user working on a different vCenter than both - USER-ONE and USER-TWO

## Test Data block

`TEST-DATA-FOR-{particular_user}` should be modified accordingly to reflect user's preferences.

## Variable ini data changes
> CLUSTER block - SHOULD NOT BE MODIFIED unless application is changed (e.g. atlaspoc -> atlaspoc2)

> USER-{number_in_words} blocks - should be modified with user's credentials and CID

> DATA-ORCHESTRATORS - should be changed accordingly to deployed data orchestrators
>- hostname_prefix - prefix for every DO deployed by API test

> VCENTER{number_in_digits} blocks - should be changed when using different vCenters than default
>- ip - based on test infrastructure https://confluence.eng.nimblestorage.com/pages/viewpage.action?spaceKey=WIQ&title=Test+Infrastructure+for+Atlas+Service+1
>- username - based on test infrastructure https://confluence.eng.nimblestorage.com/pages/viewpage.action?spaceKey=WIQ&title=Test+Infrastructure+for+Atlas+Service+1
>- username_read_only_privilege - username for account with read-only priviliges to VSPHERE
>- username_non_admin_privilege - username for account with non-admin priviliges to VSPHERE
>- password - based on test infrastructure https://confluence.eng.nimblestorage.com/pages/viewpage.action?spaceKey=WIQ&title=Test+Infrastructure+for+Atlas+Service+1
>- esxi_host - esxi host address placed on vCenter
>- esxi_username - should be modified with user's credentials
>- esxi_password - should be modified with user's credentials
>- datastore - according to vCenter used by particular user. Example: ca29-oct12vc67124-ds1
>- datastore_62tb - according to vCenter used by particular user. Example: ca29-oct12vc67124-ds2

> ATLAS-API block - SHOULD NOT BE CHANGED as are global constants for rest api calls

> TEST-DATA-FOR-USER-{number_in_words} blocks - should be changed 
>- psgw_name - (unique) name of Protection Store Gateway to be created in given Test Case
>- gateway - based on test infrastructure https://confluence.eng.nimblestorage.com/pages/viewpage.action?spaceKey=WIQ&title=Test+Infrastructure+for+Atlas+Service+1
>- network - based on test infrastructure https://confluence.eng.nimblestorage.com/pages/viewpage.action?spaceKey=WIQ&title=Test+Infrastructure+for+Atlas+Service+1
>- netmask - based on test infrastructure https://confluence.eng.nimblestorage.com/pages/viewpage.action?spaceKey=WIQ&title=Test+Infrastructure+for+Atlas+Service+1
>- dns - based on test infrastructure https://confluence.eng.nimblestorage.com/pages/viewpage.action?spaceKey=WIQ&title=Test+Infrastructure+for+Atlas+Service+1
>- dns2 - based on test infrastructure https://confluence.eng.nimblestorage.com/pages/viewpage.action?spaceKey=WIQ&title=Test+Infrastructure+for+Atlas+Service+1
>- ntp_server_address - based on test infrastructure https://confluence.eng.nimblestorage.com/pages/viewpage.action?spaceKey=WIQ&title=Test+Infrastructure+for+Atlas+Service+1
>- policy_name - name of the Protection Policy
>- network_name - for testing purpose should be set to "VM Network"
>- network_type - for testing purpose should be set to STATIC
>- proxy - based on test infrastructure https://confluence.eng.nimblestorage.com/pages/viewpage.action?spaceKey=WIQ&title=Test+Infrastructure+for+Atlas+Service+1
>- port - based on test infrastructure https://confluence.eng.nimblestorage.com/pages/viewpage.action?spaceKey=WIQ&title=Test+Infrastructure+for+Atlas+Service+1
>- secondary_psgw_ip - based on test infrastructure https://confluence.eng.nimblestorage.com/pages/viewpage.action?spaceKey=WIQ&title=Test+Infrastructure+for+Atlas+Service+1

> SANITY - components required for sanity tests. Should be changed if needed.
>- sanity_vm - virtual machine name used in sanity tests
>- sanity_policy = name for Protection Policy used in sanity tests
>- static_policy = name for static Protection Policy (shouldn't be deleted from vCenter)
>- static_psgw = name for static Protection Store Gateway (shouldn't be deleted from vCenter)
>- sanity_psgw = name for Protection Store Gateway used in sanity tests
>- sanity_vcenter - vCenter that should be used for sanity tests

> CONTENT-LIBRARY - should be changed accordingly to the content library on vCenters
>- content_library - name of content library on each vCenter