---
layout: default
title: AWS Authentication
parent: Guides
nav_order: 2
description: "Complete AWS credential setup and authentication guide"
---

# AWS Authentication Guide
{: .no_toc }

Complete guide for setting up AWS credentials and authentication for Amazon Bedrock access.
{: .fs-6 .fw-300 }

## Table of contents
{: .no_toc .text-delta }

1. TOC
{:toc}

---

## Overview

The Amazon Chat Completions Server supports multiple AWS authentication methods to access Amazon Bedrock models. This guide covers all available authentication options and best practices for different deployment scenarios.

## Authentication Methods

### 1. Static Credentials

The simplest method using direct access keys.

**Configuration:**
```env
AWS_ACCESS_KEY_ID=AKIA1234567890EXAMPLE
AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
AWS_REGION=us-east-1
```

**Use Cases:**
- Development and testing
- Simple deployments
- When other methods aren't available

**Security Considerations:**
- Store credentials securely
- Use least-privilege IAM policies
- Rotate keys regularly
- Never commit to version control

### 2. AWS Profile

Use AWS CLI profiles for credential management.

**Setup:**
```bash
# Configure AWS CLI profile
aws configure --profile my-profile
# AWS Access Key ID: AKIA1234567890EXAMPLE
# AWS Secret Access Key: wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
# Default region name: us-east-1
# Default output format: json
```

**Configuration:**
```env
AWS_PROFILE=my-profile
AWS_REGION=us-east-1
```

**Use Cases:**
- Development environments
- Multiple AWS accounts
- Shared development machines

### 3. IAM Roles (Recommended for Production)

Use IAM roles for secure, temporary credentials.

**For EC2 Instances:**
```env
# No credentials needed - uses instance profile
AWS_REGION=us-east-1
```

**For ECS/Fargate:**
```env
# Uses task role
AWS_REGION=us-east-1
```

**For Lambda:**
```env
# Uses execution role
AWS_REGION=us-east-1
```

### 4. Role Assumption

Assume roles for cross-account access or enhanced security.

**Configuration:**
```env
AWS_ROLE_ARN=arn:aws:iam::123456789012:role/BedrockAccessRole
AWS_ROLE_SESSION_NAME=amazon-chat-session
AWS_REGION=us-east-1

# Optional: External ID for enhanced security
AWS_EXTERNAL_ID=unique-external-id

# Optional: Base credentials for assumption
AWS_ACCESS_KEY_ID=AKIA1234567890EXAMPLE
AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
```

### 5. Web Identity Tokens (OIDC)

For Kubernetes, GitHub Actions, and other OIDC providers.

**Configuration:**
```env
AWS_ROLE_ARN=arn:aws:iam::123456789012:role/GitHubActionsRole
AWS_WEB_IDENTITY_TOKEN_FILE=/var/run/secrets/eks.amazonaws.com/serviceaccount/token
AWS_REGION=us-east-1
```

## IAM Permissions

### Required Permissions

Minimum IAM policy for Bedrock access:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "bedrock:InvokeModel",
                "bedrock:InvokeModelWithResponseStream"
            ],
            "Resource": [
                "arn:aws:bedrock:*::foundation-model/anthropic.claude-*",
                "arn:aws:bedrock:*::foundation-model/amazon.titan-*",
                "arn:aws:bedrock:*::foundation-model/ai21.*",
                "arn:aws:bedrock:*::foundation-model/cohere.*",
                "arn:aws:bedrock:*::foundation-model/meta.*"
            ]
        }
    ]
}
```

### Model-Specific Permissions

For specific models only:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "bedrock:InvokeModel",
                "bedrock:InvokeModelWithResponseStream"
            ],
            "Resource": [
                "arn:aws:bedrock:us-east-1::foundation-model/anthropic.claude-3-haiku-20240307-v1:0",
                "arn:aws:bedrock:us-east-1::foundation-model/anthropic.claude-3-sonnet-20240229-v1:0"
            ]
        }
    ]
}
```

