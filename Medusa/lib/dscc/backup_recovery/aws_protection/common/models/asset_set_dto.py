import tests.steps.aws_protection.inventory_manager_steps as IMS
from dataclasses_json import dataclass_json, LetterCase
from dataclasses import dataclass, field
from tests.e2e.aws_protection.context import Context


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class AwsAssetsDto:
    ec2_instances: list = field(default_factory=list)
    ebs_volumes: list = field(default_factory=list)
    vpcs: list = field(default_factory=list)
    subnets: list = field(default_factory=list)
    # [ec2_instance, ebs_volume] -> AWS
    attached_ec2_ebs: list = field(default_factory=list)
    # [csp_machine_instance, csp_volume] -> DSCC
    attached_csps: list = field(default_factory=list)

    def get_csp_attached_assets_for_aws_attached_assets(self, context: Context):
        """Populate attached_csps with DSCC assets corresponding to AWS assets from attached_ec2_ebs

        Args:
            context (Context): The Context
        """

        # retrieve corresponding DSCC assets to AWS assets
        for ec2, ebs in self.attached_ec2_ebs:
            csp_instance = IMS.get_csp_instance_by_ec2_instance_id(context, ec2_instance_id=ec2.id)
            csp_volume = IMS.get_csp_volume_by_ebs_volume_id(context, ebs_volume_id=ebs.id)

            self.attached_csps.append([csp_instance, csp_volume])
