#!/usr/bin/env python3
"""
IDP Bedrock MCP Server - Stdio Version
Exposes document attribute extraction via MCP protocol over stdio transport using FastMCP
"""

import json
import os
import sys
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Union

import boto3
from fastmcp import FastMCP

# Initialize FastMCP server
mcp = FastMCP("idp-bedrock")

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
                    print(f"✅ Discovered Step Functions: {sm['stateMachineArn']}", file=sys.stderr)
                    return sm["stateMachineArn"]
    except Exception as e:
        print(f"⚠️  Could not discover Step Functions: {e}", file=sys.stderr)
    return None


def discover_s3_bucket(region):
    """Discover S3 bucket"""
    try:
        s3_client = boto3.client("s3", region_name=region)
        response = s3_client.list_buckets()
        for bucket in response["Buckets"]:
            if "idp-bedrock" in bucket["Name"].lower() and "data" in bucket["Name"].lower():
                print(f"✅ Discovered S3 bucket: {bucket['Name']}", file=sys.stderr)
                return bucket["Name"]
    except Exception as e:
        print(f"⚠️  Could not discover S3 bucket: {e}", file=sys.stderr)
    return None


def get_fallback_values(region, account_id):
    """Get fallback configuration values"""
    state_machine_arn = f"arn:aws:states:{region}:{account_id}:stateMachine:idp-bedrock-StepFunctions"
    bucket_name = f"idp-bedrock-data-{account_id}"
    print(f"⚠️  Using fallback Step Functions ARN: {state_machine_arn}", file=sys.stderr)
    print(f"⚠️  Using fallback bucket name: {bucket_name}", file=sys.stderr)
    return state_machine_arn, bucket_name


def get_hardcoded_fallbacks():
    """Get hardcoded fallback values as last resort"""
    state_machine_arn = "arn:aws:states:us-east-1:471112811980:stateMachine:idp-bedrock-StepFunctions"
    bucket_name = "idp-bedrock-data-471112811980"
    print("⚠️  Using hardcoded fallbacks", file=sys.stderr)
    return state_machine_arn, bucket_name


def get_configuration():
    """Get configuration from environment variables or AWS discovery"""
    state_machine_arn = os.getenv("STATE_MACHINE_ARN")
    bucket_name = os.getenv("BUCKET_NAME")

    # If environment variables are not set, try to discover from AWS
    if not state_machine_arn or not bucket_name:
        print("⚠️  Environment variables not set, attempting AWS discovery...", file=sys.stderr)
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
            print(f"❌ Error during AWS discovery: {e}", file=sys.stderr)
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


def is_local_file(path: str) -> bool:
    """Check if a path is a local file path"""
    # Skip if it's a URL or S3 URI
    if is_presigned_url(path) or is_s3_uri(path):
        print(f"🔍 File detection for '{path}': skipping (URL/S3 URI)", file=sys.stderr)
        return False

    # Try the path as-is first
    path_obj = Path(path)
    if path_obj.exists() and path_obj.is_file():
        print(f"🔍 File detection for '{path}': FOUND as local file", file=sys.stderr)
        return True

    # If it's a relative path, try resolving it from current working directory
    if not path_obj.is_absolute():
        cwd = Path.cwd()
        resolved_path = cwd / path
        if resolved_path.exists() and resolved_path.is_file():
            print(f"🔍 File detection for '{path}': FOUND as local file (resolved from {cwd})", file=sys.stderr)
            return True

    # Try common locations if it's just a filename
    if "/" not in path and "\\" not in path:
        # Try current directory
        current_dir_path = Path.cwd() / path
        if current_dir_path.exists() and current_dir_path.is_file():
            print(f"🔍 File detection for '{path}': FOUND in current directory", file=sys.stderr)
            return True

        # Try common project directories
        common_dirs = ["demo/originals", "originals", "documents", "files"]
        for common_dir in common_dirs:
            project_path = Path.cwd() / common_dir / path
            if project_path.exists() and project_path.is_file():
                print(f"🔍 File detection for '{path}': FOUND at {project_path}", file=sys.stderr)
                return True

    print(f"🔍 File detection for '{path}': NOT FOUND (cwd: {Path.cwd()})", file=sys.stderr)
    return False


