# Code Structure Guide

## Introduction

This document will help you navigate the codebase like a map. We'll explore each folder and important file, explaining what they do and how they fit together.

---

## Project Root Structure

```
intelligent-document-processing-with-amazon-bedrock/
├── app.py                    # 🎯 CDK app entry point
├── cdk.json                  # ⚙️  CDK configuration
├── config-example.yml        # 📝 Configuration template
├── pyproject.toml            # 📦 Python project metadata
├── requirements.txt          # 📦 Python dependencies
├── requirements-dev.txt      # 🔧 Development dependencies
├── install_deps.sh          # 🚀 Dependency installer
├── install_env.sh           # 🐍 Python venv setup
├── infra/                   # 🏗️  Infrastructure code (AWS CDK)
├── src/                     # 💻 Application source code
├── mcp/                     # 🔌 MCP servers
├── demo/                    # 🎓 Examples and demos
├── media/                   # 🖼️  Documentation images
└── docs/                    # 📚 Documentation (you are here!)
```

---

## Root-Level Files Explained

### `app.py` - The Entry Point
**Location:** `/app.py`
**Purpose:** Main entry point for AWS CDK deployment

**What it does:**
```python
#!/usr/bin/env python3
import aws_cdk as cdk
from infra.stack import IDPBedrockStack

# Create CDK app
app = cdk.App()

# Create the main stack
IDPBedrockStack(app, "IDPBedrockStack")

# Deploy!
app.synth()
```

**Key points:**
- This is what runs when you execute `cdk deploy`
- Loads configuration from `cdk.json` and `config.yml`
- Creates all AWS resources defined in `infra/`

**When you'll use it:** Usually you won't modify this file - it just ties everything together.

---

### `cdk.json` - CDK Configuration
**Location:** `/cdk.json`
**Purpose:** Tells CDK how to run your app

**Example content:**
```json
{
  "app": "python3 app.py",
  "context": {
    "@aws-cdk/core:newStyleStackSynthesis": true,
    "stack_name": "idp-bedrock",
    "stack_region": "us-east-1"
  }
}
```

**Important fields:**
- `"app"`: Command to execute the CDK app
- `"context"`: Configuration values available to all stacks

---

### `config-example.yml` - Your Deployment Settings
**Location:** `/config-example.yml`
**Purpose:** Template for your deployment configuration

**Copy it to create your own:**
```bash
cp config-example.yml config.yml
```

**What you'll configure:**
```yaml
# Stack basics
stack_name: my-idp-project
stack_region: us-east-1

# Lambda settings
lambda:
  architecture: X86_64
  python_runtime: PYTHON_3_13

# S3 encryption
s3:
  encryption: SSE-S3

# Bedrock models
bedrock:
  region: us-east-1
  model_ids:
    - anthropic.claude-3-sonnet-20240229-v1:0
    - us.amazon.nova-premier-v1:0

# User authentication
authentication:
  MFA: false
  users:
    - you@example.com

# Web UI
frontend:
  deploy_ecs: true
  ecs_memory: 2_048
  ecs_cpu: 1_024
```

**When to edit:** Before your first deployment!

---

### `pyproject.toml` - Python Project Metadata
**Location:** `/pyproject.toml`
**Purpose:** Defines project metadata and dependencies

**Key sections:**
```toml
[project]
name = "idp-bedrock"
version = "0.1.0"
requires-python = ">=3.10"

[project.dependencies]
aws-cdk-lib = "^2.0.0"
constructs = "^10.0.0"
boto3 = "^1.26.0"

[build-system]
requires = ["setuptools", "wheel"]
```

**What it includes:**
- Project name and version
- Python version requirement
- Dependencies and their versions
- Build system configuration

---

## Infrastructure Code (`infra/`)

This folder contains all the AWS resource definitions.

```
infra/
├── __init__.py
├── stack.py                 # 🏗️  Main stack
├── constructs/              # 🧩 Reusable components
│   ├── __init__.py
│   ├── api.py              # API Gateway + Lambda + Step Functions
│   ├── buckets.py          # S3 buckets
│   ├── cognito_auth.py     # Authentication
│   └── layers.py           # Lambda layers
└── stacks/
    ├── __init__.py
    └── ecs.py              # Web UI (Streamlit)
```

