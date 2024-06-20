"""
    This file has data classes representing each section in (atlantia)variables.ini file.
    """

from dataclasses import dataclass

"""
panaroma_context_models.py file contains all data model classes for PQA context file.
    Usage:
    ------
        from panaroma_context_models import <model name>

    Data classes:
    --------
        - Cluster
        - ArrayCredentials
        - ArrayConfig
        - UserProvided
        - CommonServicesAPI
        - PanoramaAPI
        - Proxy

    Return:
    -------
        :- None
"""


@dataclass
class Cluster:
    """
    Cluster class will construct data model for given fields

    input Data fields for Cluster model and these fields should send in order is like below:
        version
        url
        atlantia_url
        oauth2_server
        panorama_url

    """

    version: str = "v1"
    url: str = "http://127.0.0.1:5000"
    atlantia_url: str = "http://127.0.0.1:5002"
    oauth2_server: str = "https://sso.common.cloud.hpe.com/as/token.oauth2"
    panorama_url: str = ""
    static_token: str = None


@dataclass
class ArrayCredentials:
    """
    ArrayCredentials class will construct data model for given fields

    input Data fields for ArrayCredentials model and these fields should send in order is like below:
        username
        password

    """

    username: str = ""
    password: str = ""


@dataclass
class ArrayConfig:
    """
    ArrayConfig class will construct data model for given fields

    input Data fields for ArrayConfig model and these fields should send in order is like below:
        totalvolumescount: 0
        thickvolumescount: 0
        snapscountpervolume: 0

    """

    totalvolumescount: 0
    thickvolumescount: 0
    snapscountpervolume: 0


# Sections such as USER-ONE ,USER-TWO sections
@dataclass
class UserProvided:
    """
    UserProvided class will construct data model for given fields

    input Data fields for UserProvided model and these fields should send in order is like below:
        username
        credential_name
        api_client_id
        api_client_secret

    """

    username: str = "alertzprometheus+1@gmail.com"
    credential_name: str = ""
    api_client_id: str = ""
    api_client_secret: str = ""


@dataclass
class PanoramaAPI:
    """
    PanoramaAPI class will construct data model for given fields

    input Data fields for PanoramaAPI model and these fields should send in order is like below:
        volumes_consumption
        volumes_cost_trend
        volumes_usage_trend
        volumes_creation_trend
        volumes_activity_trend
        volume_usage
        volume_usage_trend
        volume_io_trend
        snapshots
        clones
        snapshots_consumption
        snapshots_cost_trend
        snapshots_usage_trend
        snapshots_creation_trend
        snapshots_age_trend
        snapshots_retention_trend
        clones_consumption
        clones_cost_trend
        clones_usage_trend
        clones_creation_trend
        clones_activity_trend
        inventory_storage_systems_summary
        inventory-storage-systems-cost-trend
        inventory_storage_systems
        inventory_storage_systems_config

    """

    volumes_consumption: str = "volumes-consumption"
    volumes_cost_trend: str = "volumes-cost-trend"
    volumes_usage_trend: str = "volumes-usage-trend"
    volumes_creation_trend: str = "volumes-creation-trend"
    volumes_activity_trend: str = "volumes-activity-trend"
    volume_usage: str = "volume-usage"
    volume_usage_trend: str = "volume-usage-trend"
    volume_io_trend: str = "volume-io-trend"
    snapshots: str = "snapshots"
    clones: str = "clones"
    snapshots_consumption: str = "snapshots-consumption"
    snapshots_cost_trend: str = "snapshots-cost-trend"
    snapshots_usage_trend: str = "snapshots-usage-trend"
    snapshots_creation_trend: str = "snapshots-creation-trend"
    snapshots_age_trend: str = "snapshots-age-trend"
    snapshots_retention_trend: str = "snapshots-retention-trend"
    snapshots_details: str = "snapshots"
    clones_consumption: str = "clones-consumption"
    clone_io_trend: str = "clone-io-trend"
    clones_cost_trend: str = "clones-cost-trend"
    clones_usage_trend: str = "clones-usage-trend"
    clones_creation_trend: str = "clones-creation-trend"
    clones_activity_trend: str = "clones-activity-trend"
    collection_summary: str = "collection-summary"
    inventory_storage_systems_summary: str = "inventory-storage-systems-summary"
    inventory_storage_systems_cost_trend: str = "inventory-storage-systems-cost-trend"
    inventory_storage_systems: str = "inventory-storage-systems"
    inventory_storage_systems_config: str = "inventory-storage-systems-config"
    clones_detail: str = "clones-detail"
    application_lineage: str = "application-lineage"
    # systems
    systems: str = "systems"
    # App Lineage
    applications: str = "applications"
    application_snapshots: str = "snapshots"
    application_clones: str = "clones"
    application_volumes: str = "volumes"


@dataclass
class Proxy:
    """
    Proxy class will construct data model for given fields

    input Data fields for Proxy model and these fields should send in order is like below:
        proxy_uri

    """

    proxy_uri: str = "http://hpeproxy.its.hpecorp.net:443"


@dataclass
class CXO_29_Array:
    """Class for storing CXO_29_Array credentials"""

    array_ip: str = "cxo-array29.lab.nimblestorage.com"
    username: str = ""
    password: str = ""
