import logging
import time
from lib.common.enums.ec2_username import EC2Username
from tests.e2e.aws_protection.context import Context
from lib.common.enums.io_types import IOType
from lib.platform.aws_boto3.remote_ssh_manager import RemoteConnect
from lib.platform.host.io_manager import IOManager
from lib.platform.host.vdbench_config_models import (
    BasicParameters,
    StorageDefinitions,
    WorkloadDefinitions,
    RunDefinitions,
)
from json import loads

logger = logging.getLogger()


def run_dd_command(context: Context, instance, run_type="full"):
    io_manager = _create_remote_connect(context=context, instance=instance)
    devices = io_manager.get_devices()
    # Fill disk with zeros and random data sequentially.
    if run_type.lower() == "full":
        _run_dd_for_full_backup(devices=devices, io_manager=io_manager)
    # Overwrite the existing data in the data block with alternative.
    # Incremental backup does not necessarily increase the backup size.
    elif run_type.lower() == "incremental":
        _run_dd_for_synthetic_backup(devices=devices, io_manager=io_manager)
    io_manager.client.close_connection()


def _run_dd_for_full_backup(devices: list[str], io_manager: IOManager):
    for device in devices:
        io_manager.execute_dd_command(fill=IOType.RANDOM.value, device=device, block_size="1M", count=2048)
        io_manager.execute_dd_command(
            fill=IOType.ZERO.value,
            device=device,
            block_size="1M",
            count=2048,
            seek=2100,
        )
        io_manager.execute_dd_command(
            fill=IOType.RANDOM.value,
            device=device,
            block_size="512",
            count=1000,
            seek=4500,
        )
        io_manager.execute_dd_command(
            fill=IOType.ZERO.value,
            device=device,
            block_size="512",
            count=1000,
            seek=5600,
        )


def _run_dd_for_synthetic_backup(devices: list[str], io_manager: IOManager):
    for device in devices:
        io_manager.execute_dd_command(fill=IOType.ZERO.value, device=device, block_size="512", count=1024)
        io_manager.execute_dd_command(
            fill=IOType.RANDOM.value,
            device=device,
            block_size="512",
            count=1024,
            seek=2100,
        )
        io_manager.execute_dd_command(fill=IOType.ZERO.value, device=device, block_size="1M", count=500, seek=4500)
        io_manager.execute_dd_command(
            fill=IOType.RANDOM.value,
            device=device,
            block_size="1M",
            count=500,
            seek=5600,
        )


# TODO: DEPRECATED , same function exists in common_steps.py
def _create_remote_connect(context: Context, instance, source_instance):
    public_dns_name = instance.public_dns_name

    ec2_instance = source_instance if source_instance else instance
    user_name: str = EC2Username.get_ec2_username(ec2_instance=ec2_instance)

    for i in range(5):
        try:
            remote_client = RemoteConnect(
                instance_dns_name=public_dns_name, username=user_name, key_filename=context.key_pair
            )
            break
        except Exception as e:
            seconds = 120 + i * 120
            time.sleep(seconds)
            logger.warn(f"Create ssh client retry: {i}, Error: {e}")

    io_manager = IOManager(context=context, client=remote_client)
    return io_manager


def copy_vdbench_executable_to_ec2_instance(io_manager: IOManager):
    # NOTE: use CommonSteps.connect_to_ec2_instance to create an instance of IOManager
    io_manager.copy_vdbench_executable_to_remote_host()


def install_java_in_remote_host(io_manager: IOManager):
    """Install java in ec2 instance using yum/apt command"""
    # NOTE: use CommonSteps.connect_to_ec2_instance to create an instance of IOManager
    io_manager.install_java_in_remote_host()


def copy_vdbench_custom_config_file_to_ec2_instance(io_manager: IOManager):
    """Copy vdbench config file to ec2 instance"""

    io_manager.copy_vdbench_custom_config_file_to_remote_host()


