# How It Works: Document Processing Workflow

## Introduction

This document takes you on a journey through the system, following a document from upload to final extraction. We'll see exactly what happens at each step, with real examples and code snippets.

---

## The Complete Journey: A Real Example

Let's say you're processing customer invoices and want to extract:
- Invoice number
- Date
- Total amount
- Customer name

Here's the complete workflow:

```
📄 Invoice.pdf uploaded
    ↓
⬆️  Uploaded to S3
    ↓
🚀 Step Functions workflow starts
    ↓
🔍 Textract extracts text
    ↓
🤖 Bedrock AI extracts attributes
    ↓
💾 Results saved to S3 & DynamoDB
    ↓
✅ You receive structured data
```

Let's follow each step in detail!

---

## Step 1: Document Upload

### Using the Web UI

**What you do:**
1. Log into the web interface
2. Click "Upload Document"
3. Select `invoice_jan_2024.pdf`
4. Click "Upload"

**What happens behind the scenes:**

#### 1.1 Authentication Check
```python
# Streamlit app code
if not st.session_state.get('authenticated'):
    # Show login page
    username = st.text_input("Email")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        # Call Cognito
        response = cognito.authenticate(username, password)

        if response['success']:
            st.session_state.authenticated = True
            st.session_state.token = response['token']
```

**AWS Cognito validates:**
- Is the email registered?
- Is the password correct?
- Is the account verified?

If yes, returns a JWT token (like a temporary pass).

#### 1.2 Get Upload URL
```python
# Frontend requests pre-signed URL
response = requests.post(
    f"{API_URL}/upload-url",
    headers={"Authorization": f"Bearer {token}"},
    json={"filename": "invoice_jan_2024.pdf"}
)

upload_data = response.json()
# Returns:
# {
#   "upload_url": "https://s3.amazonaws.com/bucket/upload?signature=...",
#   "file_key": "uploads/user123/invoice_jan_2024.pdf",
#   "expires_in": 3600
# }
```

**Lambda function (get_presigned_url):**
```python
def lambda_handler(event, context):
    # Extract user ID from JWT token
    user_id = event['requestContext']['authorizer']['claims']['sub']

    filename = event['body']['filename']

    # Generate S3 key with user ID for isolation
    file_key = f"uploads/{user_id}/{filename}"

    # Create pre-signed URL (valid for 1 hour)
    s3 = boto3.client('s3')
    upload_url = s3.generate_presigned_url(
        'put_object',
        Params={
            'Bucket': os.environ['BUCKET_NAME'],
            'Key': file_key
        },
        ExpiresIn=3600
    )

    return {
        'statusCode': 200,
        'body': json.dumps({
            'upload_url': upload_url,
            'file_key': file_key,
            'expires_in': 3600
        })
    }
```

**Why pre-signed URLs?**
- Browser uploads directly to S3 (faster!)
- API doesn't handle large file data (cheaper!)
- Secure (expires after 1 hour)
- User can only upload to their own folder

#### 1.3 Upload to S3
```javascript
// Frontend uploads file directly to S3
const response = await fetch(upload_url, {
    method: 'PUT',
    body: file,
    headers: {
        'Content-Type': 'application/pdf'
    }
});

if (response.ok) {
    console.log('Upload successful!');
}
```

**What's stored in S3:**
```
s3://idp-bedrock-documents/
└── uploads/
    └── user-123-456-789/
        └── invoice_jan_2024.pdf  [125 KB]
```

**S3 metadata:**
- Content-Type: application/pdf
- Size: 125 KB
- Upload date: 2024-01-15T10:30:00Z
- User: user-123-456-789
- Encryption: AES-256 (automatic)

---

## Step 2: Start Extraction Job

### Submitting the Extraction Request

**What you do:**
1. Define attributes to extract
2. Choose AI model
3. Click "Extract"

**UI code:**
```python
# User fills out form
attributes = {
    "invoice_number": st.text_input("Invoice Number Description",
                                     value="The invoice number"),
    "date": st.text_input("Date Description",
                           value="Invoice date in YYYY-MM-DD format"),
    "total": st.text_input("Total Description",
                            value="Total amount as number"),
    "customer_name": st.text_input("Customer Description",
                                     value="Customer or company name")
}

model_id = st.selectbox("Model", [
    "anthropic.claude-3-sonnet-20240229-v1:0",
    "meta.llama3-70b-instruct-v1:0"
])

if st.button("Extract"):
    job_id = submit_extraction_job(
        file_key="uploads/user123/invoice_jan_2024.pdf",
        attributes=attributes,
        model_id=model_id
    )
```