### Enhanced Permissions

For additional features like model listing:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "bedrock:InvokeModel",
                "bedrock:InvokeModelWithResponseStream",
                "bedrock:ListFoundationModels",
                "bedrock:GetFoundationModel"
            ],
            "Resource": "*"
        }
    ]
}
```

## Setup Examples

### Development Environment

**Option 1: AWS CLI Profile**
```bash
# Install AWS CLI
pip install awscli

# Configure profile
aws configure --profile bedrock-dev
# Enter your credentials and region

# Set environment
export AWS_PROFILE=bedrock-dev
export AWS_REGION=us-east-1

# Start server
amazon-chat serve
```

**Option 2: Environment Variables**
```bash
# Set credentials
export AWS_ACCESS_KEY_ID=your-access-key
export AWS_SECRET_ACCESS_KEY=your-secret-key
export AWS_REGION=us-east-1

# Start server
amazon-chat serve
```

### Production Deployment

**EC2 Instance with IAM Role:**

1. Create IAM role with Bedrock permissions
2. Attach role to EC2 instance
3. Configure application:

```env
# .env file
AWS_REGION=us-east-1
# No credentials needed - uses instance profile
```

**ECS/Fargate with Task Role:**

```yaml
# ECS task definition
taskRoleArn: arn:aws:iam::123456789012:role/BedrockTaskRole
containerDefinitions:
  - name: amazon-chat-server
    environment:
      - name: AWS_REGION
        value: us-east-1
```

**Kubernetes with IRSA:**

```yaml
# ServiceAccount
apiVersion: v1
kind: ServiceAccount
metadata:
  name: amazon-chat-sa
  annotations:
    eks.amazonaws.com/role-arn: arn:aws:iam::123456789012:role/BedrockRole

---
# Deployment
apiVersion: apps/v1
kind: Deployment
metadata:
  name: amazon-chat-server
spec:
  template:
    spec:
      serviceAccountName: amazon-chat-sa
      containers:
      - name: server
        env:
        - name: AWS_REGION
          value: us-east-1
```

## Regional Configuration

### Available Regions

Bedrock is available in specific regions:

```env
# US East (N. Virginia)
AWS_REGION=us-east-1

# US West (Oregon)
AWS_REGION=us-west-2

# Europe (Frankfurt)
AWS_REGION=eu-central-1

# Asia Pacific (Singapore)
AWS_REGION=ap-southeast-1

# Asia Pacific (Tokyo)
AWS_REGION=ap-northeast-1
```

### Model Availability by Region

Different models are available in different regions:

| Model | us-east-1 | us-west-2 | eu-central-1 | ap-southeast-1 |
|-------|-----------|-----------|--------------|----------------|
| Claude 3 Haiku | ✅ | ✅ | ✅ | ✅ |
| Claude 3 Sonnet | ✅ | ✅ | ✅ | ✅ |
| Claude 3 Opus | ✅ | ✅ | ❌ | ❌ |
| Titan Text Express | ✅ | ✅ | ✅ | ✅ |

## Troubleshooting

### Common Issues

**1. Access Denied Errors**
```
Error: An error occurred (AccessDeniedException) when calling the InvokeModel operation
```

**Solutions:**
- Verify IAM permissions include `bedrock:InvokeModel`
- Check resource ARNs in policy
- Ensure model is available in your region

**2. Invalid Credentials**
```
Error: The security token included in the request is invalid
```

**Solutions:**
- Check AWS credentials are correct
- Verify credentials haven't expired
- For assumed roles, check role trust policy

**3. Region Mismatch**
```
Error: Model not found in region
```

**Solutions:**
- Verify model availability in your region
- Check AWS_REGION environment variable
- Use correct model IDs for your region

**4. Role Assumption Failures**
```
Error: User is not authorized to perform: sts:AssumeRole
```

**Solutions:**
- Check role trust policy allows your principal
- Verify external ID if required
- Ensure base credentials have `sts:AssumeRole` permission

### Debugging Commands

**Test AWS Credentials:**
```bash
aws sts get-caller-identity
```

**List Available Models:**
```bash
aws bedrock list-foundation-models --region us-east-1
```

**Test Model Access:**
```bash
aws bedrock invoke-model \
  --model-id anthropic.claude-3-haiku-20240307-v1:0 \
  --body '{"anthropic_version":"bedrock-2023-05-31","max_tokens":10,"messages":[{"role":"user","content":"Hi"}]}' \
  --cli-binary-format raw-in-base64-out \
  --region us-east-1 \
  output.json
