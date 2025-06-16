import json
from datetime import datetime
from unittest.mock import Mock, patch

import pytest
from click.testing import CliRunner

from src.open_bedrock_server.cli.main import main
from src.open_bedrock_server.core.knowledge_base_models import (
    Citation,
    DataSource,
    DataSourceList,
    KnowledgeBase,
    KnowledgeBaseHealth,
    KnowledgeBaseList,
    KnowledgeBaseQueryResponse,
    RAGResponse,
    RetrievalResult,
)


@pytest.mark.knowledge_base
@pytest.mark.integration
@pytest.mark.kb_cli
class TestKnowledgeBaseCLICommands:
    """Test Knowledge Base CLI commands."""

    @pytest.fixture
    def runner(self):
        """CLI test runner."""
        return CliRunner()

    @pytest.fixture
    def mock_kb_service(self):
        """Mock KnowledgeBaseService for CLI testing."""
        with patch(
            "src.open_bedrock_server.cli.main.KnowledgeBaseService"
        ) as mock_service:
            mock_instance = Mock()
            mock_service.return_value = mock_instance
            yield mock_instance

    @pytest.fixture
    def sample_knowledge_base(self):
        """Sample knowledge base for testing."""
        return KnowledgeBase(
            knowledge_base_id="kb-123456789",
            name="test-kb",
            description="Test knowledge base",
            role_arn="arn:aws:iam::123456789012:role/test-role",
            storage_configuration={
                "type": "OPENSEARCH_SERVERLESS",
                "opensearchServerlessConfiguration": {
                    "collectionArn": "arn:aws:aoss:us-east-1:123456789012:collection/test-collection",
                    "vectorIndexName": "test-index",
                    "fieldMapping": {
                        "vectorField": "vector",
                        "textField": "text",
                        "metadataField": "metadata",
                    },
                },
            },
            status="ACTIVE",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

    def test_kb_list_command_success(
        self, runner, mock_kb_service, sample_knowledge_base
    ):
        """Test kb list command success."""
        # Mock service response
        kb_list = KnowledgeBaseList(
            knowledge_bases=[sample_knowledge_base], next_token=None
        )
        mock_kb_service.list_knowledge_bases.return_value = kb_list

        result = runner.invoke(main, ["kb", "list"])

        assert result.exit_code == 0
        assert "kb-123456789" in result.output
        assert "test-kb" in result.output
        assert "ACTIVE" in result.output

        mock_kb_service.list_knowledge_bases.assert_called_once()

    def test_kb_list_command_with_options(self, runner, mock_kb_service):
        """Test kb list command with options."""
        kb_list = KnowledgeBaseList(knowledge_bases=[], next_token="next-token")
        mock_kb_service.list_knowledge_bases.return_value = kb_list

        result = runner.invoke(
            main, ["kb", "list", "--limit", "5", "--region", "us-west-2"]
        )

        assert result.exit_code == 0
        mock_kb_service.list_knowledge_bases.assert_called_once_with(limit=5)

    def test_kb_list_command_json_output(
        self, runner, mock_kb_service, sample_knowledge_base
    ):
        """Test kb list command with JSON output."""
        kb_list = KnowledgeBaseList(
            knowledge_bases=[sample_knowledge_base], next_token=None
        )
        mock_kb_service.list_knowledge_bases.return_value = kb_list

        result = runner.invoke(main, ["kb", "list", "--output", "json"])

        assert result.exit_code == 0
        # Should be valid JSON
        output_data = json.loads(result.output)
        assert "knowledge_bases" in output_data
        assert len(output_data["knowledge_bases"]) == 1
        assert output_data["knowledge_bases"][0]["knowledge_base_id"] == "kb-123456789"

    def test_kb_get_command_success(
        self, runner, mock_kb_service, sample_knowledge_base
    ):
        """Test kb get command success."""
        mock_kb_service.get_knowledge_base.return_value = sample_knowledge_base

        result = runner.invoke(main, ["kb", "get", "kb-123456789"])

        assert result.exit_code == 0
        assert "kb-123456789" in result.output
        assert "test-kb" in result.output
        assert "Test knowledge base" in result.output

        mock_kb_service.get_knowledge_base.assert_called_once_with("kb-123456789")

    def test_kb_get_command_not_found(self, runner, mock_kb_service):
        """Test kb get command when knowledge base not found."""
        mock_kb_service.get_knowledge_base.side_effect = Exception(
            "Knowledge base not found"
        )

        result = runner.invoke(main, ["kb", "get", "kb-nonexistent"])

        assert result.exit_code != 0
        assert "Knowledge base not found" in result.output

    def test_kb_create_command_success(
        self, runner, mock_kb_service, sample_knowledge_base
    ):
        """Test kb create command success."""
        mock_kb_service.create_knowledge_base.return_value = sample_knowledge_base

        # Create a temporary config file
        config_data = {
            "name": "test-kb",
            "description": "Test knowledge base",
            "role_arn": "arn:aws:iam::123456789012:role/test-role",
            "storage_configuration": {
                "type": "OPENSEARCH_SERVERLESS",
                "opensearchServerlessConfiguration": {
                    "collectionArn": "arn:aws:aoss:us-east-1:123456789012:collection/test-collection",
                    "vectorIndexName": "test-index",
                    "fieldMapping": {
                        "vectorField": "vector",
                        "textField": "text",
                        "metadataField": "metadata",
                    },
                },
            },
        }

        with runner.isolated_filesystem():
            with open("kb_config.json", "w") as f:
                json.dump(config_data, f)

            result = runner.invoke(main, ["kb", "create", "--config", "kb_config.json"])

        assert result.exit_code == 0
        assert "Successfully created knowledge base" in result.output
        assert "kb-123456789" in result.output

        mock_kb_service.create_knowledge_base.assert_called_once()

    def test_kb_create_command_invalid_config(self, runner, mock_kb_service):
        """Test kb create command with invalid config."""
        with runner.isolated_filesystem():
            with open("invalid_config.json", "w") as f:
                json.dump({"name": "test-kb"}, f)  # Missing required fields

            result = runner.invoke(
                main, ["kb", "create", "--config", "invalid_config.json"]
            )

        assert result.exit_code != 0
        assert "Error" in result.output

    def test_kb_update_command_success(
        self, runner, mock_kb_service, sample_knowledge_base
    ):
        """Test kb update command success."""
        updated_kb = sample_knowledge_base.model_copy()
        updated_kb.description = "Updated description"
        mock_kb_service.update_knowledge_base.return_value = updated_kb

        result = runner.invoke(
            main,
            ["kb", "update", "kb-123456789", "--description", "Updated description"],
        )

        assert result.exit_code == 0
        assert "Successfully updated knowledge base" in result.output

        mock_kb_service.update_knowledge_base.assert_called_once()

    def test_kb_delete_command_success(self, runner, mock_kb_service):
        """Test kb delete command success."""
        mock_kb_service.delete_knowledge_base.return_value = True

        result = runner.invoke(main, ["kb", "delete", "kb-123456789", "--confirm"])

        assert result.exit_code == 0
        assert "Successfully deleted knowledge base" in result.output

        mock_kb_service.delete_knowledge_base.assert_called_once_with("kb-123456789")

    def test_kb_delete_command_without_confirm(self, runner, mock_kb_service):
        """Test kb delete command without confirmation."""
        result = runner.invoke(main, ["kb", "delete", "kb-123456789"])

        assert result.exit_code != 0
        assert "confirmation required" in result.output.lower()

        # Should not call the service
        mock_kb_service.delete_knowledge_base.assert_not_called()

    def test_kb_query_command_success(self, runner, mock_kb_service):
        """Test kb query command success."""
        query_response = KnowledgeBaseQueryResponse(
            query_text="What is machine learning?",
            retrieval_results=[
                RetrievalResult(
                    content="Machine learning is a subset of AI...",
                    score=0.95,
                    metadata={"source": "ml_book.pdf"},
                    location={
                        "type": "S3",
                        "s3Location": {"uri": "s3://bucket/ml_book.pdf"},
                    },
                )
            ],
            citations=[],
        )
        mock_kb_service.query_knowledge_base.return_value = query_response

        result = runner.invoke(
            main, ["kb", "query", "kb-123456789", "What is machine learning?"]
        )

        assert result.exit_code == 0
        assert "Machine learning is a subset of AI" in result.output
        assert "Score: 0.95" in result.output
        assert "Source: ml_book.pdf" in result.output

        mock_kb_service.query_knowledge_base.assert_called_once()

    def test_kb_query_command_with_options(self, runner, mock_kb_service):
        """Test kb query command with options."""
        query_response = KnowledgeBaseQueryResponse(
            query_text="What is ML?", retrieval_results=[], citations=[]
        )
        mock_kb_service.query_knowledge_base.return_value = query_response

        result = runner.invoke(
            main,
            [
                "kb",
                "query",
                "kb-123456789",
                "What is ML?",
                "--max-results",
                "3",
                "--search-type",
                "SEMANTIC",
            ],
        )

        assert result.exit_code == 0
        mock_kb_service.query_knowledge_base.assert_called_once()

    def test_kb_chat_command_success(self, runner, mock_kb_service):
        """Test kb chat command success."""
        rag_response = RAGResponse(
            query_text="Explain machine learning",
            generated_text="Machine learning is a powerful technology that...",
            retrieval_results=[
                RetrievalResult(
                    content="ML definition...",
                    score=0.9,
                    metadata={"source": "textbook.pdf"},
                    location={
                        "type": "S3",
                        "s3Location": {"uri": "s3://bucket/textbook.pdf"},
                    },
                )
            ],
            citations=[
                Citation(
                    generated_response_part="Machine learning is",
                    retrieved_references=[
                        {
                            "content": "ML definition...",
                            "metadata": {"source": "textbook.pdf"},
                        }
                    ],
                )
            ],
        )
        mock_kb_service.retrieve_and_generate.return_value = rag_response

        result = runner.invoke(
            main, ["kb", "chat", "kb-123456789", "Explain machine learning"]
        )

        assert result.exit_code == 0
        assert "Machine learning is a powerful technology" in result.output
        assert "Citations:" in result.output
        assert "textbook.pdf" in result.output

        mock_kb_service.retrieve_and_generate.assert_called_once()

    def test_kb_chat_command_interactive_mode(self, runner, mock_kb_service):
        """Test kb chat command in interactive mode."""
        rag_response = RAGResponse(
            query_text="Hello",
            generated_text="Hello! How can I help you?",
            retrieval_results=[],
            citations=[],
        )
        mock_kb_service.retrieve_and_generate.return_value = rag_response

        # Simulate interactive input
        result = runner.invoke(
            main, ["kb", "chat", "kb-123456789", "--interactive"], input="Hello\nexit\n"
        )

        assert result.exit_code == 0
        assert "Hello! How can I help you?" in result.output
        assert "Chat session ended" in result.output

    def test_kb_chat_command_with_session(self, runner, mock_kb_service):
        """Test kb chat command with session management."""
        rag_response = RAGResponse(
            query_text="Follow up question",
            generated_text="Based on our previous conversation...",
            retrieval_results=[],
            citations=[],
            session_id="session-123",
        )
        mock_kb_service.retrieve_and_generate.return_value = rag_response

        result = runner.invoke(
            main,
            [
                "kb",
                "chat",
                "kb-123456789",
                "Follow up question",
                "--session-id",
                "session-123",
            ],
        )

        assert result.exit_code == 0
        assert "Based on our previous conversation" in result.output

        # Verify session ID was passed
        call_args = mock_kb_service.retrieve_and_generate.call_args[0][1]  # RAGRequest
        assert call_args.session_id == "session-123"

    def test_kb_health_command_success(self, runner, mock_kb_service):
        """Test kb health command success."""
        health = KnowledgeBaseHealth(
            knowledge_base_id="kb-123456789",
            status="HEALTHY",
            last_updated=datetime.now(),
            details={
                "status": "ACTIVE",
                "document_count": 1000,
                "embedding_model": "amazon.titan-embed-text-v1",
            },
        )
        mock_kb_service.health_check.return_value = health

        result = runner.invoke(main, ["kb", "health", "kb-123456789"])

        assert result.exit_code == 0
        assert "Status: HEALTHY" in result.output
        assert "Document Count: 1000" in result.output
        assert "amazon.titan-embed-text-v1" in result.output

        mock_kb_service.health_check.assert_called_once_with("kb-123456789")

    def test_kb_health_command_unhealthy(self, runner, mock_kb_service):
        """Test kb health command with unhealthy status."""
        health = KnowledgeBaseHealth(
            knowledge_base_id="kb-123456789",
            status="UNHEALTHY",
            last_updated=datetime.now(),
            details={"error": "Knowledge base not found"},
        )
        mock_kb_service.health_check.return_value = health

        result = runner.invoke(main, ["kb", "health", "kb-123456789"])

        assert result.exit_code == 0
        assert "Status: UNHEALTHY" in result.output
        assert "Knowledge base not found" in result.output

    def test_data_source_commands(self, runner, mock_kb_service):
        """Test data source related commands."""
        # Test list data sources
        data_source = DataSource(
            data_source_id="ds-123456789",
            knowledge_base_id="kb-123456789",
            name="test-datasource",
            status="AVAILABLE",
        )
        ds_list = DataSourceList(data_sources=[data_source], next_token=None)
        mock_kb_service.list_data_sources.return_value = ds_list

        result = runner.invoke(main, ["kb", "datasource", "list", "kb-123456789"])

        assert result.exit_code == 0
        assert "ds-123456789" in result.output
        assert "test-datasource" in result.output
        assert "AVAILABLE" in result.output

    def test_ingestion_job_commands(self, runner, mock_kb_service):
        """Test ingestion job related commands."""
        # Test start ingestion job
        mock_kb_service.start_ingestion_job.return_value = {
            "ingestionJobId": "job-123456789",
            "status": "STARTING",
        }

        result = runner.invoke(
            main, ["kb", "ingest", "start", "kb-123456789", "ds-123456789"]
        )

        assert result.exit_code == 0
        assert "job-123456789" in result.output
        assert "STARTING" in result.output

        mock_kb_service.start_ingestion_job.assert_called_once_with(
            "kb-123456789", "ds-123456789"
        )

    def test_ingestion_job_status_command(self, runner, mock_kb_service):
        """Test ingestion job status command."""
        mock_kb_service.get_ingestion_job.return_value = {
            "ingestionJobId": "job-123456789",
            "status": "COMPLETE",
            "statistics": {
                "numberOfDocumentsScanned": 100,
                "numberOfNewDocumentsIndexed": 50,
                "numberOfModifiedDocumentsIndexed": 25,
                "numberOfDocumentsDeleted": 5,
            },
        }

        result = runner.invoke(
            main,
            ["kb", "ingest", "status", "kb-123456789", "ds-123456789", "job-123456789"],
        )

        assert result.exit_code == 0
        assert "COMPLETE" in result.output
        assert "Documents Scanned: 100" in result.output
        assert "New Documents: 50" in result.output

    def test_command_error_handling(self, runner, mock_kb_service):
        """Test command error handling."""
        mock_kb_service.get_knowledge_base.side_effect = Exception("AWS service error")

        result = runner.invoke(main, ["kb", "get", "kb-123456789"])

        assert result.exit_code != 0
        assert "Error" in result.output
        assert "AWS service error" in result.output

    def test_command_with_verbose_output(
        self, runner, mock_kb_service, sample_knowledge_base
    ):
        """Test command with verbose output."""
        mock_kb_service.get_knowledge_base.return_value = sample_knowledge_base

        result = runner.invoke(main, ["kb", "get", "kb-123456789", "--verbose"])

        assert result.exit_code == 0
        # Should include more detailed information in verbose mode
        assert "Storage Configuration:" in result.output
        assert "OPENSEARCH_SERVERLESS" in result.output

    def test_command_with_different_regions(
        self, runner, mock_kb_service, sample_knowledge_base
    ):
        """Test command with different AWS regions."""
        mock_kb_service.get_knowledge_base.return_value = sample_knowledge_base

        result = runner.invoke(
            main, ["kb", "get", "kb-123456789", "--region", "eu-west-1"]
        )

        assert result.exit_code == 0
        # Service should be initialized with the specified region
        mock_kb_service.assert_called_with(region="eu-west-1")

    def test_command_output_formatting(
        self, runner, mock_kb_service, sample_knowledge_base
    ):
        """Test different output formatting options."""
        mock_kb_service.get_knowledge_base.return_value = sample_knowledge_base

        # Test table format (default)
        result = runner.invoke(main, ["kb", "get", "kb-123456789", "--output", "table"])
        assert result.exit_code == 0
        assert "│" in result.output  # Table formatting character

        # Test JSON format
        result = runner.invoke(main, ["kb", "get", "kb-123456789", "--output", "json"])
        assert result.exit_code == 0
        output_data = json.loads(result.output)
        assert output_data["knowledge_base_id"] == "kb-123456789"

    def test_command_input_validation(self, runner):
        """Test command input validation."""
        # Test invalid knowledge base ID format
        result = runner.invoke(main, ["kb", "get", "invalid-id"])
        assert result.exit_code != 0

        # Test missing required arguments
        result = runner.invoke(main, ["kb", "query"])
        assert result.exit_code != 0

        # Test invalid options
        result = runner.invoke(main, ["kb", "list", "--limit", "invalid"])
        assert result.exit_code != 0

    def test_command_help_messages(self, runner):
        """Test command help messages."""
        # Test main kb command help
        result = runner.invoke(main, ["kb", "--help"])
        assert result.exit_code == 0
        assert "Knowledge Base commands" in result.output

        # Test subcommand help
        result = runner.invoke(main, ["kb", "list", "--help"])
        assert result.exit_code == 0
        assert "List knowledge bases" in result.output

    @patch("builtins.input", side_effect=["y"])
    def test_interactive_confirmation(self, mock_input, runner, mock_kb_service):
        """Test interactive confirmation prompts."""
        mock_kb_service.delete_knowledge_base.return_value = True

        result = runner.invoke(main, ["kb", "delete", "kb-123456789"])

        assert result.exit_code == 0
        assert "Successfully deleted" in result.output

    def test_command_with_config_file(
        self, runner, mock_kb_service, sample_knowledge_base
    ):
        """Test commands with configuration file."""
        mock_kb_service.create_knowledge_base.return_value = sample_knowledge_base

        config_data = {
            "name": "test-kb-from-config",
            "description": "Test knowledge base from config",
            "role_arn": "arn:aws:iam::123456789012:role/test-role",
            "storage_configuration": {"type": "OPENSEARCH_SERVERLESS"},
        }

        with runner.isolated_filesystem():
            with open("kb.json", "w") as f:
                json.dump(config_data, f)

            result = runner.invoke(main, ["kb", "create", "--config", "kb.json"])

        assert result.exit_code == 0
        mock_kb_service.create_knowledge_base.assert_called_once()

    def test_command_with_environment_variables(
        self, runner, mock_kb_service, sample_knowledge_base
    ):
        """Test commands with environment variables."""
        import os

        mock_kb_service.get_knowledge_base.return_value = sample_knowledge_base

        with patch.dict(os.environ, {"AWS_REGION": "ap-southeast-1"}):
            result = runner.invoke(main, ["kb", "get", "kb-123456789"])

        assert result.exit_code == 0
        # Should use environment variable for region
        mock_kb_service.assert_called_with(region="ap-southeast-1")

    def test_command_progress_indicators(
        self, runner, mock_kb_service, sample_knowledge_base
    ):
        """Test command progress indicators for long-running operations."""
        # Simulate a slow operation
        import time

        def slow_create(*args, **kwargs):
            time.sleep(0.1)  # Simulate network delay
            return sample_knowledge_base

        mock_kb_service.create_knowledge_base.side_effect = slow_create

        config_data = {
            "name": "test-kb",
            "role_arn": "test-arn",
            "storage_configuration": {},
        }

        with runner.isolated_filesystem():
            with open("kb.json", "w") as f:
                json.dump(config_data, f)

            result = runner.invoke(main, ["kb", "create", "--config", "kb.json"])

        assert result.exit_code == 0
        # Should show some indication of progress for long operations
        assert "Creating" in result.output or "Successfully" in result.output
