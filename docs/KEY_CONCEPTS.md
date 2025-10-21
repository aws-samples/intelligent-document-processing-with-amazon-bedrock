# Key Concepts for Beginners

## Introduction

This document explains all the technical terms and concepts you'll encounter in this project. Each concept is explained from the ground up, assuming you're new to programming and cloud computing.

---

## Programming Concepts

### What is Python?

**Simple Definition:** A programming language that's easy to read and write.

**Why we use it:**
- Looks almost like English
- Great for data processing and AI
- Huge ecosystem of libraries (pre-written code you can use)

**Example:**
```python
# This is Python code - notice how readable it is!
def calculate_total(price, quantity):
    total = price * quantity
    return total

# Using the function
result = calculate_total(10.99, 3)
print(result)  # Shows: 32.97
```

**In this project:** Almost everything is written in Python - the Lambda functions, web UI, and infrastructure code.

---

### What is a Function?

**Simple Definition:** A reusable block of code that does a specific task.

**Analogy:** Like a recipe. You write it once, use it many times.

**Example:**
```python
# Define a function
def greet_user(name):
    message = f"Hello, {name}!"
    return message

# Use the function
greeting = greet_user("Alice")  # Returns "Hello, Alice!"
greeting = greet_user("Bob")    # Returns "Hello, Bob!"
```

**Parts of a function:**
- **Name**: `greet_user` - what you call it
- **Parameters**: `name` - input it needs
- **Body**: The code inside (the recipe steps)
- **Return**: The output it gives back

**In this project:** Each Lambda function is literally a function that processes documents.

---

### What is an API?

**Simple Definition:** Application Programming Interface - a way for programs to talk to each other.

**Analogy:** Like a menu at a restaurant:
- The menu shows what you can order (available endpoints)
- You make a request (place an order)
- The kitchen prepares it (server processes)
- You get a response (your food arrives)

**Example HTTP Request:**
```http
POST /extract
{
  "document": "invoice.pdf",
  "attributes": {"total": "The invoice total"}
}
```

**Example HTTP Response:**
```json
{
  "job_id": "abc-123",
  "status": "PROCESSING"
}
```

**Types of API requests:**
- **GET**: Retrieve information (like viewing a menu)
- **POST**: Send information (like placing an order)
- **PUT**: Update information (like changing your order)
- **DELETE**: Remove information (like canceling your order)

**In this project:** The API Gateway exposes endpoints that let you upload documents and get results.

---

### What is JSON?

**Simple Definition:** JavaScript Object Notation - a format for organizing data.

**Why it's useful:** Both humans and computers can read it easily.

**Example:**
```json
{
  "invoice_number": "INV-2024-001",
  "date": "2024-01-15",
  "items": [
    {
      "name": "Widget",
      "price": 29.99,
      "quantity": 2
    }
  ],
  "total": 59.98
}
```

**Rules:**
- Use curly braces `{}` for objects
- Use square brackets `[]` for lists
- Put keys in quotes: `"key": "value"`
- Separate items with commas

**In this project:**
- You define attributes in JSON
- AI returns extracted data in JSON
- API responses are in JSON

---

### What are Environment Variables?

**Simple Definition:** Settings stored outside your code.

**Why use them:**
- Keep secrets safe (passwords, API keys)
- Change behavior without changing code
- Different settings for dev/production

**Example:**
```python
import os

# Read from environment
bucket_name = os.environ.get('BUCKET_NAME')
api_key = os.environ.get('API_KEY')

# Use them
upload_to_bucket(bucket_name, file)
```

**Setting environment variables:**
```bash
# In terminal (Linux/Mac)
export BUCKET_NAME="my-bucket"
export API_KEY="secret-key-123"

# In Windows
set BUCKET_NAME=my-bucket
set API_KEY=secret-key-123
```

**In this project:** Lambda functions use environment variables for bucket names, model IDs, and region settings.

---

## Cloud Computing Concepts

### What is "The Cloud"?

**Simple Definition:** Someone else's computer that you rent.

**More accurate:** Data centers owned by companies (AWS, Google, Microsoft) where you can run your programs and store your data.