```

## Security Best Practices

### 1. Principle of Least Privilege

Grant only necessary permissions:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "bedrock:InvokeModel"
            ],
            "Resource": [
                "arn:aws:bedrock:us-east-1::foundation-model/anthropic.claude-3-haiku-20240307-v1:0"
            ],
            "Condition": {
                "StringEquals": {
                    "aws:RequestedRegion": "us-east-1"
                }
            }
        }
    ]
}
```

### 2. Use IAM Roles Instead of Keys

Prefer IAM roles over static credentials:

```bash
# Good: Use instance profile
# No credentials in environment

# Avoid: Static credentials
export AWS_ACCESS_KEY_ID=...
export AWS_SECRET_ACCESS_KEY=...
```

### 3. Credential Rotation

For static credentials, implement rotation:

```python
import boto3
from datetime import datetime, timedelta

def check_key_age():
    iam = boto3.client('iam')
    
    # Get access key metadata
    response = iam.list_access_keys()
    
    for key in response['AccessKeyMetadata']:
        age = datetime.now(key['CreateDate'].tzinfo) - key['CreateDate']
        
        if age > timedelta(days=90):
            print(f"Warning: Access key {key['AccessKeyId']} is {age.days} days old")
```

### 4. Environment-Specific Configuration

Use different credentials for different environments:

```bash
# Development
export AWS_PROFILE=dev-profile

# Staging
export AWS_PROFILE=staging-profile

# Production
# Use IAM roles, no profile needed
```

### 5. Audit and Monitoring

Monitor AWS API usage:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "bedrock:InvokeModel"
            ],
            "Resource": "*",
            "Condition": {
                "Bool": {
                    "aws:CloudTrailLogged": "true"
                }
            }
        }
    ]
}
```

## Configuration Examples

### Docker Deployment

```dockerfile
FROM python:3.11-slim

# Install application
COPY . /app
WORKDIR /app
RUN pip install -e .

# Use IAM role (no credentials in image)
ENV AWS_REGION=us-east-1

CMD ["amazon-chat", "serve", "--host", "0.0.0.0"]
```

### Docker Compose

```yaml
version: '3.8'
services:
  amazon-chat:
    build: .
    environment:
      - AWS_REGION=us-east-1
      # For development only
      - AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID}
      - AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY}
    ports:
      - "8000:8000"
```

### Kubernetes Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: amazon-chat-server
spec:
  replicas: 3
  selector:
    matchLabels:
      app: amazon-chat-server
  template:
    metadata:
      labels:
        app: amazon-chat-server
    spec:
      serviceAccountName: amazon-chat-sa
      containers:
      - name: server
        image: amazon-chat-server:latest
        env:
        - name: AWS_REGION
          value: us-east-1
        ports:
        - containerPort: 8000
```

### GitHub Actions

```yaml
name: Deploy
on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    permissions:
      id-token: write
      contents: read
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Configure AWS credentials
      uses: aws-actions/configure-aws-credentials@v2
      with:
        role-to-assume: arn:aws:iam::123456789012:role/GitHubActionsRole
        aws-region: us-east-1
    
    - name: Test Bedrock access
      run: |
        aws bedrock list-foundation-models --region us-east-1
```

---

This guide covers all aspects of AWS authentication for the Amazon Chat Completions Server. Choose the method that best fits your deployment scenario and security requirements. 