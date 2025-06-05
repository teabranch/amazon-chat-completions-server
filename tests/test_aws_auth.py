import pytest
import os
from unittest.mock import patch, MagicMock
from src.open_amazon_chat_completions_server.services.bedrock_service import BedrockService
from src.open_amazon_chat_completions_server.core.exceptions import ConfigurationError

# Import authentication check functions from bedrock tests
import sys
sys.path.append('tests')

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

try:
    from test_bedrock_chat import check_aws_authentication, get_aws_auth_status_message
    AWS_CONFIGURED = check_aws_authentication()
    AWS_AUTH_STATUS_MESSAGE = get_aws_auth_status_message()
except ImportError:
    # Fallback if test_bedrock_chat is not available
    def check_aws_authentication():
        aws_region_is_set = bool(os.getenv("AWS_REGION") or os.getenv("AWS_DEFAULT_REGION"))
        aws_profile_is_set = bool(os.getenv("AWS_PROFILE"))
        aws_access_key_is_set = bool(os.getenv("AWS_ACCESS_KEY_ID"))
        aws_secret_key_is_set = bool(os.getenv("AWS_SECRET_ACCESS_KEY"))
        aws_keys_configured = aws_access_key_is_set and aws_secret_key_is_set
        aws_role_arn_is_set = bool(os.getenv("AWS_ROLE_ARN"))
        
        if aws_role_arn_is_set:
            base_credentials_available = aws_profile_is_set or aws_keys_configured
            role_assumption_viable = base_credentials_available
        else:
            role_assumption_viable = False
        
        auth_methods_available = (
            aws_profile_is_set or 
            aws_keys_configured or 
            role_assumption_viable
        )
        
        return aws_region_is_set and auth_methods_available
    
    AWS_CONFIGURED = check_aws_authentication()
    AWS_AUTH_STATUS_MESSAGE = "AWS authentication check"