def _resolve_file_path(file_path: str) -> Path:
    """
    Resolve file path using various strategies.

    Args:
        file_path: Input file path

    Returns:
        Resolved Path object

    Raises:
        Exception: If file cannot be found
    """
    # Try the path as-is first
    path_obj = Path(file_path)
    if path_obj.exists() and path_obj.is_file():
        return path_obj

    # If it's a relative path, try resolving it from current working directory
    if not path_obj.is_absolute():
        cwd = Path.cwd()
        resolved_path_candidate = cwd / file_path
        if resolved_path_candidate.exists() and resolved_path_candidate.is_file():
            return resolved_path_candidate

    # Try common locations if it's just a filename
    if "/" not in file_path and "\\" not in file_path:
        # Try current directory
        current_dir_path = Path.cwd() / file_path
        if current_dir_path.exists() and current_dir_path.is_file():
            return current_dir_path

        # Try common project directories
        common_dirs = ["demo/originals", "originals", "documents", "files"]
        for common_dir in common_dirs:
            project_path = Path.cwd() / common_dir / file_path
            if project_path.exists() and project_path.is_file():
                return project_path

    raise Exception(f"Local file does not exist: {file_path} (searched in current dir: {Path.cwd()})")


def _get_content_type(file_extension: str) -> str:
    """
    Determine content type based on file extension.

    Args:
        file_extension: File extension including the dot

    Returns:
        MIME content type string
    """
    content_type_map = {
        ".pdf": "application/pdf",
        ".txt": "text/plain",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ".doc": "application/msword",
    }
    return content_type_map.get(file_extension.lower(), "application/octet-stream")


def upload_local_file(file_path: str, bucket_name: str) -> str:
    """
    Upload a local file to S3 bucket

    Args:
        file_path: Local file path
        bucket_name: Target S3 bucket name

    Returns:
        S3 key for the uploaded file

    Raises:
        Exception: If upload fails
    """
    if not bucket_name:
        raise Exception("S3 bucket not configured. Cannot upload local files.")

    try:
        # Resolve file path
        resolved_path = _resolve_file_path(file_path)
        print(f"📁 Resolved file path: {file_path} → {resolved_path}", file=sys.stderr)

        # Generate unique S3 key
        file_extension = resolved_path.suffix
        unique_id = str(uuid.uuid4())[:8]
        s3_key = f"uploaded/{resolved_path.stem}_{unique_id}{file_extension}"

        # Determine content type
        content_type = _get_content_type(file_extension)

        # Upload to S3 using the resolved path
        with open(resolved_path, "rb") as file_data:
            s3_client.put_object(
                Bucket=bucket_name,
                Key=s3_key,
                Body=file_data,
                ContentType=content_type,
            )

        # Verify the upload was successful by checking if the object exists
        try:
            s3_client.head_object(Bucket=bucket_name, Key=s3_key)
            print(f"📤 Uploaded local file {file_path} to s3://{bucket_name}/{s3_key}", file=sys.stderr)
        except Exception as verify_error:
            raise Exception(
                f"Upload verification failed for s3://{bucket_name}/{s3_key}: {str(verify_error)}"
            ) from verify_error

        # Brief wait for S3 consistency (much simpler now)
        time.sleep(int(1))

        return s3_key

    except Exception as e:
        raise Exception(f"Failed to upload local file {file_path}: {str(e)}") from e


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

        print(f"📥 Downloaded from presigned URL and uploaded to s3://{bucket_name}/{s3_key}", file=sys.stderr)
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
            print(f"📁 Using existing file in our bucket: {source_key}", file=sys.stderr)
            return source_key

        # Copy from external bucket to our bucket
        file_path = Path(source_key)
        file_extension = file_path.suffix
        unique_id = str(uuid.uuid4())[:8]
        target_key = f"uploaded/{file_path.stem}_{unique_id}{file_extension}"

        # Copy the object
        copy_source = {"Bucket": source_bucket, "Key": source_key}
        s3_client.copy_object(CopySource=copy_source, Bucket=bucket_name, Key=target_key)

        print(f"📋 Copied from {s3_uri} to s3://{bucket_name}/{target_key}", file=sys.stderr)
        return target_key

    except Exception as e:
        raise Exception(f"Failed to process S3 URI {s3_uri}: {str(e)}") from e


