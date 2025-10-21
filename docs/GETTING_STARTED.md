# Getting Started: Deployment and Setup Guide

## Introduction

This guide will walk you through deploying the Intelligent Document Processing system from scratch. We'll go step-by-step, assuming you're new to AWS and cloud deployments.

**Time required:** 45-90 minutes for first-time setup

---

## Prerequisites

### 1. AWS Account

**What you need:**
- An AWS account (sign up at https://aws.amazon.com)
- Credit card for billing (AWS has free tiers for many services)
- IAM user with administrator access

**Create an AWS account:**
1. Go to https://aws.amazon.com
2. Click "Create an AWS Account"
3. Follow the signup process
4. Verify your email and phone number
5. Add payment method

**Create an IAM user (recommended):**
```bash
# Don't use root account for deployments!
# Create an IAM user with admin permissions instead
```

1. Log into AWS Console as root user
2. Go to IAM service
3. Click "Users" → "Add users"
4. Username: `idp-deployer`
5. Access type: Check "Programmatic access"
6. Permissions: Attach "AdministratorAccess" policy
7. Download credentials CSV (keep this safe!)

---

### 2. Install Required Software

#### Python 3.10 or Higher

**Check if you have Python:**
```bash
python3 --version
# Should show: Python 3.10.x or higher
```

**Install Python (if needed):**

**macOS:**
```bash
# Using Homebrew
brew install python@3.10
```

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install python3.10 python3.10-venv python3-pip
```

**Windows:**
1. Download from https://www.python.org/downloads/
2. Run installer
3. ✅ Check "Add Python to PATH"
4. Click "Install Now"

---

#### Node.js (for AWS CDK)

**Check if you have Node.js:**
```bash
node --version
# Should show: v18.x or higher
```

**Install Node.js:**

**macOS:**
```bash
brew install node
```

**Ubuntu/Debian:**
```bash
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt install -y nodejs
```

**Windows:**
1. Download from https://nodejs.org
2. Run installer
3. Accept defaults

---

#### Git

**Check if you have Git:**
```bash
git --version
```

**Install Git:**

**macOS:**
```bash
brew install git
```

**Ubuntu/Debian:**
```bash
sudo apt install git
```

**Windows:**
1. Download from https://git-scm.com
2. Run installer

---

#### AWS CLI

**Check if you have AWS CLI:**
```bash
aws --version
# Should show: aws-cli/2.x.x
```

**Install AWS CLI:**

**macOS:**
```bash
brew install awscli
```

**Linux:**
```bash
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install
```

**Windows:**
1. Download from https://aws.amazon.com/cli/
2. Run MSI installer

**Configure AWS CLI:**
```bash
aws configure

# Enter when prompted:
AWS Access Key ID: [from IAM user CSV]
AWS Secret Access Key: [from IAM user CSV]
Default region name: us-east-1
Default output format: json
```

**Verify configuration:**
```bash
aws sts get-caller-identity

# Should show:
# {
#   "UserId": "AIDAI...",
#   "Account": "123456789012",
#   "Arn": "arn:aws:iam::123456789012:user/idp-deployer"
# }
```

---

## Step 1: Clone the Repository

**Open terminal and run:**
```bash
# Navigate to where you want the project
cd ~/projects  # or wherever you keep code

# Clone the repository
git clone https://github.com/aws-samples/intelligent-document-processing-with-amazon-bedrock.git

# Enter the directory
cd intelligent-document-processing-with-amazon-bedrock

# Check you're in the right place
ls
# Should see: app.py, infra/, src/, etc.
```

---

## Step 2: Set Up Python Environment

### Create Virtual Environment

**What is a virtual environment?**
Think of it as a isolated space for this project's dependencies, so they don't interfere with other Python projects.

```bash
# Create virtual environment
python3 -m venv .venv

# Activate it
# macOS/Linux:
source .venv/bin/activate

# Windows:
.venv\Scripts\activate

# Your prompt should now show (.venv)
```

**You'll know it worked when you see:**
```bash
(.venv) user@computer:~/project$
```

---

### Install Python Dependencies

```bash
# Upgrade pip (Python package manager)
pip install --upgrade pip

# Install project dependencies
pip install -r requirements.txt

# Install development dependencies (optional, for development)
pip install -r requirements-dev.txt
```

**This installs:**
- AWS CDK libraries
- Boto3 (AWS SDK for Python)
- PyYAML (for config files)
- And other dependencies

**Wait for installation to complete** (may take 2-5 minutes)

---

## Step 3: Install AWS CDK CLI

```bash
# Install CDK globally using npm
npm install -g aws-cdk

# Verify installation
cdk --version
# Should show: 2.x.x
```

---

## Step 4: Request Bedrock Model Access

**Important:** You must request access to AI models before using them.

### Request Access in AWS Console

1. Log into AWS Console
2. Go to **Amazon Bedrock** service
3. Click **Model access** in left sidebar
4. Click **Modify model access**
5. Check these models:
   - ✅ Anthropic Claude 3 Sonnet
   - ✅ Anthropic Claude 3.5 Sonnet
   - ✅ Amazon Nova Premier (if available)
   - ✅ Meta Llama 3.1 (optional)
6. Click **Request model access**

**Access is usually granted instantly**, but some models may require:
- Use case description
- Approval (1-2 business days)

**Verify access:**
```bash
aws bedrock list-foundation-models --region us-east-1

# Should show a list of models you have access to
```

---

## Step 5: Configure Your Deployment

### Create Configuration File

```bash
# Copy example config
cp config-example.yml config.yml

# Edit with your preferred editor
nano config.yml
# or
vim config.yml
# or
code config.yml  # if using VS Code
```

### Configure Settings

**Basic configuration:**
```yaml
# Stack name (must be unique in your AWS account)
stack_name: my-idp-bedrock
stack_region: us-east-1

# Lambda settings
lambda:
  architecture: X86_64           # or ARM_64 (cheaper, but less compatible)
  python_runtime: PYTHON_3_13    # or PYTHON_3_12, PYTHON_3_11

# S3 encryption
s3:
  encryption: SSE-S3             # Free encryption
  # Or use KMS for more control:
  # encryption: SSE-KMS
  # kms_key_id: alias/my-key

# Bedrock configuration
bedrock:
  region: us-east-1
  model_ids:
    # List models you have access to
    - anthropic.claude-3-sonnet-20240229-v1:0
    - us.anthropic.claude-3-5-sonnet-20241022-v2:0
    - us.amazon.nova-premier-v1:0

# Authentication
authentication:
  MFA: false                     # Set true for multi-factor auth
  users:
    - your-email@example.com     # Replace with your email
    - colleague@example.com      # Add more users as needed

# Frontend (web UI)
frontend:
  deploy_ecs: true               # Set false to skip web UI
  ecs_memory: 2_048              # MB (2 GB)
  ecs_cpu: 1_024                 # CPU units (1 vCPU)
```

**Save and close the file**

---

## Step 6: Bootstrap CDK (First Time Only)

**What is bootstrapping?**
CDK needs to create some resources in your AWS account to manage deployments (like an S3 bucket for templates).

**Run once per account per region:**
```bash
cdk bootstrap aws://ACCOUNT-ID/us-east-1

# Replace ACCOUNT-ID with your AWS account number
# Get it with:
aws sts get-caller-identity --query Account --output text
```

**Example:**
```bash
cdk bootstrap aws://123456789012/us-east-1
```

**Output:**
```
 ⏳  Bootstrapping environment aws://123456789012/us-east-1...
 ✅  Environment aws://123456789012/us-east-1 bootstrapped.
```

**What it creates:**
- `CDKToolkit` CloudFormation stack
- S3 bucket for deployment assets
- IAM roles for deployments
- ECR repository for Docker images

---

## Step 7: Review Changes (Optional but Recommended)

**See what will be created:**
```bash
cdk synth

# This generates CloudFormation template
# Output is saved to cdk.out/
```

**Preview changes:**
```bash
cdk diff

# Shows resources that will be created/modified/deleted
```

**Example output:**
```
Stack my-idp-bedrock
Resources
[+] AWS::S3::Bucket DocumentBucket
[+] AWS::Lambda::Function RunTextractFunction
[+] AWS::ApiGateway::RestApi IDPAPI
[+] AWS::Cognito::UserPool UserPool
...
```

---

## Step 8: Deploy!

**Deploy the stack:**
```bash
cdk deploy

# Or with auto-approval (skip confirmations):
cdk deploy --require-approval never
```

**What happens:**
1. CDK uploads code to S3
2. Creates CloudFormation stack
3. Provisions all resources
4. Configures permissions
5. Deploys Lambda functions
6. Sets up API Gateway
7. Creates Cognito user pool
8. Deploys web UI (if enabled)

**Time:** 15-30 minutes for complete deployment

**Output you'll see:**
```
my-idp-bedrock: deploying...

[1/50] Creating AWS::S3::Bucket DocumentBucket
[2/50] Creating AWS::IAM::Role LambdaExecutionRole
[3/50] Creating AWS::Lambda::Function RunTextractFunction
...
[48/50] Creating AWS::CloudFormation::Stack ECSStack
[49/50] Creating outputs
[50/50] Stack deployed

✅  my-idp-bedrock

Outputs:
my-idp-bedrock.APIEndpoint = https://abc123.execute-api.us-east-1.amazonaws.com/prod
my-idp-bedrock.WebUIURL = https://def456.cloudfront.net
my-idp-bedrock.UserPoolId = us-east-1_ABC123
my-idp-bedrock.UserPoolClientId = 7a8b9c0d1e2f3g4h

Stack ARN:
arn:aws:cloudformation:us-east-1:123456789012:stack/my-idp-bedrock/uuid
```

**Save these outputs!** You'll need them to use the system.

---

## Step 9: Create User Accounts

### Set User Passwords

The users listed in `config.yml` are created, but they need passwords.

**Set password for each user:**
```bash
aws cognito-idp admin-set-user-password \
  --user-pool-id us-east-1_ABC123 \
  --username your-email@example.com \
  --password "YourSecurePassword123!" \
  --permanent
```

**Password requirements:**
- At least 8 characters
- Uppercase letter
- Lowercase letter
- Number
- Special character

**Repeat for each user in your config**

---

## Step 10: Test the Deployment

### Option 1: Web UI

**Open the web interface:**
1. Copy the `WebUIURL` from deployment outputs
2. Paste in browser: `https://def456.cloudfront.net`
3. You should see the login page

**Log in:**
1. Enter email address
2. Enter password (set in previous step)
3. Click "Sign In"

**Test extraction:**
1. Click "Upload Document"
2. Choose a PDF or image file
3. Define attributes:
   ```
   Name: document_type
   Description: The type of document (invoice, receipt, contract, etc.)
   ```
4. Click "Extract"
5. Wait for results (10-60 seconds)
6. View extracted data!

---

### Option 2: Python SDK

**Create a test script:**
```python
# test_extraction.py
from idp_bedrock.client import IDPClient
import os

# Initialize client
client = IDPClient(
    api_endpoint=os.environ['IDP_API_ENDPOINT'],
    # You'll need to authenticate - see authentication section
)

# Extract attributes
result = client.extract_attributes(
    file_path="test_invoice.pdf",
    attributes={
        "invoice_number": "The invoice number",
        "date": "Invoice date",
        "total": "Total amount"
    },
    model_id="anthropic.claude-3-sonnet-20240229-v1:0"
)

print("Extracted data:")
print(result)
```

**Run:**
```bash
export IDP_API_ENDPOINT="https://abc123.execute-api.us-east-1.amazonaws.com/prod"
python test_extraction.py
```

---

### Option 3: AWS Console Verification

**Check resources were created:**

1. **S3 Buckets:**
   - Go to S3 console
   - Find bucket: `my-idp-bedrock-documents-123456789012`

2. **Lambda Functions:**
   - Go to Lambda console
   - Filter by "my-idp-bedrock"
   - Should see: run_textract, run_idp_on_text, etc.

3. **API Gateway:**
   - Go to API Gateway console
   - Find "IDP Bedrock API"
   - Check endpoints

4. **Cognito:**
   - Go to Cognito console
   - Find user pool: "my-idp-bedrock-users"
   - Check users are created

5. **Step Functions:**
   - Go to Step Functions console
   - Find state machine: "my-idp-bedrock-StateMachine"
   - View workflow diagram

---

## Step 11: Try the Demo Notebook

**Jupyter notebook with examples:**

```bash
# Install Jupyter
pip install jupyter

# Install ipykernel
python -m ipykernel install --user --name idp-bedrock

# Start Jupyter
jupyter notebook demo/idp_bedrock_demo.ipynb
```

**The notebook includes:**
- Setup and authentication
- Basic extraction examples
- Advanced features (few-shot learning)
- Batch processing
- Error handling

---

## Common Issues and Solutions

### Issue 1: CDK Deploy Fails with "Access Denied"

**Cause:** IAM user doesn't have sufficient permissions

**Solution:**
```bash
# Verify IAM permissions
aws iam get-user

# Attach AdministratorAccess policy (for deployment)
aws iam attach-user-policy \
  --user-name idp-deployer \
  --policy-arn arn:aws:iam::aws:policy/AdministratorAccess
```

---

### Issue 2: "Model not found" Error

**Cause:** Haven't requested Bedrock model access

**Solution:**
1. Go to Bedrock console
2. Click "Model access"
3. Request access to models
4. Wait for approval

**Verify:**
```bash
aws bedrock list-foundation-models --region us-east-1
```

---

### Issue 3: Web UI Shows 403 Forbidden

**Cause:** Cognito authentication issue

**Solution:**
1. Check user exists:
   ```bash
   aws cognito-idp list-users \
     --user-pool-id us-east-1_ABC123
   ```

2. Reset password:
   ```bash
   aws cognito-idp admin-set-user-password \
     --user-pool-id us-east-1_ABC123 \
     --username your-email@example.com \
     --password "NewPassword123!" \
     --permanent
   ```

---

### Issue 4: Lambda Function Timeout

**Cause:** Processing large documents

**Solution:**
Increase timeout in `config.yml`:
```yaml
lambda:
  timeout: 300  # 5 minutes instead of default
```

Redeploy:
```bash
cdk deploy
```

---

### Issue 5: High Costs

**Cause:** Leaving resources running

**Solution:**
Monitor costs:
```bash
# Check current month spend
aws ce get-cost-and-usage \
  --time-period Start=2024-01-01,End=2024-01-31 \
  --granularity MONTHLY \
  --metrics BlendedCost
```

**Reduce costs:**
1. Delete old documents from S3
2. Reduce ECS task size (if using web UI)
3. Use cheaper models (Amazon Titan instead of Claude)
4. Implement lifecycle policies

---

## Cleanup / Uninstall

**To delete everything:**

```bash
# Delete the CloudFormation stack
cdk destroy

# Confirm deletion
# This will DELETE:
# - All Lambda functions
# - API Gateway
# - Step Functions
# - Cognito user pool
# - ECS cluster and service
# - CloudFront distribution

# Note: S3 buckets are retained by default (to prevent data loss)
# Delete manually if needed:
aws s3 rm s3://my-idp-bedrock-documents-123456789012 --recursive
aws s3 rb s3://my-idp-bedrock-documents-123456789012
```

**Estimated time:** 10-15 minutes

---

## Cost Estimation

**Monthly costs for low usage (100 documents/month):**

| Service | Usage | Cost |
|---------|-------|------|
| Lambda | 100 executions, 512MB, 30s avg | ~$0.10 |
| Bedrock | 100K tokens (Claude) | ~$0.30 |
| Textract | 100 pages | ~$0.15 |
| S3 | 1 GB storage, 100 uploads | ~$0.03 |
| DynamoDB | 100 reads/writes | ~$0.01 |
| API Gateway | 100 requests | ~$0.01 |
| ECS (web UI) | Always running | ~$30.00 |
| **Total** | | **~$30.60** |

**To reduce costs:**
- Don't deploy ECS (use Python SDK only): Saves ~$30/month
- Use cheaper models: Saves ~50% on Bedrock
- Implement lifecycle policies: Reduces S3 costs

**For high usage (10,000 documents/month):**
- Textract: ~$15
- Bedrock: ~$30
- Other: ~$5
- ECS (optional): ~$30
- **Total: ~$80** (without ECS) or **~$110** (with web UI)

---

## Next Steps After Deployment

### 1. Explore the Demo Notebook
```bash
jupyter notebook demo/idp_bedrock_demo.ipynb
```

### 2. Process Your Own Documents
Upload documents via web UI and experiment with different attributes

### 3. Integrate with Your Applications
Use the Python SDK in your existing projects:
```python
from idp_bedrock.client import IDPClient

client = IDPClient()
result = client.extract_attributes(...)
```

### 4. Set Up Few-Shot Learning
Improve accuracy for specific use cases by providing examples

### 5. Monitor and Optimize
- Check CloudWatch logs
- Monitor costs in AWS Cost Explorer
- Optimize model selection for your use case

### 6. Enable Advanced Features
- Multi-factor authentication
- Custom domains for web UI
- CI/CD pipeline for updates
- Data retention policies

---

## Security Best Practices

### 1. Use MFA
Enable multi-factor authentication:
```yaml
# config.yml
authentication:
  MFA: true
```

### 2. Restrict API Access
Use VPC endpoints for private APIs:
```yaml
# config.yml
api:
  private: true
  vpc_id: vpc-123abc
```

### 3. Encrypt with KMS
Use customer-managed encryption keys:
```yaml
# config.yml
s3:
  encryption: SSE-KMS
  kms_key_id: alias/idp-bedrock-key
```

### 4. Enable CloudTrail
Log all API calls:
```bash
aws cloudtrail create-trail \
  --name idp-bedrock-trail \
  --s3-bucket-name my-cloudtrail-bucket
```

### 5. Regular Updates
Keep dependencies updated:
```bash
pip install --upgrade -r requirements.txt
cdk deploy
```

---

## Getting Help

### Documentation
- **Project docs:** `/docs` folder
- **AWS CDK docs:** https://docs.aws.amazon.com/cdk/
- **Amazon Bedrock docs:** https://docs.aws.amazon.com/bedrock/

### Troubleshooting
1. Check CloudWatch Logs
   - Go to CloudWatch console
   - Select log group: `/aws/lambda/my-idp-bedrock-*`
   - View recent logs

2. Check Step Functions Execution
   - Go to Step Functions console
   - Click on failed execution
   - View error details

3. Review CloudFormation Events
   - Go to CloudFormation console
   - Click on stack
   - View Events tab for errors

### Community Support
- GitHub Issues: Report bugs or ask questions
- AWS Forums: Community support
- AWS Support: Paid support plans

---

## Summary

You've now:
1. ✅ Installed all prerequisites
2. ✅ Cloned the repository
3. ✅ Configured your deployment
4. ✅ Deployed to AWS
5. ✅ Created user accounts
6. ✅ Tested the system

**Congratulations!** You have a fully functional intelligent document processing system running in your AWS account.

Start processing documents and extracting valuable data!

---

## Quick Reference

**Deploy:**
```bash
cdk deploy
```

**Update after code changes:**
```bash
cdk deploy
```

**View logs:**
```bash
aws logs tail /aws/lambda/my-idp-bedrock-run-idp --follow
```

**Destroy everything:**
```bash
cdk destroy
```

**Check costs:**
```bash
aws ce get-cost-and-usage \
  --time-period Start=$(date -d '1 month ago' +%Y-%m-%d),End=$(date +%Y-%m-%d) \
  --granularity MONTHLY \
  --metrics BlendedCost
```

---

Happy document processing! 🎉