### `infra/stack.py` - Main Stack
**Location:** `/infra/stack.py`
**Purpose:** Orchestrates all infrastructure components

**Code walkthrough:**
```python
from aws_cdk import Stack
from constructs import Construct
from .constructs.buckets import IDPBedrockBuckets
from .constructs.cognito_auth import CognitoAuthenticationConstruct
from .constructs.api import IDPBedrockAPIConstructs
from .stacks.ecs import IDPBedrockECSStack

class IDPBedrockStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs):
        super().__init__(scope, construct_id, **kwargs)

        # 1. Create S3 buckets
        buckets = IDPBedrockBuckets(self, "Buckets")

        # 2. Set up authentication
        auth = CognitoAuthenticationConstruct(
            self, "Auth",
            bucket=buckets.document_bucket
        )

        # 3. Create API, Lambdas, Step Functions
        api = IDPBedrockAPIConstructs(
            self, "API",
            bucket=buckets.document_bucket,
            user_pool=auth.user_pool
        )

        # 4. Deploy web UI (optional)
        if config.get("frontend", {}).get("deploy_ecs"):
            ecs = IDPBedrockECSStack(
                self, "ECS",
                api_endpoint=api.api_url,
                user_pool=auth.user_pool
            )
```

**Flow:**
1. Create storage (S3)
2. Set up authentication (Cognito)
3. Build API infrastructure (Gateway, Lambdas, Step Functions)
4. Deploy web UI (ECS with Streamlit)

**When to modify:** When adding new AWS resources or changing overall architecture.

---

### `infra/constructs/buckets.py` - S3 Buckets
**Location:** `/infra/constructs/buckets.py`
**Purpose:** Creates and configures S3 buckets

**What it creates:**
```python
from aws_cdk import aws_s3 as s3
from aws_cdk import RemovalPolicy

class IDPBedrockBuckets(Construct):
    def __init__(self, scope, id, **kwargs):
        super().__init__(scope, id, **kwargs)

        # Main document bucket
        self.document_bucket = s3.Bucket(
            self, "DocumentBucket",
            bucket_name=f"{stack_name}-documents-{account_id}",
            encryption=s3.BucketEncryption.S3_MANAGED,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            versioning=True,
            removal_policy=RemovalPolicy.RETAIN  # Don't delete on stack deletion
        )
```

**Features configured:**
- Encryption (SSE-S3 or KMS)
- Versioning (keep old versions of files)
- Public access blocked (security)
- Lifecycle policies (auto-delete old files)

---

### `infra/constructs/cognito_auth.py` - Authentication
**Location:** `/infra/constructs/cognito_auth.py`
**Purpose:** Sets up user authentication

**What it creates:**
```python
from aws_cdk import aws_cognito as cognito

class CognitoAuthenticationConstruct(Construct):
    def __init__(self, scope, id, **kwargs):
        super().__init__(scope, id, **kwargs)

        # User Pool
        self.user_pool = cognito.UserPool(
            self, "UserPool",
            user_pool_name=f"{stack_name}-users",
            self_sign_up_enabled=False,  # Admin creates users
            sign_in_aliases=cognito.SignInAliases(
                email=True
            ),
            password_policy=cognito.PasswordPolicy(
                min_length=8,
                require_lowercase=True,
                require_uppercase=True,
                require_digits=True
            ),
            mfa=cognito.Mfa.OPTIONAL if config.get("MFA") else cognito.Mfa.OFF
        )

        # App Client (for web app)
        self.user_pool_client = self.user_pool.add_client(
            "AppClient",
            auth_flows=cognito.AuthFlow(
                user_password=True,
                user_srp=True
            )
        )

        # Create initial users
        for email in config.get("authentication", {}).get("users", []):
            cognito.CfnUserPoolUser(
                self, f"User{email.split('@')[0]}",
                user_pool_id=self.user_pool.user_pool_id,
                username=email,
                user_attributes=[
                    {"name": "email", "value": email}
                ]
            )
```

