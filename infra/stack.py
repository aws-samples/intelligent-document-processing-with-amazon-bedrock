"""
Copyright © Amazon.com and Affiliates
"""

import json
import logging
import sys
from typing import Any, Dict

import aws_cdk.aws_apigateway as apigw_v1
from aws_cdk import Aws, RemovalPolicy, Stack, Tags
from aws_cdk import CfnOutput as output
from aws_cdk import aws_iam as iam
from aws_cdk import aws_kms as kms
from aws_cdk import aws_lambda as _lambda
from aws_cdk import aws_s3 as _s3
from aws_cdk import aws_ssm as ssm
from cdk_nag import NagPackSuppression, NagSuppressions
from constructs import Construct

from infra.constructs.api import IDPBedrockAPIConstructs
from infra.constructs.buckets import ServerAccessLogsBucket
from infra.constructs.cognito_auth import (
    CognitoAuthenticationConstruct,
    CognitoCallbackUpdater,
)
from infra.constructs.layers import IDPBedrockLambdaLayers
from infra.stacks.ecs import IDPBedrockECSStack

LOGGER = logging.Logger("STACK-BUILD", level=logging.DEBUG)
HANDLER = logging.StreamHandler(sys.stdout)
HANDLER.setFormatter(
    logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
)
LOGGER.addHandler(HANDLER)