**Benefits:**
- No hardware to buy
- No maintenance (they handle it)
- Scale up or down instantly
- Pay only for what you use

**Analogy:** Like renting an apartment vs. building a house. You get the benefits without the hassle of ownership.

---

### What is AWS?

**Simple Definition:** Amazon Web Services - Amazon's cloud computing platform.

**What they offer:**
- Servers (EC2, Lambda)
- Storage (S3)
- Databases (DynamoDB, RDS)
- AI services (Bedrock, SageMaker)
- Networking (VPC, CloudFront)
- And 200+ other services!

**In this project:** We use about 10 different AWS services to build a complete solution.

---

### What is Serverless?

**Simple Definition:** Running code without managing servers.

**Traditional way:**
1. Buy a server
2. Install operating system
3. Install your software
4. Monitor it 24/7
5. Scale by buying more servers

**Serverless way:**
1. Write your code
2. Upload it
3. AWS runs it when needed
4. AWS handles everything else

**Benefits:**
- No servers to manage
- Automatic scaling
- Pay only when code runs
- Built-in high availability

**Analogy:**
- Traditional = Owning a car (maintenance, insurance, parking)
- Serverless = Uber (pay per ride, no maintenance)

**In this project:** Lambda, API Gateway, and Step Functions are all serverless.

---

### What is a Region?

**Simple Definition:** A geographic location where AWS has data centers.

**Examples:**
- `us-east-1` = Northern Virginia, USA
- `eu-west-1` = Ireland
- `ap-southeast-1` = Singapore

**Why it matters:**
- **Latency**: Choose a region close to your users
- **Compliance**: Some data must stay in certain countries
- **Cost**: Prices vary by region
- **Service availability**: New services launch in some regions first

**In this project:** You configure which region to deploy to in `config.yml`.

---

## AWS Services Explained

### Amazon S3 (Simple Storage Service)

**Simple Definition:** Cloud storage for files.

**Concepts:**

**Bucket:** Like a folder, but at the top level
```
my-app-bucket/           ← Bucket
  ├── documents/         ← Folder (called "prefix")
  │   ├── file1.pdf
  │   └── file2.docx
  └── images/
      └── photo.jpg
```

**Object:** A file stored in S3
- Has a key (path): `documents/file1.pdf`
- Has content: The actual file data
- Has metadata: Size, type, upload date, etc.

**S3 URL formats:**
```
s3://bucket-name/path/to/file.pdf           ← S3 URI
https://bucket-name.s3.amazonaws.com/path   ← HTTPS URL
```

**Storage classes:**
- **Standard**: Fast access, higher cost
- **Infrequent Access**: Cheaper, for files you rarely need
- **Glacier**: Very cheap, for archives

**In this project:** S3 stores uploaded documents, extracted text, and results.

---

### AWS Lambda

**Simple Definition:** Run code without servers. You upload a function, AWS runs it when triggered.

**Concepts:**

**Function:** Your code packaged as a deployment unit
```python
# This is a Lambda function
def lambda_handler(event, context):
    # 'event' contains the input data
    # 'context' has information about the execution

    name = event.get('name', 'World')
    message = f"Hello, {name}!"

    return {
        'statusCode': 200,
        'body': message
    }
```

**Trigger:** What starts the function
- API Gateway request
- File uploaded to S3
- Scheduled time (cron job)
- Another AWS service

**Execution environment:**
- You choose: memory (128 MB to 10 GB)
- CPU scales with memory
- Maximum runtime: 15 minutes
- Temporary disk space: 512 MB to 10 GB

**Lambda Layers:** Shared code/libraries
```
Lambda Function
    ├── Your code (unique)
    └── Lambda Layer (shared)
        ├── python-docx library
        ├── boto3 library
        └── custom utilities
```

**Benefits:**
- Auto-scaling (1 to 1000s of instances)
- Pay per 100ms of execution
- No idle charges

**In this project:** We have 6 different Lambda functions, each doing a specific task.

---

### Amazon API Gateway

**Simple Definition:** Creates and manages APIs for your applications.

