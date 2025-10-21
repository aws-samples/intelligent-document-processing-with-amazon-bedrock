# Understanding the Architecture

## Introduction

This document explains how the Intelligent Document Processing system is built. We'll use simple analogies and visual diagrams to help you understand each component and how they work together.

## The Big Picture: A Restaurant Analogy

Think of this system like a restaurant:

- **Frontend (Web Interface)** = Dining room where customers place orders
- **API Gateway** = Waiter who takes orders to the kitchen
- **Step Functions** = Head chef who coordinates all the cooks
- **Lambda Functions** = Individual cooks, each with a specialty
- **Amazon Bedrock** = Master chef consultant (the AI)
- **S3 Storage** = Pantry where ingredients (documents) are stored
- **DynamoDB** = Order tracking system

When you upload a document, it's like placing an order. The system routes it through different "stations" until you get your final result!

## Architecture Layers

### Layer 1: User Interaction Layer

This is how users interact with the system.

#### Option A: Web Interface (Streamlit)
```
User's Web Browser
        ↓
CloudFront CDN (content delivery)
        ↓
Application Load Balancer
        ↓
ECS Container (running Streamlit app)
        ↓
Cognito (checks: "Are you logged in?")
        ↓
API Gateway (processes your request)
```

**What's happening:**
1. You open a website in your browser
2. CloudFront serves the web pages quickly (it's like a cache)
3. The load balancer directs traffic to the app server
4. Streamlit app (written in Python) shows you the interface
5. Cognito verifies you're allowed to use the system
6. When you submit, it calls the API

#### Option B: Python SDK
```python
from idp_bedrock.client import IDPClient

# Your Python code directly calls the API
client = IDPClient()
result = client.extract_attributes(
    file_path="invoice.pdf",
    attributes={"total": "The total amount on the invoice"}
)
```

**What's happening:**
1. Your Python script imports the library
2. It creates a client object
3. Calls methods that send HTTP requests to the API
4. No web browser needed!

#### Option C: MCP (Model Context Protocol)
```
AI Agent (like Claude)
        ↓
MCP Server
        ↓
API Gateway
```

**What's happening:**
1. An AI assistant is talking to you
2. When you ask it to extract document info, it uses MCP
3. MCP is like a special protocol that lets AI tools call APIs
4. The AI can process documents on your behalf

---

### Layer 2: API Gateway Layer

**What is API Gateway?**
Think of it as a smart receptionist. It:
- Receives incoming requests
- Checks if you're authorized
- Routes requests to the right place
- Handles errors gracefully

**Endpoints Available:**

| Endpoint | What It Does | Example |
|----------|--------------|---------|
| `POST /extract` | Start a new extraction job | Upload a PDF and attribute list |
| `GET /status/{job_id}` | Check if job is done | "Is my extraction complete?" |
| `GET /results/{job_id}` | Get extraction results | Retrieve the extracted data |
| `POST /upload-url` | Get upload link | Request a URL to upload large files |
| `GET /models` | List available AI models | "What models can I use?" |

**Example Request:**
```http
POST /extract
Content-Type: application/json

{
  "document_url": "s3://my-bucket/invoice.pdf",
  "attributes": {
    "invoice_number": "The invoice number",
    "total_amount": "The total amount to be paid",
    "due_date": "When payment is due"
  },
  "model_id": "anthropic.claude-v2"
}
```

**Example Response:**
```json
{
  "job_id": "abc-123-xyz",
  "status": "PROCESSING",
  "message": "Your extraction job has started"
}
```

---

### Layer 3: Orchestration Layer (Step Functions)

**What are Step Functions?**
Imagine a flowchart that automatically executes. Step Functions is AWS's way of creating workflows.

**Our Workflow:**

```
START
  ↓
┌─────────────────────┐
│  Receive Document   │
└──────────┬──────────┘
           ↓
┌─────────────────────┐
│  What file type?    │ ← CHOICE STEP
└──────────┬──────────┘
           ↓
    ┌──────┴──────┬──────────┬─────────┐
    ↓             ↓          ↓         ↓
┌────────┐  ┌──────────┐ ┌──────┐ ┌────────┐
│ Image/ │  │  Office  │ │ Text │ │  BDA   │
│  PDF   │  │   File   │ │ File │ │ Mode   │
└───┬────┘  └─────┬────┘ └───┬──┘ └───┬────┘
    ↓             ↓          ↓        ↓
┌────────┐  ┌──────────┐     │    ┌────────┐
│Textract│  │ Extract  │     │    │Run BDA │
│Extract │  │  Text    │     │    │        │
└───┬────┘  └─────┬────┘     │    └───┬────┘
    ↓             ↓          ↓        ↓
    └──────┬──────┴──────────┴────────┘
           ↓
┌─────────────────────┐
│  Run AI Extraction  │
│   (Amazon Bedrock)  │
└──────────┬──────────┘
           ↓
┌─────────────────────┐
│   Parse Results     │
└──────────┬──────────┘
           ↓
┌─────────────────────┐
│  Save to S3 & DDB   │
└──────────┬──────────┘
           ↓
         END
```

**Step-by-Step Explanation:**

1. **Receive Document**: Gets information about the uploaded file
2. **Choice Step**: Like an `if/else` in programming - routes based on file type
3. **Parallel Processing**: Multiple paths for different document types
4. **AI Extraction**: All paths converge here - the AI reads and extracts
5. **Parse Results**: Converts AI response to structured data
6. **Save**: Stores results in database and cloud storage

**Why Use Step Functions?**
- **Automatic retries**: If a step fails, it tries again
- **Error handling**: Can catch errors and handle them gracefully
- **Visual monitoring**: You can see exactly where a job is in the workflow
- **Scalability**: Can run many workflows simultaneously

---

### Layer 4: Processing Layer (Lambda Functions)

**What are Lambda Functions?**
Think of them as small, focused programs that run in the cloud. You don't need to manage servers - AWS runs them for you.

**Key Lambda Functions in This Project:**

#### 1. `run_textract` - Text Extraction from Images/PDFs
**Location:** `src/lambda/run_textract/`

**What it does:**
```python
# Pseudo-code
def extract_text_from_document(s3_path):
    # Call AWS Textract service
    response = textract.analyze_document(s3_path)

    # Convert response to plain text
    text = parse_textract_response(response)

    # Save extracted text
    save_to_s3(text)

    return text
```

**Real example:** You upload a scanned invoice (image). This function uses AWS Textract to read all the text from the image.

#### 2. `run_idp_on_text` - AI Attribute Extraction from Text
**Location:** `src/lambda/run_idp_on_text/`

**What it does:**
```python
# Pseudo-code
def extract_attributes(text, attribute_definitions, model_id):
    # Build a prompt for the AI
    prompt = f"""
    You are an expert at extracting information from documents.

    Document text:
    {text}

    Extract these attributes:
    {attribute_definitions}

    Return JSON format.
    """

    # Call Amazon Bedrock (AI)
    ai_response = bedrock.invoke(model_id, prompt)

    # Parse the JSON response
    extracted_data = json.loads(ai_response)

    return extracted_data
```

**Real example:**
- Input: "Invoice #12345 dated 01/15/2024. Total: $599.99"
- Attributes: `{"invoice_number": "...", "date": "...", "total": "..."}`
- Output: `{"invoice_number": "12345", "date": "01/15/2024", "total": "$599.99"}`

#### 3. `run_idp_on_image` - AI Extraction Directly from Images
**Location:** `src/lambda/run_idp_on_image/`

**What it does:**
Uses vision-capable AI models (like Claude with vision) to extract information directly from images without text extraction first.

**When to use:** When layout, formatting, or visual elements matter (like charts, diagrams, forms with checkboxes)

#### 4. `read_office_file` - Extract from Word/Excel/PowerPoint
**Location:** `src/lambda/read_office_file/`

**What it does:**
```python
# Pseudo-code
def read_office_file(file_path, file_type):
    if file_type == "docx":
        text = extract_from_word(file_path)
    elif file_type == "xlsx":
        text = extract_from_excel(file_path)
    elif file_type == "pptx":
        text = extract_from_powerpoint(file_path)

    return text
```

Uses Python libraries like `python-docx`, `openpyxl`, and `python-pptx` to read these files.

#### 5. `get_presigned_url` - Generate Upload Links
**Location:** `src/lambda/get_presigned_url/`

**What it does:**
Creates a temporary, secure URL that allows you to upload files directly to S3.

**Why:** Your browser can upload huge files directly to S3 without going through the API, which is faster and cheaper.

```python
# Example of what it returns
{
  "upload_url": "https://s3.amazonaws.com/bucket/file?signature=xyz...",
  "expires_in": 3600  # 1 hour
}
```

#### 6. `retrieve_from_ddb` - Get Results from Database
**Location:** `src/lambda/retrieve_from_ddb/`

**What it does:**
Queries DynamoDB (database) to get the status and results of your extraction jobs.

```python
# Pseudo-code
def get_job_results(job_id):
    # Query database
    record = dynamodb.get_item(job_id)

    if record['status'] == 'COMPLETED':
        # Get results from S3
        results = s3.get_object(record['result_location'])
        return results
    else:
        return {"status": record['status'], "message": "Still processing"}
```

---

### Layer 5: AI Layer (Amazon Bedrock)

**What is Amazon Bedrock?**
It's AWS's service that gives you access to multiple AI models through a single API.

**Available Models:**

| Model Family | Provider | Best For | Cost Level |
|-------------|----------|----------|------------|
| Claude | Anthropic | Complex reasoning, long documents | $$$ |
| GPT | OpenAI | General purpose, creative tasks | $$$ |
| Llama | Meta | Open-source, customizable | $$ |
| Nova | Amazon | Fast, cost-effective | $ |
| Titan | Amazon | Embeddings, simple tasks | $ |

**How It Works:**

```python
# Simplified example
import boto3

bedrock = boto3.client('bedrock-runtime')

response = bedrock.invoke_model(
    modelId='anthropic.claude-v2',
    body={
        "prompt": "Extract the invoice total from: Invoice #123, Total: $500",
        "max_tokens": 1000,
        "temperature": 0.1
    }
)

# Response contains the AI's answer
print(response['body'])  # "$500"
```

**Important Settings:**

- **Temperature**: How creative vs. precise (0 = precise, 1 = creative)
  - For data extraction, use low temperature (0.1-0.3)

- **Max Tokens**: Maximum length of response
  - 1 token ≈ 0.75 words
  - For extraction tasks, usually 1000-2000 tokens is enough

- **Top P**: Another creativity control (usually keep at 0.9-1.0)

---

### Layer 6: Storage Layer

#### Amazon S3 (Simple Storage Service)
**What it stores:**
- Original uploaded documents
- Extracted text files
- AI responses (JSON)
- Processing logs

**Bucket Structure:**
```
idp-bedrock-bucket/
├── uploads/
│   ├── user123/
│   │   ├── invoice-2024-01.pdf
│   │   └── receipt-2024-02.jpg
├── extracted-text/
│   ├── job-abc-123/
│   │   └── extracted.txt
└── results/
    ├── job-abc-123/
    │   └── results.json
```

**Security:**
- Encryption at rest (SSE-S3 or KMS)
- Private by default (not publicly accessible)
- Pre-signed URLs for temporary access

#### DynamoDB (NoSQL Database)
**What it stores:**
- Job metadata (ID, status, timestamps)
- User information
- Processing statistics

**Example Record:**
```json
{
  "job_id": "abc-123-xyz",
  "user_id": "user@example.com",
  "status": "COMPLETED",
  "created_at": "2024-01-15T10:30:00Z",
  "completed_at": "2024-01-15T10:30:45Z",
  "document_type": "PDF",
  "model_used": "claude-v2",
  "result_s3_path": "s3://bucket/results/abc-123-xyz/results.json",
  "token_count": 1250
}
```

**Why DynamoDB?**
- Very fast lookups (milliseconds)
- Scales automatically
- Pay only for what you use
- Perfect for key-value lookups (like job_id → status)

---

### Layer 7: Security Layer

#### Amazon Cognito (Authentication)
**What it does:**
Manages user accounts and login.

**User Flow:**
```
1. User visits website
2. Redirected to Cognito login page
3. Enters email/password
4. Cognito verifies credentials
5. Returns JWT token (like a temporary pass)
6. User includes token with each request
7. API Gateway validates token before processing
```

**Features Available:**
- Email/password authentication
- Password reset via email
- Multi-factor authentication (MFA) - optional
- Session management

#### KMS (Key Management Service)
**What it does:**
Encrypts sensitive data.

**What gets encrypted:**
- Documents in S3
- Database records
- Communication between services

**How it works:**
1. You upload a document
2. S3 asks KMS for an encryption key
3. KMS generates a unique key
4. S3 encrypts the document
5. When you download, S3 asks KMS to decrypt
6. You get the original file

**You don't need to do anything** - it's automatic!

#### IAM (Identity and Access Management)
**What it does:**
Controls what each component can do.

**Example Policy:**
```json
{
  "Effect": "Allow",
  "Action": "s3:GetObject",
  "Resource": "arn:aws:s3:::my-bucket/*"
}
```

Translation: "Allow reading objects from my-bucket"

**Principle of Least Privilege:**
Each Lambda function can only access what it needs:
- `run_textract` can call Textract and read/write S3
- `retrieve_from_ddb` can only read DynamoDB
- Users can only access their own documents

---

## How Components Communicate

### 1. Synchronous Communication (Request-Response)
```
API Gateway → Lambda → Response
```
**Example:** Getting job status
- You ask: "Is job abc-123 done?"
- Lambda checks database
- Returns: "Yes, here are the results"
- All happens in 1-2 seconds

### 2. Asynchronous Communication (Event-Driven)
```
Step Functions → Lambda (triggered by event)
```
**Example:** Document processing
- Step Functions says: "Run text extraction"
- Lambda starts processing
- Step Functions moves to next step
- They don't wait for each other

### 3. Service-to-Service Communication
```
Lambda → Bedrock API
Lambda → S3 API
Lambda → DynamoDB API
```
All AWS services talk to each other using APIs.

---

## Data Flow: Complete Example

Let's trace what happens when you extract invoice information:

### Step 1: Upload Document
```
You → Web UI → API Gateway → get_presigned_url Lambda
                                      ↓
                            Returns upload URL
                                      ↓
You → S3 (direct upload) → Document stored
```

### Step 2: Start Extraction
```
You → Web UI → API Gateway → Step Functions
                                      ↓
                            Job created, returns job_id
                                      ↓
                            DynamoDB (save job record)
```

### Step 3: Processing (Automated)
```
Step Functions → Check file type
                      ↓
                  PDF detected
                      ↓
            run_textract Lambda
                      ↓
        AWS Textract (extract text)
                      ↓
          Save text to S3
                      ↓
      run_idp_on_text Lambda
                      ↓
      Build prompt with attributes
                      ↓
        Amazon Bedrock (Claude AI)
                      ↓
        Parse JSON response
                      ↓
    Save results to S3 & DynamoDB
                      ↓
          Status: COMPLETED
```

### Step 4: Get Results
```
You → Web UI → API Gateway → retrieve_from_ddb Lambda
                                      ↓
                            Query DynamoDB for job_id
                                      ↓
                              Get S3 path from record
                                      ↓
                            Download results from S3
                                      ↓
                              Return to you
```

Total time: Usually 10-60 seconds depending on document size and model speed.

---

## Scaling and Performance

### How It Scales

**Small Usage (1-10 documents/day):**
- Cost: A few cents per day
- Speed: 10-30 seconds per document
- Resources: Minimal Lambda executions

**Medium Usage (100-1,000 documents/day):**
- Cost: $5-20 per day
- Speed: Same (Lambda scales automatically)
- Resources: Multiple Lambda instances run in parallel

**Large Usage (10,000+ documents/day):**
- Cost: $100-500+ per day
- Speed: Same (still parallel)
- Resources: AWS automatically adds capacity
- May need to request quota increases

**Key Point:** You don't need to manage servers or worry about capacity. AWS scales automatically!

### Performance Optimizations

1. **Lambda Layers**: Shared code loaded once, not with every function
2. **CloudFront CDN**: Web UI loads fast globally
3. **DynamoDB Indexing**: Fast job lookups
4. **S3 Transfer Acceleration**: Faster uploads from distant locations
5. **Provisioned Concurrency**: Can pre-warm Lambda functions for instant starts

---

## Cost Breakdown

Typical cost for processing 1,000 PDF pages:

| Service | Cost | What It Does |
|---------|------|--------------|
| Textract | $15 | Text extraction (1,000 pages × $0.015) |
| Bedrock (Claude) | $3-6 | AI extraction (~2M tokens) |
| Lambda | $0.20 | Function executions |
| S3 | $0.05 | Storage (1GB for a month) |
| DynamoDB | $0.10 | Database operations |
| **Total** | **~$18-21** | For 1,000 pages |

**Per page:** About $0.018-0.021 (less than 3 cents)

---

## Summary

The architecture is designed with these principles:

1. **Serverless**: No servers to manage - AWS handles infrastructure
2. **Scalable**: Handles 1 or 1 million documents automatically
3. **Secure**: Encryption, authentication, least-privilege access
4. **Cost-effective**: Pay only for what you use
5. **Modular**: Each component does one thing well
6. **Resilient**: Automatic retries and error handling

The system is like an assembly line where each station (Lambda function) has a specific job, the foreman (Step Functions) coordinates everything, and the AI (Bedrock) provides the intelligence to understand and extract information.

---

## Next Reading

- **KEY_CONCEPTS.md**: Deep dive into technical terms
- **CODE_STRUCTURE.md**: Understand the codebase organization
- **HOW_IT_WORKS.md**: Detailed workflow explanations
