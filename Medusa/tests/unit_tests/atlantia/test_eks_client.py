import logging

from pytest import fixture, mark
from tests.e2e.aws_protection.context import SanityContext
import lib.platform.kubernetes.kubernetes_client as K8Client
import tests.steps.aws_protection.eks.eks_common_steps as EKSCommonSteps

logger = logging.getLogger()

CLUSTER_CONFIG_YAML = "utils/eksctl/eks_cluster_config.yaml"
APP_CONFIG_YAML = "utils/eksctl/nginx_dynamic_volume.yaml"


@fixture(scope="module")
def context():
    context = SanityContext(set_static_policy=False)
    # Create an EKS cluster
    EKSCommonSteps.setup_eks_cluster(
        context=context,
        cluster_config_yaml=CLUSTER_CONFIG_YAML,
        app_config_yamls=[APP_CONFIG_YAML],
        cluster_timeout=1800,
        app_timeout=300,
    )
    (context.eks_cluster_name, context.eks_cluster_aws_region) = EKSCommonSteps.read_yaml_get_eks_cluster_info(
        CLUSTER_CONFIG_YAML
    )
    yield context
    logger.info(f"\n{'EKS cluster teardown Start'.center(40, '*')}")
    EKSCommonSteps.cleanup_eks_cluster(
        cluster_name=context.eks_cluster_name,
        aws_account_id=context.aws_eks_account_id,
        cluster_config_yaml=CLUSTER_CONFIG_YAML,
        need_asset_info=True,
    )
    logger.info(f"\n{'EKS cluster teardown Complete'.center(40, '*')}")


@mark.eks_sanity
@mark.order(100)
def test_kube_client_connect(context: SanityContext):
    client = K8Client.KubernetesClient()
    cl = client.get_eks_service_namespace("nginx-dynamic-ns")
