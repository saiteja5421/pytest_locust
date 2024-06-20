class IDNotFoundError(Exception):
    def __init__(self, name):
        self.message = f"{name} - not found in inventory!"
        super().__init__(self.message)


class VcenterNotFoundError(Exception):
    def __init__(self, name):
        self.message = f"Failed to find vCenter: {name}"
        super().__init__(self.message)


class NoSuitableVcenterFoundError(Exception):
    def __init__(self, excluded_vcenters, vcenter_names_for_usage):
        self.message = f"We didn't find any vcenter suitable for run!!! Excluded vcenters: {excluded_vcenters} and returned vcenters: {vcenter_names_for_usage}"
        super().__init__(self.message)


class BackupUsageNotFoundError(Exception):
    def __init__(self, name):
        self.message = f"Failed to find backup usage summary of {name}"
        super().__init__(self.message)


class BackupUsageCompareError(Exception):
    def __init__(self, error_array):
        self.message = f"Comparing usage summary failed with: {error_array}"
        super().__init__(self.message)


class StorageRescanError(Exception):
    def __init__(self, error_message):
        self.message = f"Resize request failed with error: {error_message}"
        super().__init__(self.message)


class NetworkInterfaceNotFoundError(Exception):
    def __init__(self):
        self.message = f"Network interface ID doesn't exists."
        super().__init__(self.message)


class UnusedIPNotFoundError(Exception):
    def __init__(self, *args: object):
        self.message = "All specified IPs are in use. Add more IPs to range in context or delete stale entries."
        super().__init__(*args)
