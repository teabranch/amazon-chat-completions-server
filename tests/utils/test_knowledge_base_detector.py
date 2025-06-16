import pytest

from src.open_amazon_chat_completions_server.core.models import Message
from src.open_amazon_chat_completions_server.utils.knowledge_base_detector import (
    DetectionResult,
    DetectionStrategy,
    KnowledgeBaseDetector,
)


@pytest.mark.knowledge_base
@pytest.mark.unit
@pytest.mark.kb_detector
class TestKnowledgeBaseDetector:
    """Test Knowledge Base detection logic."""

    def test_detection_result_creation(self):
        """Test DetectionResult model creation."""
        result = DetectionResult(
            should_use_kb=True,
            confidence=0.85,
            detected_patterns=["question_word", "specific_topic"],
            reasoning="Query contains question words and mentions specific topics",
        )

        assert result.should_use_kb is True
        assert result.confidence == 0.85
        assert "question_word" in result.detected_patterns
        assert "reasoning" in result.model_dump()

    def test_detector_initialization(self):
        """Test KnowledgeBaseDetector initialization."""
        detector = KnowledgeBaseDetector()

        # Should have default configuration
        assert detector.threshold >= 0.0
        assert detector.threshold <= 1.0
        assert isinstance(detector.strategies, list)
        assert len(detector.strategies) > 0

    def test_detector_custom_threshold(self):
        """Test KnowledgeBaseDetector with custom threshold."""
        detector = KnowledgeBaseDetector(threshold=0.8)
        assert detector.threshold == 0.8

    def test_question_word_detection(self):
        """Test detection of question words."""
        detector = KnowledgeBaseDetector()

        # Test various question patterns
        question_queries = [
            "What is machine learning?",
            "How does neural networks work?",
            "Why is Python popular?",
            "When was AI invented?",
            "Where can I find documentation?",
            "Who created TensorFlow?",
            "Which algorithm is best?",
            "Can you explain quantum computing?",
            "Tell me about deep learning",
            "Explain the concept of blockchain",
        ]

        for query in question_queries:
            result = detector.detect_retrieval_intent(query)
            assert result.should_use_kb is True, f"Should detect question in: {query}"
            assert result.confidence > 0.0
            assert (
                "question_word" in result.detected_patterns
                or "question_pattern" in result.detected_patterns
            )

    def test_specific_topic_detection(self):
        """Test detection of specific technical topics."""
        detector = KnowledgeBaseDetector()

        topic_queries = [
            "machine learning algorithms",
            "neural network architecture",
            "API documentation",
            "software engineering principles",
            "database optimization techniques",
            "cloud computing services",
            "cybersecurity best practices",
            "data science methodologies",
        ]

        for query in topic_queries:
            result = detector.detect_retrieval_intent(query)
            assert result.should_use_kb is True, f"Should detect topic in: {query}"
            assert "specific_topic" in result.detected_patterns

    def test_information_request_detection(self):
        """Test detection of information requests."""
        detector = KnowledgeBaseDetector()

        info_queries = [
            "I need information about Python libraries",
            "Please provide details on AWS services",
            "Show me examples of REST APIs",
            "Find documentation for React hooks",
            "Search for best practices in testing",
        ]

        for query in info_queries:
            result = detector.detect_retrieval_intent(query)
            assert result.should_use_kb is True, (
                f"Should detect info request in: {query}"
            )
            assert "information_request" in result.detected_patterns

    def test_domain_keywords_detection(self):
        """Test detection of domain-specific keywords."""
        detector = KnowledgeBaseDetector()

        domain_queries = [
            "microservices architecture patterns",
            "kubernetes deployment strategies",
            "terraform infrastructure code",
            "docker containerization guide",
            "elasticsearch indexing performance",
        ]

        for query in domain_queries:
            result = detector.detect_retrieval_intent(query)
            assert result.should_use_kb is True, (
                f"Should detect domain keywords in: {query}"
            )
            assert result.confidence > 0.0

    def test_conversational_context_detection(self):
        """Test detection based on conversation context."""
        detector = KnowledgeBaseDetector()

        # Create conversation with technical context
        messages = [
            Message(role="user", content="I'm working on a machine learning project"),
            Message(
                role="assistant",
                content="That's great! What specific area are you focusing on?",
            ),
            Message(role="user", content="Can you help me with this?"),
        ]

        result = detector.detect_retrieval_intent(
            "Can you help me with this?", conversation_history=messages
        )

        # Should detect based on context even though the current query is generic
        assert result.should_use_kb is True
        assert "conversation_context" in result.detected_patterns

    def test_low_confidence_queries(self):
        """Test queries that should result in low confidence or no KB usage."""
        detector = KnowledgeBaseDetector()

        casual_queries = [
            "Hello there!",
            "How are you?",
            "Thanks for helping",
            "Good morning",
            "Yes, that's correct",
            "I agree",
            "Sounds good",
        ]

        for query in casual_queries:
            result = detector.detect_retrieval_intent(query)
            # These should either not use KB or have very low confidence
            if result.should_use_kb:
                assert result.confidence < 0.5, (
                    f"Casual query should have low confidence: {query}"
                )

    def test_mixed_confidence_scenarios(self):
        """Test scenarios with mixed signals."""
        detector = KnowledgeBaseDetector()

        # Query with question word but casual context
        result = detector.detect_retrieval_intent("What's up?")
        # Should have some confidence but not high
        assert result.confidence < 0.8

        # Technical term in casual sentence
        result = detector.detect_retrieval_intent("I like machine learning")
        assert result.should_use_kb is True  # Technical term detected
        assert result.confidence > 0.3

    def test_threshold_effect(self):
        """Test how different thresholds affect decisions."""
        # Low threshold detector
        low_detector = KnowledgeBaseDetector(threshold=0.3)

        # High threshold detector
        high_detector = KnowledgeBaseDetector(threshold=0.8)

        # Borderline query
        query = "I like Python programming"

        low_result = low_detector.detect_retrieval_intent(query)
        high_result = high_detector.detect_retrieval_intent(query)

        # Same confidence, different decisions based on threshold
        assert low_result.confidence == high_result.confidence
        # Low threshold more likely to use KB
        if low_result.confidence >= 0.3 and low_result.confidence < 0.8:
            assert low_result.should_use_kb is True
            assert high_result.should_use_kb is False

    def test_confidence_calculation(self):
        """Test confidence score calculation."""
        detector = KnowledgeBaseDetector()

        # High confidence query (multiple signals)
        high_query = "What are the best machine learning algorithms for classification?"
        high_result = detector.detect_retrieval_intent(high_query)

        # Medium confidence query (single signal)
        medium_query = "Python libraries"
        medium_result = detector.detect_retrieval_intent(medium_query)

        # Low confidence query (weak signal)
        low_query = "That's interesting"
        low_result = detector.detect_retrieval_intent(low_query)

        # High confidence should be higher than medium, medium higher than low
        assert high_result.confidence > medium_result.confidence
        assert medium_result.confidence > low_result.confidence

    def test_empty_or_none_queries(self):
        """Test handling of empty or None queries."""
        detector = KnowledgeBaseDetector()

        # Empty string
        result = detector.detect_retrieval_intent("")
        assert result.should_use_kb is False
        assert result.confidence == 0.0

        # None query should be handled gracefully
        result = detector.detect_retrieval_intent(None)
        assert result.should_use_kb is False
        assert result.confidence == 0.0

    def test_long_complex_queries(self):
        """Test handling of long, complex queries."""
        detector = KnowledgeBaseDetector()

        complex_query = """
        I'm working on a complex data science project involving machine learning
        algorithms for natural language processing. Can you help me understand
        the differences between transformer architectures like BERT and GPT,
        and provide guidance on which would be better for sentiment analysis
        tasks? I also need to know about preprocessing techniques and evaluation
        metrics that would be most appropriate for this use case.
        """

        result = detector.detect_retrieval_intent(complex_query)

        # Should have high confidence due to multiple technical terms and clear questions
        assert result.should_use_kb is True
        assert result.confidence > 0.8
        assert len(result.detected_patterns) > 1

    def test_strategy_composition(self):
        """Test that multiple detection strategies work together."""
        detector = KnowledgeBaseDetector()

        # Query that should trigger multiple strategies
        query = "What are the best practices for API security in microservices architecture?"
        result = detector.detect_retrieval_intent(query)

        # Should detect multiple patterns
        expected_patterns = ["question_word", "specific_topic"]
        for pattern in expected_patterns:
            assert pattern in result.detected_patterns

        # Should have high confidence
        assert result.confidence > 0.7

    def test_reasoning_generation(self):
        """Test that appropriate reasoning is generated."""
        detector = KnowledgeBaseDetector()

        query = "How does Docker work?"
        result = detector.detect_retrieval_intent(query)

        assert result.reasoning is not None
        assert len(result.reasoning) > 0
        assert isinstance(result.reasoning, str)

        # Reasoning should mention detected patterns
        for _pattern in result.detected_patterns:
            # The reasoning should reference the types of patterns found
            assert any(
                keyword in result.reasoning.lower()
                for keyword in ["question", "topic", "pattern", "signal"]
            )

    def test_case_insensitive_detection(self):
        """Test that detection works regardless of case."""
        detector = KnowledgeBaseDetector()

        queries = [
            "WHAT IS MACHINE LEARNING?",
            "what is machine learning?",
            "What Is Machine Learning?",
            "wHaT iS mAcHiNe LeArNiNg?",
        ]

        results = [detector.detect_retrieval_intent(query) for query in queries]

        # All should have the same detection result
        first_result = results[0]
        for result in results[1:]:
            assert result.should_use_kb == first_result.should_use_kb
            assert (
                abs(result.confidence - first_result.confidence) < 0.01
            )  # Allow small floating point differences

    def test_unicode_and_special_characters(self):
        """Test handling of unicode and special characters."""
        detector = KnowledgeBaseDetector()

        unicode_queries = [
            "¿Qué es machine learning?",  # Spanish
            "What is AI? 🤖",  # Emoji
            "Machine learning - what's that?",  # Punctuation
            "API documentation (REST)",  # Parentheses
        ]

        for query in unicode_queries:
            result = detector.detect_retrieval_intent(query)
            # Should not crash and should still detect patterns when present
            assert isinstance(result, DetectionResult)
            assert isinstance(result.confidence, float)
            assert 0.0 <= result.confidence <= 1.0

    @pytest.mark.parametrize(
        "strategy",
        [
            DetectionStrategy.CONSERVATIVE,
            DetectionStrategy.BALANCED,
            DetectionStrategy.AGGRESSIVE,
        ],
    )
    def test_different_strategies(self, strategy):
        """Test different detection strategies."""
        detector = KnowledgeBaseDetector(strategy=strategy)

        # Borderline query
        query = "I'm learning about Python"
        result = detector.detect_retrieval_intent(query)

        # All strategies should work but may have different thresholds
        assert isinstance(result, DetectionResult)
        assert 0.0 <= result.confidence <= 1.0

        # Conservative should be more restrictive
        if strategy == DetectionStrategy.CONSERVATIVE:
            assert detector.threshold >= 0.6
        elif strategy == DetectionStrategy.AGGRESSIVE:
            assert detector.threshold <= 0.4

    def test_conversation_history_impact(self):
        """Test how conversation history affects detection."""
        detector = KnowledgeBaseDetector()

        # Generic query without context
        generic_query = "Tell me more"
        result_no_context = detector.detect_retrieval_intent(generic_query)

        # Same query with technical context
        technical_history = [
            Message(role="user", content="I'm building a REST API"),
            Message(role="assistant", content="Great! What framework are you using?"),
            Message(role="user", content="FastAPI with Python"),
        ]

        result_with_context = detector.detect_retrieval_intent(
            generic_query, conversation_history=technical_history
        )

        # Context should increase confidence
        assert result_with_context.confidence >= result_no_context.confidence
        if result_with_context.should_use_kb and not result_no_context.should_use_kb:
            assert "conversation_context" in result_with_context.detected_patterns
