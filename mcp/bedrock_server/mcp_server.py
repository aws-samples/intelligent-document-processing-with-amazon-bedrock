"""
Tabulate MCP Server - Exposes document attribute extraction via MCP protocol
"""

import json
import os
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Union

import boto3
from mcp.server.fastmcp import FastMCP

# Initialize MCP server with stateless HTTP for AgentCore Runtime compatibility
mcp = FastMCP(host="0.0.0.0", stateless_http=True)

# Initialize AWS clients
stepfunctions_client = boto3.client("stepfunctions")
s3_client = boto3.client("s3")


def discover_step_functions(region, account_id):
    """Discover Step Functions state machine"""
    try:
        sf_client = boto3.client("stepfunctions", region_name=region)
        paginator = sf_client.get_paginator("list_state_machines")
        for page in paginator.paginate():
            for sm in page["stateMachines"]:
                if "idp-bedrock" in sm["name"].lower():
                    print(f"✅ Discovered Step Functions: {sm['stateMachineArn']}")
                    return sm["stateMachineArn"]
    except Exception as e:
        print(f"⚠️  Could not discover Step Functions: {e}")
    return None


def discover_s3_bucket(region):
    """Discover S3 bucket"""
    try:
        s3_client = boto3.client("s3", region_name=region)
        response = s3_client.list_buckets()
        for bucket in response["Buckets"]:
            if "idp-bedrock" in bucket["Name"].lower() and "data" in bucket["Name"].lower():
                print(f"✅ Discovered S3 bucket: {bucket['Name']}")
                return bucket["Name"]
    except Exception as e:
        print(f"⚠️  Could not discover S3 bucket: {e}")
    return None


def get_fallback_values(region, account_id):
    """Get fallback configuration values"""
    state_machine_arn = f"arn:aws:states:{region}:{account_id}:stateMachine:idp-bedrock-StepFunctions"
    bucket_name = f"idp-bedrock-data-{account_id}"
    print(f"⚠️  Using fallback Step Functions ARN: {state_machine_arn}")
    print(f"⚠️  Using fallback bucket name: {bucket_name}")
    return state_machine_arn, bucket_name


def get_hardcoded_fallbacks():
    """Get hardcoded fallback values as last resort"""
    state_machine_arn = "arn:aws:states:us-east-1:471112811980:stateMachine:idp-bedrock-StepFunctions"
    bucket_name = "idp-bedrock-data-471112811980"
    print("⚠️  Using hardcoded fallbacks")
    return state_machine_arn, bucket_name


def get_configuration():
    """Get configuration from environment variables or AWS discovery"""
    state_machine_arn = os.getenv("STATE_MACHINE_ARN")
    bucket_name = os.getenv("BUCKET_NAME")

    # If environment variables are not set, try to discover from AWS
    if not state_machine_arn or not bucket_name:
        print("⚠️  Environment variables not set, attempting AWS discovery...")
        try:
            boto_session = boto3.Session()
            region = boto_session.region_name
            account_id = boto3.client("sts").get_caller_identity()["Account"]

            if not state_machine_arn:
                state_machine_arn = discover_step_functions(region, account_id)

            if not bucket_name:
                bucket_name = discover_s3_bucket(region)

            # Use fallback naming patterns if discovery failed
            if not state_machine_arn or not bucket_name:
                fallback_sm, fallback_bucket = get_fallback_values(region, account_id)
                if not state_machine_arn:
                    state_machine_arn = fallback_sm
                if not bucket_name:
                    bucket_name = fallback_bucket

        except Exception as e:
            print(f"❌ Error during AWS discovery: {e}")
            state_machine_arn, bucket_name = get_hardcoded_fallbacks()

    return state_machine_arn, bucket_name


# Get configuration
STATE_MACHINE_ARN, BUCKET_NAME = get_configuration()

SUPPORTED_MODELS = [
    "us.anthropic.claude-opus-4-6-v1",
    "us.anthropic.claude-sonnet-4-6",
    "us.anthropic.claude-opus-4-1-20250805-v1:0",
    "us.anthropic.claude-sonnet-4-20250514-v1:0",
    "us.anthropic.claude-3-7-sonnet-20250219-v1:0",
    "us.anthropic.claude-3-5-sonnet-20241022-v2:0",
    "us.anthropic.claude-3-5-haiku-20241022-v1:0",
    "us.anthropic.claude-3-haiku-20240307-v1:0",
    "us.amazon.nova-premier-v1:0",
    "us.amazon.nova-pro-v1:0",
    "us.amazon.nova-lite-v1:0",
]


def is_presigned_url(path: str) -> bool:
    """Check if a path is a presigned URL"""
    return path.startswith(("http://", "https://")) and ("amazonaws.com" in path or "s3" in path)