def create_vdbench_config_file_in_ec2_instance(context: Context, io_manager: IOManager):
    """Create vdbench config file in ec2 instance

    Args:
        context (Context): context object
        io_manager (IOManager): IOManager object
    """
    devices = io_manager.get_devices()
    config_path = context.vdbench_config_path
    basic_content = list()
    sd_content = list()
    wd_content = list()
    rd_content = list()
    for serial, device in enumerate(devices, start=1):
        config = {"basic": {}, "sd": {}, "wd": {}, "rd": {}}
        storage_definition = context.sd % (serial, device)
        workload_definition = context.wd % (serial, serial)
        run_definition = context.rd % serial
        if serial == 1:
            config["basic"].update(
                loads(
                    BasicParameters(
                        comp_ratio=f"compratio={context.compratio}",
                        validate=f"validate={context.validate}",
                        dedup_ratio=f"dedupratio={context.dedupratio}",
                        dedup_unit=f"dedupunit={context.dedupunit}\n",
                    ).to_json()
                )
            )
            config["sd"].update(loads(StorageDefinitions(storage_definition=storage_definition).to_json()))
            config["wd"].update(loads(WorkloadDefinitions(workload_definition=workload_definition).to_json()))
            config["rd"].update(loads(RunDefinitions(run_definition=run_definition).to_json()))
            basic_content.extend(list(config["basic"].values()))
            sd_content.extend(list(config["sd"].values()))
            wd_content.extend(list(config["wd"].values()))
            rd_content.extend(list(config["rd"].values()))
        else:
            config["sd"].update(loads(StorageDefinitions(storage_definition=storage_definition).to_json()))
            config["wd"].update(loads(WorkloadDefinitions(workload_definition=workload_definition).to_json()))
            config["rd"].update(loads(RunDefinitions(run_definition=run_definition).to_json()))
            sd_content.extend(list(config["sd"].values()))
            wd_content.extend(list(config["wd"].values()))
    content = basic_content + sd_content + wd_content + rd_content
    content = [line + "\n" for line in content]
    io_manager.create_vdbench_config_in_ec2_instance(remote_file=config_path, content=content)
    io_manager.client.close_connection()


def create_vdbench_config_file_for_generating_files_and_dirs(
    context: Context,
    file_size,
    file_count,
    dir_name,
    depth,
    width,
    io_manager: IOManager,
):
    # NOTE: use CommonSteps.connect_to_ec2_instance to create an instance of IOManager

    devices = io_manager.get_devices()
    config_path = f"{io_manager.home_directory}/config"
    basic_content = list()
    fsd_content = list()
    fwd_content = list()
    frd_content = list()
    for serial in range(1, len(devices) + 1):
        config = {"basic": {}, "fsd": {}, "fwd": {}, "frd": {}}
        storage_definition = context.fsd % (serial, dir_name, depth, width, file_count, file_size)
        workload_definition = context.fwd % (serial, serial, "$operation")
        run_definition = context.frd % (serial, "$format")
        if serial == 1:
            config["basic"].update(
                loads(
                    BasicParameters(
                        comp_ratio=f"compratio={context.compratio}",
                        validate=f"validate={context.validate}",
                        dedup_ratio=f"dedupratio={context.dedupratio}",
                        dedup_unit=f"dedupunit={context.dedupunit}\n",
                    ).to_json()
                )
            )
            config["fsd"].update(loads(StorageDefinitions(storage_definition=storage_definition).to_json()))
            config["fwd"].update(loads(WorkloadDefinitions(workload_definition=workload_definition).to_json()))
            config["frd"].update(loads(RunDefinitions(run_definition=run_definition).to_json()))
            basic_content.extend(list(config["basic"].values()))
            fsd_content.extend(list(config["fsd"].values()))
            fwd_content.extend(list(config["fwd"].values()))
            frd_content.extend(list(config["frd"].values()))
        else:
            config["fsd"].update(loads(StorageDefinitions(storage_definition=storage_definition).to_json()))
            config["fwd"].update(loads(WorkloadDefinitions(workload_definition=workload_definition).to_json()))
            config["frd"].update(loads(RunDefinitions(run_definition=run_definition).to_json()))
            fsd_content.extend(list(config["fsd"].values()))
            fwd_content.extend(list(config["fwd"].values()))
            frd_content.extend(list(config["frd"].values()))
    content = basic_content + fsd_content + fwd_content + frd_content
    content = [line + "\n" for line in content]
    io_manager.create_vdbench_config_in_ec2_instance(remote_file=config_path, content=content)


def run_vdbench(io_manager: IOManager, validate=False, custom_config_file_name="config"):
    success_message = "Vdbench execution completed successfully"
    channel = io_manager.client.client.get_transport().open_session()
    if validate:
        channel.exec_command(
            "sudo ./vdbench -jro -f %s format=%s operation=%s" % (custom_config_file_name, "no", "read")
        )
    else:
        channel.exec_command(
            "sudo ./vdbench -j -f %s format=%s operation=%s " % (custom_config_file_name, "yes", "write")
        )
    result = False
    while True:
        buffer = channel.recv(1024)
        if not buffer:
            break
        if success_message in str(buffer):
            result = True
            break
    io_manager.client.close_connection()
    return result