**Features:**
- Email-based login
- Password requirements
- Optional MFA
- Pre-created user accounts

---

### `infra/constructs/api.py` - The Heart of the System
**Location:** `/infra/constructs/api.py`
**Purpose:** Creates API Gateway, Lambda functions, and Step Functions

**This is a big file!** Let's break it down:

#### Part 1: Lambda Layers
```python
from aws_cdk import aws_lambda as lambda_

# Shared dependencies
idp_layer = lambda_.LayerVersion(
    self, "IDPBedrockLayer",
    code=lambda_.Code.from_asset("src/layers/idp_bedrock"),
    compatible_runtimes=[lambda_.Runtime.PYTHON_3_10],
    description="Core IDP Bedrock library"
)

textractor_layer = lambda_.LayerVersion(
    self, "TextractorLayer",
    code=lambda_.Code.from_asset("src/layers/textractor"),
    description="Document parsing library"
)
```

#### Part 2: Lambda Functions
```python
# Text extraction Lambda
run_textract_fn = lambda_.Function(
    self, "RunTextract",
    runtime=lambda_.Runtime.PYTHON_3_10,
    code=lambda_.Code.from_asset("src/lambda/run_textract"),
    handler="run_textract.lambda_handler",
    timeout=Duration.minutes(5),
    memory_size=512,
    layers=[textractor_layer, powertools_layer],
    environment={
        "BUCKET_NAME": bucket.bucket_name,
        "POWERTOOLS_SERVICE_NAME": "run_textract"
    }
)

# Grant permissions
bucket.grant_read_write(run_textract_fn)
```

**Pattern:** Each Lambda function follows this structure:
1. Define function properties
2. Attach layers
3. Set environment variables
4. Grant IAM permissions

#### Part 3: Step Functions State Machine
```python
from aws_cdk import aws_stepfunctions as sfn
from aws_cdk import aws_stepfunctions_tasks as tasks

# Load state machine definition
with open("src/step_functions/state_machine.json") as f:
    definition = json.load(f)

state_machine = sfn.StateMachine(
    self, "IDPStateMachine",
    definition_body=sfn.DefinitionBody.from_string(
        json.dumps(definition)
    ),
    timeout=Duration.minutes(30)
)
```

#### Part 4: API Gateway
```python
from aws_cdk import aws_apigateway as apigw

api = apigw.RestApi(
    self, "IDPAPI",
    rest_api_name="IDP Bedrock API",
    description="API for intelligent document processing"
)

# Add endpoints
extract = api.root.add_resource("extract")
extract.add_method(
    "POST",
    apigw.LambdaIntegration(start_extraction_fn),
    authorizer=cognito_authorizer
)

status = api.root.add_resource("status").add_resource("{jobId}")
status.add_method(
    "GET",
    apigw.LambdaIntegration(get_status_fn),
    authorizer=cognito_authorizer
)
```

**When to modify:** When adding new endpoints, Lambda functions, or changing the workflow.

---

### `infra/stacks/ecs.py` - Web UI Deployment
**Location:** `/infra/stacks/ecs.py`
**Purpose:** Deploys the Streamlit web interface

**What it creates:**
- ECS Cluster
- Fargate Service (serverless containers)
- Application Load Balancer
- CloudFront Distribution (CDN)
- Docker container with Streamlit app

**Key resources:**
```python
from aws_cdk import aws_ecs as ecs
from aws_cdk import aws_ec2 as ec2

# VPC for networking
vpc = ec2.Vpc(self, "VPC", max_azs=2)

# ECS Cluster
cluster = ecs.Cluster(self, "Cluster", vpc=vpc)

# Fargate Service (serverless containers)
service = ecs_patterns.ApplicationLoadBalancedFargateService(
    self, "StreamlitService",
    cluster=cluster,
    memory_limit_mib=2048,
    cpu=1024,
    task_image_options=ecs_patterns.ApplicationLoadBalancedTaskImageOptions(
        image=ecs.ContainerImage.from_asset("src/ecs"),
        container_port=8501,  # Streamlit default port
        environment={
            "API_ENDPOINT": api_endpoint,
            "USER_POOL_ID": user_pool.user_pool_id,
            "USER_POOL_CLIENT_ID": user_pool_client.user_pool_client_id
        }
    )
)
```