**What it does:**
1. Receives HTTP requests
2. Validates the request
3. Checks authentication
4. Routes to appropriate Lambda
5. Returns the response

**Types:**

**REST API:** Traditional API
```
POST /extract
GET /status/{jobId}
DELETE /job/{jobId}
```

**HTTP API:** Simpler, cheaper, faster
```
ANY /extract
ANY /{proxy+}
```

**WebSocket API:** For real-time two-way communication

**Features:**
- Request validation (is the data correct?)
- Rate limiting (max requests per second)
- API keys (for tracking usage)
- CORS (cross-origin requests)

**In this project:** API Gateway is the front door - all requests come through here.

---

### AWS Step Functions

**Simple Definition:** Visual workflow service - coordinates multiple steps.

**Concepts:**

**State Machine:** The workflow definition
```json
{
  "StartAt": "ExtractText",
  "States": {
    "ExtractText": {
      "Type": "Task",
      "Resource": "arn:aws:lambda:...:run_textract",
      "Next": "ProcessWithAI"
    },
    "ProcessWithAI": {
      "Type": "Task",
      "Resource": "arn:aws:lambda:...:run_idp",
      "End": true
    }
  }
}
```

**State types:**
- **Task**: Do something (call Lambda, API, etc.)
- **Choice**: If/else logic
- **Parallel**: Run multiple things at once
- **Wait**: Pause for a time
- **Succeed/Fail**: End states

**Error handling:**
```json
{
  "Retry": [
    {
      "ErrorEquals": ["NetworkError"],
      "MaxAttempts": 3,
      "BackoffRate": 2.0
    }
  ]
}
```

If a step fails with NetworkError, retry up to 3 times, waiting 1s, then 2s, then 4s.

**In this project:** Step Functions orchestrates the document processing pipeline.

---

### Amazon DynamoDB

**Simple Definition:** Fast NoSQL database.

**SQL vs. NoSQL:**

**SQL (Relational):**
```
Table: Invoices
+----+--------------+-------+
| ID | Date         | Total |
+----+--------------+-------+
| 1  | 2024-01-15   | 99.99 |
| 2  | 2024-01-16   | 49.99 |
+----+--------------+-------+
```

**NoSQL (DynamoDB):**
```json
{
  "invoice_id": "1",
  "date": "2024-01-15",
  "total": 99.99,
  "items": [
    {"name": "Widget", "price": 49.99},
    {"name": "Gadget", "price": 50.00}
  ],
  "customer": {
    "name": "John Doe",
    "email": "john@example.com"
  }
}
```

**Key concepts:**

**Partition Key:** Unique identifier (like invoice_id)
**Sort Key:** Optional second part of key (like date)
**Attributes:** The data fields (can be different for each item!)

**Querying:**
```python
# Get one item
response = table.get_item(Key={'job_id': 'abc-123'})

# Query multiple items
response = table.query(
    KeyConditionExpression='user_id = :user',
    ExpressionAttributeValues={':user': 'user@example.com'}
)
```

**Capacity modes:**
- **On-demand**: Pay per request, auto-scales
- **Provisioned**: Set read/write capacity, cheaper if predictable

**In this project:** DynamoDB stores job metadata and status.

---

### Amazon Bedrock

**Simple Definition:** Access multiple AI models through one API.

**Concepts:**

**Foundation Model:** Large pre-trained AI model
- Trained on massive datasets
- Can understand and generate text
- Some can understand images too

**Available model families:**
```
Anthropic Claude    → Best for: reasoning, long documents
Meta Llama          → Best for: open-source, customization
Amazon Titan        → Best for: embeddings, simple tasks
Cohere Command      → Best for: enterprise, multilingual
AI21 Jurassic       → Best for: specific languages
Stability AI        → Best for: image generation
```

**Model ID format:**
```
anthropic.claude-v2                          ← Basic model
anthropic.claude-v2:1                        ← Specific version
anthropic.claude-3-sonnet-20240229-v1:0      ← Detailed version
```

**Inference parameters:**

