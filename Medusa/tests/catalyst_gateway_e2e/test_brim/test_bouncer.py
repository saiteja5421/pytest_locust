"""
Test case run backup job for all three backup types
"""
import logging
from pytest import fixture, mark
from lib.common.users.api.bouncer import Bouncer
from tests.catalyst_gateway_e2e.test_context import SanityContext


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
@mark.order(10)
def test_bouncer_service(context):
    print("----------Test Bouncer service ------------------")
    url = "https://scint-app.qa.cds.hpe.com"
    sub_obj = Bouncer(context.user)
    res_json = sub_obj.get_subscription(url)
    print(res_json)
    assert res_json["allowed"] == False
