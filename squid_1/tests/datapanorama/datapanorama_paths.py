from tests.datapanorama.panorama_context_models import PanoramaAPI


DATA_OBSERVABILITY = "/data-observability/v1alpha1"
CONSUMPTION_VOLUMES_SUMMARY = f"{DATA_OBSERVABILITY}/{PanoramaAPI.volumes_consumption}"
CONSUMPTION_VOLUMES_COST_TREND = f"{DATA_OBSERVABILITY}/{PanoramaAPI.volumes_cost_trend}"
CONSUMPTION_VOLUMES_USAGE_TREND = f"{DATA_OBSERVABILITY}/{PanoramaAPI.volume_usage_trend}"
CONSUMPTION_VOLUMES_CREATION_TREND = f"{DATA_OBSERVABILITY}/{PanoramaAPI.volumes_creation_trend}"
CONSUMPTION_VOLUMES_ACTIVITY_TREND = f"{DATA_OBSERVABILITY}/{PanoramaAPI.volumes_activity_trend}"
CONSUMPTION_SNAPSHOTS_SUMMARY = f"{DATA_OBSERVABILITY}/{PanoramaAPI.snapshots_consumption}"
CONSUMPTION_SNAPSHOTS_COST_TREND = f"{DATA_OBSERVABILITY}/{PanoramaAPI.snapshots_cost_trend}"
CONSUMPTION_SNAPSHOTS_USAGE_TREND = f"{DATA_OBSERVABILITY}/{PanoramaAPI.snapshots_usage_trend}"
CONSUMPTION_SNAPSHOTS_CREATION_TREND = f"{DATA_OBSERVABILITY}/{PanoramaAPI.snapshots_creation_trend}"
CONSUMPTION_SNAPSHOTS_AGE_TREND = f"{DATA_OBSERVABILITY}/{PanoramaAPI.snapshots_age_trend}"
CONSUMPTION_SNAPSHOTS_RETENTION = f"{DATA_OBSERVABILITY}/{PanoramaAPI.snapshots_retention_trend}"
CONSUMPTION_SNAPSHOTS_TOTAL = f"{DATA_OBSERVABILITY}/{PanoramaAPI.snapshots}"
CONSUMPTION_CLONES_SUMMARY = f"{DATA_OBSERVABILITY}/{PanoramaAPI.clones_consumption}"
CONSUMPTION_CLONES_COST_TREND = f"{DATA_OBSERVABILITY}/{PanoramaAPI.clones_cost_trend}"
CONSUMPTION_CLONES_USAGE_TREND = f"{DATA_OBSERVABILITY}/{PanoramaAPI.clones_usage_trend}"
CONSUMPTION_CLONES_CREATION_TREND = f"{DATA_OBSERVABILITY}/{PanoramaAPI.clones_creation_trend}"
CONSUMPTION_CLONES_ACTIVITY_TREND = f"{DATA_OBSERVABILITY}/{PanoramaAPI.clones_activity_trend}"
INVENTORY_STORAGE_SYSTEMS_SUMMARY = f"{DATA_OBSERVABILITY}/{PanoramaAPI.inventory_storage_systems_summary}"
INVENTORY_STORAGE_SYSTEMS_INFO = f"{DATA_OBSERVABILITY}/{PanoramaAPI.inventory_storage_systems}"
INVENTORY_STORAGE_SYSTEMS_COST_TREND = f"{DATA_OBSERVABILITY}/{PanoramaAPI.inventory_storage_systems_cost_trend}"
APPLINEAGE_SUMMARY = f"{DATA_OBSERVABILITY}/{PanoramaAPI.applications}"
