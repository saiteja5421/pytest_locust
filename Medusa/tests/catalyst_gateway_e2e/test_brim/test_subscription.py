"""
Test case run backup job for all three backup types
"""
import logging
from pytest import fixture, mark
from tests.catalyst_gateway_e2e.test_context import SanityContext

from lib.common.users.api.subscription import Subscription

logger = logging.getLogger()


@fixture(scope="module")
def context():
    # pdb.set_trace()
    print("Context started")

    test_context = SanityContext()
    yield test_context
    logger.info(f"\n{'Teardown Start'.center(40, '*')}")
    # unassign_protecion_policy_from_vm(test_context)
    logger.info(f"\n{'Teardown Complete'.center(40, '*')}")


@mark.brim
@mark.order(3)
@mark.skip
def test_subscription_service(context):
    print("------------Test Subscription service-----------------")
    url = "https://scint-app.qa.cds.hpe.com/api/v1"

    sub_obj = Subscription(context.user)
    res_json = sub_obj.get_subscription(url)
    print(res_json)
    assert res_json["items"]
