from enum import Enum


class AWSRegions(Enum):
    AWS_US_EAST_1 = "USA, North Virginia"
    AWS_US_EAST_2 = "USA, Ohio"
    AWS_US_WEST_1 = "USA, North California"
    AWS_US_WEST_2 = "USA, Oregon"
    AWS_CA_CENTRAL_1 = "Canada, Quebec"
    AWS_EU_CENTRAL_1 = "Germany, Frankfurt"
    AWS_EU_WEST_1 = "Ireland, Dublin"
    AWS_EU_WEST_2 = "United Kingdom, London"
    AWS_EU_WEST_3 = "France, Paris"
    AWS_EU_NORTH_1 = "Sweden, Stockholm"
    AWS_AP_NORTHEAST_1 = "Japan, Tokyo"
    AWS_AP_NORTHEAST_2 = "South Korea, Seoul"
    AWS_AP_NORTHEAST_3 = "Japan, Osaka"
    AWS_AP_SOUTHEAST_1 = "Singapore"
    AWS_AP_SOUTHEAST_2 = "Australia, Sydney"
    AWS_AP_SOUTH_1 = "India, Mumbai"
    any = "any"


class AwsStorageLocation(Enum):
    AWS_US_EAST_1 = "aws:us-east-1"
    AWS_US_EAST_2 = "aws:us-east-2"
    AWS_US_WEST_1 = "aws:us-west-1"
    AWS_US_WEST_2 = "aws:us-west-2"
    AWS_CA_CENTRAL_1 = "aws:ca-central-1"
    AWS_EU_CENTRAL_1 = "aws:eu-central-1"
    AWS_EU_WEST_1 = "aws:eu-west-1"
    AWS_EU_WEST_2 = "aws:eu-west-2"
    AWS_EU_WEST_3 = "aws:eu-west-3"
    AWS_EU_NORTH_1 = "aws:eu-north-1"
    AWS_AP_NORTHEAST_1 = "aws:ap-northeast-1"
    AWS_AP_NORTHEAST_2 = "aws:ap-northeast-2"
    AWS_AP_NORTHEAST_3 = "aws:ap-northeast-3"
    AWS_AP_SOUTHEAST_1 = "aws:ap-southeast-1"
    AWS_AP_SOUTHEAST_2 = "aws:ap-southeast-2"
    AWS_AP_SOUTHEAST_3 = "aws:ap-southeast-3"
    AWS_AP_SOUTH_1 = "aws:ap-south-1"
    any = "any"
