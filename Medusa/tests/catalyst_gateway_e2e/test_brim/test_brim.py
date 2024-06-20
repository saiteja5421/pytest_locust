import logging
from time import sleep
from pytest import fixture, mark

# from api.PSG.psg import ProtectionStoreGroup
from lib.common.enums.backup_type_schedule_ids import BackupTypeScheduleIDs
from lib.common.enums.provided_users import ProvidedUser

# from payloads.protection_group import PSG
# from api.bouncer.bouncer import Bouncer
from tests.catalyst_gateway_e2e.test_context import Context
from tests.steps.tasks import tasks
from requests import codes

logger = logging.getLogger()


brim_input = {
    "brimBackup": [
        {
            "account": "INGRAM MICRO ASIA TEST",
            "protectionJobId": "0ed5e6a8-d590-40de-ab2a-2452ee6c7faa",
            "waitTime": 600,
            "name": "PSG-INGRAM-1",
        },
        {
            "account": "INGRAM MICRO ASIA TEST",
            "protectionJobId": "44d2116c-e022-40f5-9605-843fa0a514c7",
            "waitTime": 600,
            "name": "PSG-INGRAM-2",
        },
        {
            "account": "BRIM2",
            "protectionJobId": "adad26a5-c2cf-4a4c-80ea-b7e44aa307ce",
            "waitTime": 600,
            "name": "PSG-1-BRIM2",
        },
    ]
}


@fixture(scope="module")
def brim2_context():
    # pdb.set_trace()
    print("Context started")
    brim2_test_context = Context(test_provided_user=ProvidedUser.user_two)
    yield brim2_test_context
    logger.info(f"\n{'Teardown Start'.center(40, '*')}")
    # unassign_protecion_policy_from_vm(test_context)
    logger.info(f"\n{'Teardown Complete'.center(40, '*')}")


@fixture(scope="module")
def ingram_context():
    # pdb.set_trace()
    print("Context started")
    ingram_test_context = Context(test_provided_user=ProvidedUser.user_one)
    yield ingram_test_context
    logger.info(f"\n{'Teardown Start'.center(40, '*')}")
    # unassign_protecion_policy_from_vm(test_context)
    logger.info(f"\n{'Teardown Complete'.center(40, '*')}")


def protectiongroup_backup_validate(protection_job_id, timeout, user):
    # user = User(user_obj)
    psg = ProtectionStoreGroup(user)
    response = psg.post_runbackupnow(protection_job_id, BackupTypeScheduleIDs.all)
    assert response.status_code == codes.accepted, f"{response.content}"
    # timeout=i['waitTime']
    task_id = tasks.get_task_id(response)
    print(f"task id {task_id}")
    status = tasks.wait_for_task(
        task_id,
        user,
        timeout,
        message=f"Backup creation time exceed {timeout / 60:1f} minutes - TIMEOUT",
    )
    assert status == "succeeded", f"Create backup using Protection group Task: {status}"


@mark.brim
@mark.order(10)
def test_run_backup_now_brim2(brim2_context):
    # Get Brim2 account context and Ingram account context
    # Take backup with BRIM2 user
    for i in brim_input["brimBackup"]:
        if i["account"] == "BRIM2":
            print("Backup for BRIM2")
            print(f"Take backup for user {i['account']} -> with {i['protectionJobId']}")
            protectiongroup_backup_validate(i["protectionJobId"], i["waitTime"], brim2_context.user)


@mark.brim
@mark.order(20)
def test_run_backup_now_ingram(ingram_context):
    # Get Brim2 account context and Ingram account context
    for i in brim_input["brimBackup"]:
        if i["account"] == "INGRAM MICRO ASIA TEST":
            print("Backup for INGRAM MICRO ASIA TEST")
            print(f"Take backup for user {i['account']} -> with {i['protectionJobId']}")
            protectiongroup_backup_validate(i["protectionJobId"], i["waitTime"], ingram_context.user)
            sleep(i["waitTime"])
            logger.info(
                f"wait for {i['waitTime']} seconds for cloud backup to complete. If successive backups are initiated consecutively then it will fail. so this wait time is added"
            )
