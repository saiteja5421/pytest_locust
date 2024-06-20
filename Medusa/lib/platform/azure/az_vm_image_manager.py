import logging
import time
from typing import Union

from azure.identity import DefaultAzureCredential, ClientSecretCredential
from azure.mgmt.compute import ComputeManagementClient
from azure.mgmt.compute.models import (
    VirtualMachineImage,
    GalleryImage,
    Gallery,
    GalleryImageVersion,
    VirtualMachine,
    GalleryImageIdentifier,
    GalleryImageFeature,
    SecurityTypes,
    DiskControllerTypes,
    OperatingSystemTypes,
    HyperVGeneration,
    GalleryImageVersionPublishingProfile,
    StorageAccountType,
    GalleryImageVersionStorageProfile,
    GalleryArtifactVersionFullSource,
)
from lib.common.enums.az_regions import AZRegion
from azure.mgmt.compute.v2022_08_01.models._models_py3 import (
    Image,
    ImageUpdate,
)

logger = logging.getLogger()


class AZVMImageManager:
    def __init__(
        self,
        credential: Union[DefaultAzureCredential, ClientSecretCredential],
        subscription_id: str,
    ) -> None:
        self.compute_client = ComputeManagementClient(credential, subscription_id)

    def get_vm_image(
        self, location: AZRegion, publisher_name: str, offer: str, skus: str, version: str
    ) -> VirtualMachineImage:
        """Gets a virtual machine image

        Args:
            location (AZRegion): Name of support Azure region
            publisher_name (str): Image publisher
            offer (str): Image publisher offer
            skus (str): Image SKU
            version (str): Image SKU version

        Returns:
            VirtualMachineImage: VirtualMachineImage
        """
        vm_image = self.compute_client.virtual_machine_images.get(location.value, publisher_name, offer, skus, version)
        logger.info(f"Virtual Machine Image acquired: {vm_image}")
        return vm_image

    def get_gallery_image_version(
        self,
        resource_group_name: str,
        gallery_name: str,
        gallery_image_name: str,
        gallery_image_version_name: str,
    ) -> GalleryImageVersion:
        """Gets Gallery Image Version

        Args:
            resource_group_name (str): Name of resource group
            gallery_name (str): Name of Shared Image Gallery
            gallery_image_name (str): Name of Gallery Image Definition
            gallery_image_version_name (str): Name of Gallery Image Version

        Returns:
            GalleryImageVersion: Gallery Image Version
        """
        image_version: GalleryImageVersion = self.compute_client.gallery_image_versions.get(
            resource_group_name=resource_group_name,
            gallery_name=gallery_name,
            gallery_image_name=gallery_image_name,
            gallery_image_version_name=gallery_image_version_name,
        )
        logger.info(f"Gallery Image Version acquired: {gallery_image_version_name}")
        return image_version

    def get_gallery_image(self, resource_group_name: str, gallery_name: str, gallery_image_name: str) -> GalleryImage:
        """Gets Gallery Image Definition

        Args:
            resource_group_name (str): Name of resource group
            gallery_name (str): Name of Shared Image Gallery
            gallery_image_name (str): Name of Gallery Image Definition

        Returns:
            GalleryImage: GalleryImage
        """
        image: GalleryImage = self.compute_client.gallery_images.get(
            resource_group_name=resource_group_name,
            gallery_name=gallery_name,
            gallery_image_name=gallery_image_name,
        )
        logger.info(f"Gallery Image acquired: {gallery_image_name}")
        return image

    def get_gallery(
        self,
        resource_group_name: str,
        gallery_name: str,
    ) -> Gallery:
        """Get Shared Image Gallery

        Args:
            resource_group_name (str): Name of resource group
            gallery_name (str): Name of gallery

        Returns:
            Gallery: Shared gallery
        """
        gallery: Gallery = self.compute_client.galleries.get(
            resource_group_name=resource_group_name,
            gallery_name=gallery_name,
        )
        logger.info(f"Shared Gallery acquired: {gallery}")
        return gallery

    def create_gallery(
        self,
        resource_group_name: str,
        gallery_name: str,
        location: AZRegion = AZRegion.WEST_US_2,
    ) -> Gallery:
        """Creates Image Gallery

        Args:
            resource_group_name (str): Name of resource group
            gallery_name (str): Name of gallery
            location (AZRegion, optional): Resource location. Defaults to AZRegion.WEST_US_2.

        Returns:
            Gallery: Image Gallery that's created
        """
        gallery: Gallery = Gallery(location=location.value)
        shared_gallery: Gallery = self.compute_client.galleries.begin_create_or_update(
            resource_group_name=resource_group_name,
            gallery_name=gallery_name,
            gallery=gallery,
        ).result()
        logger.info(f"Created/Updated Gallery: {gallery_name}")
        return shared_gallery

    def create_gallery_image_definition(
        self,
        resource_group_name: str,
        gallery_name: str,
        gallery_image_name: str,
        vm: VirtualMachine,
        location: AZRegion = AZRegion.WEST_US_2,
        os_type: OperatingSystemTypes = OperatingSystemTypes.LINUX,
        hyper_v_generation: HyperVGeneration = HyperVGeneration.V2,
    ) -> GalleryImage:
        """Creates a Gallery Image Definition from a source VM

        Args:
            resource_group_name (str): Name of resource group
            gallery_name (str): Name of gallery
            gallery_image_name (str): Name of gallery image definition
            vm (VirtualMachine): Source virtual machine
            location (AZRegion, optional): Resource location. Defaults to AZRegion.WEST_US_2.
            os_type (OperatingSystemTypes, optional): Operating system type. Defaults to OperatingSystemTypes.LINUX.
            hyper_v_generation (HyperVGeneration, optional): Hypervisor generation of the virtual machine. Defaults to HyperVGeneration.V2.

        Returns:
            GalleryImage: Gallery Image Definition that was created
        """
        gallery_image_identifier: GalleryImageIdentifier = GalleryImageIdentifier(
            publisher=vm.storage_profile.image_reference.publisher,
            offer=vm.storage_profile.image_reference.offer,
            sku=vm.storage_profile.image_reference.sku,
        )

        gallery_image_features = [
            GalleryImageFeature(name="SecurityType", value=SecurityTypes.TRUSTED_LAUNCH),
            GalleryImageFeature(name="DiskControllerTypes", value=DiskControllerTypes.SCSI),
            GalleryImageFeature(name="IsAcceleratedNetworkSupported", value=True),
        ]

        gallery_image: GalleryImage = GalleryImage(
            location=location.value,
            os_type=os_type,
            identifier=gallery_image_identifier,
            hyper_v_generation=hyper_v_generation,
            features=gallery_image_features,
        )

        gallery_image_definition: GalleryImage = self.compute_client.gallery_images.begin_create_or_update(
            resource_group_name, gallery_name, gallery_image_name, gallery_image
        ).result()
        logger.info(f"Created Gallery Image Definition: {gallery_image_name}")
        return gallery_image_definition

    def create_image_version(
        self,
        resource_group_name: str,
        vm_name: str,
        gallery_name: str,
        gallery_image_name: str,
        gallery_image_version_name: str = "0.0.1",
        location: AZRegion = AZRegion.WEST_US_2,
        storage_account_type: StorageAccountType = StorageAccountType.STANDARD_LRS,
    ) -> GalleryImageVersion:
        """Creates gallery image version

        Args:
            resource_group_name (str): Name of resource group
            vm_name (str): Name of source virtual machine
            gallery_name (str): Name of gallery
            gallery_image_name (str): Name of gallery image definition
            gallery_image_version_name (str): Name of gallery image version
            location (AZRegion, optional): Resource location. Defaults to AZRegion.WEST_US_2.
            storage_account_type (StorageAccountType, optional): Storage account type to be used to store the image. Defaults to StorageAccountType.STANDARD_LRS.

        Returns:
            GalleryImageVersion: Gallery Image Version that's created
        """
        logger.info(f"Getting VM {vm_name}")
        vm: VirtualMachine = self.compute_client.virtual_machines.get(
            resource_group_name=resource_group_name,
            vm_name=vm_name,
            expand="instanceView",
        )

        logger.info(f"Deallocating VM {vm_name}")
        self.compute_client.virtual_machines.begin_deallocate(
            resource_group_name=resource_group_name,
            vm_name=vm_name,
        ).result()

        logger.info(f"Generalizing the VM {vm_name}")
        self.compute_client.virtual_machines.generalize(
            resource_group_name=resource_group_name,
            vm_name=vm_name,
        )

        logger.info(f"Creating Gallery Image Version: {gallery_image_version_name}")
        publishing_profile = GalleryImageVersionPublishingProfile(storage_account_type=storage_account_type)
        storage_profile = GalleryImageVersionStorageProfile(
            source=GalleryArtifactVersionFullSource(
                id=vm.id,
            ),
        )
        gallery_image_version: GalleryImageVersion = GalleryImageVersion(
            location=location.value,
            publishing_profile=publishing_profile,
            storage_profile=storage_profile,
        )
        image_version: GalleryImageVersion = self.compute_client.gallery_image_versions.begin_create_or_update(
            resource_group_name=resource_group_name,
            gallery_name=gallery_name,
            gallery_image_name=gallery_image_name,
            gallery_image_version_name=gallery_image_version_name,
            gallery_image_version=gallery_image_version,
        ).result()

        logger.info(f"Created Gallery Image Version: {gallery_image_version_name} for Image {gallery_image_name}")
        return image_version

    def delete_image_version(
        self,
        resource_group_name: str,
        gallery_name: str,
        gallery_image_name: str,
        gallery_image_version_name: str,
    ):
        """Delete Image Version

        Args:
            resource_group_name (str): Name of resource group
            gallery_name (str): Name of gallery
            gallery_image_name (str): Name of image definition
            gallery_image_version_name (str): Name of image version
        """
        logger.info(f"Deleting Gallery Image Version: {gallery_image_version_name}")
        self.compute_client.gallery_image_versions.begin_delete(
            resource_group_name=resource_group_name,
            gallery_name=gallery_name,
            gallery_image_name=gallery_image_name,
            gallery_image_version_name=gallery_image_version_name,
        ).result()
        logger.info(f"Deleted Gallery Image Version: {gallery_image_version_name}")

    def delete_gallery_image_definition(
        self,
        resource_group_name: str,
        gallery_name: str,
        gallery_image_name: str,
    ):
        """Deletes entire image definition

        Args:
            resource_group_name (str): Name of resource group
            gallery_name (str): Name of gallery
            gallery_image_name (str): Name of image definition
        """
        logger.info(f"Deleting Gallery Image Definition: {gallery_image_name}")
        image_versions = self.compute_client.gallery_image_versions.list_by_gallery_image(
            resource_group_name=resource_group_name,
            gallery_name=gallery_name,
            gallery_image_name=gallery_image_name,
        )
        for image_version in image_versions:
            self.delete_image_version(
                resource_group_name=resource_group_name,
                gallery_name=gallery_name,
                gallery_image_name=gallery_image_name,
                gallery_image_version_name=image_version.name,
            )
            while True:
                try:
                    version = self.get_gallery_image_version(
                        resource_group_name=resource_group_name,
                        gallery_name=gallery_name,
                        gallery_image_name=gallery_image_name,
                        gallery_image_version_name=image_version.name,
                    )
                    logger.info(f"Image Version {version.name} is being deleted")
                    time.sleep(60)
                except Exception as e:
                    logger.info(f"Image Version {image_version.name} was deleted, {e}")
                    break
        self.compute_client.gallery_images.begin_delete(
            resource_group_name=resource_group_name,
            gallery_name=gallery_name,
            gallery_image_name=gallery_image_name,
        ).result()
        logger.info(f"Deleted Gallery Image Definition: {gallery_image_name}")

    def get_image(self, resource_group_name: str, image_name: str, expand: Union[str, None] = None) -> Image:
        """Get VM Image

        NOTE:
            -   Same result as self.compute_client.virtual_machine_images.get()
            -   self.compute_client.virtual_machine_images has limited operations

        Args:
            resource_group_name (str): Name of Resource Group
            image_name (str): Name of Image
            expand (str | None, optional): Expand expression to apply on the operation. Defaults to None.

        Returns:
            image (Image): Image object that was obtained
        """
        image: Image = self.compute_client.images.get(
            resource_group_name=resource_group_name, image_name=image_name, expand=expand
        )
        logger.info(f"Obtained Image {image_name} ({image.id})")
        return image

    def add_tags_to_vm_image(
        self,
        resource_group_name: str,
        image_name: str,
        tags: dict[str, str],
    ) -> Image:
        """Add tags to VM Image

        NOTE: Can only update Tags to a VM Image

        Args:
            resource_group_name (str): Name of Resource Group
            image_name (str): Name of Image
            tags (dict[str, str]): Tags to add to VM Image

        Returns:
            updated_image (Image): Image object with new tags
        """
        image = self.get_vm_image(resource_group_name=resource_group_name, image_name=image_name, expand=None)
        logger.info(f"Appending {tags} to existing Snapshot Tags {image.tags}")
        image.tags = {**image.tags, **tags}

        image_update = ImageUpdate(
            tags=image.tags,
            source_virtual_machine=image.source_virtual_machine,
            storage_profile=image.storage_profile,
            hyper_v_generation=image.hyper_v_generation,
        )
        updated_image: Image = self.compute_client.images.begin_update(
            resource_group_name=resource_group_name, image_name=image_name, parameters=image_update
        ).result()
        logger.info(f"Updated Image {image_name} ({updated_image.id}) to have tags {tags}")
        return updated_image

    def remove_tags_from_vm_image(self, resource_group_name: str, image_name: str, tag_keys: list[str]) -> Image:
        """Remove Tags from VM Image

        Args:
            resource_group_name (str): Name of Resource Group
            image_name (str): Name of Image
            tag_keys (list[str]): List of Tag Keys to remove

        Returns:
            updated_image (Image): Updated Image object
        """
        image = self.get_vm_image(resource_group_name=resource_group_name, image_name=image_name, expand=None)
        logger.info(f"Removing tags {tag_keys} from VM Image {image_name}")
        for tag_key in tag_keys:
            if tag_key in image.tags.keys():
                del image.tags[tag_key]

        image_update = ImageUpdate(
            tags=image.tags,
            source_virtual_machine=image.source_virtual_machine,
            storage_profile=image.storage_profile,
            hyper_v_generation=image.hyper_v_generation,
        )
        updated_image: Image = self.compute_client.images.begin_update(
            resource_group_name=resource_group_name, image_name=image_name, parameters=image_update
        ).result()
        logger.info(f"Updated Image {image_name} ({updated_image.id}) to now have tags {updated_image.tags}")
        return updated_image