**API request:**
```http
POST /extract
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
Content-Type: application/json

{
  "file_key": "uploads/user123/invoice_jan_2024.pdf",
  "attributes": {
    "invoice_number": "The invoice number",
    "date": "Invoice date in YYYY-MM-DD format",
    "total": "Total amount as number",
    "customer_name": "Customer or company name"
  },
  "model_id": "anthropic.claude-3-sonnet-20240229-v1:0"
}
```

**Lambda handler (start_extraction):**
```python
def lambda_handler(event, context):
    # Parse request
    body = json.loads(event['body'])
    user_id = event['requestContext']['authorizer']['claims']['sub']

    # Verify user owns this file
    if not body['file_key'].startswith(f"uploads/{user_id}/"):
        return {
            'statusCode': 403,
            'body': json.dumps({'error': 'Access denied'})
        }

    # Generate job ID
    job_id = str(uuid.uuid4())

    # Create DynamoDB record
    ddb = boto3.client('dynamodb')
    ddb.put_item(
        TableName=os.environ['TABLE_NAME'],
        Item={
            'job_id': {'S': job_id},
            'user_id': {'S': user_id},
            'status': {'S': 'PENDING'},
            'file_key': {'S': body['file_key']},
            'attributes': {'S': json.dumps(body['attributes'])},
            'model_id': {'S': body['model_id']},
            'created_at': {'S': datetime.utcnow().isoformat()},
            'updated_at': {'S': datetime.utcnow().isoformat()}
        }
    )

    # Start Step Functions execution
    sfn = boto3.client('stepfunctions')
    sfn.start_execution(
        stateMachineArn=os.environ['STATE_MACHINE_ARN'],
        name=job_id,
        input=json.dumps({
            'job_id': job_id,
            'file_key': body['file_key'],
            'bucket': os.environ['BUCKET_NAME'],
            'attributes': body['attributes'],
            'model_id': body['model_id']
        })
    )

    return {
        'statusCode': 200,
        'body': json.dumps({
            'job_id': job_id,
            'status': 'PROCESSING',
            'message': 'Extraction job started'
        })
    }
```

**Response:**
```json
{
  "job_id": "abc-123-def-456",
  "status": "PROCESSING",
  "message": "Extraction job started"
}
```

**What's created:**

**DynamoDB record:**
```json
{
  "job_id": "abc-123-def-456",
  "user_id": "user-123-456-789",
  "status": "PENDING",
  "file_key": "uploads/user123/invoice_jan_2024.pdf",
  "attributes": "{\"invoice_number\": \"The invoice number\", ...}",
  "model_id": "anthropic.claude-3-sonnet-20240229-v1:0",
  "created_at": "2024-01-15T10:30:15Z",
  "updated_at": "2024-01-15T10:30:15Z"
}
```

**Step Functions execution started:**
- Execution ID: abc-123-def-456
- Status: RUNNING
- Start time: 2024-01-15T10:30:15Z

---

## Step 3: Step Functions Workflow Execution

### The Orchestration Begins

**Step Functions receives the input:**
```json
{
  "job_id": "abc-123-def-456",
  "file_key": "uploads/user123/invoice_jan_2024.pdf",
  "bucket": "idp-bedrock-documents",
  "attributes": {
    "invoice_number": "The invoice number",
    "date": "Invoice date in YYYY-MM-DD format",
    "total": "Total amount as number",
    "customer_name": "Customer or company name"
  },
  "model_id": "anthropic.claude-3-sonnet-20240229-v1:0"
}
```

### State 1: Determine File Type

```json
{
  "Type": "Choice",
  "Choices": [
    {
      "Variable": "$.file_key",
      "StringMatches": "*.pdf",
      "Next": "CheckIfImagePDF"
    },
    {
      "Variable": "$.file_key",
      "StringMatches": "*.docx",
      "Next": "ReadOfficeFile"
    },
    {
      "Variable": "$.file_key",
      "StringMatches": "*.xlsx",
      "Next": "ReadOfficeFile"
    },
    {
      "Variable": "$.file_key",
      "StringMatches": "*.pptx",
      "Next": "ReadOfficeFile"
    }
  ],
  "Default": "ExtractTextWithTextract"
}
```