---

## Application Source Code (`src/`)

```
src/
├── lambda/                   # Lambda function code
│   ├── run_textract/
│   ├── run_idp_on_text/
│   ├── run_idp_on_image/
│   ├── read_office_file/
│   ├── run_bda/
│   ├── get_presigned_url/
│   ├── retrieve_from_ddb/
│   └── upload_few_shot/
├── layers/                   # Shared code libraries
│   ├── idp_bedrock/
│   ├── textractor/
│   └── extra_deps/
├── ecs/                      # Web UI code
│   └── src/
│       ├── Home.py
│       ├── components/
│       └── app_pages/
└── step_functions/
    └── state_machine.json    # Workflow definition
```

---

## Lambda Functions Deep Dive

### Structure of a Lambda Function Folder

Each Lambda function has this structure:
```
run_textract/
├── run_textract.py          # Main handler code
├── requirements.txt         # Python dependencies
└── README.md               # Documentation
```

### `src/lambda/run_textract/` - Text Extraction

**File:** `src/lambda/run_textract/run_textract.py`

**Code structure:**
```python
import boto3
import json
from aws_lambda_powertools import Logger, Tracer

logger = Logger()
tracer = Tracer()

# AWS clients
textract = boto3.client('textract')
s3 = boto3.client('s3')

@tracer.capture_lambda_handler
@logger.inject_lambda_context
def lambda_handler(event, context):
    """
    Extract text from document using AWS Textract.

    Input event:
    {
        "bucket": "my-bucket",
        "key": "documents/file.pdf",
        "job_id": "abc-123"
    }

    Returns:
    {
        "text": "Extracted text content...",
        "page_count": 3,
        "confidence": 98.5
    }
    """

    # 1. Get input parameters
    bucket = event['bucket']
    key = event['key']
    job_id = event['job_id']

    logger.info(f"Processing document: s3://{bucket}/{key}")

    # 2. Call Textract
    response = textract.detect_document_text(
        Document={
            'S3Object': {
                'Bucket': bucket,
                'Name': key
            }
        }
    )

    # 3. Parse response
    text = extract_text_from_response(response)

    # 4. Save extracted text to S3
    output_key = f"extracted-text/{job_id}/text.txt"
    s3.put_object(
        Bucket=bucket,
        Key=output_key,
        Body=text.encode('utf-8')
    )

    # 5. Return result
    return {
        'text': text,
        'text_s3_path': f"s3://{bucket}/{output_key}",
        'page_count': len(response['Blocks']),
        'job_id': job_id
    }


def extract_text_from_response(response):
    """Helper function to parse Textract response."""
    blocks = response['Blocks']
    text_blocks = [b for b in blocks if b['BlockType'] == 'LINE']
    text = '\n'.join([b['Text'] for b in text_blocks])
    return text
```

**Key patterns:**
1. **Lambda handler**: Function named `lambda_handler` with `(event, context)` parameters
2. **Input from event**: Extract parameters from `event` dict
3. **AWS service calls**: Use boto3 clients
4. **Error handling**: Try/except blocks (not shown for brevity)
5. **Return value**: Dict that becomes input to next step

---

### `src/lambda/run_idp_on_text/` - AI Extraction

**File:** `src/lambda/run_idp_on_text/run_idp_on_text.py`

**This is the most important Lambda!** It's where the AI magic happens.

