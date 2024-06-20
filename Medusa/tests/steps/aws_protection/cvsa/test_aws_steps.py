import pytest
from unittest import mock
import tests.steps.aws_protection.cvsa.cloud_steps as aws_steps


@pytest.mark.parametrize(
    "all_amis, expected_newest_ami",
    [
        [
            [
                {"Name": "atlantia-cvsa-v4.3.3.2238.11-dae85fd82b366e91851d167f0ccf12c3-1663590993"},
                {
                    "Name": "atlantia-cvsa-v4.3.3-2238.11-cbe49dc961e828ac5501db0e30e34e1752fcac19dfb04f11db0f3431d6b9d279"
                },
                {
                    "Name": "atlantia-cvsa-v4.3.3-2246.30-ebdcd84e51aa69d205484d72576ae08e345ab69991c2d62f5b322746e4b83685"
                },
            ],
            "4.3.3-2246.30-ebdcd84e51aa69d205484d72576ae08e345ab69991c2d62f5b322746e4b83685",
        ],
        [
            [
                {"Name": "atlantia-cvsa-v4.3.3-2238.11-dae85fd82b366e91851d167f0ccf12c3-1663590993"},
                {"Name": "atlantia-cvsa-v4.3.3.2246.30-ebdcd84e51aa69d205484d72576ae08e-45ab69991c"},
            ],
            "4.3.3-2246.30-ebdcd84e51aa69d205484d72576ae08e-45ab69991c",
        ],
    ],
)
@mock.patch("tests.steps.aws_protection.cvsa.cvsa_manager_steps.get_all_amis_for_environment")
@mock.patch("tests.steps.aws_protection.cvsa.cvsa_manager_steps.get_cvsa_version")
def test_verify_newest_ami_with_success(get_cvsa_version, get_all_amis_for_environment, all_amis, expected_newest_ami):
    get_all_amis_for_environment.return_value = all_amis
    get_cvsa_version.return_value = expected_newest_ami
    aws_steps.verify_newest_ami(mock.MagicMock(), "test-cam-id")


@pytest.mark.parametrize(
    "all_amis, instance_ami",
    [
        [
            [
                {"Name": "atlantia-cvsa-v4.3.3-2238.11-dae85fd82b366e91851d167f0ccf12c3-1663590993"},
                {"Name": "atlantia-cvsa-v4.3.3.2246.30-ebdcd84e51aa69d205484d72576ae08e-45ab69991c"},
            ],
            "4.3.3-2238.11-dae85fd82b366e91851d167f0ccf12c3-1663590993",
        ],
        [[], "4.3.3-2246.30-ebdcd84e51aa69d205484d72576ae08e-45ab69991c"],
        [
            [
                {"Name": "atlantia-cvsa-invalid-version"},
            ],
            "4.3.3-2246.30-ebdcd84e51aa69d205484d72576ae08e-45ab69991c",
        ],
    ],
)
@mock.patch("tests.steps.aws_protection.cvsa.cvsa_manager_steps.get_all_amis_for_environment")
@mock.patch("tests.steps.aws_protection.cvsa.cvsa_manager_steps.get_cvsa_version")
def test_verify_newest_ami_with_error(get_cvsa_version, get_all_amis_for_environment, all_amis, instance_ami):
    get_all_amis_for_environment.return_value = all_amis
    get_cvsa_version.return_value = instance_ami

    with pytest.raises(AssertionError):
        aws_steps.verify_newest_ami(mock.MagicMock(), "test-cam-id")
