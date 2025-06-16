from datetime import datetime
from unittest.mock import Mock, patch

import pytest

from src.open_bedrock_server.core.knowledge_base_models import (
    Citation,
    RetrievalResult,
    RetrieveAndGenerateResponse,
)
from src.open_bedrock_server.core.models import (
    ChatCompletionRequest,
    ChatCompletionResponse,
    ChatCompletionChoice,
    Message,
    Usage,
)
from src.open_bedrock_server.services.knowledge_base_integration_service import (
    IntegrationResult,
    IntegrationStrategy,
    KnowledgeBaseIntegrationService,
)



@pytest.mark.knowledge_base
@pytest.mark.integration
@pytest.mark.kb_integration
class TestKnowledgeBaseIntegrationService:
    """Test Knowledge Base integration service."""

    @pytest.fixture
    def mock_kb_service(self):
        """Mock KnowledgeBaseService."""
        with patch(
            "src.open_bedrock_server.services.knowledge_base_integration_service.KnowledgeBaseService"
        ) as mock_service:
            mock_instance = Mock()
            mock_service.return_value = mock_instance
            yield mock_instance

    @pytest.fixture
    def mock_detector(self):
        """Mock KnowledgeBaseDetector."""
        with patch(
            "src.open_bedrock_server.services.knowledge_base_integration_service.KnowledgeBaseDetector"
        ) as mock_detector:
            mock_instance = Mock()
            mock_detector.return_value = mock_instance
            yield mock_instance

    @pytest.fixture
    def mock_bedrock_service(self):
        """Mock BedrockService for fallback chat."""
        with patch(
            "src.open_bedrock_server.services.knowledge_base_integration_service.BedrockService"
        ) as mock_service:
            mock_instance = Mock()
            mock_service.return_value = mock_instance
            yield mock_instance

    @pytest.fixture
    def integration_service(self, mock_kb_service, mock_detector, mock_bedrock_service):
        """Create KnowledgeBaseIntegrationService with mocked dependencies."""
        service = KnowledgeBaseIntegrationService()
        service.kb_service = mock_kb_service
        service.detector = mock_detector
        service.bedrock_service = mock_bedrock_service
        return service

    @pytest.fixture
    def sample_chat_request(self):
        """Sample chat completion request."""
        return ChatCompletionRequest(
            model="anthropic.claude-3-haiku-20240307-v1:0",
            messages=[Message(role="user", content="What is machine learning?")],
            max_tokens=100,
            temperature=0.7,
        )

    @pytest.fixture
    def sample_rag_response(self):
        """Sample RAG response."""
        return RetrieveAndGenerateResponse(
            output="Machine learning is a subset of artificial intelligence...",
            citations=[
                Citation(
                    generatedResponsePart={"text": "Machine learning is a subset"},
                    retrievedReferences=[
                        {
                            "content": "ML is a method of data analysis...",
                            "location": {
                                "type": "S3",
                                "s3Location": {"uri": "s3://bucket/ml_textbook.pdf"},
                            },
                            "metadata": {"source": "ml_textbook.pdf"},
                        }
                    ],
                )
            ],
        )

    @pytest.fixture
    def sample_chat_response(self):
        """Sample regular chat response."""
        return ChatCompletionResponse(
            id="chatcmpl-123",
            object="chat.completion",
            created=int(datetime.now().timestamp()),
            model="anthropic.claude-3-haiku-20240307-v1:0",
            choices=[
                ChatCompletionChoice(
                    index=0,
                    message=Message(
                        role="assistant",
                        content="I'd be happy to help you with that question.",
                    ),
                    finish_reason="stop",
                )
            ],
            usage=Usage(prompt_tokens=10, completion_tokens=15, total_tokens=25),
        )

    def test_integration_service_initialization(self):
        """Test service initialization."""
        service = KnowledgeBaseIntegrationService()
        assert service.region == "us-east-1"  # Default region
        assert service.default_strategy == IntegrationStrategy.CONTEXT_AUGMENTATION

    def test_integration_service_custom_initialization(self):
        """Test service initialization with custom parameters."""
        service = KnowledgeBaseIntegrationService(
            region="us-west-2", default_strategy=IntegrationStrategy.DIRECT_RAG
        )
        assert service.region == "us-west-2"
        assert service.default_strategy == IntegrationStrategy.DIRECT_RAG

    @pytest.mark.asyncio
    async def test_process_chat_with_kb_explicit(
        self,
        integration_service,
        mock_kb_service,
        sample_chat_request,
        sample_rag_response,
    ):
        """Test processing chat with explicit knowledge base ID."""
        # Set explicit KB ID
        sample_chat_request.knowledge_base_id = "kb-123456789"

        # Mock RAG response
        mock_kb_service.retrieve_and_generate.return_value = sample_rag_response

        result = await integration_service.process_chat_with_kb(sample_chat_request)

        assert isinstance(result, IntegrationResult)
        assert result.used_kb is True
        assert result.strategy_used == IntegrationStrategy.DIRECT_RAG
        assert result.chat_response is not None
        assert (
            "Machine learning is a subset"
            in result.chat_response.choices[0].message.content
        )

        # Verify KB service was called
        mock_kb_service.retrieve_and_generate.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_chat_with_auto_detection_positive(
        self,
        integration_service,
        mock_detector,
        mock_kb_service,
        sample_chat_request,
        sample_rag_response,
    ):
        """Test processing chat with auto-detection (positive case)."""
        # Set auto KB mode
        sample_chat_request.auto_kb = True

        # Mock positive detection
        mock_detector.should_use_knowledge_base.return_value = True

        # Mock RAG response
        mock_kb_service.retrieve_and_generate.return_value = sample_rag_response

        result = await integration_service.process_chat_with_kb(sample_chat_request)

        assert result.used_kb is True
        assert result.detection_result.should_use_kb is True
        assert result.detection_result.confidence == 0.85

        # Verify detection was called
        mock_detector.detect_retrieval_intent.assert_called_once()
        mock_kb_service.retrieve_and_generate.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_chat_with_auto_detection_negative(
        self,
        integration_service,
        mock_detector,
        mock_bedrock_service,
        sample_chat_request,
        sample_chat_response,
    ):
        """Test processing chat with auto-detection (negative case)."""
        # Set auto KB mode
        sample_chat_request.auto_kb = True

        # Mock negative detection
        mock_detector.detect_retrieval_intent.return_value = DetectionResult(
            should_use_kb=False,
            confidence=0.2,
            detected_patterns=["casual_greeting"],
            reasoning="Query appears to be a casual greeting",
        )

        # Mock regular chat response
        mock_bedrock_service.chat_completion.return_value = sample_chat_response

        result = await integration_service.process_chat_with_kb(sample_chat_request)

        assert result.used_kb is False
        assert result.detection_result.should_use_kb is False
        assert result.detection_result.confidence == 0.2

        # Verify fallback chat was called
        mock_bedrock_service.chat_completion.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_chat_without_kb_features(
        self,
        integration_service,
        mock_bedrock_service,
        sample_chat_request,
        sample_chat_response,
    ):
        """Test processing chat without KB features enabled."""
        # Don't set KB ID or auto_kb
        mock_bedrock_service.chat_completion.return_value = sample_chat_response

        result = await integration_service.process_chat_with_kb(sample_chat_request)

        assert result.used_kb is False
        assert result.detection_result is None
        assert result.strategy_used is None

        # Verify regular chat was called
        mock_bedrock_service.chat_completion.assert_called_once()

    @pytest.mark.asyncio
    async def test_direct_rag_strategy(
        self,
        integration_service,
        mock_kb_service,
        sample_chat_request,
        sample_rag_response,
    ):
        """Test direct RAG strategy."""
        sample_chat_request.knowledge_base_id = "kb-123456789"
        mock_kb_service.retrieve_and_generate.return_value = sample_rag_response

        result = await integration_service._execute_direct_rag(
            sample_chat_request, "kb-123456789"
        )

        assert isinstance(result, IntegrationResult)
        assert result.used_kb is True
        assert result.strategy_used == IntegrationStrategy.DIRECT_RAG
        assert result.rag_response == sample_rag_response

        # Check that chat response was properly converted
        assert (
            result.chat_response.choices[0].message.content
            == sample_rag_response.generated_text
        )

    @pytest.mark.asyncio
    async def test_context_augmentation_strategy(
        self,
        integration_service,
        mock_kb_service,
        mock_bedrock_service,
        sample_chat_request,
        sample_rag_response,
        sample_chat_response,
    ):
        """Test context augmentation strategy."""
        sample_chat_request.knowledge_base_id = "kb-123456789"

        # Mock retrieval (without generation)
        retrieval_response = sample_rag_response.model_copy()
        retrieval_response.generated_text = None  # No generation in retrieval-only
        mock_kb_service.query_knowledge_base.return_value = retrieval_response

        # Mock chat with augmented context
        mock_bedrock_service.chat_completion.return_value = sample_chat_response

        result = await integration_service._execute_context_augmentation(
            sample_chat_request, "kb-123456789"
        )

        assert result.used_kb is True
        assert result.strategy_used == IntegrationStrategy.CONTEXT_AUGMENTATION

        # Verify both KB query and chat completion were called
        mock_kb_service.query_knowledge_base.assert_called_once()
        mock_bedrock_service.chat_completion.assert_called_once()

        # Check that context was augmented
        call_args = mock_bedrock_service.chat_completion.call_args[0][0]
        assert len(call_args.messages) > len(sample_chat_request.messages)

    @pytest.mark.asyncio
    async def test_citation_handling_openai_format(
        self, integration_service, mock_kb_service, sample_chat_request
    ):
        """Test citation handling in OpenAI format."""
        sample_chat_request.knowledge_base_id = "kb-123456789"
        sample_chat_request.citation_format = "OPENAI"

        # Mock RAG response with citations
        rag_response = RAGResponse(
            query_text="What is ML?",
            generated_text="Machine learning is AI.",
            retrieval_results=[
                RetrievalResult(
                    content="ML definition...",
                    score=0.9,
                    metadata={"source": "book.pdf", "page": 1},
                    location={
                        "type": "S3",
                        "s3Location": {"uri": "s3://bucket/book.pdf"},
                    },
                )
            ],
            citations=[
                Citation(
                    generated_response_part="Machine learning is AI",
                    retrieved_references=[
                        {
                            "content": "ML definition...",
                            "metadata": {"source": "book.pdf", "page": 1},
                        }
                    ],
                )
            ],
        )
        mock_kb_service.retrieve_and_generate.return_value = rag_response

        result = await integration_service._execute_direct_rag(
            sample_chat_request, "kb-123456789"
        )

        # Check that citations are included in OpenAI format
        response_content = result.chat_response.choices[0].message.content
        assert "[1]" in response_content or "【1】" in response_content

    @pytest.mark.asyncio
    async def test_session_management(
        self, integration_service, mock_kb_service, sample_rag_response
    ):
        """Test session management for conversational RAG."""
        # Create request with session ID
        request = ChatCompletionRequest(
            model="anthropic.claude-3-haiku-20240307-v1:0",
            messages=[Message(role="user", content="What is ML?")],
            knowledge_base_id="kb-123456789",
            session_id="session-123",
        )

        mock_kb_service.retrieve_and_generate.return_value = sample_rag_response

        await integration_service._execute_direct_rag(request, "kb-123456789")

        # Verify session ID was passed to KB service
        call_args = mock_kb_service.retrieve_and_generate.call_args[0][1]  # RAGRequest
        assert call_args.session_id == "session-123"

    @pytest.mark.asyncio
    async def test_custom_retrieval_config(
        self, integration_service, mock_kb_service, sample_rag_response
    ):
        """Test custom retrieval configuration."""
        request = ChatCompletionRequest(
            model="anthropic.claude-3-haiku-20240307-v1:0",
            messages=[Message(role="user", content="What is ML?")],
            knowledge_base_id="kb-123456789",
            retrieval_config={
                "vector_search_config": {
                    "numberOfResults": 3,
                    "overrideSearchType": "SEMANTIC",
                }
            },
        )

        mock_kb_service.retrieve_and_generate.return_value = sample_rag_response

        await integration_service._execute_direct_rag(request, "kb-123456789")

        # Verify retrieval config was passed correctly
        call_args = mock_kb_service.retrieve_and_generate.call_args[0][1]  # RAGRequest
        assert call_args.retrieval_config.vector_search_config["numberOfResults"] == 3
        assert (
            call_args.retrieval_config.vector_search_config["overrideSearchType"]
            == "SEMANTIC"
        )

    @pytest.mark.asyncio
    async def test_error_handling_kb_service_failure(
        self,
        integration_service,
        mock_kb_service,
        mock_bedrock_service,
        sample_chat_request,
        sample_chat_response,
    ):
        """Test error handling when KB service fails."""
        sample_chat_request.knowledge_base_id = "kb-123456789"

        # Mock KB service failure
        mock_kb_service.retrieve_and_generate.side_effect = Exception(
            "KB service error"
        )

        # Mock fallback chat response
        mock_bedrock_service.chat_completion.return_value = sample_chat_response

        result = await integration_service.process_chat_with_kb(sample_chat_request)

        # Should fallback to regular chat
        assert result.used_kb is False
        assert result.error is not None
        assert "KB service error" in result.error

        # Verify fallback was called
        mock_bedrock_service.chat_completion.assert_called_once()

    @pytest.mark.asyncio
    async def test_conversation_history_context(
        self, integration_service, mock_detector, mock_kb_service, sample_rag_response
    ):
        """Test that conversation history is used for context."""
        request = ChatCompletionRequest(
            model="anthropic.claude-3-haiku-20240307-v1:0",
            messages=[
                Message(role="user", content="I'm working on a ML project"),
                Message(
                    role="assistant",
                    content="That's great! What aspect are you focusing on?",
                ),
                Message(role="user", content="Can you help me with this?"),
            ],
            auto_kb=True,
        )

        # Mock positive detection due to context
        mock_detector.detect_retrieval_intent.return_value = DetectionResult(
            should_use_kb=True,
            confidence=0.8,
            detected_patterns=["conversation_context"],
            reasoning="Technical context detected in conversation",
        )

        mock_kb_service.retrieve_and_generate.return_value = sample_rag_response

        await integration_service.process_chat_with_kb(request)

        # Verify conversation history was passed to detector
        call_args = mock_detector.detect_retrieval_intent.call_args
        assert len(call_args[1]["conversation_history"]) == 3  # All messages passed

    @pytest.mark.asyncio
    async def test_strategy_override(
        self,
        integration_service,
        mock_kb_service,
        sample_chat_request,
        sample_rag_response,
    ):
        """Test strategy override via request parameters."""
        sample_chat_request.knowledge_base_id = "kb-123456789"
        sample_chat_request.integration_strategy = "CONTEXT_AUGMENTATION"

        # Should use context augmentation instead of default direct RAG
        with patch.object(
            integration_service, "_execute_context_augmentation"
        ) as mock_context_aug:
            mock_context_aug.return_value = IntegrationResult(
                used_kb=True,
                strategy_used=IntegrationStrategy.CONTEXT_AUGMENTATION,
                chat_response=None,
            )

            result = await integration_service.process_chat_with_kb(sample_chat_request)

            assert result.strategy_used == IntegrationStrategy.CONTEXT_AUGMENTATION
            mock_context_aug.assert_called_once()

    @pytest.mark.asyncio
    async def test_concurrent_requests_handling(
        self, integration_service, mock_kb_service, sample_rag_response
    ):
        """Test handling of concurrent requests."""
        import asyncio

        mock_kb_service.retrieve_and_generate.return_value = sample_rag_response

        # Create multiple requests
        requests = [
            ChatCompletionRequest(
                model="anthropic.claude-3-haiku-20240307-v1:0",
                messages=[Message(role="user", content=f"Question {i}")],
                knowledge_base_id="kb-123456789",
            )
            for i in range(5)
        ]

        # Process concurrently
        tasks = [
            integration_service.process_chat_with_kb(request) for request in requests
        ]

        results = await asyncio.gather(*tasks)

        # All should succeed
        assert len(results) == 5
        for result in results:
            assert result.used_kb is True

        # Service should be called for each request
        assert mock_kb_service.retrieve_and_generate.call_count == 5

    def test_integration_result_serialization(self):
        """Test IntegrationResult model serialization."""
        result = IntegrationResult(
            used_kb=True,
            strategy_used=IntegrationStrategy.DIRECT_RAG,
            chat_response=None,
            detection_result=DetectionResult(
                should_use_kb=True,
                confidence=0.8,
                detected_patterns=["question_word"],
                reasoning="Question detected",
            ),
        )

        # Should be serializable
        result_dict = result.model_dump()
        assert result_dict["used_kb"] is True
        assert result_dict["strategy_used"] == "DIRECT_RAG"
        assert result_dict["detection_result"]["confidence"] == 0.8

    @pytest.mark.asyncio
    async def test_memory_efficiency_large_context(
        self, integration_service, mock_kb_service, sample_rag_response
    ):
        """Test memory efficiency with large conversation context."""
        # Create request with large conversation history
        large_messages = [
            Message(role="user", content=f"Message {i}: " + "x" * 1000)
            for i in range(100)
        ]

        request = ChatCompletionRequest(
            model="anthropic.claude-3-haiku-20240307-v1:0",
            messages=large_messages,
            knowledge_base_id="kb-123456789",
        )

        mock_kb_service.retrieve_and_generate.return_value = sample_rag_response

        # Should handle large context without issues
        result = await integration_service.process_chat_with_kb(request)

        assert result.used_kb is True
        assert result.chat_response is not None