**Our file:** `invoice_jan_2024.pdf` → Matches "*.pdf" → Goes to CheckIfImagePDF

### State 2: Extract Text with Textract

```json
{
  "Type": "Task",
  "Resource": "arn:aws:states:::lambda:invoke",
  "Parameters": {
    "FunctionName": "arn:aws:lambda:us-east-1:123456:function:run_textract",
    "Payload.$": "$"
  },
  "ResultPath": "$.textract_result",
  "Next": "RunIDPOnText"
}
```

**Lambda execution begins...**

---

## Step 4: Text Extraction (Textract Lambda)

**Lambda: run_textract**

**Input received:**
```json
{
  "job_id": "abc-123-def-456",
  "file_key": "uploads/user123/invoice_jan_2024.pdf",
  "bucket": "idp-bedrock-documents",
  ...
}
```

**Lambda function code:**
```python
def lambda_handler(event, context):
    logger.info(f"Extracting text for job {event['job_id']}")

    # Call AWS Textract
    textract = boto3.client('textract')

    response = textract.detect_document_text(
        Document={
            'S3Object': {
                'Bucket': event['bucket'],
                'Name': event['file_key']
            }
        }
    )

    # Parse Textract response
    text = extract_text_from_blocks(response['Blocks'])

    logger.info(f"Extracted {len(text)} characters")

    # Save extracted text to S3
    s3 = boto3.client('s3')
    text_key = f"extracted-text/{event['job_id']}/document.txt"

    s3.put_object(
        Bucket=event['bucket'],
        Key=text_key,
        Body=text.encode('utf-8'),
        ContentType='text/plain'
    )

    # Update DynamoDB status
    ddb = boto3.client('dynamodb')
    ddb.update_item(
        TableName=os.environ['TABLE_NAME'],
        Key={'job_id': {'S': event['job_id']}},
        UpdateExpression='SET #status = :status, text_path = :path',
        ExpressionAttributeNames={'#status': 'status'},
        ExpressionAttributeValues={
            ':status': {'S': 'EXTRACTING_ATTRIBUTES'},
            ':path': {'S': f's3://{event["bucket"]}/{text_key}'}
        }
    )

    return {
        'text': text,
        'text_s3_path': f's3://{event["bucket"]}/{text_key}',
        'page_count': len([b for b in response['Blocks'] if b['BlockType'] == 'PAGE'])
    }


def extract_text_from_blocks(blocks):
    """Parse Textract blocks into plain text."""
    lines = []

    for block in blocks:
        if block['BlockType'] == 'LINE':
            lines.append(block['Text'])

    return '\n'.join(lines)
```

**Textract API response (simplified):**
```json
{
  "Blocks": [
    {
      "BlockType": "LINE",
      "Text": "INVOICE",
      "Confidence": 99.8,
      "Geometry": {...}
    },
    {
      "BlockType": "LINE",
      "Text": "Invoice Number: INV-2024-001",
      "Confidence": 99.5
    },
    {
      "BlockType": "LINE",
      "Text": "Date: January 15, 2024",
      "Confidence": 98.9
    },
    {
      "BlockType": "LINE",
      "Text": "Customer: Acme Corporation",
      "Confidence": 99.2
    },
    {
      "BlockType": "LINE",
      "Text": "Total Amount: $1,250.00",
      "Confidence": 99.7
    }
  ]
}
```

**Extracted text:**
```
INVOICE
Invoice Number: INV-2024-001
Date: January 15, 2024
Customer: Acme Corporation

Item Description                  Qty    Price     Total
Widget Pro                        10     $100.00   $1,000.00
Gadget Plus                       5      $50.00    $250.00

                                         Subtotal:  $1,250.00
                                         Tax:       $0.00
                                         Total:     $1,250.00
```

**Saved to S3:**
```
s3://idp-bedrock-documents/extracted-text/abc-123-def-456/document.txt
```