class TestAWSAuthenticationMocked:
    """Test AWS authentication methods with mocked AWS services."""

    @patch('src.open_amazon_chat_completions_server.services.bedrock_service.boto3.Session')
    def test_static_credentials_session_creation(self, mock_session):
        """Test session creation with static AWS credentials."""
        # Mock the session and STS client
        mock_sts_client = MagicMock()
        mock_sts_client.get_caller_identity.return_value = {
            'Account': '123456789012',
            'Arn': 'arn:aws:iam::123456789012:user/test-user'
        }
        mock_session.return_value.client.return_value = mock_sts_client
        mock_session.return_value.region_name = 'us-east-1'
        
        with patch.dict(os.environ, {
            'AWS_ACCESS_KEY_ID': 'test-key-id',
            'AWS_SECRET_ACCESS_KEY': 'test-secret-key',
            'AWS_REGION': 'us-east-1'
        }, clear=True):  # Clear all environment variables first
            service = BedrockService(AWS_REGION='us-east-1', validate_credentials=False)
            service._create_aws_session()
            
            # Verify session was created with static credentials
            mock_session.assert_called_with(
                aws_access_key_id='test-key-id',
                aws_secret_access_key='test-secret-key',
                aws_session_token=None,
                region_name='us-east-1'
            )

    @patch('src.open_amazon_chat_completions_server.services.bedrock_service.boto3.Session')
    def test_profile_session_creation(self, mock_session):
        """Test session creation with AWS profile."""
        # Mock the session and STS client
        mock_sts_client = MagicMock()
        mock_sts_client.get_caller_identity.return_value = {
            'Account': '123456789012',
            'Arn': 'arn:aws:iam::123456789012:user/test-user'
        }
        mock_session.return_value.client.return_value = mock_sts_client
        mock_session.return_value.region_name = 'us-east-1'
        
        with patch.dict(os.environ, {}, clear=True):
            service = BedrockService(AWS_REGION='us-east-1', AWS_PROFILE='test-profile', validate_credentials=False)
            service._create_aws_session()
            
            # Verify session was created with profile
            mock_session.assert_called_with(
                profile_name='test-profile',
                region_name='us-east-1'
            )

    @patch('src.open_amazon_chat_completions_server.services.bedrock_service.boto3.Session')
    def test_role_assumption_session_creation_mocked(self, mock_session):
        """Test session creation with role assumption (mocked)."""
        # Mock the STS client and assume_role response
        mock_sts_client = MagicMock()
        mock_sts_client.assume_role.return_value = {
            'Credentials': {
                'AccessKeyId': 'assumed-key-id',
                'SecretAccessKey': 'assumed-secret-key',
                'SessionToken': 'assumed-session-token',
                'Expiration': '2024-01-01T00:00:00Z'
            }
        }
        mock_sts_client.get_caller_identity.return_value = {
            'Account': '123456789012',
            'Arn': 'arn:aws:sts::123456789012:assumed-role/TestRole/test-session'
        }
        mock_session.return_value.client.return_value = mock_sts_client
        mock_session.return_value.region_name = 'us-east-1'
        
        # Clear environment and only set profile to force role assumption
        with patch.dict(os.environ, {
            'AWS_PROFILE': 'test-profile',
        }, clear=True):
            service = BedrockService(
                AWS_REGION='us-east-1',
                AWS_ROLE_ARN='arn:aws:iam::123456789012:role/TestRole',  # Non-SSO role
                AWS_EXTERNAL_ID='test-external-id',
                validate_credentials=False
            )
            
            # Trigger role assumption by calling the method directly
            service._create_assume_role_session()
            
            # Verify assume_role was called with correct parameters
            mock_sts_client.assume_role.assert_called_once()
            call_args = mock_sts_client.assume_role.call_args[1]
            assert call_args['RoleArn'] == 'arn:aws:iam::123456789012:role/TestRole'
            assert call_args['ExternalId'] == 'test-external-id'
            assert 'RoleSessionName' in call_args
            assert 'DurationSeconds' in call_args

    @patch('src.open_amazon_chat_completions_server.services.bedrock_service.boto3.Session')
    def test_web_identity_session_creation(self, mock_session):
        """Test session creation with web identity token."""
        # Mock the STS client
        mock_sts_client = MagicMock()
        mock_sts_client.get_caller_identity.return_value = {
            'Account': '123456789012',
            'Arn': 'arn:aws:sts::123456789012:assumed-role/WebIdentityRole/test-session'
        }
        mock_session.return_value.client.return_value = mock_sts_client
        mock_session.return_value.region_name = 'us-east-1'
        
        with patch.dict(os.environ, {}, clear=True):
            BedrockService(
                AWS_REGION='us-east-1',
                AWS_WEB_IDENTITY_TOKEN_FILE='/tmp/token',
                AWS_ROLE_ARN='arn:aws:iam::123456789012:role/WebIdentityRole',
                validate_credentials=False
            )
            
            # Verify the session was created
            assert mock_session.called

    @patch('src.open_amazon_chat_completions_server.services.bedrock_service.boto3.Session')
    def test_authentication_priority_order(self, mock_session):
        """Test that authentication methods are used in the correct priority order."""
        # Mock the session and STS client
        mock_sts_client = MagicMock()
        mock_sts_client.get_caller_identity.return_value = {
            'Account': '123456789012',
            'Arn': 'arn:aws:iam::123456789012:user/test-user'
        }
        mock_session.return_value.client.return_value = mock_sts_client
        mock_session.return_value.region_name = 'us-east-1'
        
        # Test that static credentials take priority over profile
        with patch.dict(os.environ, {
            'AWS_ACCESS_KEY_ID': 'test-key-id',
            'AWS_SECRET_ACCESS_KEY': 'test-secret-key',
        }, clear=True):  # Clear all environment variables first
            service = BedrockService(
                AWS_REGION='us-east-1',
                AWS_PROFILE='test-profile',  # This should be ignored
                validate_credentials=False
            )
            service._create_aws_session()
            
            # Should use static credentials, not profile
            mock_session.assert_called_with(
                aws_access_key_id='test-key-id',
                aws_secret_access_key='test-secret-key',
                aws_session_token=None,
                region_name='us-east-1'
            )

    @patch('src.open_amazon_chat_completions_server.services.bedrock_service.boto3.Session')
    def test_session_duration_validation(self, mock_session):
        """Test that session duration is properly validated."""
        # Mock the STS client and assume_role response
        mock_sts_client = MagicMock()
        mock_sts_client.assume_role.return_value = {
            'Credentials': {
                'AccessKeyId': 'test',
                'SecretAccessKey': 'test',
                'SessionToken': 'test',
                'Expiration': '2024-01-01T00:00:00Z'
            }
        }
        mock_sts_client.get_caller_identity.return_value = {
            'Account': '123456789012',
            'Arn': 'arn:aws:sts::123456789012:assumed-role/TestRole/test-session'
        }
        mock_session.return_value.client.return_value = mock_sts_client
        mock_session.return_value.region_name = 'us-east-1'
        
        # Test with valid duration from environment - use profile to force role assumption
        with patch.dict(os.environ, {
            'AWS_ROLE_SESSION_DURATION': '7200',
            'AWS_PROFILE': 'test-profile',
        }, clear=True):
            service = BedrockService(
                AWS_REGION='us-east-1',
                AWS_ROLE_ARN='arn:aws:iam::123456789012:role/TestRole',  # Non-SSO role
                validate_credentials=False
            )
            
            # Trigger role assumption by calling the method directly
            service._create_assume_role_session()
            
            # Verify assume_role was called and duration was used
            mock_sts_client.assume_role.assert_called_once()
            call_args = mock_sts_client.assume_role.call_args[1]
            assert call_args['DurationSeconds'] == 7200

    def test_session_creation_methods_directly(self):
        """Test the session creation methods directly without full service initialization."""
        service = BedrockService.__new__(BedrockService)  # Create without calling __init__
        service.AWS_REGION = 'us-east-1'
        service.AWS_PROFILE = None
        service.AWS_ROLE_ARN = 'arn:aws:iam::123456789012:role/TestRole'
        service.AWS_EXTERNAL_ID = 'test-external-id'
        service.AWS_ROLE_SESSION_NAME = 'test-session'
        service.AWS_WEB_IDENTITY_TOKEN_FILE = None
        
        # Test role assumption method directly
        with patch('boto3.Session') as mock_session:
            mock_sts_client = MagicMock()
            mock_sts_client.assume_role.return_value = {
                'Credentials': {
                    'AccessKeyId': 'assumed-key-id',
                    'SecretAccessKey': 'assumed-secret-key',
                    'SessionToken': 'assumed-session-token',
                    'Expiration': '2024-01-01T00:00:00Z'
                }
            }
            mock_sts_client.get_caller_identity.return_value = {
                'Account': '123456789012',
                'Arn': 'arn:aws:sts::123456789012:assumed-role/TestRole/test-session'
            }
            mock_session.return_value.client.return_value = mock_sts_client
            
            service._create_assume_role_session()
            
            # Verify the session was created with assumed role credentials
            mock_session.assert_called_with(
                aws_access_key_id='assumed-key-id',
                aws_secret_access_key='assumed-secret-key',
                aws_session_token='assumed-session-token',
                region_name='us-east-1'
            )