class IDPBedrockStack(Stack):
    """
    IDP Bedrock stack
    """

    def __init__(self, scope: Construct, stack_name: str, config: Dict[str, Any], **kwargs) -> None:  # noqa: C901
        description = "IDP with Amazon Bedrock (uksb-0rxb2u6bob)"
        super().__init__(scope, stack_name, description=description, **kwargs)

        ## Set architecture and Python Runtime
        LOGGER.info("Setting architecture and Python Runtime")
        architecture = config["lambda"].get("architecture", "X86_64")
        python_runtime = config["lambda"].get("python_runtime", "PYTHON_3_11")

        if architecture == "ARM_64":
            self._architecture = _lambda.Architecture.ARM_64
        elif architecture == "X86_64":
            self._architecture = _lambda.Architecture.X86_64
        else:
            raise RuntimeError("Select one option for system architecture among [ARM_64, X86_64]")

        if python_runtime == "PYTHON_3_9":
            self._runtime = _lambda.Runtime.PYTHON_3_9
        elif python_runtime == "PYTHON_3_10":
            self._runtime = _lambda.Runtime.PYTHON_3_10
        elif python_runtime == "PYTHON_3_11":
            self._runtime = _lambda.Runtime.PYTHON_3_11
        elif python_runtime == "PYTHON_3_12":
            self._runtime = _lambda.Runtime.PYTHON_3_12
        elif python_runtime == "PYTHON_3_13":
            self._runtime = _lambda.Runtime.PYTHON_3_13
        elif python_runtime == "PYTHON_3_14":
            self._runtime = _lambda.Runtime.PYTHON_3_14
        else:
            raise RuntimeError("Select a Python version >= PYTHON_3_9")

        ## ** Create logging bucket for server access logs **
        LOGGER.info("Creating logging bucket for server access logs")
        s3_logs_bucket = ServerAccessLogsBucket(self, f"{stack_name}-LOGS-BUCKET", stack_name=stack_name)

        ## **************** Create S3 Bucket ****************
        LOGGER.info("Creating S3 bucket for data storage")
        if config["s3"]["encryption"] == "SSE-KMS":
            if config["s3"]["kms_key_arn"] != "None":
                self.s3_kms_key = kms.Key.from_key_arn(
                    self,
                    f"{stack_name}-s3-key",
                    key_arn=config["s3"]["kms_key_arn"],
                )
            else:
                self.s3_kms_key = kms.Key(
                    self,
                    f"{stack_name}-s3-key",
                    alias=f"{stack_name}-s3-key",
                    enabled=True,
                    enable_key_rotation=True,
                    key_spec=kms.KeySpec.SYMMETRIC_DEFAULT,
                    key_usage=kms.KeyUsage.ENCRYPT_DECRYPT,
                )
            bucket_key_enabled = True
            encryption = _s3.BucketEncryption.KMS
        else:
            bucket_key_enabled = False
            encryption = _s3.BucketEncryption.S3_MANAGED
            self.s3_kms_key = None

        if config["s3"]["use_existing_bucket"]:
            self.s3_data_bucket = _s3.Bucket.from_bucket_name(
                self, id=f"{stack_name}-data", bucket_name=config["s3"]["bucket_name"]
            )
        else:
            data_bucket_name = f"{stack_name.lower()}-data-{Aws.ACCOUNT_ID}"
            self.s3_data_bucket = _s3.Bucket(
                self,
                id=f"{stack_name}-data",
                bucket_name=data_bucket_name,
                block_public_access=_s3.BlockPublicAccess.BLOCK_ALL,
                removal_policy=RemovalPolicy.DESTROY,
                bucket_key_enabled=bucket_key_enabled,
                server_access_logs_bucket=s3_logs_bucket.bucket,
                server_access_logs_prefix=f"buckets/{data_bucket_name}",
                encryption=encryption,
                enforce_ssl=True,
            )

        ## **************** Lambda layers ****************
        LOGGER.info("Creating Lambda layers")
        self.layers = IDPBedrockLambdaLayers(
            self,
            f"{stack_name}-layers",
            stack_name=stack_name,
            architecture=self._architecture,
            python_runtime=self._runtime,
        )

        ## ********** Bedrock configs ***********
        LOGGER.info("Creating Bedrock configs")
        bedrock_region = kwargs["env"].region
        if "bedrock" in config:
            if "region" in config["bedrock"]:
                bedrock_region = (
                    kwargs["env"].region if config["bedrock"]["region"] == "None" else config["bedrock"]["region"]
                )

        ## ********** Textract configs ***********
        LOGGER.info("Creating Textract configs")
        textract_region = config["stack_region"]
        if "textract" in config:
            if "table_flatten_headers" in config["textract"]:
                table_flatten_headers = config["textract"]["table_flatten_headers"]
            if "table_remove_column_headers" in config["textract"]:
                table_remove_column_headers = config["textract"]["table_remove_column_headers"]
            if "table_duplicate_text_in_merged_cells" in config["textract"]:
                table_duplicate_text_in_merged_cells = config["textract"]["table_duplicate_text_in_merged_cells"]
            if "hide_footer_layout" in config["textract"]:
                hide_footer_layout = config["textract"]["hide_footer_layout"]
            if "hide_header_layout" in config["textract"]:
                hide_header_layout = config["textract"]["hide_header_layout"]
            if "hide_page_num_layout" in config["textract"]:
                hide_page_num_layout = config["textract"]["hide_page_num_layout"]
            if "use_table" in config["textract"]:
                use_table = config["textract"]["use_table"]

        ## **************** Cognito ****************
        LOGGER.info("Creating Cognito user pool and client")
        mfa_enabled = config.get("authentication", {}).get("MFA", True)
        access_token_validity = config.get("authentication", {}).get("access_token_validity", 60)
        cognito_users = config.get("authentication", {}).get("users", [])
        cognito_users = [user for user in cognito_users if user != "XXX@XXX.com"]
        self.cognito_authn = CognitoAuthenticationConstruct(
            self,
            f"{stack_name}-AUTH",
            stack_name=stack_name,
            mfa_enabled=mfa_enabled,
            access_token_validity=access_token_validity,
            cognito_users=cognito_users,
        )

        ## **************** API Constructs  ****************
        # There should be only one AWS::ApiGateway::Account resource per region per account
        LOGGER.info("Creating API constructs")
        cloud_watch_role = iam.Role(
            self,
            "ApiGatewayCloudWatchLoggingRole",
            assumed_by=iam.ServicePrincipal("apigateway.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AmazonAPIGatewayPushToCloudWatchLogs")
            ],
        )
        apigw_account = apigw_v1.CfnAccount(self, "ApiGatewayAccount", cloud_watch_role_arn=cloud_watch_role.role_arn)

        self.api_constructs = IDPBedrockAPIConstructs(
            self,
            f"{stack_name}-API",
            stack_name=stack_name,
            s3_data_bucket=self.s3_data_bucket,
            s3_kms_key=self.s3_kms_key,
            layers=self.layers,
            user_pool=self.cognito_authn.user_pool,
            user_pool_client=self.cognito_authn.user_pool_client,
            bedrock_region=bedrock_region,
            textract_region=textract_region,
            table_flatten_headers=table_flatten_headers,
            table_remove_column_headers=table_remove_column_headers,
            table_duplicate_text_in_merged_cells=table_duplicate_text_in_merged_cells,
            hide_footer_layout=hide_footer_layout,
            hide_header_layout=hide_header_layout,
            hide_page_num_layout=hide_page_num_layout,
            use_table=use_table,
            architecture=self._architecture,
            python_runtime=self._runtime,
        )
        self.api_constructs.node.add_dependency(apigw_account)

        ## **************** Set SSM Parameters ****************
        # Note: StringParameter name cannot start with "aws".
        LOGGER.info("Creating SSM parameters")
        self.ssm_cover_image_url = ssm.StringParameter(
            self,
            f"{stack_name}-SSM-CoverImageUrl",
            parameter_name=f"/{stack_name}/ecs/COVER_IMAGE_URL",
            string_value=config["frontend"]["cover_image_url"],
        )
        self.ssm_assistant_avatar_url = ssm.StringParameter(
            self,
            f"{stack_name}-SSM-AssistantAvatarUrl",
            parameter_name=f"/{stack_name}/ecs/ASSISTANT_AVATAR_URL",
            string_value=config["frontend"]["assistant_avatar"],
        )
        self.ssm_bedrock_model_ids = ssm.StringParameter(
            self,
            f"{stack_name}-SSM-BedrockModelIds",
            parameter_name=f"/{stack_name}/ecs/BEDROCK_MODEL_IDS",
            string_value=json.dumps(config["bedrock"].get("model_ids", [])),
        )
        self.ssm_region = ssm.StringParameter(
            self,
            f"{stack_name}-SSM-Region",
            parameter_name=f"/{stack_name}/ecs/REGION",
            string_value=self.region,
        )
        self.ssm_bucket_name = ssm.StringParameter(
            self,
            f"{stack_name}-SSM-BucketName",
            parameter_name=f"/{stack_name}/ecs/BUCKET_NAME",
            string_value=self.s3_data_bucket.bucket_name,
        )
        self.bucket_name_output = output(self, id="S3BucketName", value=self.s3_data_bucket.bucket_name)

        ## **************** ECS UI NestedStack ****************
        LOGGER.info("Creating ECS UI nested stack")
        if config["frontend"]["deploy_ecs"]:
            self.streamlit_constructs = IDPBedrockECSStack(
                self,
                f"{stack_name}-ECS",
                stack_name=stack_name,
                s3_data_bucket=self.s3_data_bucket,
                s3_logs_bucket=s3_logs_bucket.bucket,
                ecs_cpu=config["frontend"]["ecs_cpu"],
                ecs_memory=config["frontend"]["ecs_memory"],
                open_to_public_internet=config["frontend"]["open_to_public_internet"],
                ip_address_allowed=config["frontend"].get("ip_address_allowed"),
                ssm_client_id=self.cognito_authn.ssm_client_id,
                ssm_user_pool_id=self.cognito_authn.ssm_user_pool_id,
                ssm_cognito_domain=self.cognito_authn.ssm_cognito_domain,
                ssm_region=self.ssm_region,
                ssm_api_uri=self.api_constructs.ssm_api_uri,
                ssm_bucket_name=self.ssm_bucket_name,
                ssm_cover_image_url=self.ssm_cover_image_url,
                ssm_bedrock_model_ids=self.ssm_bedrock_model_ids,
                ssm_assistant_avatar_url=self.ssm_assistant_avatar_url,
                ssm_state_machine_arn=self.api_constructs.ssm_state_machine_arn,
                state_machine_name=self.api_constructs.idp_bedrock_state_machine.state_machine_name,
            )

            self.cloudfront_distribution_name = output(
                self,
                id="CloudfrontDistributionName",
                value=self.streamlit_constructs.cloudfront.domain_name,
            )

            ## **************** Cognito Callback Updater ****************
            # This construct updates the Cognito User Pool Client with the CloudFront domain
            LOGGER.info("Creating Cognito Callback Updater")
            CognitoCallbackUpdater(
                self,
                f"{stack_name}-callback-updater",
                user_pool_id=self.cognito_authn.user_pool_id,
                client_id=self.cognito_authn.client_id,
                cloudfront_domain=self.streamlit_constructs.cloudfront.domain_name,
            )

        # suppress AwsSolutions-L1 on the shared provider framework Lambda
        NagSuppressions.add_stack_suppressions(
            self,
            [
                NagPackSuppression(
                    id="AwsSolutions-L1",
                    reason="Runtime for AWS Custom Resource provider framework Lambda is managed by CDK.",
                )
            ],
            apply_to_nested_stacks=True,
        )

        ## **************** Tags ****************
        Tags.of(self).add("StackName", stack_name)
        Tags.of(self).add("Team", "GenAIIC")