**Lambda returns to Step Functions:**
```json
{
  "text": "INVOICE\nInvoice Number: INV-2024-001...",
  "text_s3_path": "s3://idp-bedrock-documents/extracted-text/abc-123-def-456/document.txt",
  "page_count": 1
}
```

**Step Functions state data now includes:**
```json
{
  "job_id": "abc-123-def-456",
  "file_key": "uploads/user123/invoice_jan_2024.pdf",
  "attributes": {...},
  "model_id": "anthropic.claude-3-sonnet-20240229-v1:0",
  "textract_result": {
    "text": "INVOICE\nInvoice Number: INV-2024-001...",
    "text_s3_path": "s3://...",
    "page_count": 1
  }
}
```

---

## Step 5: AI Attribute Extraction (Bedrock Lambda)

**Lambda: run_idp_on_text**

This is where the magic happens!

**Input received:**
```json
{
  "job_id": "abc-123-def-456",
  "textract_result": {
    "text": "INVOICE\nInvoice Number: INV-2024-001...",
    ...
  },
  "attributes": {
    "invoice_number": "The invoice number",
    "date": "Invoice date in YYYY-MM-DD format",
    "total": "Total amount as number",
    "customer_name": "Customer or company name"
  },
  "model_id": "anthropic.claude-3-sonnet-20240229-v1:0"
}
```

### 5.1 Build the Prompt

**Lambda code:**
```python
def build_prompt(text, attributes, few_shot_examples=None):
    """Build extraction prompt for AI."""

    system_prompt = """You are an expert at extracting structured information from documents.
You must extract exactly the attributes specified and return them in valid JSON format.
If an attribute cannot be found, use null.
Return ONLY the JSON object, no additional text."""

    # Build attribute descriptions
    attr_list = []
    for key, description in attributes.items():
        attr_list.append(f'- {key}: {description}')

    attributes_section = '\n'.join(attr_list)

    # Few-shot examples (if provided)
    examples_section = ""
    if few_shot_examples:
        examples_section = "\n\nExamples:\n"
        for example in few_shot_examples:
            examples_section += f"\nDocument: {example['input']}"
            examples_section += f"\nOutput: {json.dumps(example['output'], indent=2)}\n"

    # Build final prompt
    prompt = f"""{system_prompt}

Extract these attributes:
{attributes_section}
{examples_section}

Document text:
\"\"\"
{text}
\"\"\"

Return only valid JSON:"""

    return prompt
```

**Generated prompt:**
```
You are an expert at extracting structured information from documents.
You must extract exactly the attributes specified and return them in valid JSON format.
If an attribute cannot be found, use null.
Return ONLY the JSON object, no additional text.

Extract these attributes:
- invoice_number: The invoice number
- date: Invoice date in YYYY-MM-DD format
- total: Total amount as number
- customer_name: Customer or company name

Document text:
"""
INVOICE
Invoice Number: INV-2024-001
Date: January 15, 2024
Customer: Acme Corporation

Item Description                  Qty    Price     Total
Widget Pro                        10     $100.00   $1,000.00
Gadget Plus                       5      $50.00    $250.00

                                         Subtotal:  $1,250.00
                                         Tax:       $0.00
                                         Total:     $1,250.00
"""

Return only valid JSON:
```

### 5.2 Call Amazon Bedrock

**Lambda code:**
```python
def invoke_bedrock(model_id, prompt):
    """Call Amazon Bedrock API."""

    bedrock = boto3.client('bedrock-runtime')

    # Build request body (format depends on model)
    if 'anthropic' in model_id:
        request_body = {
            "anthropic_version": "bedrock-2023-05-31",
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "max_tokens": 2000,
            "temperature": 0.1,  # Low temperature for consistency
            "top_p": 0.9
        }
    elif 'llama' in model_id:
        request_body = {
            "prompt": prompt,
            "max_gen_len": 2000,
            "temperature": 0.1
        }

    # Invoke model
    logger.info(f"Calling Bedrock model: {model_id}")

    response = bedrock.invoke_model(
        modelId=model_id,
        body=json.dumps(request_body)
    )

    # Parse response
    response_body = json.loads(response['body'].read())

    if 'anthropic' in model_id:
        return response_body['content'][0]['text']
    elif 'llama' in model_id:
        return response_body['generation']
```