```python
{
    "prompt": "Extract the total from this invoice...",
    "max_tokens": 2000,        # Maximum response length
    "temperature": 0.1,        # Creativity (0=precise, 1=creative)
    "top_p": 0.9,              # Diversity of word choice
    "stop_sequences": ["\n\n"] # When to stop generating
}
```

**Tokens:** Units of text
- 1 token ≈ 4 characters
- 1 token ≈ 0.75 words
- "Hello world" ≈ 2 tokens
- This paragraph ≈ 50 tokens

**Pricing:** Usually per 1,000 tokens
- Input tokens: $0.003 - $0.015 per 1K
- Output tokens: $0.015 - $0.075 per 1K

**In this project:** Bedrock is the AI brain that reads documents and extracts information.

---

### Amazon Textract

**Simple Definition:** OCR (Optical Character Recognition) service - extracts text from images and PDFs.

**What it can do:**

**Text detection:**
```
Image of handwritten note
        ↓
"Please call me tomorrow at 555-1234"
```

**Table extraction:**
```
Image of table
        ↓
CSV or JSON with table data
```

**Form extraction:**
```
Image of filled form
        ↓
Key-value pairs: {"Name": "John Doe", "Date": "01/15/2024"}
```

**Features:**
- Handles handwriting
- Detects printed text
- Understands layouts (forms, tables)
- Supports many languages
- Works on scanned documents

**Pricing:** Per page
- Text detection: $0.0015/page
- Forms: $0.05/page
- Tables: $0.015/page

**In this project:** Textract extracts text from scanned PDFs and images before AI processing.

---

### Amazon Cognito

**Simple Definition:** User authentication and management service.

**Concepts:**

**User Pool:** Database of users
```
Users:
  - user1@example.com (verified)
  - user2@example.com (pending)
  - user3@example.com (verified)
```

**Identity Pool:** Temporary AWS credentials for users

**Authentication flow:**
```
1. User enters email/password
2. Cognito checks credentials
3. Cognito returns JWT tokens
4. User includes token in API requests
5. API Gateway validates token
6. Request is authorized
```

**JWT (JSON Web Token):** Encrypted token containing user info
```
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkw...
```

Decodes to:
```json
{
  "sub": "user-id-123",
  "email": "user@example.com",
  "exp": 1704067200  // Expiration timestamp
}
```

**Features:**
- Email verification
- Password reset
- Multi-factor authentication (MFA)
- Social login (Google, Facebook)
- Custom authentication flows

**In this project:** Cognito manages user logins for the web UI and API access.

---

## Infrastructure as Code Concepts

### What is Infrastructure as Code (IaC)?

**Simple Definition:** Defining cloud resources using code instead of clicking in a web console.

**Without IaC:**
1. Log into AWS console
2. Click "Create S3 bucket"
3. Fill out form
4. Click "Create Lambda function"
5. Upload code
6. Configure settings
7. Repeat for all resources...

**With IaC:**
```python
# Define everything in code
bucket = s3.Bucket("my-bucket")
function = lambda_.Function(
    "my-function",
    code=lambda_.Code.from_asset("./code")
)
```

Then run one command: `cdk deploy`

**Benefits:**
- **Repeatable**: Deploy identical environments
- **Version controlled**: Track changes over time
- **Documented**: Code shows exactly what you have
- **Testable**: Validate before deploying
- **Shareable**: Others can use your infrastructure

---

### What is AWS CDK?

**Simple Definition:** AWS Cloud Development Kit - write infrastructure using programming languages (Python, TypeScript, etc.)

**CDK vs. other tools:**

| Tool | Language | Level |
|------|----------|-------|
| **CloudFormation** | YAML/JSON | Low-level (verbose) |
| **CDK** | Python/TS/Java | High-level (concise) |
| **Terraform** | HCL | Multi-cloud |

**CDK example:**
```python
from aws_cdk import (
    Stack,
    aws_s3 as s3,
    aws_lambda as lambda_
)

class MyStack(Stack):
    def __init__(self, scope, id):
        super().__init__(scope, id)

        # Create S3 bucket - just 1 line!
        bucket = s3.Bucket(self, "MyBucket")

        # Create Lambda function
        function = lambda_.Function(
            self, "MyFunction",
            runtime=lambda_.Runtime.PYTHON_3_10,
            code=lambda_.Code.from_asset("./my_function"),
            handler="index.handler"
        )

        # Grant Lambda permission to read bucket
        bucket.grant_read(function)
```