**Code structure:**
```python
import boto3
import json
from typing import Dict, List

bedrock = boto3.client('bedrock-runtime')

def lambda_handler(event, context):
    """
    Extract attributes from text using Amazon Bedrock.

    Input event:
    {
        "text": "Document text content...",
        "attributes": {
            "invoice_number": "The invoice number",
            "total": "The total amount"
        },
        "model_id": "anthropic.claude-v2",
        "few_shot_examples": [...],  # Optional
        "job_id": "abc-123"
    }
    """

    # 1. Extract parameters
    text = event['text']
    attributes = event['attributes']
    model_id = event.get('model_id', 'anthropic.claude-v2')
    few_shot = event.get('few_shot_examples', [])

    # 2. Build prompt
    prompt = build_extraction_prompt(text, attributes, few_shot)

    # 3. Call Bedrock
    response = invoke_bedrock_model(model_id, prompt)

    # 4. Parse JSON response
    extracted_data = parse_response(response)

    # 5. Save results
    save_results(event['job_id'], extracted_data)

    return {
        'statusCode': 200,
        'extracted_data': extracted_data,
        'job_id': event['job_id']
    }


def build_extraction_prompt(text: str, attributes: Dict, few_shot: List) -> str:
    """
    Build the prompt for the AI model.
    """

    system_prompt = """You are an expert at extracting structured information
    from unstructured documents. Extract only the requested attributes and
    return them in valid JSON format."""

    # Build attribute descriptions
    attr_descriptions = []
    for key, description in attributes.items():
        attr_descriptions.append(f'- {key}: {description}')

    attributes_section = '\n'.join(attr_descriptions)

    # Build few-shot examples section
    examples_section = ""
    if few_shot:
        examples_section = "\n\nExamples:\n"
        for example in few_shot:
            examples_section += f"\nInput: {example['input']}"
            examples_section += f"\nOutput: {json.dumps(example['output'])}\n"

    # Assemble final prompt
    prompt = f"""{system_prompt}

Extract these attributes:
{attributes_section}
{examples_section}

Document text:
{text}

Return only valid JSON with the extracted attributes. Use null for missing fields.
"""

    return prompt


def invoke_bedrock_model(model_id: str, prompt: str) -> str:
    """
    Call Amazon Bedrock to run the AI model.
    """

    # Different models have different request formats
    if "anthropic" in model_id:
        body = {
            "anthropic_version": "bedrock-2023-05-31",
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "max_tokens": 2000,
            "temperature": 0.1
        }
    elif "meta.llama" in model_id:
        body = {
            "prompt": prompt,
            "max_gen_len": 2000,
            "temperature": 0.1
        }
    # ... other model formats

    # Invoke model
    response = bedrock.invoke_model(
        modelId=model_id,
        body=json.dumps(body)
    )

    # Parse response
    response_body = json.loads(response['body'].read())

    if "anthropic" in model_id:
        return response_body['content'][0]['text']
    elif "meta.llama" in model_id:
        return response_body['generation']
    # ... other model parsers


def parse_response(response_text: str) -> Dict:
    """
    Parse the AI's JSON response.
    """

    # Sometimes models wrap JSON in markdown
    # Example: ```json\n{...}\n```
    if "```json" in response_text:
        start = response_text.find("```json") + 7
        end = response_text.rfind("```")
        response_text = response_text[start:end].strip()

    # Parse JSON
    try:
        data = json.loads(response_text)
        return data
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON: {e}")
        logger.error(f"Response was: {response_text}")
        raise


def save_results(job_id: str, data: Dict):
    """
    Save extraction results to S3 and DynamoDB.
    """

    # Save to S3
    s3_key = f"results/{job_id}/extracted.json"
    s3.put_object(
        Bucket=os.environ['BUCKET_NAME'],
        Key=s3_key,
        Body=json.dumps(data, indent=2)
    )

    # Update DynamoDB
    ddb = boto3.client('dynamodb')
    ddb.update_item(
        TableName=os.environ['TABLE_NAME'],
        Key={'job_id': {'S': job_id}},
        UpdateExpression='SET #status = :status, result_path = :path',
        ExpressionAttributeNames={'#status': 'status'},
        ExpressionAttributeValues={
            ':status': {'S': 'COMPLETED'},
            ':path': {'S': f's3://{os.environ["BUCKET_NAME"]}/{s3_key}'}
        }
    )
