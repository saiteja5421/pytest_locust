import yaml

"""
This utility will extend the PyYAML libraries to support unknown tags that are
used in the below yaml file.

The cloud formation template that we use for setting up onboarded accounts: 
https://github.hpe.com/nimble-dcs/atlantia-cloud-account-manager/blob/master/build/cloudformation/configure-customer-roles.yaml
"""


class SafeLoaderIgnoreUnknown(yaml.SafeLoader):
    def ignore_unknown(self, node):
        return None


SafeLoaderIgnoreUnknown.add_constructor(None, SafeLoaderIgnoreUnknown.ignore_unknown)