def is_s3_uri(path: str) -> bool:
    """Check if a path is an S3 URI (s3://bucket/key)"""
    return path.startswith("s3://")


def download_from_presigned_url(presigned_url: str, bucket_name: str) -> str:
    """
    Download a file from a presigned URL and upload it to our S3 bucket

    Args:
        presigned_url: The presigned URL to download from
        bucket_name: Target S3 bucket name

    Returns:
        S3 key for the uploaded file

    Raises:
        Exception: If download or upload fails
    """
    from urllib.parse import urlparse

    import requests

    if not bucket_name:
        raise Exception("S3 bucket not configured. Cannot process presigned URLs.")

    try:
        # Download the file from the presigned URL
        response = requests.get(presigned_url, timeout=60)
        response.raise_for_status()

        # Extract filename from URL or generate one
        parsed_url = urlparse(presigned_url)
        filename = Path(parsed_url.path).name
        if not filename or filename == "/":
            filename = "downloaded_file"

        # Generate unique S3 key
        file_path = Path(filename)
        file_extension = file_path.suffix
        unique_id = str(uuid.uuid4())[:8]
        s3_key = f"uploaded/{file_path.stem}_{unique_id}{file_extension}"

        # Upload to our S3 bucket
        s3_client.put_object(
            Bucket=bucket_name,
            Key=s3_key,
            Body=response.content,
            ContentType=response.headers.get("content-type", "application/octet-stream"),
        )

        print(f"📥 Downloaded from presigned URL and uploaded to s3://{bucket_name}/{s3_key}")
        return s3_key

    except Exception as e:
        raise Exception(f"Failed to download from presigned URL {presigned_url}: {str(e)}") from e


def process_s3_uri(s3_uri: str, bucket_name: str) -> str:
    """
    Process an S3 URI and copy the file to our bucket if needed

    Args:
        s3_uri: S3 URI in format s3://bucket/key
        bucket_name: Target S3 bucket name

    Returns:
        S3 key for the file (either original or copied)

    Raises:
        Exception: If processing fails
    """
    if not bucket_name:
        raise Exception("S3 bucket not configured. Cannot process S3 URIs.")

    try:
        # Parse S3 URI
        if not s3_uri.startswith("s3://"):
            raise Exception(f"Invalid S3 URI format: {s3_uri}")

        uri_parts = s3_uri[5:].split("/", 1)  # Remove s3:// and split
        if len(uri_parts) != 2:
            raise Exception(f"Invalid S3 URI format: {s3_uri}")

        source_bucket, source_key = uri_parts

        # If it's already in our bucket, return the key as-is
        if source_bucket == bucket_name:
            print(f"📁 Using existing file in our bucket: {source_key}")
            return source_key

        # Copy from external bucket to our bucket
        file_path = Path(source_key)
        file_extension = file_path.suffix
        unique_id = str(uuid.uuid4())[:8]
        target_key = f"uploaded/{file_path.stem}_{unique_id}{file_extension}"

        # Copy the object
        copy_source = {"Bucket": source_bucket, "Key": source_key}
        s3_client.copy_object(CopySource=copy_source, Bucket=bucket_name, Key=target_key)

        print(f"📋 Copied from {s3_uri} to s3://{bucket_name}/{target_key}")
        return target_key

    except Exception as e:
        raise Exception(f"Failed to process S3 URI {s3_uri}: {str(e)}") from e


def process_document_paths(documents: List[str]) -> tuple[List[str], List[str]]:
    """
    Process document paths, handling S3 URIs, presigned URLs, and S3 keys

    Args:
        documents: List of document paths (S3 keys, S3 URIs, and presigned URLs)

    Returns:
        Tuple of (processed_s3_keys, upload_info)
    """
    processed_documents = []
    upload_info = []

    for doc_path in documents:
        if is_presigned_url(doc_path):
            # Presigned URL - download and upload to our bucket
            try:
                s3_key = download_from_presigned_url(doc_path, BUCKET_NAME)
                processed_documents.append(s3_key)
                upload_info.append(f"Downloaded from presigned URL → s3://{BUCKET_NAME}/{s3_key}")
            except Exception as e:
                raise Exception(f"Failed to process presigned URL {doc_path}: {str(e)}") from e
        elif is_s3_uri(doc_path):
            # S3 URI - copy to our bucket if needed
            try:
                s3_key = process_s3_uri(doc_path, BUCKET_NAME)
                processed_documents.append(s3_key)
                upload_info.append(f"Processed S3 URI {doc_path} → s3://{BUCKET_NAME}/{s3_key}")
            except Exception as e:
                raise Exception(f"Failed to process S3 URI {doc_path}: {str(e)}") from e
        else:
            # Assume it's already an S3 key in our bucket
            processed_documents.append(doc_path)
            upload_info.append(f"Using existing S3 key: {doc_path}")

    return processed_documents, upload_info