**Bedrock API call:**
```
POST https://bedrock-runtime.us-east-1.amazonaws.com/model/anthropic.claude-3-sonnet-20240229-v1:0/invoke

{
  "anthropic_version": "bedrock-2023-05-31",
  "messages": [
    {
      "role": "user",
      "content": "You are an expert at extracting..."
    }
  ],
  "max_tokens": 2000,
  "temperature": 0.1,
  "top_p": 0.9
}
```

**Bedrock response:**
```json
{
  "id": "msg_123abc",
  "type": "message",
  "role": "assistant",
  "content": [
    {
      "type": "text",
      "text": "{\n  \"invoice_number\": \"INV-2024-001\",\n  \"date\": \"2024-01-15\",\n  \"total\": 1250.00,\n  \"customer_name\": \"Acme Corporation\"\n}"
    }
  ],
  "model": "claude-3-sonnet-20240229",
  "usage": {
    "input_tokens": 342,
    "output_tokens": 45
  }
}
```

### 5.3 Parse AI Response

**Lambda code:**
```python
def parse_ai_response(response_text):
    """Parse and validate AI response."""

    # Sometimes models wrap JSON in markdown
    if '```json' in response_text:
        # Extract JSON from markdown code block
        start = response_text.find('```json') + 7
        end = response_text.rfind('```')
        response_text = response_text[start:end].strip()
    elif '```' in response_text:
        start = response_text.find('```') + 3
        end = response_text.rfind('```')
        response_text = response_text[start:end].strip()

    # Parse JSON
    try:
        data = json.loads(response_text)
        logger.info("Successfully parsed JSON response")
        return data
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON: {e}")
        logger.error(f"Response was: {response_text}")
        raise ValueError("AI returned invalid JSON")
```

**Parsed result:**
```python
{
    "invoice_number": "INV-2024-001",
    "date": "2024-01-15",
    "total": 1250.00,
    "customer_name": "Acme Corporation"
}
```

### 5.4 Save Results

**Lambda code:**
```python
def save_results(job_id, extracted_data, bucket):
    """Save extraction results."""

    # Save to S3
    s3 = boto3.client('s3')
    result_key = f"results/{job_id}/extracted.json"

    s3.put_object(
        Bucket=bucket,
        Key=result_key,
        Body=json.dumps(extracted_data, indent=2),
        ContentType='application/json'
    )

    # Update DynamoDB
    ddb = boto3.client('dynamodb')
    ddb.update_item(
        TableName=os.environ['TABLE_NAME'],
        Key={'job_id': {'S': job_id}},
        UpdateExpression='SET #status = :status, result_path = :path, completed_at = :time',
        ExpressionAttributeNames={'#status': 'status'},
        ExpressionAttributeValues={
            ':status': {'S': 'COMPLETED'},
            ':path': {'S': f's3://{bucket}/{result_key}'},
            ':time': {'S': datetime.utcnow().isoformat()}
        }
    )

    logger.info(f"Results saved for job {job_id}")
```

**Saved to S3:**
```
s3://idp-bedrock-documents/results/abc-123-def-456/extracted.json
```

**File content:**
```json
{
  "invoice_number": "INV-2024-001",
  "date": "2024-01-15",
  "total": 1250.0,
  "customer_name": "Acme Corporation"
}
```

**DynamoDB updated:**
```json
{
  "job_id": "abc-123-def-456",
  "user_id": "user-123-456-789",
  "status": "COMPLETED",
  "file_key": "uploads/user123/invoice_jan_2024.pdf",
  "text_path": "s3://.../extracted-text/abc-123-def-456/document.txt",
  "result_path": "s3://.../results/abc-123-def-456/extracted.json",
  "created_at": "2024-01-15T10:30:15Z",
  "updated_at": "2024-01-15T10:30:47Z",
  "completed_at": "2024-01-15T10:30:47Z"
}
```

**Lambda returns to Step Functions:**
```json
{
  "statusCode": 200,
  "extracted_data": {
    "invoice_number": "INV-2024-001",
    "date": "2024-01-15",
    "total": 1250.0,
    "customer_name": "Acme Corporation"
  },
  "result_s3_path": "s3://.../results/abc-123-def-456/extracted.json"
}
```

---

## Step 6: Step Functions Completes

**Final state:**
```json
{
  "Type": "Succeed",
  "Comment": "Extraction completed successfully"
}
```

**Step Functions execution:**
- Status: SUCCEEDED
- Duration: 32 seconds
- End time: 2024-01-15T10:30:47Z

---

## Step 7: Retrieve Results

### User Checks Status

**UI code:**
```python
# Poll for status
while True:
    response = requests.get(
        f"{API_URL}/status/{job_id}",
        headers={"Authorization": f"Bearer {token}"}
    )

    status = response.json()

    if status['status'] == 'COMPLETED':
        # Get results
        results = get_results(job_id)
        show_results(results)
        break
    elif status['status'] == 'FAILED':
        st.error(f"Extraction failed: {status['error']}")
        break
    else:
        time.sleep(2)  # Wait 2 seconds
