from pytest import fixture
from tests.catalyst_gateway_e2e.test_context import Context
from tests.steps.vm_protection.common_steps import perform_cleanup_old_protection_store


@fixture(scope="module")
def context():
    test_context = Context()
    yield test_context


def test_perform_cleanup_old_protection_store(context):
    perform_cleanup_old_protection_store(context)
