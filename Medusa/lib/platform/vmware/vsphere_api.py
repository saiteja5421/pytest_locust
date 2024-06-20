import base64
from requests import codes
import json

from lib.common.common import get, post, delete


class VsphereApi:
    def __init__(self, vcenter_address, username, password):
        self.vcenter_address = vcenter_address
        self.username = username
        self.password = password
        self.vcenter = f"https://{vcenter_address}"
        self.session = "api/session"
        self.content_library = "api/content/local-library"
        self.vms_list = "api/vcenter/vm"
        self.token = self._generate_session_token()
        self.headers = {"Content-type": "application/json", "vmware-api-session-id": self.token}
        self.psgvm_network = "VM Network"

    def _generate_session_token(self):
        token: str = ""
        base64_bytes = base64.b64encode(":".join([self.username, self.password]).encode("ascii"))
        authorization = f"Basic {base64_bytes.decode('ascii')}"
        headers = {"Authorization": authorization}
        path = self.session
        response = post(self.vcenter, path, headers=headers)
        if response.status_code == codes.created:
            token = response.json()
        return token

    def _get_library_details(self, library_id):
        path = f"{self.content_library}/{library_id}"
        return get(self.vcenter, path, headers=self.headers)

    def _delete_content_library(self, library_id):
        path = f"{self.content_library}/{library_id}"
        return delete(self.vcenter, path, headers=self.headers)

    def _get_content_library_ids(self):
        content_path = self.content_library
        return get(self.vcenter, content_path, headers=self.headers)

    def _get_vms_list(self):
        vms_list = self.vms_list
        return get(self.vcenter, vms_list, headers=self.headers)

    def _get_vm_id(self, vm_name):
        """Get psgw_vm id eg: vm-1306.

        Args:
            psgw_name (str): protection store gateway name

        Returns:
            str: returns str, which contains psgw_vm id
        """
        vm_info = []
        vms_list = self._get_vms_list()
        if vms_list.status_code == codes.ok:
            vm_info = next(filter(lambda x: x["name"] == vm_name, vms_list.json()))
        else:
            assert False, "Failed to get vm list"
        return vm_info["vm"]

    def get_vm_network_nic(self, vm_name):
        """Get psgw_vm VM network details.

        Args:
            psgw_name (str): protection store gateway name

        Returns:
            str: returns str, which contains vm network nic, vm id and vm nic state
        """
        vm_id = self._get_vm_id(vm_name)
        vm_info_path = f"api/vcenter/vm/{vm_id}"
        vm_info = get(self.vcenter, vm_info_path, headers=self.headers)
        if vm_info.status_code == codes.ok:
            vm_details = vm_info.json()
            for key, value in vm_details["nics"].items():
                if value["backing"]["network_name"] == self.psgvm_network:
                    vm_network_nic = key
                    vm_network_state = value["state"]
        else:
            assert False, "Failed to get psg_vm details"
        return vm_network_nic, vm_id, vm_network_state

    def disconnect_vm_nic(self, vm_name):
        """Perform disconnect of psgw_vm vm network nic.

        Args:
            psgw_name (str): protection store gateway name

        Returns:
            str: returns str, which contains message of disconnect action result
        """
        vm_network_nic, vm_id, vm_network_state = self.get_vm_network_nic(vm_name)
        vm_disconnect_path = f"api/vcenter/vm/{vm_id}/hardware/ethernet/{vm_network_nic}?action=disconnect"
        response = post(self.vcenter, vm_disconnect_path, headers=self.headers)
        message = ""
        if response.status_code == codes.no_content:
            message = f"Disconnect of psg_vm successfull"
        else:
            assert False, "Disconnect of psg_vm failed"
        return message

    def reconnect_vm_nic(self, vm_name):
        """Perform reconnect of psgw_vm vm network nic.

        Args:
            psgw_name (str): protection store gateway name

        Returns:
            str: returns str, which contains message of reconnect action result
        """
        vm_network_nic, vm_id, vm_network_state = self.get_vm_network_nic(vm_name)
        vm_reconnect_path = f"api/vcenter/vm/{vm_id}/hardware/ethernet/{vm_network_nic}?action=connect"
        response = post(self.vcenter, vm_reconnect_path, headers=self.headers)
        message = ""
        if response.status_code == codes.no_content:
            message = f"Reconnect of psg_vm successfull"
        else:
            assert False, "Reconnect of psg_vm failed"
        return message

    def clear_content_library(self, library_name):
        delete = True
        message = f"{library_name} content library not found in vCenter {self.vcenter}"
        library_ids = self._get_content_library_ids()
        library_ids = library_ids.json()
        if library_ids:
            for library_id in library_ids:
                library = self._get_library_details(library_id)
                if library.status_code == codes.ok:
                    library = library.json()
                    if library["name"] == library_name:
                        response = self._delete_content_library(library_id)
                        if response.status_code == codes.no_content:
                            message = f"Cleared content library {library_name} from vCenter {self.vcenter}"
                        else:
                            message = f"Failed to delete content library {library_name} - {response.content}"
                            delete = False
                        break
        return (delete, message)

    def get_content_lib_datastore_obj(self, library_name):
        library_ids = self._get_content_library_ids()
        library_ids = library_ids.json()
        if library_ids:
            for library_id in library_ids:
                library = self._get_library_details(library_id)
                if library.status_code == codes.ok:
                    library = library.json()
                    if library["name"] == library_name:
                        datastore_obj = library["storage_backings"][0]["datastore_id"]
                        return datastore_obj

    def relocate_vm_datastore(self, vm_name, datastore_obj):
        vm_obj = self._get_vm_id(vm_name)
        payload = json.dumps({"placement": {"datastore": datastore_obj}})
        vm_relocate = f"api/vcenter/vm/{vm_obj}?action=relocate"
        response = post(
            self.vcenter,
            vm_relocate,
            json_data=payload,
            headers=self.headers,
        )
        assert response.status_code == codes.no_content, f"Failed to relocate the  psgw vm{vm_name}"