```

**This Lambda is complex because:**
1. Builds sophisticated prompts
2. Handles multiple model formats
3. Parses various response formats
4. Implements token counting and truncation
5. Handles errors gracefully

---

### `src/lambda/read_office_file/` - Office Document Parser

**File:** `src/lambda/read_office_file/read_office_file.py`

**What it does:** Extracts text from .docx, .xlsx, .pptx files

**Key libraries used:**
```python
from docx import Document          # python-docx
from openpyxl import load_workbook # Excel
from pptx import Presentation      # PowerPoint
```

**Code structure:**
```python
def lambda_handler(event, context):
    file_path = download_from_s3(event['bucket'], event['key'])
    file_extension = event['key'].split('.')[-1].lower()

    if file_extension == 'docx':
        text = extract_from_word(file_path)
    elif file_extension == 'xlsx':
        text = extract_from_excel(file_path)
    elif file_extension == 'pptx':
        text = extract_from_powerpoint(file_path)
    else:
        raise ValueError(f"Unsupported file type: {file_extension}")

    return {'text': text}


def extract_from_word(file_path):
    """Extract text from Word document."""
    doc = Document(file_path)
    paragraphs = [p.text for p in doc.paragraphs]
    return '\n\n'.join(paragraphs)


def extract_from_excel(file_path):
    """Extract text from Excel spreadsheet."""
    wb = load_workbook(file_path, data_only=True)
    all_text = []

    for sheet_name in wb.sheetnames:
        sheet = wb[sheet_name]
        all_text.append(f"Sheet: {sheet_name}")

        for row in sheet.iter_rows(values_only=True):
            row_text = '\t'.join([str(cell) if cell else '' for cell in row])
            all_text.append(row_text)

    return '\n'.join(all_text)


def extract_from_powerpoint(file_path):
    """Extract text from PowerPoint."""
    prs = Presentation(file_path)
    all_text = []

    for slide_num, slide in enumerate(prs.slides, 1):
        all_text.append(f"Slide {slide_num}:")

        for shape in slide.shapes:
            if hasattr(shape, "text"):
                all_text.append(shape.text)

    return '\n\n'.join(all_text)
```

---

## Lambda Layers (`src/layers/`)

Layers contain shared code and dependencies.

### `src/layers/idp_bedrock/` - Core Library

**Structure:**
```
idp_bedrock/
├── python/                  # Required structure for layers
│   └── idp_bedrock/
│       ├── __init__.py
│       ├── client.py        # Python SDK client
│       ├── model/
│       │   ├── bedrock.py   # Bedrock utilities
│       │   └── parser.py    # Response parsing
│       └── messaging/
│           ├── events.py    # Event definitions
│           └── publisher.py # Event publishing
└── requirements.txt
```

**Example - Client Class:**
**File:** `src/layers/idp_bedrock/python/idp_bedrock/client.py`

```python
class IDPClient:
    """
    Python SDK for IDP Bedrock.

    Example usage:
        client = IDPClient()
        result = client.extract_attributes(
            file_path="invoice.pdf",
            attributes={"total": "The invoice total"}
        )
    """

    def __init__(self, api_endpoint=None, auth_token=None):
        self.api_endpoint = api_endpoint or os.environ.get('IDP_API_ENDPOINT')
        self.auth_token = auth_token or os.environ.get('IDP_AUTH_TOKEN')

    def extract_attributes(self, file_path, attributes, model_id=None, few_shot=None):
        """
        Extract attributes from a document.
        """
        # 1. Upload file
        upload_url = self._get_upload_url()
        self._upload_file(file_path, upload_url)

        # 2. Start extraction
        job_id = self._start_extraction(
            file_key=file_path,
            attributes=attributes,
            model_id=model_id,
            few_shot=few_shot
        )

        # 3. Wait for completion
        result = self._wait_for_completion(job_id, timeout=300)

        return result

    def _get_upload_url(self):
        """Get pre-signed upload URL."""
        response = requests.post(
            f"{self.api_endpoint}/upload-url",
            headers={"Authorization": f"Bearer {self.auth_token}"}
        )
        return response.json()['upload_url']

    # ... other methods
```

**This makes it easy for users:**
```python
# Instead of manual API calls, use the SDK
from idp_bedrock.client import IDPClient

client = IDPClient()
result = client.extract_attributes(
    file_path="my-doc.pdf",
    attributes={
        "invoice_number": "The invoice number",
        "total": "Total amount"
    }
)