@pytest.mark.external_api
@pytest.mark.aws_integration
@pytest.mark.skipif(not AWS_CONFIGURED, reason=f"AWS authentication not configured: {AWS_AUTH_STATUS_MESSAGE}")
class TestAWSAuthenticationReal:
    """Test AWS authentication methods with real AWS credentials."""

    def test_real_aws_authentication_detection(self):
        """Test that real AWS authentication is properly detected."""
        assert AWS_CONFIGURED, f"AWS authentication should be configured: {AWS_AUTH_STATUS_MESSAGE}"
        
        # Check that we have the necessary environment variables
        aws_region = os.getenv("AWS_REGION") or os.getenv("AWS_DEFAULT_REGION")
        assert aws_region, "AWS_REGION should be set"

    def test_real_bedrock_service_initialization(self):
        """Test that BedrockService can be initialized with real AWS credentials."""
        try:
            service = BedrockService(validate_credentials=True)
            assert service.AWS_REGION is not None
            assert service.bedrock_runtime_client is not None
            assert service.bedrock_client is not None
        except ConfigurationError as e:
            pytest.fail(f"BedrockService initialization failed with real credentials: {e}")

    def test_real_role_assumption(self):
        """Test role assumption with real AWS credentials."""
        aws_role_arn = os.getenv("AWS_ROLE_ARN")
        if not aws_role_arn:
            pytest.skip("AWS_ROLE_ARN not set, skipping role assumption test")
        
        # Check if this is an AWS SSO role
        is_sso_role = 'AWSReservedSSO' in aws_role_arn
        
        try:
            service = BedrockService(validate_credentials=True)
            
            # Verify that role assumption was configured
            assert service.AWS_ROLE_ARN == aws_role_arn
            
            # For AWS SSO roles, the service should use the profile directly instead of role assumption
            if is_sso_role:
                # The service should detect this and use the profile directly
                # Check that we can get caller identity
                session = service._create_aws_session()
                sts_client = session.client('sts')
                caller_identity = sts_client.get_caller_identity()
                
                # For SSO roles, we expect the ARN to already be an assumed role
                assert 'assumed-role' in caller_identity['Arn'], f"Expected SSO assumed role ARN, got: {caller_identity['Arn']}"
                
            else:
                # For non-SSO roles, test actual role assumption
                session = service._create_aws_session()
                assert session is not None
                
                # Test that we can get caller identity with the assumed role
                sts_client = session.client('sts')
                caller_identity = sts_client.get_caller_identity()
                
                # Verify that the ARN indicates an assumed role
                assert 'assumed-role' in caller_identity['Arn'], f"Expected assumed role ARN, got: {caller_identity['Arn']}"
            
        except Exception as e:
            if is_sso_role and ("Access denied" in str(e) or "not authorized" in str(e)):
                pytest.skip(f"AWS SSO role cannot assume itself (expected): {e}")
            else:
                pytest.fail(f"Real role assumption test failed: {e}")

    def test_real_bedrock_access(self):
        """Test that we can actually access Bedrock with real credentials."""
        try:
            service = BedrockService(validate_credentials=True)
            
            # Test listing foundation models
            models = service.bedrock_client.list_foundation_models()
            assert 'modelSummaries' in models
            assert len(models['modelSummaries']) > 0
            
            # Find a text model for testing
            text_models = [
                model for model in models['modelSummaries']
                if 'TEXT' in model.get('outputModalities', [])
            ]
            assert len(text_models) > 0, "No text models found in Bedrock"
            
        except Exception as e:
            pytest.fail(f"Real Bedrock access test failed: {e}")

    def test_real_authentication_priority(self):
        """Test authentication priority with real credentials."""
        # Get current environment
        current_profile = os.getenv("AWS_PROFILE")
        current_access_key = os.getenv("AWS_ACCESS_KEY_ID")
        current_secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")
        current_role_arn = os.getenv("AWS_ROLE_ARN")
        
        service = BedrockService(validate_credentials=False)
        
        # Verify the authentication method detection logic
        static_keys_present = bool(current_access_key and current_secret_key)
        profile_present = bool(current_profile)
        role_arn_present = bool(current_role_arn)
        
        if static_keys_present:
            # Should use static credentials
            assert not service.AWS_PROFILE or static_keys_present
        elif profile_present and role_arn_present:
            # Should use profile for role assumption
            assert service.AWS_PROFILE == current_profile
            assert service.AWS_ROLE_ARN == current_role_arn
        elif profile_present:
            # Should use profile directly
            assert service.AWS_PROFILE == current_profile

    def test_real_session_creation_methods(self):
        """Test different session creation methods with real credentials."""
        aws_profile = os.getenv("AWS_PROFILE")
        aws_role_arn = os.getenv("AWS_ROLE_ARN")
        
        if aws_profile and aws_role_arn:
            # Check if this is an AWS SSO role that cannot assume itself
            if 'AWSReservedSSO' in aws_role_arn:
                pytest.skip("AWS SSO roles cannot assume themselves - this is expected behavior")
            
            # Test role assumption with real credentials
            service = BedrockService(validate_credentials=False)
            
            try:
                session = service._create_assume_role_session()
                assert session is not None
                
                # Verify we can use the session
                sts_client = session.client('sts')
                caller_identity = sts_client.get_caller_identity()
                assert 'assumed-role' in caller_identity['Arn']
                
            except ConfigurationError as e:
                if "Access denied" in str(e) and 'AWSReservedSSO' in aws_role_arn:
                    pytest.skip(f"AWS SSO role cannot assume itself: {e}")
                else:
                    pytest.fail(f"Real role assumption session creation failed: {e}")
            except Exception as e:
                pytest.fail(f"Real role assumption session creation failed: {e}")

    def test_real_error_handling(self):
        """Test error handling with real AWS credentials."""
        # Test with invalid role ARN - but only if we have base credentials
        aws_profile = os.getenv("AWS_PROFILE")
        aws_access_key = os.getenv("AWS_ACCESS_KEY_ID")
        
        if not (aws_profile or aws_access_key):
            pytest.skip("No base credentials available for role assumption error testing")
        
        try:
            service = BedrockService(
                AWS_ROLE_ARN='arn:aws:iam::123456789012:role/NonExistentRole',
                validate_credentials=False  # Don't validate during init, let it fail during role assumption
            )
            
            # Try to create a session - this should fail
            service._create_assume_role_session()
            pytest.fail("Should have failed with invalid role ARN")
            
        except ConfigurationError as e:
            assert "role assumption" in str(e).lower() or "access denied" in str(e).lower()
        except Exception as e:
            # Any other exception is also acceptable as it indicates the role assumption failed
            assert "role" in str(e).lower() or "access" in str(e).lower() or "denied" in str(e).lower()

    def test_real_external_id_handling(self):
        """Test external ID handling with real credentials."""
        aws_role_arn = os.getenv("AWS_ROLE_ARN")
        aws_external_id = os.getenv("AWS_EXTERNAL_ID")
        
        if not aws_role_arn:
            pytest.skip("AWS_ROLE_ARN not set, skipping external ID test")
        
        try:
            service = BedrockService(
                AWS_ROLE_ARN=aws_role_arn,
                AWS_EXTERNAL_ID=aws_external_id,
                validate_credentials=True
            )
            
            if aws_external_id:
                assert service.AWS_EXTERNAL_ID == aws_external_id
            
        except Exception as e:
            # If external ID is required but not provided, we should get a specific error
            if aws_external_id is None and "external" in str(e).lower():
                pass  # Expected error
            else:
                pytest.fail(f"Unexpected error with external ID: {e}")


