"""
Copyright © Amazon.com and Affiliates
"""

import copy
import logging
import os
import random
import time
from typing import Any, Union

import boto3
import botocore
from botocore.exceptions import ClientError

LOGGER = logging.getLogger("CallBedrock")
logging.basicConfig(level=logging.INFO)
REGION = os.environ.get("BEDROCK_REGION")

config = botocore.config.Config(
    connect_timeout=120,
    read_timeout=120,
    retries={
        "max_attempts": 10,
        "mode": "adaptive",  # Adaptive retry mode for throttling
    },
)


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


def generate_conversation(
    bedrock_client: Any,
    model_id: str,
    system_prompts: list[dict],
    messages: list[dict],
    logger: logging.Logger = LOGGER,
    temperature: float = 0.0,
    top_k: int = 200,
    thinking_budget: int = 0,
    retry_model_id: str = "anthropic.claude-3-5-sonnet-20240620-v1:0",
):
    """
    Sends messages to a model

    Args:
        bedrock_client: The Boto3 Bedrock runtime client.
        model_id (str): The model ID to use.
        system_prompts (JSON) : The system prompts for the model to use.
        messages (JSON) : The messages to send to the model.

    Returns:
        response (JSON): The conversation that the model generated.
    """
    logger.info("Generating message with model %s", model_id)

    # Get base inference parameters and customize them
    inference_config = get_model_params()
    inference_config["temperature"] = temperature

    # Additional inference parameters to use
    additional_model_fields: dict[str, Any] = {}
    if "claude" in model_id:
        additional_model_fields["top_k"] = top_k
    if "claude-3-7-sonnet" in model_id and thinking_budget > 0:
        additional_model_fields["thinking"] = {
            "type": "enabled",
            "budget_tokens": thinking_budget,
        }
        # temperature must be set to 1 when thinking is enabled
        inference_config["temperature"] = 1.0
    start_time = time.time()

    # Send the message
    try:
        response = bedrock_client.converse(
            modelId=model_id,
            messages=messages,
            system=system_prompts,
            inferenceConfig=inference_config,
            additionalModelRequestFields=additional_model_fields,
        )

    except bedrock_client.exceptions.ThrottlingException as e:
        logger.error("Throttling error: %s", e)
        # Implement proper retry mechanism with exponential backoff
        max_retries = 5
        retry_count = 0
        retry_model_id = model_id  # Use original model for retries

        while retry_count < max_retries:
            retry_count += 1
            # Exponential backoff with jitter for more effective retries
            # 2^retry_count * (0.8 to 1.2 random jitter) seconds
            backoff_time = (2**retry_count) * (0.8 + random.random() * 0.4)
            logger.info(
                f"Retry attempt {retry_count}/{max_retries} after {backoff_time:.2f} "
                f"seconds with model {retry_model_id}"
            )
            time.sleep(int(backoff_time))

            try:
                response = bedrock_client.converse(
                    modelId=retry_model_id,
                    messages=messages,
                    system=system_prompts,
                    inferenceConfig=inference_config,
                    additionalModelRequestFields=additional_model_fields,
                )
                logger.info(f"Retry {retry_count} successful")
                break  # Break the retry loop on success
            except bedrock_client.exceptions.ThrottlingException as retry_e:
                logger.error(f"Throttling error on retry {retry_count}: {retry_e}")
                # If we're on the last retry and still getting throttled, try fallback model
                if retry_count == max_retries - 1:
                    logger.info(f"Using fallback model {retry_model_id} for final retry")
                if retry_count == max_retries:
                    raise Exception(f"Failed after {max_retries} retries due to throttling") from retry_e
            except Exception as other_e:
                logger.error(f"Other error on retry {retry_count}: {other_e}")
                raise  # Re-raise non-throttling exceptions

    end_time = time.time()
    # Log token usage.
    token_usage = response["usage"]
    logger.info("Input tokens: %s", token_usage["inputTokens"])
    logger.info("Output tokens: %s", token_usage["outputTokens"])
    logger.info("Total tokens: %s", token_usage["totalTokens"])
    logger.info("Stop reason: %s", response["stopReason"])
    logger.info(f"Bedrock generate_conversation call took {end_time - start_time:.2f} seconds")

    return response


def call_bedrock(
    messages: list[dict] = [],  # noqa: B006
    model_id: str = "anthropic.claude-3-sonnet-20240229-v1:0",
    system_prompt: str = "Act as a useful assistant",
    profile_name: str = "",
    bedrock_client: Union[Any, None] = None,
    temperature: float = 0.0,
    top_k: int = 200,
    thinking_budget: int = 0,
    logger: logging.Logger = LOGGER,
):
    """
    Entrypoint for calling Bedrock models

    Args:
        messages (list): Messages to send to the model
        model (str, optional): Model name. Defaults to "Haiku_35".
        system_prompt (str, optional): System prompt for the model. Defaults to None.
        profile_name (str, optional): AWS profile name to use. Defaults to None.
        bedrock_client (boto3.client, optional): Existing Bedrock client. Defaults to None.
        temperature (float, optional): Sampling temperature. Defaults to 0.0.
        top_k (int, optional): Top-k sampling parameter. Defaults to 200.
        thinking_budget (int, optional): Thinking budget for Claude 3.7. Defaults to 0.
        logger (logging.Logger, optional): Logger to use. Defaults to LOGGER.
    """
    # Initialize messages if None
    if messages is None:
        messages = []

    # If no bedrock_client is provided, create one with optional profile
    if bedrock_client is None:
        if profile_name:
            # Create a session with the specified profile
            session = boto3.Session(profile_name=profile_name)
            # Create client using the session directly since create_bedrock_client doesn't accept session parameter
            bedrock_client = session.client(service_name="bedrock-runtime", region_name=REGION, config=config)
        else:
            # Use default client
            bedrock_client = create_bedrock_client(REGION, config)

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    # Setup the system prompts and messages to send to the model.
    if system_prompt:
        system_prompts = [{"text": system_prompt}]
    else:
        system_prompts = [{"text": "Act as a useful assistant"}]

    try:
        response = generate_conversation(
            bedrock_client=bedrock_client,
            model_id=model_id,
            system_prompts=system_prompts,
            messages=messages,
            temperature=temperature,
            top_k=top_k,
            logger=logger,
            thinking_budget=thinking_budget,
        )

        # Add the response message to the conversation.
        output_message = response["output"]["message"]
        out_messages = copy.copy(messages)
        out_messages.append(output_message)
        try:
            if "text" in output_message["content"][0]:
                output_message = output_message["content"][0]["text"]
            else:
                output_message = output_message["content"][1]["text"]
        except (KeyError, IndexError):
            print("could not find text in response message")
            return "", []

        return output_message, out_messages

    except ClientError as err:
        message = err.response["Error"]["Message"]
        logger.error("A client error occurred: %s", message)
        print(f"A client error occurred: {message}")
        return "", []