print(result)
```

---

## Web UI Code (`src/ecs/src/`)

The Streamlit web application.

**Structure:**
```
src/ecs/src/
├── Dockerfile               # Container definition
├── Home.py                 # Main entry point
├── requirements.txt        # Python dependencies
├── components/             # Reusable UI components
│   ├── __init__.py
│   ├── auth.py            # Authentication
│   ├── file_upload.py     # File uploader
│   ├── attribute_form.py  # Attribute definition
│   └── results_table.py   # Results display
└── app_pages/             # Application pages
    ├── __init__.py
    ├── extract.py         # Extraction page
    ├── history.py         # Job history
    └── settings.py        # User settings
```

### `Home.py` - Main App
**File:** `src/ecs/src/Home.py`

```python
import streamlit as st
from components.auth import check_authentication
from app_pages import extract, history, settings

# Configure Streamlit
st.set_page_config(
    page_title="IDP Bedrock",
    page_icon="📄",
    layout="wide"
)

# Check if user is logged in
if not check_authentication():
    st.stop()  # Stop here if not authenticated

# Sidebar navigation
page = st.sidebar.selectbox(
    "Navigate",
    ["Extract Attributes", "Job History", "Settings"]
)

# Route to selected page
if page == "Extract Attributes":
    extract.show()
elif page == "Job History":
    history.show()
elif page == "Settings":
    settings.show()
```

### `app_pages/extract.py` - Extraction Page
**File:** `src/ecs/src/app_pages/extract.py`

```python
import streamlit as st
import requests
from components.file_upload import show_file_uploader
from components.attribute_form import show_attribute_form
from components.results_table import show_results

def show():
    """Display the extraction page."""

    st.title("📄 Extract Attributes from Documents")

    # Step 1: Upload file
    st.header("1. Upload Document")
    uploaded_file = show_file_uploader()

    if uploaded_file:
        st.success(f"Uploaded: {uploaded_file.name}")

        # Step 2: Define attributes
        st.header("2. Define Attributes to Extract")
        attributes = show_attribute_form()

        # Step 3: Choose model
        st.header("3. Select AI Model")
        model = st.selectbox(
            "Model",
            ["anthropic.claude-v2", "meta.llama3-70b", "amazon.titan-text"]
        )

        # Step 4: Submit
        if st.button("Extract", type="primary"):
            with st.spinner("Processing..."):
                job_id = submit_extraction(
                    file=uploaded_file,
                    attributes=attributes,
                    model=model
                )

                st.success(f"Job submitted: {job_id}")

                # Wait for results
                results = wait_for_results(job_id)

                # Display results
                st.header("Results")
                show_results(results)


def submit_extraction(file, attributes, model):
    """Submit extraction job to API."""

    # Get upload URL
    response = requests.post(
        f"{API_ENDPOINT}/upload-url",
        headers={"Authorization": f"Bearer {st.session_state.token}"}
    )
    upload_url = response.json()['upload_url']
    file_key = response.json()['key']

    # Upload file
    requests.put(upload_url, data=file.getvalue())

    # Start extraction
    response = requests.post(
        f"{API_ENDPOINT}/extract",
        headers={"Authorization": f"Bearer {st.session_state.token}"},
        json={
            "file_key": file_key,
            "attributes": attributes,
            "model_id": model
        }
    )

    return response.json()['job_id']