```

**API call:**
```http
GET /status/abc-123-def-456
Authorization: Bearer eyJhbGci...
```

**Lambda (get_status):**
```python
def lambda_handler(event, context):
    job_id = event['pathParameters']['jobId']
    user_id = event['requestContext']['authorizer']['claims']['sub']

    # Query DynamoDB
    ddb = boto3.client('dynamodb')
    response = ddb.get_item(
        TableName=os.environ['TABLE_NAME'],
        Key={'job_id': {'S': job_id}}
    )

    if 'Item' not in response:
        return {
            'statusCode': 404,
            'body': json.dumps({'error': 'Job not found'})
        }

    item = response['Item']

    # Verify ownership
    if item['user_id']['S'] != user_id:
        return {
            'statusCode': 403,
            'body': json.dumps({'error': 'Access denied'})
        }

    return {
        'statusCode': 200,
        'body': json.dumps({
            'job_id': job_id,
            'status': item['status']['S'],
            'created_at': item['created_at']['S'],
            'updated_at': item['updated_at']['S'],
            'completed_at': item.get('completed_at', {}).get('S')
        })
    }
```

### Get Full Results

**API call:**
```http
GET /results/abc-123-def-456
Authorization: Bearer eyJhbGci...
```

**Lambda (get_results):**
```python
def lambda_handler(event, context):
    job_id = event['pathParameters']['jobId']
    user_id = event['requestContext']['authorizer']['claims']['sub']

    # Get job record
    ddb = boto3.client('dynamodb')
    response = ddb.get_item(
        TableName=os.environ['TABLE_NAME'],
        Key={'job_id': {'S': job_id}}
    )

    item = response['Item']

    # Verify completed
    if item['status']['S'] != 'COMPLETED':
        return {
            'statusCode': 400,
            'body': json.dumps({
                'error': 'Job not completed',
                'status': item['status']['S']
            })
        }

    # Get results from S3
    s3 = boto3.client('s3')
    result_path = item['result_path']['S']  # s3://bucket/key

    # Parse S3 path
    bucket = result_path.split('/')[2]
    key = '/'.join(result_path.split('/')[3:])

    # Download results
    obj = s3.get_object(Bucket=bucket, Key=key)
    results = json.loads(obj['Body'].read())

    return {
        'statusCode': 200,
        'body': json.dumps({
            'job_id': job_id,
            'status': 'COMPLETED',
            'results': results,
            'completed_at': item['completed_at']['S']
        })
    }
```

**Response:**
```json
{
  "job_id": "abc-123-def-456",
  "status": "COMPLETED",
  "results": {
    "invoice_number": "INV-2024-001",
    "date": "2024-01-15",
    "total": 1250.0,
    "customer_name": "Acme Corporation"
  },
  "completed_at": "2024-01-15T10:30:47Z"
}
```

### Display in UI

**Streamlit code:**
```python
# Display results in a nice table
st.success("Extraction completed!")

st.write("### Extracted Data")

df = pd.DataFrame([results['results']])
st.dataframe(df)

# Allow download
st.download_button(
    "Download JSON",
    data=json.dumps(results['results'], indent=2),
    file_name=f"{job_id}_results.json",
    mime="application/json"
)
```

**User sees:**
```
✅ Extraction completed!

