# AWS Authentication Guide

This guide covers all AWS authentication methods supported by the Amazon Chat Completions Server for accessing AWS Bedrock services.

## Overview

The server supports multiple AWS authentication methods with automatic detection and intelligent fallback. The authentication system is designed to work seamlessly across different deployment environments, from local development to production cloud deployments.

## Authentication Methods

### 1. Static Credentials

**Best for:** Development, testing, CI/CD pipelines
**Security Level:** ⚠️ Medium (requires secure storage)

```env
AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE
AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
AWS_SESSION_TOKEN=your-session-token  # Optional, for temporary credentials
AWS_REGION=us-east-1
```

**Advantages:**
- Simple to set up
- Works in any environment
- Good for automation

**Disadvantages:**
- Requires credential management
- Long-term credentials
- Risk of exposure

### 2. AWS Profile

**Best for:** Local development, multiple AWS accounts
**Security Level:** ✅ High (managed by AWS CLI)

```env
AWS_PROFILE=your-aws-profile
AWS_REGION=us-east-1
```

**Setup:**
```bash
# Configure AWS CLI profile
aws configure --profile your-aws-profile

# Or use AWS SSO
aws configure sso --profile your-aws-profile

# List existing profiles
aws configure list-profiles
```

**Advantages:**
- Credentials managed by AWS CLI
- Supports AWS SSO
- Easy profile switching
- Secure credential storage

**Disadvantages:**
- Requires AWS CLI setup
- Local environment only

### 3. Role Assumption

**Best for:** Cross-account access, enhanced security, temporary elevated permissions
**Security Level:** ✅ High (time-limited, auditable)

```env
# Base credentials (required for role assumption)
AWS_PROFILE=base-profile
# OR
AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE
AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY

# Role to assume
AWS_ROLE_ARN=arn:aws:iam::123456789012:role/BedrockAccessRole
AWS_EXTERNAL_ID=unique-external-id  # Optional, for cross-account scenarios
AWS_ROLE_SESSION_NAME=amazon-chat-completions-session  # Optional
AWS_ROLE_SESSION_DURATION=3600  # Optional, 900-43200 seconds (default: 3600)
AWS_REGION=us-east-1
```

#### Role Trust Policy Examples

**Same Account Role:**
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "AWS": "arn:aws:iam::123456789012:user/username"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
```

**Cross-Account Role with External ID:**
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "AWS": "arn:aws:iam::SOURCE-ACCOUNT:user/username"
      },
      "Action": "sts:AssumeRole",
      "Condition": {
        "StringEquals": {
          "sts:ExternalId": "unique-external-id"
        }
      }
    }
  ]
}
```

**Advantages:**
- Time-limited sessions
- Audit trail via CloudTrail
- Least privilege access
- Cross-account support
- External ID for additional security

**Disadvantages:**
- Requires base credentials
- More complex setup
- Session expiration

### 4. Web Identity Token (OIDC)

**Best for:** Kubernetes, GitHub Actions, GitLab CI, other OIDC providers
**Security Level:** ✅ High (no long-term credentials, automatic rotation)

```env
AWS_WEB_IDENTITY_TOKEN_FILE=/var/run/secrets/eks.amazonaws.com/serviceaccount/token
AWS_ROLE_ARN=arn:aws:iam::123456789012:role/EKSBedrockRole
AWS_ROLE_SESSION_NAME=amazon-chat-completions-session  # Optional
AWS_REGION=us-east-1
```

#### Kubernetes Setup

**ServiceAccount:**
```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: amazon-chat-completions
  namespace: default
  annotations:
    eks.amazonaws.com/role-arn: arn:aws:iam::123456789012:role/EKSBedrockRole
```

**Deployment:**
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: amazon-chat-completions
spec:
  template:
    spec:
      serviceAccountName: amazon-chat-completions
      containers:
      - name: app
        image: amazon-chat-completions:latest
        env:
        - name: AWS_REGION
          value: us-east-1
```

#### GitHub Actions Setup

```yaml
name: Deploy
on: [push]

jobs:
  deploy:
    runs-on: ubuntu-latest
    permissions:
      id-token: write
      contents: read
    steps:
    - uses: aws-actions/configure-aws-credentials@v4
      with:
        role-to-assume: arn:aws:iam::123456789012:role/GitHubActionsRole
        aws-region: us-east-1
    - name: Deploy
      run: |
        # Your deployment commands
```

**Advantages:**
- No long-term credentials
- Automatic token rotation
- Native cloud integration
- Secure by default

**Disadvantages:**
- Requires OIDC provider setup
- Environment-specific

### 5. Instance Profile/Default Chain

**Best for:** EC2 instances, ECS tasks, Lambda functions
**Security Level:** ✅ High (no credential management, automatic rotation)

```env
# Only region required
AWS_REGION=us-east-1
```

**Credential Chain Order:**
1. Environment variables (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`)
2. Shared credentials file (`~/.aws/credentials`)
3. Shared config file (`~/.aws/config`)
4. IAM instance profiles (EC2)
5. ECS task roles
6. EKS service account roles

**Advantages:**
- No credential management
- Automatic rotation
- Native AWS integration
- Secure by default

**Disadvantages:**
- AWS environment only
- Less control over permissions

## Authentication Priority

The server uses this priority order for authentication:

