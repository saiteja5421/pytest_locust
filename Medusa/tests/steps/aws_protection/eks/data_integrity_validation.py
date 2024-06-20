import logging
from lib.dscc.backup_recovery.aws_protection.eks.domain_models.csp_k8s_model import CSPK8sResourcesListModel
from lib.platform.kubernetes.kubernetes_client import KubernetesClient
from tests.e2e.aws_protection.context import Context
from tests.steps.aws_protection.eks.csp_eks_inventory_steps import get_csp_k8s_cluster_by_name, get_csp_k8s_resources

logger = logging.getLogger()


def validate_restored_cluster_resources_dscc(context: Context, resources_before_backup: CSPK8sResourcesListModel):
    """Validate if the list of kubernetes resources after restore is the same as before backup.
    Check length of resource lists and their fields.

    Args:
        context (Context): Context object
        resources_before_backup (CSPK8sResourcesListModel): list of kubernetes resources before taking a backup.
    """
    cluster_info = get_csp_k8s_cluster_by_name(context, context.eks_cluster_name, context.eks_cluster_aws_region)
    resources_after_restore_list = get_csp_k8s_resources(context, cluster_info.id).items
    resources_before_backup_list = resources_before_backup.items
    num_of_resrcs_before_backup = len(resources_before_backup_list)
    num_of_resrcs_after_restore = len(resources_after_restore_list)
    assert (
        num_of_resrcs_before_backup == num_of_resrcs_after_restore
    ), f"The amount of resources differs after the restore. Before backup: {num_of_resrcs_before_backup}, after backup: {num_of_resrcs_after_restore}"
    logger.debug(
        f"Resources before backup: {resources_before_backup_list} \n Resources after restore: {resources_after_restore_list}"
    )

    for item_index in range(num_of_resrcs_after_restore):
        resrc_before_backup = resources_before_backup_list[item_index]
        resrc_after_backup = resources_after_restore_list[item_index]
        assert resrc_before_backup.compare_static_values(resrc_after_backup), "Resources changed after restore."


def write_data_and_generate_checksum_kube_pod(
    pod_name: str,
    namespace: str,
    mount_path: str = "",
    filename: str = "test_file.dat",
    file_size_in_gb: int = 1,
) -> str:
    """Write generated file with random content to kubernetes pod and generate checksum.
    Args:
        pod_name (str): kubernetes pod name where file is written.
        namespace (str): kubernetes namespace where provided pod is placed.
        mount_path (str): path where file will be written.
        filename (str): name of the file that will be written on pod.
        file_size_in_gb (int): declares number of gb for generated file.
    Returns:
        str: Checksum value
    """
    kubernetes_client = KubernetesClient()
    logger.info(f"Writing data into pod {pod_name}")
    filepath = f"{mount_path}/{filename}"
    command_create_file = f"dd if=/dev/random of={filepath} bs=1M count={file_size_in_gb * 1000}"
    kubernetes_client.pod_command_exec(pod_name, namespace, command_create_file)
    command_checksum = f"cksum {filepath}"
    response = kubernetes_client.pod_command_exec(pod_name, namespace, command_checksum)
    checksum_value = response.split()[0]
    return checksum_value


def read_data_and_verify_checksum_kube_pod(
    pod_name: str,
    namespace: str,
    checksum_before_backup: str,
    mount_path: str = "",
    filename: str = "test_file.dat",
):
    """Verify the checksum before the backup and the checksum after the restore.
    Args:
        pod_name (str): kubernetes pod name where checksum is read from.
        namespace (str): kubernetes namespace where provided pod is placed.
        mount_path (str): path where file will be written.
        filename (str): name of the file that will be written on pod.
        checksum_before_backup (str): checksum taken before backup which is validated with checksum after restore.
    """
    kubernetes_client = KubernetesClient()
    logger.info(f"Reading data and verifying checksum on pod {pod_name}")
    filepath = f"{mount_path}/{filename}"
    command = f"cksum {filepath}"
    response = kubernetes_client.pod_command_exec(pod_name, namespace, command)
    checksum_after_restore = response.split()[0]
    assert checksum_before_backup == checksum_after_restore, "Checksum changed after restore."