```

---

## Step Functions Definition

**File:** `src/step_functions/state_machine.json`

**This is a JSON file defining the workflow:**

```json
{
  "Comment": "IDP Bedrock Document Processing Workflow",
  "StartAt": "DetermineFileType",
  "States": {
    "DetermineFileType": {
      "Type": "Choice",
      "Choices": [
        {
          "Variable": "$.file_extension",
          "StringMatches": "*.pdf",
          "Next": "ExtractTextWithTextract"
        },
        {
          "Variable": "$.file_extension",
          "StringMatches": "*.docx",
          "Next": "ReadOfficeFile"
        }
      ],
      "Default": "ExtractTextWithTextract"
    },

    "ExtractTextWithTextract": {
      "Type": "Task",
      "Resource": "arn:aws:states:::lambda:invoke",
      "Parameters": {
        "FunctionName": "${RunTextractFunction}",
        "Payload.$": "$"
      },
      "ResultPath": "$.textract_result",
      "Next": "RunIDPOnText"
    },

    "ReadOfficeFile": {
      "Type": "Task",
      "Resource": "arn:aws:states:::lambda:invoke",
      "Parameters": {
        "FunctionName": "${ReadOfficeFileFunction}",
        "Payload.$": "$"
      },
      "ResultPath": "$.office_result",
      "Next": "RunIDPOnText"
    },

    "RunIDPOnText": {
      "Type": "Task",
      "Resource": "arn:aws:states:::lambda:invoke",
      "Parameters": {
        "FunctionName": "${RunIDPOnTextFunction}",
        "Payload.$": "$"
      },
      "ResultPath": "$.extraction_result",
      "Next": "SaveResults"
    },

    "SaveResults": {
      "Type": "Task",
      "Resource": "arn:aws:states:::dynamodb:putItem",
      "Parameters": {
        "TableName": "${ResultsTable}",
        "Item": {
          "job_id": {"S.$": "$.job_id"},
          "status": {"S": "COMPLETED"},
          "results.$": "$.extraction_result"
        }
      },
      "End": true
    }
  }
}
```

**Key sections:**
- **Choice states**: Route based on conditions
- **Task states**: Invoke Lambda functions
- **Parameters**: Pass data to tasks
- **ResultPath**: Where to store task output in the state data

---

## MCP Servers (`mcp/`)

**Structure:**
```
mcp/
├── local_server/            # Local development server
│   ├── server.py
│   └── requirements.txt
└── bedrock_server/          # Production server
    ├── server.py
    ├── lambda_handler.py
    └── requirements.txt
```

**File:** `mcp/local_server/server.py`

```python
from mcp.server import Server
from mcp.types import Tool, TextContent
import boto3

app = Server("idp-bedrock-mcp")

@app.list_tools()
async def list_tools() -> list[Tool]:
    """List available MCP tools."""
    return [
        Tool(
            name="extract_document_attributes",
            description="Extract structured attributes from documents",
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {"type": "string"},
                    "attributes": {"type": "object"}
                }
            }
        )
    ]

@app.call_tool()
async def call_tool(name: str, arguments: dict):
    """Handle tool calls."""
    if name == "extract_document_attributes":
        # Upload file to S3
        # Call API
        # Return results
        result = extract_attributes(
            arguments['file_path'],
            arguments['attributes']
        )
        return [TextContent(type="text", text=json.dumps(result))]
```

---

## Configuration Files

### `.gitignore`
```
# Python
__pycache__/
*.py[cod]
*$py.class
*.egg-info/
.venv/
venv/

# CDK
cdk.out/
.cdk.staging/

# Config
config.yml

# IDE
.vscode/
.idea/

# OS
.DS_Store
```

### `requirements.txt`
```
aws-cdk-lib>=2.0.0
constructs>=10.0.0
boto3>=1.26.0
pyyaml>=6.0
```

### `requirements-dev.txt`
```
pytest>=7.0.0
black>=22.0.0
flake8>=4.0.0
mypy>=0.950
```

---

## Summary

**Key takeaways:**

1. **Root level**: Entry points and configuration
2. **`infra/`**: All AWS infrastructure defined in Python
3. **`src/lambda/`**: Individual Lambda functions
4. **`src/layers/`**: Shared code and libraries
5. **`src/ecs/`**: Web UI application
6. **`mcp/`**: AI agent integration

**Navigation tips:**
- Start with `app.py` to understand deployment
- Look at `infra/stack.py` for resource relationships
- Dive into specific Lambdas for business logic
- Check `config-example.yml` for customization options

**Modification guide:**
- Adding a feature? Start in `src/lambda/`
- Changing infrastructure? Look in `infra/`
- Updating UI? Check `src/ecs/src/`
- New configuration? Edit `config.yml`

---

## Next Reading

- **HOW_IT_WORKS.md**: Follow a document through the system
- **GETTING_STARTED.md**: Deploy and test the system
