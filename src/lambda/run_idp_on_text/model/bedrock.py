"""
Copyright © Amazon.com and Affiliates
"""

import boto3


def create_bedrock_client(bedrock_region, bedrock_config=None):
    return boto3.client(
        service_name="bedrock-runtime",
        region_name=bedrock_region,
        config=bedrock_config,
    )


def get_model_params() -> dict:
    return {
        "temperature": 0.0,  # temperature of the sampling process
        "stopSequences": [],  # words after which the generation is stopped
        "maxTokens": 4_096,  # max tokens to be generated
    }