**CDK workflow:**
```bash
cdk init          # Create new project
cdk synth         # Generate CloudFormation template
cdk diff          # Show what will change
cdk deploy        # Deploy to AWS
cdk destroy       # Delete all resources
```

**In this project:** All infrastructure is defined in Python using CDK (see `infra/` folder).

---

## AI and Machine Learning Concepts

### What is a Large Language Model (LLM)?

**Simple Definition:** An AI trained on huge amounts of text to understand and generate human-like language.

**How they're trained:**
1. Collect billions of web pages, books, articles
2. Train neural network to predict next word
3. Repeat trillions of times
4. Result: Model that "understands" language

**What they can do:**
- Answer questions
- Summarize text
- Extract information
- Translate languages
- Write code
- Generate creative content

**What they can't do (well):**
- Math (they approximate, not calculate)
- Factual guarantee (they can "hallucinate")
- Access real-time information
- Execute code (they generate it)

**In this project:** We use LLMs (Claude, GPT, etc.) to extract structured information from unstructured documents.

---

### What is Prompt Engineering?

**Simple Definition:** Crafting instructions to get the best results from AI.

**Bad prompt:**
```
Extract invoice data
```

**Good prompt:**
```
You are an expert at extracting information from invoices.

From the invoice text below, extract the following information:
- invoice_number: The unique invoice identifier
- date: The invoice date in YYYY-MM-DD format
- total: The total amount as a number

Return only valid JSON. If a field is not found, use null.

Invoice text:
[document content]
```

**Techniques:**

**1. Role-playing:** "You are an expert..."
```
You are an expert accountant with 20 years of experience...
```

**2. Few-shot learning:** Show examples
```
Example 1:
Input: "Invoice #123, Total: $100"
Output: {"invoice_number": "123", "total": 100}

Example 2:
Input: "Order 456, Amount due: $50.00"
Output: {"invoice_number": "456", "total": 50}

Now extract from: [your document]
```

**3. Clear constraints:**
```
- Return ONLY JSON, no explanations
- Use null for missing fields
- Dates must be YYYY-MM-DD format
- Numbers should not include currency symbols
```

**In this project:** The Lambda functions build prompts with system instructions, attributes, examples, and document text.

---

### What is Few-Shot Learning?

**Simple Definition:** Teaching AI by example.

**Zero-shot:** No examples
```
Extract the urgency level from this customer message.
Message: "My order hasn't arrived and I need it for tomorrow's meeting!"
```

**Few-shot:** With examples
```
Examples:
- "Just checking on my order" → Urgency: Low
- "Need this ASAP for meeting tomorrow!" → Urgency: High
- "Product broken, need replacement" → Urgency: Medium

Now classify:
Message: "My order hasn't arrived and I need it for tomorrow's meeting!"
→ Urgency: High
```

**When to use:**
- Custom categories or formats
- Ambiguous tasks
- Specific output format needed
- Domain-specific terminology

**In this project:** You can upload few-shot examples to improve extraction accuracy for your specific use case.

---

### What is Temperature?

**Simple Definition:** Controls randomness in AI responses.

**Temperature = 0:**
- Always picks the most likely next word
- Responses are consistent and predictable
- Good for: Data extraction, factual answers

**Temperature = 1:**
- Sometimes picks less likely words
- Responses are creative and varied
- Good for: Creative writing, brainstorming

**Example:**

**Prompt:** "The capital of France is"

| Temperature | Possible completions |
|-------------|---------------------|
| 0.0 | "Paris." (100% of the time) |
| 0.5 | "Paris." (95%), "Paris, France." (5%) |
| 1.0 | "Paris." (70%), "Paris, France." (20%), "Paris, a beautiful city" (10%) |

**In this project:** We use low temperature (0.1-0.3) for extraction to ensure consistent, accurate results.

---

## Security Concepts

### What is Encryption?

