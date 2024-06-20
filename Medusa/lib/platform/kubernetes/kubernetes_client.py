import logging
from kubernetes import client, config
from kubernetes.stream import stream
import os
import requests

from tests.steps.aws_protection.eks.eks_common_steps import run_ctl_command

logger = logging.getLogger()


class KubernetesClient:
    def __init__(self):
        kube_config = os.environ.get("KUBECONFIG", "~/.kube/config")
        proxy_url = os.environ.get("http_proxy")
        self.config = config.load_kube_config(config_file=kube_config)
        if proxy_url:
            logger.info("Setting proxy: {}".format(proxy_url))
            client.Configuration._default.proxy = proxy_url
        self.api_instance = client.CoreV1Api()
        self.network_api_instance = client.NetworkingV1Api()
        self.apps_v1_api = client.AppsV1Api()
        self.storage_v1_api = client.StorageV1Api()
        self.rbac_authorization_v1_api = client.RbacAuthorizationV1Api()

    def pod_command_exec(self, pod_name: str, namespace: str, command: str) -> str:
        """Execute bash command on provided kubernetes pod.
        Args:
            pod_name (str): kubernetes pod name where command is executed.
            namespace (str): kubernetes namespace where provided pod is placed.
            command (str): bash command to execute on kubernetes pod.
        Returns:
            str: The read of stdout or stderr depends on returncode after command execution.
        """
        exec_command = ["/bin/sh", "-c", command]
        response = None
        logger.debug(f"Executing command {command} on pod {pod_name} within {namespace} namespace.")
        resp = stream(
            self.api_instance.connect_get_namespaced_pod_exec,
            pod_name,
            namespace,
            command=exec_command,
            stderr=True,
            stdin=False,
            stdout=True,
            tty=False,
            _preload_content=False,
        )

        while resp.is_open():
            resp.update(timeout=1)
            if resp.peek_stdout():
                response = f"{resp.read_stdout()}"
                logger.debug(f"STDOUT: \n{response}")
            if resp.peek_stderr():
                response = resp.read_stderr()
                logger.debug(f"STDERR: \n{resp.read_stderr()}")
        resp.close()

        if resp.returncode != 0:
            raise Exception(f"Script failed with stderr: {response}")

        logger.debug(f"Successfully executed command {command} on pod {pod_name} within {namespace} namespace.")
        return response

    def get_configmap_for_all_namespaces(self) -> dict:
        """This method returns a JSON format object with configmap for all namespaces available in a region.

        Returns:
            dict: A dictionary (JSON) format response containing all details of the list of configmaps. It is of type 'V1ConfigMapList'. It contains the following arguments:
                    api_version - The versioned schema of this representation of an object.
                    items - list of ConfigMap objects.
                    kind - A string value representing the REST resource this object represents.
                    metadata - some metadata associated with the response. It is optional.

        """
        try:
            config_map_list = self.api_instance.list_config_map_for_all_namespaces()
            logger.info(f"Config Map List being returned here -> {config_map_list}")
            return config_map_list

        except Exception as e:
            logger.error("Exception occurred while executing list_config_map_for_all_namespace: %s \n" % e)

    def get_namespaced_config_map(self, namespace: str) -> dict:
        """This method returns a dictionary(JSON) object containing details of configmap for a specific namespace in a region.

        Args:
            namespace (str): The namespace whose configmaps are returned.

        Returns:
            dict: A dictionary (JSON) format response containing all details of the configmaps associated with the namespace. It is of type 'V1ConfigMapList'. It contains the following arguments:
                    api_version - The versioned schema of this representation of an object.
                    items - list of ConfigMap objects.
                    kind - A string value representing the REST resource this object represents.
                    metadata - some metadata associated with the response. It is optional.
        """
        try:
            namespaced_config_map = self.api_instance.list_namespaced_config_map(namespace=namespace)
            logger.info(f"Config Map for the namespace '{namespace}' is -> {namespaced_config_map}")
            return namespaced_config_map
        except Exception as e:
            logger.error("Exception occurred while executing list_namespaced_config_map: %s\n" % e)

    def get_namespaces(self) -> dict:
        """This method returns a list of all the namespaces in a region.

        Returns:
            dict: A dictionary (JSON) format response containing list of namespaces. It is of type 'V1NamespaceList'. It contains attributes as follows:
                    api_version - APIVersion defines the versioned schema of this representation of an object.
                    items - Items is a list of all the namespaces.
                    kind - Kind is a string  value representing  the REST resource this object represnts.
                    metadata - optional set of data associated with the response.
        """
        try:
            namespace_list = self.api_instance.list_namespace()
            logger.debug(f"Namespace being returned here -> {namespace_list}")
            return namespace_list
        except Exception as e:
            logger.error("Exception occurred while executing list_namespace: %s\n" % e)

    def get_eks_deployments_namespace(self, namespace: str) -> dict:
        """This method returns a list of all the deployments in a region for the namespace.
        Returns:
            dict: A dictionary (JSON) format response containing list of namespaces. It is of type 'V1NamespaceList'. It contains attributes as follows:
                    api_version - APIVersion defines the versioned schema of this representation of an object.
                    items - Items is a list of all the namespaces.
                    kind - Kind is a string  value representing  the REST resource this object represnts.
                    metadata - optional set of data associated with the response.
        """
        try:
            deployments_list = self.apps_v1_api.list_namespaced_deployment(namespace=namespace)
            logger.debug(f"Deployments {deployments_list} are in the Namespac {namespace}")
            return deployments_list
        except Exception as e:
            logger.error("Exception occurred while executing list_namespaced_deployment: %s\n" % e)

    def get_eks_service_namespace(self, namespace: str) -> dict:
        """This method returns a list of all the services in a region for the namespace.
        Returns:
            dict: A dictionary (JSON) format response containing list of namespaces. It is of type 'V1NamespaceList'. It contains attributes as follows:
                    api_version - APIVersion defines the versioned schema of this representation of an object.
                    items - Items is a list of all the namespaces.
                    kind - Kind is a string  value representing  the REST resource this object represnts.
                    metadata - optional set of data associated with the response.
        """
        try:
            services_list = self.api_instance.list_namespaced_service(namespace=namespace)
            logger.debug(f"Deployments {services_list} are in the Namespace {namespace}")
            return services_list
        except Exception as e:
            logger.error("Exception occurred while executing list_namespaced_service: %s\n" % e)

    def get_eks_storage_class(self, namespace: str) -> dict:
        """This method returns a list of all the storage class in a region for the namespace.
        Returns:
            dict: A dictionary (JSON) format response containing list of namespaces. It is of type 'V1NamespaceList'. It contains attributes as follows:
                    api_version - APIVersion defines the versioned schema of this representation of an object.
                    items - Items is a list of all the namespaces.
                    kind - Kind is a string  value representing  the REST resource this object represnts.
                    metadata - optional set of data associated with the response.
        """
        try:
            storage_class_list = self.storage_v1_api.list_storage_class()
            logger.info(f"Storage classes are created {storage_class_list} ")
            return storage_class_list
        except Exception as e:
            logger.error("Exception occurred while executing list_storage_class: %s\n" % e)

    def get_eks_all_ns_deployments(self) -> dict:
        """This method returns a list of all the deployments in a region for all the namespaces.

        Returns:
            dict: A dictionary (JSON) format response containing list of namespaces. It is of type 'V1NamespaceList'. It contains attributes as follows:
                    api_version - APIVersion defines the versioned schema of this representation of an object.
                    items - Items is a list of all the namespaces.
                    kind - Kind is a string  value representing  the REST resource this object represnts.
                    metadata - optional set of data associated with the response.
        """
        try:
            all_ns_deployments_list = self.apps_v1_api.list_deployment_for_all_namespaces()
            logger.debug(f"Deployments {all_ns_deployments_list} are all the Namespaces")
            return all_ns_deployments_list
        except Exception as e:
            logger.error("Exception occurred while executing list_deployment_for_all_namespaces: %s\n" % e)

    def get_k8s_list_pods_namespace(self, namespace: str) -> dict:
        """This method returns a list of all the pods in a region for the namespaces.

        Returns:
            dict: A dictionary (JSON) format response containing list of namespaces. It is of type 'V1NamespaceList'. It contains attributes as follows:
                    api_version - APIVersion defines the versioned schema of this representation of an object.
                    items - Items is a list of all the namespaces.
                    kind - Kind is a string  value representing  the REST resource this object represnts.
                    metadata - optional set of data associated with the response.
        """
        try:
            pods_list = self.api_instance.list_namespaced_pod(namespace)
            logger.debug(f"List of pods {pods_list} for the name space -> {namespace}")
            return pods_list
        except Exception as e:
            logger.error("Exception occurred while executing list_namespaced_pod: %s\n" % e)

    def get_k8s_list_replicaset_namespace(self, namespace: str) -> dict:
        """This method returns a list of all the replicaset in a region for the namespaces.

        Returns:
            dict: A dictionary (JSON) format response containing list of namespaces. It is of type 'V1NamespaceList'. It contains attributes as follows:
                    api_version - APIVersion defines the versioned schema of this representation of an object.
                    items - Items is a list of all the namespaces.
                    kind - Kind is a string  value representing  the REST resource this object represnts.
                    metadata - optional set of data associated with the response.
        """
        try:
            replica_set_list = self.apps_v1_api.list_namespaced_replica_set(namespace)
            logger.debug(f"List of replicaset {replica_set_list} for the name space -> {namespace}")
            return replica_set_list
        except Exception as e:
            logger.error("Exception occurred while executing list_namespaced_replica_set: %s\n" % e)

    def get_persistent_volume_claim_for_all_namespace(self) -> dict:
        """This method returns all the persistent volume claims by the user across all namespaces in a region.

        Returns:
            dict: A dictionary (JSON) format response containing list of all persistent volume calims by the user across all namespaces. It is of the type 'V1PersistentVolumeClaimList'. It contains the following attributes:
                    api_version - APIVersion defines the versioned schema of this representation of an object.
                    items - It is a list of all persistent volume claims.
                    kind - Kind is a string value representing the REST resource this object represents.
                    metadata - Set of optional data associated with the response.
        """
        try:
            persistent_volume_claim = self.api_instance.list_persistent_volume_claim_for_all_namespaces()
            logger.debug(f"Persistent Volume Claim Data returned here is -> {persistent_volume_claim}")
            return persistent_volume_claim
        except Exception as e:
            logger.error("Exception occurred while executing list_persistent_volume_claim_for_all_namespace: %s\n" % e)

    def get_persistent_volumes_for_all_namespace(self) -> list:
        """This method reurns all PVs across all namespaces in cluster.

        Returns:
            list: list of persistent volumes objects
        """
        try:
            persistent_volumes = self.api_instance.list_persistent_volume()
            logger.debug(f"Persistent Volume Claim Data returned here is -> {persistent_volumes}")
            return persistent_volumes
        except Exception as e:
            logger.error("Exception occurred while executing list_persistent_volume: %s\n" % e)

    def get_persistent_volumes_for_namespace(self, namespace: str):
        """This method return PVs for provided namespace.

        Args:
            namespace (str): namespace to get persistent volumes from

        Returns:
            str: persistent volume name
        """
        pvs = self.get_persistent_volumes_for_all_namespace()
        pv_names = [item.metadata.name for item in pvs.items if item.spec.claim_ref.namespace == namespace]
        return pv_names

    def get_secret_for_all_namespace(self) -> dict:
        """This method returns secret for all namespaces present in a region.

        Returns:
            dict: A dictionary (JSON) format response containing list of all secrets for all namespaces. It is of the type 'V1SecretList'. It contains attributes:
                    api_version -  APIVersion defines the versioned schema of this representation of an object.
                    items - list of all secret objects.
                    kind - Kind is a string value representing the REST resource this object represents.
                    metadata - set of optional data associated with the response data.
        """
        try:
            secret_for_all_namespace = self.api_instance.list_secret_for_all_namespaces()
            logger.debug(f"List of secret for all namespaces being returned is -> {secret_for_all_namespace}")
        except Exception as e:
            logger.error("Exception occurred while executing list_secret_for_all_namespaces: %s\n" % e)

    def get_ingress_class(self) -> dict:
        """This method returns a list of all the ingress classes in a region.

        Returns:
            dict: A dictionary (JSON) format response containing all ingress classes. It is of the type 'V1IngressClassList'. It contains arguments:
                    api_version - APIVersion defines the versioned schema of this representation of an object.
                    items - List of Ingress classes
                    kind - Kind is a string value representing the REST resource this object represents.
                    metadata - set of optional data associated with the response data.
        """
        try:
            ingress_class = self.network_api_instance.list_ingress_class()
            logger.debug(f"Ingress Class being returned here is -> {ingress_class}")
            return ingress_class
        except Exception as e:
            logger.error("Exception occurred while executing list_ingress_class: %s\n" % e)

    def get_ingress_class_for_all_namespaces(self) -> dict:
        """This method returns ingress classes for all namespaces in a region.

        Returns:
            dict: A dictionary (JSON) format response containing ingress classes across all namespaces. It is of the type 'V1IngressList'. It contains attributes such as:
                    api_version - APIVersion defines the versioned schema of this representation of an object.
                    items - List of Ingress classes
                    kind - Kind is a string value representing the REST resource this object represents.
                    metadata - set of optional data associated with the response data.
        """
        try:
            ingress_class_for_all_namespaces = self.network_api_instance.list_ingress_for_all_namespaces()
            logger.debug(
                f"Ingress Class List for all namespaces being returned is -> {ingress_class_for_all_namespaces}"
            )
            return ingress_class_for_all_namespaces
        except Exception as e:
            logger.error("Exception occurred while executing list_ingress_class_for_all_namespaces: %s\n" % e)

    def get_namespaced_ingress(self, namespace: str) -> dict:
        """This method returns ingress classes for a specific namespace in a region

        Args:
            namespace (str): The name of the namespace whose ingress classes is to be returned as response.

        Returns:
            dict: A dictionary (JSON) format response containing ingress classes for a specified namespace name. It is of the type 'V1IngressList'. It contains the following attributes:
                    api_version - APIVersion defines the versioned schema of this representation of an object.
                    items - List of Ingress classes
                    kind - Kind is a string value representing the REST resource this object represents.
                    metadata - set of optional data associated with the response data.
        """
        try:
            namespaced_ingress = self.network_api_instance.list_namespaced_ingress(namespace=namespace)
            logger.debug(f"Ingress for namespace '{namespace}' is -> {namespaced_ingress}")
            return namespaced_ingress
        except Exception as e:
            logger.error("Exception occurred while executing list_namespaced_ingress: %s\n" % e)

    def get_current_cluster_context(self) -> str:
        """Gets the current EKS cluster context name

        Returns:
            str: current cluster context name, if found. Otherwise None
        """
        try:
            # Get the current context
            current_context = config.list_kube_config_contexts()[1]
            logger.debug(f"current context set to: {current_context}")
            return current_context["name"]
        except Exception as e:
            logger.error(f"Error, while getting the current context: {e}")
            return None

    def get_available_cluster_contexts(self) -> list:
        """Get the list of available cluster contexts

        Returns:
            list: returns cluster contexts list, if found. Otherwisr []
        """
        try:
            # Get the list of available contexts
            contexts, _ = config.list_kube_config_contexts()
            cluster_contexts_list = [context["name"] for context in contexts]
            logger.debug(f"List of cluster contexts: {cluster_contexts_list}")
            return cluster_contexts_list
        except Exception as e:
            logger.error(f"Error while getting available contexts: {e}")
            return []

    def delete_k8s_service_namespace(self, namespace: str):
        """This method delete the services in a region for the given namespace.
        Returns:
            dict: A dictionary (JSON) format response containing list of namespaces. It is of type 'V1NamespaceList'. It contains attributes as follows:
                    api_version - APIVersion defines the versioned schema of this representation of an object.
                    items - Items is a list of all the namespaces.
                    kind - Kind is a string  value representing  the REST resource this object represnts.
                    metadata - optional set of data associated with the response.
        """
        try:
            self.api_instance.delete_collection_namespaced_service(namespace=namespace)
            logger.debug(f"successfully deleted service in the Namespace {namespace}")
        except Exception as e:
            logger.error("Exception occurred while executing delete_collection_namespaced_service: %s\n" % e)

    def get_eks_namespaced_config_map(self, namespace: str):
        """This method returns ConfigMapList containing a list of ConfigMap objects for the specified namespace.
        Returns:
            V1ConfigMapList: A ConfigMapList is a resource containing a list of ConfigMap objects. It contains attributes as follows:
                    api_version - APIVersion defines the versioned schema of this representation of an object.
                    items - Items is the list of ConfigMaps.
                    kind - Kind is a string value representing the REST resource this object represents.
                    metadata - optional set of data associated with the response.
        """
        try:
            configMap_obj = self.api_instance.list_namespaced_config_map(namespace=namespace)
            logger.debug(f"{configMap_obj} are in the Namespace {namespace}")
            return configMap_obj
        except Exception as e:
            logger.error("Exception occurred while executing list_namespaced_config_map: %s\n" % e)

    def get_eks_cluster_role(self):
        """This method returns ClusterRoleList which is a collection of ClusterRoles.
        Returns:
            V1ClusterRoleList: A dictionary (JSON) format response containing list of clusterRoles. It contains attributes as follows:
                    api_version - APIVersion defines the versioned schema of this representation of an object.
                    items - Items is a list of ClusterRoles.
                    kind - Kind is a string value representing the REST resource this object represents.
                    metadata - optional set of data associated with the response.
        """
        try:
            clusterRole_obj = self.rbac_authorization_v1_api.list_cluster_role()
            logger.debug(f"{clusterRole_obj}")
            return clusterRole_obj
        except Exception as e:
            logger.error("Exception occurred while executing list_cluster_role: %s\n" % e)

    def get_eks_cluster_role_binding(self):
        """This method returns ClusterRoleBindingList which is a collection of ClusterRoleBindings.
        Returns:
            V1ClusterRoleBindingList: A dictionary (JSON) format response containing list of clusterRoleBindings. It contains attributes as follows:
                    api_version - APIVersion defines the versioned schema of this representation of an object.
                    items - Items is a list of ClusterRoleBindings.
                    kind - Kind is a string value representing the REST resource this object represents.
                    metadata - optional set of data associated with the response.
        """
        try:
            clusterRoleBinding_obj = self.rbac_authorization_v1_api.list_cluster_role_binding()
            logger.debug(f"{clusterRoleBinding_obj}")
            return clusterRoleBinding_obj
        except Exception as e:
            logger.error("Exception occurred while executing list_cluster_role_binding: %s\n" % e)

    def create_eks_service_account(
        self,
        service_account_name: str = "nginx-service-account",
        namespace: str = "nginx-app",
    ) -> bool:
        """Creates ServiceAccount k8s resource in the namespace.
        Args:
            service_account_name (str, optional): ServiceAccount K8s resource name. Defaults to "nginx-service-account".
            namespace (str, optional): Name of the namespace. Defaults to "nginx-app".
        Returns:
            bool: Return boolean, Success: True, Failure: False
        """
        # Define the ServiceAccount
        service_account = client.V1ServiceAccount()
        service_account.metadata = client.V1ObjectMeta(name=service_account_name)
        # Create and verify the ServiceAccount
        try:
            self.api_instance.create_namespaced_service_account(namespace=namespace, body=service_account)
            return True
        except client.exceptions.ApiException as e:
            # If the exception is because the ServiceAccount already exists, return True
            if e.status == 409 and "AlreadyExists" in e.body:
                logger.warn(f"ServiceAccount '{service_account_name}' already exists.")
                return True
            else:
                # Capture and handle other exceptions
                logger.error(f"Error creating ServiceAccount: {e}")
                return False

    def delete_eks_service_account(
        self,
        service_account_name: str = "nginx-service-account",
        namespace: str = "nginx-app",
    ) -> bool:
        """Deletes ServiceAccount k8s resource from the namespace.
        Args:
            service_account_name (str, optional): ServiceAccount K8s resource name. Defaults to "nginx-service-account".
            namespace (str, optional): Name of the namespace. Defaults to "nginx-app".
        Returns:
            bool: Return boolean, Success: True, Failure: False
        """
        # Delete the ServiceAccount
        try:
            response = self.api_instance.delete_namespaced_service_account(
                name=service_account_name, namespace=namespace
            )
            logger.debug(f"ServiceAccount '{service_account_name}' deleted successfully, response: {response}")
            return True
        except client.exceptions.ApiException as e:
            # If the exception is because the ServiceAccount is not found, return True
            if e.status == 404:
                logger.warn(f"ServiceAccount '{service_account_name}' not found.")
                return True
            else:
                # Capture and handle other exceptions
                logger.error(f"Error deleting ServiceAccount: {e} \n response: {response}")
                return False

    def read_eks_service_account(
        self,
        service_account_name: str = "nginx-service-account",
        namespace: str = "nginx-app",
        validate_delete_resource: bool = False,
    ) -> bool:
        """Reads ServiceAccount k8s resource from the namespace.
        Args:
            service_account_name (str, optional): ServiceAccount K8s resource name. Defaults to "nginx-service-account".
            namespace (str, optional): Name of the namespace. Defaults to "nginx-app".
            validate_delete_resource  (bool, optional): Validate delete resource workflow if set to True (in case of delete workflow we will get service not found error, this flag addreseses the same), defaults to False.
        Returns:
            bool: Return boolean, Success: True, Failure: False
        """
        try:
            # Read serviceaccount info
            self.api_instance.read_namespaced_service_account(name=service_account_name, namespace=namespace)
            return True
        except client.exceptions.ApiException as e:
            # If the exception is because the ServiceAccount is not found, return False
            if e.status == 404 and validate_delete_resource:
                return True
            else:
                # Capture and handle other exceptions
                logger.info(f"Error, while checking ServiceAccount existence: {e}")
                return False

    def delete_namespace(self, namespace: str):
        """Deletes k8s namespace
        Args:
            namespace (str): Name of the namespace
        Returns:
            bool: Return boolean, Success: True, Failure: False
        """
        try:
            # Delete the namespace
            self.api_instance.delete_namespace(name=namespace, body=client.V1DeleteOptions())
            logger.debug(f"Namespace '{namespace}' deleted successfully.")
            return True
        except client.exceptions.ApiException as e:
            # If the exception is because the namespace is not found, return False
            if e.status == 404:
                logger.warn(f"Namespace '{namespace}' not found.")
                return True
            else:
                # Capture and handle other exceptions
                logger.error(f"Error deleting namespace: {e}")
                return False

    def scale_deployment(self, replicas: int, deployment_name: str, namespace: str) -> bool:
        """Scales deployment (set number of replicas)

        Args:
            replicas (int): number of pod replicas
            deployment_name (str): name of deployment to scale
            namespace (str): deployment's namespace

        Returns:
            bool: Success status of scale command execution
        """
        scale_up_result = run_ctl_command(
            ["kubectl", "scale", "deployment", f"--replicas={replicas}", f"{deployment_name}", "-n", f"{namespace}"],
        )
        return scale_up_result

    def is_nginx_running(self, load_balancer_url: str, port: int = 80):
        """Check nginx pod running status

        Args:
            load_balancer_url (str): Load balancer url
            port (int, optional): port number. Defaults to 80.

        Returns:
            Response: Response object
        """
        nginx_url = f"http://{load_balancer_url}:{port}"
        logger.debug(f"URL: {nginx_url}")
        response = requests.get(nginx_url)
        return response

    def delete_storage_class(self, sc_name):
        try:
            sc = self.storage_v1_api.delete_storage_class(sc_name)
            logger.info(f"Storage class '{sc_name}' deleted successfully.")
            return True
        except client.exceptions.ApiException as e:
            logger.error(f"Exception while deleting storage class {sc_name}")
            raise e