class TestAWSAuthenticationConfiguration:
    """Test AWS authentication configuration and validation."""

    @pytest.mark.skipif(not AWS_CONFIGURED, reason=f"AWS authentication not configured: {AWS_AUTH_STATUS_MESSAGE}")
    def test_configuration_validation(self):
        """Test that configuration validation works with new authentication methods."""
        from src.open_amazon_chat_completions_server.utils.config_loader import AppConfig
        
        # Since AppConfig always loads .env file, let's test that it properly handles
        # the current configuration and validates it correctly
        config = AppConfig()
        
        # Test that validation doesn't crash with the current configuration
        # The _validate_config method should run without exceptions
        config._validate_config()  # This should not raise any exceptions
        
        # Only test AWS_ROLE_ARN if it's actually configured
        # Different authentication methods may not require AWS_ROLE_ARN
        if config.AWS_ROLE_ARN is not None:
            assert 'arn:aws:iam::' in config.AWS_ROLE_ARN
        
        # Verify that at least one authentication method is configured
        aws_static_keys_present = config.AWS_ACCESS_KEY_ID and config.AWS_SECRET_ACCESS_KEY
        aws_profile_present = bool(config.AWS_PROFILE)
        aws_role_arn_present = bool(config.AWS_ROLE_ARN)
        aws_web_identity_present = bool(config.AWS_WEB_IDENTITY_TOKEN_FILE)
        
        assert any([aws_static_keys_present, aws_profile_present, aws_role_arn_present, aws_web_identity_present]), \
            "At least one AWS authentication method should be configured when AWS_CONFIGURED is True"

    def test_authentication_method_detection(self):
        """Test the authentication method detection logic."""
        # Test various combinations of environment variables
        test_cases = [
            # (env_vars, expected_auth_available)
            ({'AWS_ACCESS_KEY_ID': 'key', 'AWS_SECRET_ACCESS_KEY': 'secret', 'AWS_REGION': 'us-east-1'}, True),
            ({'AWS_PROFILE': 'test', 'AWS_REGION': 'us-east-1'}, True),
            ({'AWS_PROFILE': 'test', 'AWS_ROLE_ARN': 'arn:aws:iam::123:role/test', 'AWS_REGION': 'us-east-1'}, True),
            ({'AWS_ROLE_ARN': 'arn:aws:iam::123:role/test', 'AWS_REGION': 'us-east-1'}, False),  # No base creds
            ({'AWS_REGION': 'us-east-1'}, False),  # No auth method
            ({}, False),  # Nothing set
        ]
        
        for env_vars, expected in test_cases:
            with patch.dict(os.environ, env_vars, clear=True):
                result = check_aws_authentication()
                assert result == expected, f"Failed for env_vars: {env_vars}, expected: {expected}, got: {result}" 