**Simple Definition:** Scrambling data so only authorized people can read it.

**Analogy:** Like sending a locked box. Only someone with the key can open it.

**Types:**

**Encryption at rest:** Data stored on disk
```
Original file: "Secret document content"
Encrypted file: "8f7d6e5c4b3a2918f7d6e5c..."
```

**Encryption in transit:** Data being sent over network
```
Your browser → HTTPS (encrypted) → Server
```

**How it works:**
```python
# Simplified example
key = "my-secret-key-123"
plaintext = "Sensitive data"

# Encrypt
encrypted = encrypt(plaintext, key)
# Result: "k8f9d7e6c5b4a..."

# Decrypt (only works with correct key)
decrypted = decrypt(encrypted, key)
# Result: "Sensitive data"
```

**In this project:**
- S3 encrypts documents at rest
- DynamoDB encrypts database records
- All API communication uses HTTPS (TLS encryption)

---

### What is IAM (Identity and Access Management)?

**Simple Definition:** Controls who can do what in AWS.

**Concepts:**

**User:** A person or application
```
alice@example.com
jenkins-build-server
```

**Role:** A set of permissions that can be assumed
```
LambdaExecutionRole:
  - Can read from S3
  - Can write to DynamoDB
  - Can invoke Bedrock
```

**Policy:** Document defining permissions
```json
{
  "Effect": "Allow",
  "Action": "s3:GetObject",
  "Resource": "arn:aws:s3:::my-bucket/*"
}
```

Translation: "Allow reading any object from my-bucket"

**Permission flow:**
```
Lambda function tries to read S3 file
        ↓
AWS checks: Does Lambda's role allow s3:GetObject?
        ↓
Yes: Read succeeds
No: Access denied error
```

**Principle of least privilege:** Give only the permissions needed
```
# Bad - too broad
{
  "Action": "*",  // Can do anything!
  "Resource": "*"  // On everything!
}

# Good - specific
{
  "Action": "s3:GetObject",
  "Resource": "arn:aws:s3:::specific-bucket/specific-folder/*"
}
```

**In this project:** Each Lambda has its own role with only the permissions it needs.

---

### What is MFA (Multi-Factor Authentication)?

**Simple Definition:** Requiring two proofs of identity.

**Factors:**
1. **Something you know:** Password
2. **Something you have:** Phone, security key
3. **Something you are:** Fingerprint, face

**Common MFA methods:**
- SMS code: "Enter the code we texted you"
- Authenticator app: Google Authenticator, Authy
- Hardware token: YubiKey

**Example flow:**
```
1. Enter email/password ✓
2. Receive code on phone: "123456"
3. Enter code ✓
4. Access granted
```

**Why use it:** Even if someone steals your password, they can't log in without your phone.

**In this project:** You can optionally enable MFA for Cognito user authentication.

---

## Document Processing Concepts

### What is OCR (Optical Character Recognition)?

**Simple Definition:** Converting images of text into actual text.

**Example:**
```
Input: Photo of a sign reading "OPEN"
Output: The text "OPEN"
```

**Challenges:**
- Handwriting variations
- Poor image quality
- Different fonts
- Background noise
- Rotated or skewed text

**Modern OCR (like Textract) can handle:**
- Printed text in any font
- Handwritten text
- Text in tables and forms
- Multiple languages
- Complex layouts

**In this project:** AWS Textract performs OCR on scanned documents before AI extraction.

---

### What is Document Extraction?

**Simple Definition:** Pulling specific pieces of information from a document.

**Levels:**

**Level 1: Full text extraction**
```
PDF → "Invoice #123 Date: 01/15/2024 Total: $599.99"
```

**Level 2: Field extraction**
```
Document → {
  "invoice_number": "123",
  "date": "01/15/2024",
  "total": 599.99
}
```

**Level 3: Semantic extraction**
```
Document → {
  "urgency": "High",
  "sentiment": "Negative",
  "category": "Complaint",
  "suggested_action": "Immediate refund"
}
```

**Traditional approach:**
- Write regex patterns
- Define extraction rules
- Handle variations manually
- Takes weeks to build

