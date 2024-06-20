import json
import os
from os.path import join
from jsonschema import validate


def assert_valid_schema(data, schema_file):
    """Checks whether the given data matches the schemas"""

    schema = _load_json_schema(schema_file)
    return validate(data, schema)


def _load_json_schema(filename: str):
    """Loads the given schemas file
    Make sure to run the pytest from ~/k8s-cluster-mgr-tests directory.
    Example:
    ➜  k8s-cluster-mgr-tests git:(master) ✗ pytest -svra
    tests/functional-tests/restapi-tests/test_scripts/test_post_cluster.py
    """

    schemas = join(os.getcwd() + "/catalyst_gateway_e2e/schemas", filename)

    with open(schemas) as file:
        return json.loads(file.read())
