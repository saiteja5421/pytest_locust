import logging
import time
from lib.dscc.backup_recovery.aws_protection.assets import ec2
from lib.dscc.backup_recovery.protection import protection_policy, protection_job


def create_and_assign_protection_policy(ec2_instance_id, backup_only: bool = True):
    cloud_protection_id: str = ""
    protection_policy_id, protection_policy_name, protections_id, cloud_protection_id = create_protection_policy(
        backup_only=backup_only
    )

    protection_job_id, csp_machine_id, protection_policy_id = assign_protection_policy(
        ec2_instance_id,
        protection_policy_id=protection_policy_id,
        protection_policy_name=protection_policy_name,
        protections_id=protections_id,
        backup_only=backup_only,
    )
    if backup_only:
        return protection_job_id, csp_machine_id, protection_policy_id
    else:
        return protection_job_id, csp_machine_id, protection_policy_id, cloud_protection_id


def create_protection_policy(backup_only: bool = True):
    response = protection_policy.create_protection_policy(backup_only=backup_only)

    if backup_only:
        protection_policy_id, protection_policy_name, protections_id = (
            response["id"],
            response["name"],
            response["protections"][0]["id"],
        )
        return protection_policy_id, protection_policy_name, protections_id
    else:
        protection_policy_id, protection_policy_name, protections_id, cloud_protection_id = (
            response["id"],
            response["name"],
            response["protections"][0]["id"],
            response["protections"][1]["id"],
        )
        return protection_policy_id, protection_policy_name, protections_id, cloud_protection_id


def assign_protection_policy(
    ec2_instance_id,
    protection_policy_id,
    protection_policy_name,
    protections_id,
    backup_only: bool = True,
    cloud_protection_id: str = "",
):
    csp_machine_dict = ec2.get_csp_machine(ec2_instance_id)
    logging.info(f"EC2 Instance ID: {ec2_instance_id}")
    logging.info(f"CSP EC2: {csp_machine_dict}")
    csp_machine_id = csp_machine_dict["id"]
    logging.info(f"EC2 Instance ID: {ec2_instance_id}, CSP Instance ID: {csp_machine_id}")

    if not backup_only:
        # cloud_protection_id = protection_policy_id
        logging.info(
            f"Creating protection job for EC2 instance {ec2_instance_id} with Protection Policy {protection_policy_name} ({protection_policy_id}), using Protection ID {protections_id} and {cloud_protection_id}"
        )
        protection_job.create_protection_job(
            asset_id=csp_machine_id,
            protections_id_one=protections_id,
            protections_id_two=cloud_protection_id,
            protection_policy_id=protection_policy_id,
        )
    else:
        logging.info(
            f"Creating protection job for EC2 instance {ec2_instance_id} with Protection Policy {protection_policy_name} ({protection_policy_id}), using Protection ID {protections_id}"
        )
        protection_job.create_protection_job(
            asset_id=csp_machine_id, protections_id_one=protections_id, protection_policy_id=protection_policy_id
        )
    protection_job_id = None
    retry_count = 5
    while protection_job_id is None and retry_count > 0:
        protection_job_id = protection_job.get_protection_job_id(csp_machine_id)
        if protection_job_id:
            logging.info(
                f"Protection job id of protection policy is {protection_policy_name} and It is assigned to EC2 {ec2_instance_id}"
            )
            return protection_job_id, csp_machine_id, protection_policy_id
        logging.info(
            "Unable to get Protection job id of protection policy is {protection_policy_name} assigned to EC2 {ec2_instance_id}, retrying the operation to obtain protection_job_id"
        )
        retry_count -= 1
        time.sleep(1)
    logging.error(
        "Unable to get Protection job id of protection policy is {protection_policy_name} assigned to EC2 {ec2_instance_id} after 5 retries"
    )