**AI approach (this project):**
- Describe what you want
- AI figures out how to extract
- Takes minutes to set up

---

### What is an Attribute?

**In this project's context:** A piece of information you want to extract.

**Example attributes:**
```json
{
  "product_name": "The name of the product being reviewed",
  "rating": "Star rating from 1-5",
  "sentiment": "Positive, Negative, or Neutral",
  "main_complaint": "The primary issue mentioned, if any",
  "would_recommend": "Whether the reviewer would recommend this product"
}
```

**Good attribute definitions:**
- **Clear**: "The invoice total amount"
- **Specific**: "The due date in MM/DD/YYYY format"
- **Unambiguous**: "The customer's email address"

**Bad attribute definitions:**
- **Vague**: "Important information"
- **Ambiguous**: "The date" (which date?)
- **Multiple items**: "Name and address" (split into two)

---

## Workflow and Process Concepts

### What is Event-Driven Architecture?

**Simple Definition:** Components communicate by sending and reacting to events.

**Traditional (synchronous):**
```
Step 1 → Wait → Step 2 → Wait → Step 3
```

**Event-driven (asynchronous):**
```
Event 1 triggered → Step 1 executes
Event 2 triggered → Step 2 executes (in parallel!)
Event 3 triggered → Step 3 executes
```

**Example:**
```
File uploaded to S3
        ↓ (triggers event)
Lambda processes file
        ↓ (publishes event)
Another Lambda sends notification
```

**Benefits:**
- Components are loosely coupled
- Easy to add new reactions
- Natural parallelism
- Resilient to failures

**In this project:** Uploading a document triggers Step Functions, which triggers various Lambdas.

---

### What is Asynchronous Processing?

**Simple Definition:** Starting a task and continuing without waiting for it to finish.

**Synchronous (wait):**
```python
result = process_document()  # Wait here until done (could be minutes!)
print(result)
```

**Asynchronous (don't wait):**
```python
job_id = start_processing_document()  # Returns immediately
print(f"Job started: {job_id}")

# Later, check if done
status = check_status(job_id)
if status == "COMPLETED":
    result = get_results(job_id)
```

**Benefits:**
- Don't block waiting
- Can process many at once
- Better user experience
- More scalable

**In this project:** Document processing is async - you get a job_id immediately and check status later.

---

### What is Idempotency?

**Simple Definition:** Doing the same operation multiple times has the same effect as doing it once.

**Idempotent operations:**
```python
# Setting a value - idempotent
status = "COMPLETED"  # Run 100 times, status is still "COMPLETED"

# Deleting a file - idempotent
delete_file("test.txt")  # Run 100 times, file is still deleted

# GET requests - idempotent
get_user(123)  # Doesn't change anything
```

**Not idempotent:**
```python
# Incrementing - not idempotent
counter = counter + 1  # Run 100 times, counter is 100 different values

# Appending - not idempotent
list.append(item)  # Run 100 times, list has 100 copies of item

# POST requests - usually not idempotent
create_user({"name": "Alice"})  # Run 100 times, creates 100 users
```

**Why it matters:** If something fails and retries, you don't want duplicate results.

**In this project:** Job IDs ensure idempotency - resubmitting the same job doesn't create duplicates.

---

## Summary

You now understand:

1. **Programming basics**: Functions, APIs, JSON, environment variables
2. **Cloud concepts**: AWS, serverless, regions, scaling
3. **AWS services**: S3, Lambda, API Gateway, Step Functions, DynamoDB, Bedrock, Textract, Cognito
4. **Infrastructure**: IaC, CDK, deployment
5. **AI concepts**: LLMs, prompts, temperature, few-shot learning
6. **Security**: Encryption, IAM, MFA
7. **Document processing**: OCR, extraction, attributes
8. **Workflows**: Events, async processing, idempotency

These concepts form the foundation for understanding how this document processing system works!

---

## Next Reading

- **CODE_STRUCTURE.md**: See how concepts are implemented in code
- **HOW_IT_WORKS.md**: Follow a document through the system
- **GETTING_STARTED.md**: Deploy and try it yourself
