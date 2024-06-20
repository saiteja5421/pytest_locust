from common.helpers import read_config
from lib.platform.aws.models.instance import Tag


def standard_asset_tag():
    config = read_config()
    standard_asset = config["testInput"]["standard_asset_tag"]
    asset_tag = Tag(Key=f"{standard_asset['key']}", Value=f"{standard_asset['value']}")
    return asset_tag


def restore_asset_tag():
    config = read_config()
    restore_asset = config["testInput"]["restore_asset_tag"]
    asset_tag = Tag(Key=f"{restore_asset['key']}", Value=f"{restore_asset['value']}")
    return asset_tag
