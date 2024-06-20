from lib.dscc.backup_recovery.aws_protection.assets import ec2
from lib.dscc.backup_recovery.aws_protection import backups
import logging


def backup_ec2_instance(ec2_instance_id):
    csp_machine_dict = ec2.get_csp_machine(ec2_instance_id)
    csp_machine_id = csp_machine_dict["id"]

    logging.info(f"--------- Take a backup for the instance created-------")
    (
        protection_policy_id,
        protection_job_id,
    ) = backups.create_csp_machine_instance_backup(ec2_instance_id)

    logging.info(f"---Step 4: Fetch the backup created recently---")
    csp_machine = ec2.get_csp_machine(ec2_instance_id)
    csp_machine_id = csp_machine["id"]
    latest_backup = backups.get_recent_backup(csp_machine_id)

    return {
        "ec2_instance_id": ec2_instance_id,
        "csp_machine": csp_machine,
        "protection_policy_id": protection_policy_id,
        "protection_job_id": protection_job_id,
        "latest_backup": latest_backup,
    }


def backup_ec2_instance_for_given_policy(ec2_instance_id, protection_policy_id, protection_policy_name, protections_id):
    csp_machine_dict = ec2.get_csp_machine(ec2_instance_id)
    csp_machine_id = csp_machine_dict["id"]

    logging.info(f"--------- Take a backup for the instance created-------")
    (
        protection_policy_id,
        protection_job_id,
    ) = backups.create_csp_machine_instance_backup_for_given_protection_policy(
        ec2_instance_id, protection_policy_id, protection_policy_name, protections_id
    )

    logging.info(f"---Step 4: Fetch the backup created recently---")
    csp_machine = ec2.get_csp_machine(ec2_instance_id)
    csp_machine_id = csp_machine["id"]
    latest_backup = backups.get_recent_backup(csp_machine_id)

    return {
        "ec2_instance_id": ec2_instance_id,
        "csp_machine": csp_machine,
        "protection_policy_id": protection_policy_id,
        "protection_job_id": protection_job_id,
        "latest_backup": latest_backup,
    }