Extracted Data:
┌─────────────────┬────────────┬────────┬───────────────────┐
│ invoice_number  │ date       │ total  │ customer_name     │
├─────────────────┼────────────┼────────┼───────────────────┤
│ INV-2024-001    │ 2024-01-15 │ 1250.0 │ Acme Corporation  │
└─────────────────┴────────────┴────────┴───────────────────┘

[Download JSON]
```

---

## Summary: Complete Timeline

```
00:00 - User uploads invoice.pdf
00:02 - File saved to S3
00:03 - Extraction job created (job_id: abc-123)
00:04 - Step Functions starts
00:05 - Textract extraction begins
00:20 - Text extracted and saved
00:21 - Bedrock AI processing begins
00:30 - Prompt sent to Claude
00:45 - AI returns extracted data
00:46 - Results saved to S3 and DynamoDB
00:47 - Step Functions completes
00:48 - User receives results

Total time: 48 seconds
```

---

## Error Handling

### What if something goes wrong?

**Scenario 1: Textract fails**
```python
# Step Functions has retry logic
{
  "Retry": [
    {
      "ErrorEquals": ["States.TaskFailed"],
      "MaxAttempts": 3,
      "BackoffRate": 2.0
    }
  ],
  "Catch": [
    {
      "ErrorEquals": ["States.ALL"],
      "ResultPath": "$.error",
      "Next": "HandleTextractError"
    }
  ]
}
```

If Textract fails:
1. Retry after 1 second
2. Retry after 2 seconds (2^1)
3. Retry after 4 seconds (2^2)
4. If still failing, go to error handler
5. Update DynamoDB status to "FAILED"
6. Send notification to user

**Scenario 2: AI returns invalid JSON**
```python
try:
    data = json.loads(response_text)
except json.JSONDecodeError:
    # Try to fix common issues
    response_text = response_text.strip()
    response_text = response_text.replace("'", '"')  # Fix quotes

    try:
        data = json.loads(response_text)
    except:
        # Still failed - log and raise
        logger.error(f"Could not parse: {response_text}")
        raise
```

**Scenario 3: User provides bad attributes**
```python
# Validate before starting job
def validate_attributes(attributes):
    if not attributes:
        raise ValueError("Must provide at least one attribute")

    if len(attributes) > 50:
        raise ValueError("Maximum 50 attributes allowed")

    for key, description in attributes.items():
        if not description or len(description) < 5:
            raise ValueError(f"Attribute '{key}' needs better description")
```

---

## Performance Optimization

### Token Counting and Truncation

**Problem:** Documents can be huge, but models have token limits (e.g., 200K tokens)

**Solution:** Count tokens and truncate if needed
```python
def count_tokens(text):
    """Estimate token count (1 token ≈ 4 characters)."""
    return len(text) // 4


def truncate_text(text, max_tokens):
    """Truncate text to fit within token limit."""
    estimated_tokens = count_tokens(text)

    if estimated_tokens <= max_tokens:
        return text

    # Calculate how much to keep
    keep_ratio = max_tokens / estimated_tokens
    keep_chars = int(len(text) * keep_ratio)

    truncated = text[:keep_chars]

    logger.warning(f"Truncated text from {estimated_tokens} to ~{max_tokens} tokens")

    return truncated + "\n\n[...document truncated...]"
```

---

## Cost Tracking

**Each step has a cost:**

| Step | Service | Cost (example) |
|------|---------|----------------|
| Upload | S3 PUT | $0.000001 |
| Text extraction | Textract | $0.0015 (1 page) |
| AI extraction | Bedrock (Claude) | $0.003 per 1K tokens |
| Storage | S3 | $0.023 per GB/month |
| API calls | API Gateway | $0.000001 per request |
| Database | DynamoDB | $0.25 per million writes |
| Lambda | Lambda | $0.0000002 per 100ms |

**Total for 1 invoice (1 page, ~500 tokens):**
- Textract: $0.0015
- Bedrock: ~$0.002 (500 input + 100 output tokens)
- Other: <$0.0001
- **Total: ~$0.0036** (less than half a cent!)

---

## Next Steps

Now you understand the complete workflow! To learn more:

1. **GETTING_STARTED.md**: Deploy the system yourself
2. **CODE_STRUCTURE.md**: Dive deeper into the code
3. **Demo notebook**: `demo/idp_bedrock_demo.ipynb` - Try the Python SDK
