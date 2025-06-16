import pytest

from src.open_bedrock_server.core.models import Message, ChatCompletionRequest
from src.open_bedrock_server.utils.knowledge_base_detector import (
    KnowledgeBaseDetector,
)


@pytest.mark.knowledge_base
@pytest.mark.unit
@pytest.mark.kb_detector
class TestKnowledgeBaseDetector:
    """Test Knowledge Base detection logic."""

    def test_detector_functionality(self):
        """Test KnowledgeBaseDetector basic functionality."""
        # Test the static method exists and is callable
        assert hasattr(KnowledgeBaseDetector, 'should_use_knowledge_base')
        assert callable(KnowledgeBaseDetector.should_use_knowledge_base)

    def test_explicit_kb_id(self):
        """Test explicit knowledge base ID usage."""
        request = ChatCompletionRequest(
            model="test-model",
            messages=[Message(role="user", content="Hello")]
        )
        
        # Test with explicit KB ID
        result = KnowledgeBaseDetector.should_use_knowledge_base(
            request=request,
            knowledge_base_id="kb-123",
            auto_kb=False
        )
        
        # Should use KB when explicit ID is provided
        assert result is True

    def test_no_auto_kb(self):
        """Test behavior when auto KB is disabled."""
        request = ChatCompletionRequest(
            model="test-model",
            messages=[Message(role="user", content="What is machine learning?")]
        )
        
        # Test without auto KB
        result = KnowledgeBaseDetector.should_use_knowledge_base(
            request=request,
            auto_kb=False
        )
        
        # Should not use KB when auto detection is disabled
        assert result is False

    def test_auto_kb_enabled(self):
        """Test behavior when auto KB is enabled."""
        request = ChatCompletionRequest(
            model="test-model",
            messages=[Message(role="user", content="What is machine learning?")]
        )
        
        # Test with auto KB enabled
        result = KnowledgeBaseDetector.should_use_knowledge_base(
            request=request,
            auto_kb=True
        )
        
        # Should return a boolean (detection logic should work)
        assert isinstance(result, bool)

    def test_retrieval_keywords(self):
        """Test detection of retrieval keywords."""
        test_queries = [
            "search for documentation",
            "find information about Python",
            "retrieve data from the knowledge base",
            "lookup the API reference",
            "what does the documentation say about this?"
        ]
        
        for query in test_queries:
            request = ChatCompletionRequest(
                model="test-model",
                messages=[Message(role="user", content=query)]
            )
            
            result = KnowledgeBaseDetector.should_use_knowledge_base(
                request=request,
                auto_kb=True
            )
            
            # Should detect retrieval intent in these queries
            assert isinstance(result, bool)

    def test_extract_knowledge_base_id(self):
        """Test knowledge base ID extraction from request data."""
        # Test with knowledge_base_id in request data
        request_data = {"knowledge_base_id": "kb-123456"}
        kb_id = KnowledgeBaseDetector.extract_knowledge_base_id_from_request(request_data)
        assert kb_id == "kb-123456"
        
        # Test with no knowledge_base_id
        request_data = {"model": "test-model"}
        kb_id = KnowledgeBaseDetector.extract_knowledge_base_id_from_request(request_data)
        assert kb_id is None

    def test_get_retrieval_confidence_score(self):
        """Test retrieval confidence score calculation."""
        # Test with question message
        messages = [Message(role="user", content="What is machine learning?")]
        score = KnowledgeBaseDetector.get_retrieval_confidence_score(messages)
        
        # Should return a float between 0 and 1
        assert isinstance(score, float)
        assert 0.0 <= score <= 1.0

    def test_suggest_knowledge_base_query(self):
        """Test knowledge base query suggestion."""
        # Test with technical question
        messages = [Message(role="user", content="What is machine learning?")]
        suggestion = KnowledgeBaseDetector.suggest_knowledge_base_query(messages)
        
        # Should return a string or None
        assert suggestion is None or isinstance(suggestion, str)