def process_document_paths(documents: List[str]) -> tuple[List[str], List[str]]:
    """
    Process document paths, handling local files, S3 URIs, presigned URLs, and S3 keys

    Args:
        documents: List of document paths (local files, S3 keys, S3 URIs, and presigned URLs)

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
        elif is_local_file(doc_path):
            # Local file - upload to our bucket
            try:
                s3_key = upload_local_file(doc_path, BUCKET_NAME)
                processed_documents.append(s3_key)
                upload_info.append(f"Uploaded local file {doc_path} → s3://{BUCKET_NAME}/{s3_key}")
            except Exception as e:
                raise Exception(f"Failed to upload local file {doc_path}: {str(e)}") from e
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

    print(f"🔍 Step Functions input: {event}", file=sys.stderr)

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
) -> str:
    """Extract custom attributes from documents using Amazon Bedrock and AWS document processing services.

    This tool processes documents (text, PDF, images, Office files) and extracts specified attributes
    using large language models. It supports various parsing modes and can handle batch processing.

    **SUPPORTED INPUT TYPES**:
    - Local files: Automatically uploaded to S3 (e.g., '/path/to/document.pdf', './file.txt')
    - S3 keys: Used directly if in the configured bucket (e.g., 'originals/file.txt')
    - S3 URIs: Files copied from external buckets if needed (e.g., 's3://bucket/file.pdf')
    - Presigned URLs: Files downloaded and uploaded to our bucket

    Args:
        documents: List of document paths - supports local files, S3 keys, S3 URIs, and presigned URLs
        attributes: List of attribute definitions to extract
        parsing_mode: Parsing mode to use (Amazon Textract, Amazon Bedrock LLM, Bedrock Data Automation)
        instructions: Optional high-level instructions for extraction
        few_shots: Optional example input/output pairs for few-shot learning
        model_params: Model configuration parameters

    Returns:
        JSON string with extraction results
    """
    try:
        if not STATE_MACHINE_ARN:
            raise Exception("STATE_MACHINE_ARN not configured. Please check deployment configuration.")

        if model_params is None:
            model_params = {
                "model_id": "us.anthropic.claude-3-haiku-20240307-v1:0",
                "output_length": 2000,
                "temperature": 0.0,
            }

        if few_shots is None:
            few_shots = []

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

        result = {
            "success": True,
            "results": results,
            "processed_documents": len(documents),
            "extracted_attributes": [attr["name"] for attr in attributes],
            "upload_info": upload_info,
        }

        return json.dumps(result, indent=2)

    except Exception as e:
        error_result = {"success": False, "error": str(e)}
        return json.dumps(error_result, indent=2)


@mcp.tool()
def get_extraction_status(execution_arn: str) -> str:
    """Check the status of a document attribute extraction operation.

    Args:
        execution_arn: The ARN of the Step Functions execution to check

    Returns:
        JSON string with status information
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

        return json.dumps(result, indent=2)

    except Exception as e:
        error_result = {"success": False, "error": str(e)}
        return json.dumps(error_result, indent=2)


@mcp.tool()
def list_supported_models() -> str:
    """Get the list of supported Amazon Bedrock models for document attribute extraction.

    Returns:
        JSON string with supported models information
    """
    result = {
        "models": SUPPORTED_MODELS,
        "default_model": "us.anthropic.claude-3-7-sonnet-20250219-v1:0",
        "model_info": {
            "claude_models": [m for m in SUPPORTED_MODELS if "claude" in m],
            "nova_models": [m for m in SUPPORTED_MODELS if "nova" in m],
            "recommended_for_speed": "us.amazon.nova-lite-v1:0",
            "recommended_for_quality": "us.anthropic.claude-sonnet-4-20250514-v1:0",
        },
    }

    return json.dumps(result, indent=2)


@mcp.tool()
def get_bucket_info() -> str:
    """Get information about the S3 bucket used for document storage.

    Returns:
        JSON string with bucket information
    """
    result = {
        "bucket_name": BUCKET_NAME or "Not configured",
        "usage": ("The extract_document_attributes tool supports local files, S3 keys, S3 URIs, and presigned URLs"),
        "supported_formats": [
            "Text files: .txt",
            "PDF files: .pdf",
            "Images: .jpg, .jpeg, .png",
            "Office files: .doc, .docx, .ppt, .pptx, .xls, .xlsx",
            "Web files: .html, .htm, .md, .csv",
        ],
        "input_types": {
            "local_files": "Automatically uploaded to S3 (e.g., '/path/to/document.pdf', './file.txt')",
            "s3_keys": "Used directly if in configured bucket (e.g., 'originals/file.txt')",
            "s3_uris": "Copied from external buckets (e.g., 's3://bucket/file.pdf')",
            "presigned_urls": "Downloaded and processed (e.g., 'https://bucket.s3.amazonaws.com/file.pdf?...')",
        },
    }

    return json.dumps(result, indent=2)


def main():
    """Main entry point for the MCP server"""
    print("🚀 Starting IDP Bedrock MCP Server (stdio)...", file=sys.stderr)
    print("📋 Configuration:", file=sys.stderr)
    print(f"   State Machine ARN: {STATE_MACHINE_ARN}", file=sys.stderr)
    print(f"   S3 Bucket: {BUCKET_NAME}", file=sys.stderr)
    print(f"   Supported Models: {len(SUPPORTED_MODELS)}", file=sys.stderr)
    print(
        f"   Environment Variables Set: STATE_MACHINE_ARN={bool(os.getenv('STATE_MACHINE_ARN'))}, "
        f"BUCKET_NAME={bool(os.getenv('BUCKET_NAME'))}",
        file=sys.stderr,
    )

    mcp.run()


if __name__ == "__main__":
    main()