1. **Static Credentials** (`AWS_ACCESS_KEY_ID` + `AWS_SECRET_ACCESS_KEY`)
2. **AWS Profile** (`AWS_PROFILE`)
3. **Role Assumption** (`AWS_ROLE_ARN` with base credentials)
4. **Web Identity Token** (`AWS_WEB_IDENTITY_TOKEN_FILE`)
5. **Default Credential Chain** (instance profiles, etc.)

## Required AWS Permissions

### Minimum Bedrock Permissions

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeModel",
        "bedrock:InvokeModelWithResponseStream",
        "bedrock:ListFoundationModels"
      ],
      "Resource": "*"
    }
  ]
}
```

### Role Assumption Permissions

For the base credentials used to assume roles:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": "sts:AssumeRole",
      "Resource": "arn:aws:iam::*:role/YourBedrockRole"
    }
  ]
}
```

### Model-Specific Permissions

Some models may require additional permissions:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "bedrock:GetFoundationModel",
        "bedrock:GetModelInvocationLoggingConfiguration"
      ],
      "Resource": "*"
    }
  ]
}
```

## Troubleshooting

### Common Error Messages

#### "Role assumption requires base AWS credentials"

**Problem:** `AWS_ROLE_ARN` is set but no base credentials are available.

**Solution:**
```bash
# Add base credentials
AWS_PROFILE=your-profile
# OR
AWS_ACCESS_KEY_ID=your-key
AWS_SECRET_ACCESS_KEY=your-secret
```

#### "The config profile (profile-name) could not be found"

**Problem:** AWS profile doesn't exist or isn't configured.

**Solution:**
```bash
# Configure the profile
aws configure --profile profile-name

# Or check existing profiles
aws configure list-profiles

# For SSO profiles
aws configure sso --profile profile-name
```

#### "Access denied when assuming role"

**Problem:** Role trust policy doesn't allow your principal or role lacks permissions.

**Solutions:**
1. Check role trust policy allows your principal
2. Verify role has required Bedrock permissions
3. Check external ID if using cross-account access
4. Verify session duration is within limits

#### "Web identity token file not found"

**Problem:** Token file path is incorrect or file doesn't exist.

**Solution:**
```bash
# Verify the token file exists
ls -la /var/run/secrets/eks.amazonaws.com/serviceaccount/token

# Check Kubernetes ServiceAccount annotation
kubectl describe serviceaccount amazon-chat-completions
```

#### "You must specify a region"

**Problem:** `AWS_REGION` is not set.

**Solution:**
```bash
# Set the region
AWS_REGION=us-east-1

# Or use AWS_DEFAULT_REGION
AWS_DEFAULT_REGION=us-east-1
```

#### "Invalid base credentials for role assumption"

**Problem:** Base credentials are invalid or expired.

**Solutions:**
1. Refresh AWS SSO session: `aws sso login --profile your-profile`
2. Update static credentials
3. Check credential expiration

### Testing Authentication

#### Test with CLI Commands

```bash
# Test basic AWS access
aws sts get-caller-identity

# Test with specific profile
aws sts get-caller-identity --profile your-profile

# Test Bedrock access
aws bedrock list-foundation-models --region us-east-1

# Test role assumption
aws sts assume-role \
  --role-arn arn:aws:iam::123456789012:role/YourRole \
  --role-session-name test-session
```

#### Test with Application

```bash
# Test AWS configuration (if implemented)
amazon-chat config test-aws

# Or test with Python
python -c "
import boto3
session = boto3.Session()
print('Caller Identity:', session.client('sts').get_caller_identity())
print('Bedrock Models:', len(session.client('bedrock', region_name='us-east-1').list_foundation_models()['modelSummaries']))
"
```

### Debug Logging

Enable debug logging to see authentication details:

```env
LOG_LEVEL=DEBUG
```

This will show:
- Which authentication method is being used
- Role assumption attempts
- Credential validation results
- AWS API call details

## Security Best Practices

### 1. Principle of Least Privilege
- Grant only necessary Bedrock permissions
- Use resource-specific ARNs when possible
- Regularly audit permissions

### 2. Credential Rotation
- Rotate static credentials regularly
- Use temporary credentials when possible
- Monitor credential usage

### 3. Monitoring and Auditing
- Enable CloudTrail for API calls
- Monitor unusual access patterns
- Set up alerts for failed authentication

### 4. Environment Separation
- Use different roles for different environments
- Separate development and production credentials
- Use external IDs for cross-account access

### 5. Secure Storage
- Never commit credentials to version control
- Use secure secret management systems
- Encrypt credentials at rest

## Environment-Specific Recommendations

### Local Development
- Use AWS profiles with SSO
- Avoid long-term static credentials
- Use role assumption for cross-account access

### CI/CD Pipelines
- Use OIDC providers when available
- Use temporary credentials
- Store secrets in secure CI/CD secret stores

### Container Environments
- Use service account roles (EKS)
- Use task roles (ECS)
- Avoid embedding credentials in images

### Production Deployments
- Use instance profiles or service roles
- Enable comprehensive logging
- Implement credential rotation
- Use least privilege access

## Migration Guide

### From Static Credentials to Roles

1. Create IAM role with required permissions
2. Set up role trust policy
3. Update configuration to use role assumption
4. Test thoroughly
5. Remove static credentials

### From Profiles to Instance Profiles

1. Create instance profile with required permissions
2. Attach to EC2 instances
3. Remove AWS_PROFILE from configuration
4. Test with default credential chain
5. Clean up local profiles if no longer needed

This comprehensive guide should help you choose and implement the most appropriate AWS authentication method for your specific use case and environment. 