def run_idp_bedrock_api(
    state_machine_arn: str,
    documents: Union[str, Sequence[str]],
    attributes: Sequence[Dict[str, Any]],
    parsing_mode: Optional[str] = "Amazon Textract",
    instructions: Optional[str] = "",
    few_shots: Optional[Sequence[Dict[str, Any]]] = None,
    model_params: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """
    Run IDP Bedrock to extract custom attributes and scores from the text(s)
    This mirrors the functionality from demo/utils.py
    """
    if few_shots is None:
        few_shots = []

    if model_params is None:
        model_params = {
            "model_id": "us.anthropic.claude-3-7-sonnet-20250219-v1:0",
            "output_length": 2000,
            "temperature": 0.0,
        }

    if isinstance(documents, str):
        documents = [documents]

    event = json.dumps(
        {
            "attributes": attributes,
            "documents": documents,
            "instructions": instructions,
            "few_shots": few_shots,
            "model_params": model_params,
            "parsing_mode": parsing_mode,
        }
    )

    response = stepfunctions_client.start_execution(
        stateMachineArn=state_machine_arn,
        input=event,
    )

    execution_arn = response["executionArn"]

    while True:
        time.sleep(int(1))

        response = stepfunctions_client.describe_execution(executionArn=execution_arn)
        status = response["status"]

        if status == "FAILED":
            error_details = response.get("error", "Unknown error")
            raise Exception(f"Step Function execution failed: {error_details}")

        if status == "SUCCEEDED":
            outputs = json.loads(response["output"])
            results = []
            for output in outputs:
                results.append(
                    {"file_key": output["llm_answer"]["file_key"], "attributes": output["llm_answer"]["answer"]}
                )
            return results


@mcp.tool()
def extract_document_attributes(
    documents: List[str],
    attributes: List[Dict[str, Any]],
    parsing_mode: str = "Amazon Textract",
    instructions: str = "",
    few_shots: Optional[List[Dict[str, Any]]] = None,
    model_params: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Extract custom attributes from documents using Amazon Bedrock and AWS document processing services.

    This tool processes documents (text, PDF, images, Office files) and extracts specified attributes
    using large language models. It supports various parsing modes and can handle batch processing.

    **SUPPORTED INPUT TYPES**:
    - S3 keys: Used directly if in the configured bucket
    - S3 URIs: Files copied from external buckets if needed
    - Presigned URLs: Files downloaded and uploaded to our bucket

    Args:
        documents: List of document paths - supports multiple input types:
            S3 keys: ["originals/email_1.txt", "uploaded/doc_abc123.pdf"]
            S3 URIs: ["s3://my-bucket/documents/file.pdf", "s3://external-bucket/doc.txt"]
            Presigned URLs: ["https://bucket.s3.amazonaws.com/file.pdf?X-Amz-Signature=..."]
        attributes: List of attribute definitions, each containing:
            - name: str - Name of the attribute (e.g., "customer_name")
            - description: str - Description of what to extract
            - type: str (optional) - "auto", "character", "number", or "true/false"
        parsing_mode: str - "Amazon Textract", "Amazon Bedrock LLM", or "Bedrock Data Automation"
        instructions: str - Optional high-level instructions for extraction
        few_shots: List of example input/output pairs for few-shot learning
        model_params: Dict with model configuration:
            - model_id: str - Bedrock model ID to use
            - output_length: int - Maximum output length
            - temperature: float - Model temperature (0.0-1.0)

    Returns:
        Dict containing:
            - success: bool - Whether the operation succeeded
            - results: List - Extraction results for each file, each containing:
                - file_key: str - The document that was processed (S3 key)
                - attributes: Dict - Extracted attributes as key-value pairs
            - processed_documents: int - Number of documents processed
            - extracted_attributes: List[str] - Names of attributes extracted
            - upload_info: List[str] - Information about file processing (downloads, copies)

    Examples:
        # Process S3 files (mix of keys and URIs)
        extract_document_attributes(
            documents=["originals/email_1.txt", "s3://external-bucket/invoice.pdf"],
            attributes=[
                {"name": "customer_name", "description": "name of the customer"},
                {"name": "sentiment", "description": "sentiment score between 0 and 1"}
            ]
        )

        # Process presigned URLs
        extract_document_attributes(
            documents=["https://bucket.s3.amazonaws.com/document.pdf?X-Amz-Signature=..."],
            attributes=[
                {"name": "document_type", "description": "type of document"},
                {"name": "summary", "description": "brief summary of content"}
            ]
        )
    """
    if not STATE_MACHINE_ARN:
        raise Exception("STATE_MACHINE_ARN not configured. Please check deployment configuration.")

    if few_shots is None:
        few_shots = []

    if model_params is None:
        model_params = {
            "model_id": "us.anthropic.claude-3-7-sonnet-20250219-v1:0",
            "output_length": 2000,
            "temperature": 0.0,
        }

    try:
        # Process document paths - upload local files to S3 if needed
        processed_documents, upload_info = process_document_paths(documents)

        results = run_idp_bedrock_api(
            state_machine_arn=STATE_MACHINE_ARN,
            documents=processed_documents,
            attributes=attributes,
            parsing_mode=parsing_mode,
            instructions=instructions,
            few_shots=few_shots,
            model_params=model_params,
        )

        return {
            "success": True,
            "results": results,
            "processed_documents": len(documents),
            "extracted_attributes": [attr["name"] for attr in attributes],
            "upload_info": upload_info,
        }

    except Exception as e:
        return {"success": False, "error": str(e), "processed_documents": 0, "extracted_attributes": []}


@mcp.tool()
def get_extraction_status(execution_arn: str) -> Dict[str, Any]:
    """
    Check the status of a document attribute extraction operation.

    Args:
        execution_arn: The ARN of the Step Functions execution to check

    Returns:
        Dict containing:
            - status: str - "RUNNING", "SUCCEEDED", "FAILED", etc.
            - results: List - Results if completed successfully
            - error: str - Error message if failed
    """
    try:
        response = stepfunctions_client.describe_execution(executionArn=execution_arn)
        status = response["status"]

        result = {"status": status, "execution_arn": execution_arn}

        if status == "SUCCEEDED":
            outputs = json.loads(response["output"])
            results = []
            for output in outputs:
                results.append(
                    {"file_key": output["llm_answer"]["file_key"], "attributes": output["llm_answer"]["answer"]}
                )
            result["results"] = results

        elif status == "FAILED":
            result["error"] = response.get("error", "Unknown error")

        return result

    except Exception as e:
        return {"status": "ERROR", "error": str(e), "execution_arn": execution_arn}


@mcp.tool()
def list_supported_models() -> Dict[str, Any]:
    """
    Get the list of supported Amazon Bedrock models for document attribute extraction.

    Returns:
        Dict containing:
            - models: List of supported model IDs
            - default_model: The default model used if none specified
            - model_info: Additional information about model capabilities
    """
    return {
        "models": SUPPORTED_MODELS,
        "default_model": "us.anthropic.claude-3-7-sonnet-20250219-v1:0",
        "model_info": {
            "claude_models": [m for m in SUPPORTED_MODELS if "claude" in m],
            "nova_models": [m for m in SUPPORTED_MODELS if "nova" in m],
            "recommended_for_speed": "us.amazon.nova-lite-v1:0",
            "recommended_for_quality": "us.anthropic.claude-sonnet-4-20250514-v1:0",
        },
    }


@mcp.tool()
def get_bucket_info() -> Dict[str, Any]:
    """
    Get information about the S3 bucket used for document storage.

    Returns:
        Dict containing bucket name and usage instructions
    """
    return {
        "bucket_name": BUCKET_NAME or "Not configured",
        "usage": ("The extract_document_attributes tool supports S3 keys, S3 URIs, and presigned URLs"),
        "supported_formats": [
            "Text files: .txt",
            "PDF files: .pdf",
            "Images: .jpg, .jpeg, .png",
            "Office files: .doc, .docx, .ppt, .pptx, .xls, .xlsx",
            "Web files: .html, .htm, .md, .csv",
        ],
        "input_types": {
            "s3_keys": "Used directly if in configured bucket (e.g., 'originals/file.txt')",
            "s3_uris": "Copied from external buckets (e.g., 's3://bucket/file.pdf')",
            "presigned_urls": "Downloaded and processed (e.g., 'https://bucket.s3.amazonaws.com/file.pdf?...')",
        },
    }


# Note: Health check endpoint removed - FastMCP doesn't support @mcp.get() decorator
# The MCP server health can be checked by listing tools via MCP protocol

if __name__ == "__main__":
    print("🚀 Starting Tabulate MCP Server...")
    print("📋 Configuration:")
    print(f"   State Machine ARN: {STATE_MACHINE_ARN}")
    print(f"   S3 Bucket: {BUCKET_NAME}")
    print(f"   Supported Models: {len(SUPPORTED_MODELS)}")
    print(
        f"   Environment Variables Set: STATE_MACHINE_ARN={bool(os.getenv('STATE_MACHINE_ARN'))}, "
        f"BUCKET_NAME={bool(os.getenv('BUCKET_NAME'))}"
    )

    mcp.run(transport="streamable-http")
