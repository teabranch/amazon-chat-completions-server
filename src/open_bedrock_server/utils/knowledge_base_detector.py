import logging
import re
from typing import Any

from ..core.models import ChatCompletionRequest, Message

logger = logging.getLogger(__name__)


class KnowledgeBaseDetector:
    """
    Utility class for detecting when to use Knowledge Base functionality
    in chat completions requests.
    """

    # Keywords that suggest retrieval/search needs
    RETRIEVAL_KEYWORDS = [
        "search",
        "find",
        "lookup",
        "look up",
        "retrieve",
        "get information",
        "what does",
        "according to",
        "based on",
        "from the document",
        "from the docs",
        "in the documentation",
        "what is mentioned",
        "what says",
        "extract",
        "reference",
        "cite",
        "source",
        "pull information",
        "get details",
        "find details",
    ]

    # Question patterns that often need retrieval
    RETRIEVAL_QUESTION_PATTERNS = [
        r"what (?:does|do|is|are) .+ (?:say|mention|state|indicate)",
        r"(?:where|how|when|why|what) (?:can i find|is mentioned)",
        r"according to .+",
        r"based on .+",
        r"from (?:the |your )?(?:document|docs|documentation|knowledge base)",
        r"in (?:the |your )?(?:document|docs|documentation|knowledge base)",
        r"(?:search|find|lookup|retrieve) .+ (?:in|from)",
    ]

    # File-related patterns
    FILE_PATTERNS = [
        r"in (?:this|the) file",
        r"from (?:this|the) file",
        r"(?:file|document) (?:says|mentions|states|contains)",
        r"upload(?:ed)? (?:file|document)",
        r"attached (?:file|document)",
    ]

    @staticmethod
    def should_use_knowledge_base(
        request: ChatCompletionRequest,
        knowledge_base_id: str | None = None,
        auto_kb: bool = False,
    ) -> bool:
        """
        Determine if a Knowledge Base should be used for this request.

        Args:
            request: The chat completion request
            knowledge_base_id: Explicit KB ID if provided
            auto_kb: Whether auto-detection is enabled

        Returns:
            bool: True if Knowledge Base should be used
        """
        # Explicit KB ID always triggers KB usage
        if knowledge_base_id:
            logger.debug(
                f"Using KB due to explicit knowledge_base_id: {knowledge_base_id}"
            )
            return True

        # Check if request has explicit KB parameter
        if hasattr(request, "knowledge_base_id") and request.knowledge_base_id:
            logger.debug(
                f"Using KB due to request.knowledge_base_id: {request.knowledge_base_id}"
            )
            return True

        # Auto-detection only if enabled
        if not auto_kb:
            return False

        # Check if file_ids are present (often needs KB for file context)
        if hasattr(request, "file_ids") and request.file_ids:
            logger.debug("Using KB due to file_ids in request")
            return True

        # Analyze message content for retrieval indicators
        return KnowledgeBaseDetector._analyze_messages_for_retrieval(request.messages)

    @staticmethod
    def _analyze_messages_for_retrieval(messages: list[Message]) -> bool:
        """
        Analyze message content to detect retrieval/search intent.

        Args:
            messages: List of chat messages

        Returns:
            bool: True if retrieval intent is detected
        """
        # Focus on user messages for retrieval intent
        user_messages = [msg for msg in messages if msg.role == "user"]

        if not user_messages:
            return False

        # Get the latest user message (most relevant for current intent)
        latest_message = user_messages[-1]
        content = latest_message.content.lower() if latest_message.content else ""

        # Check for explicit retrieval keywords
        keyword_found = any(
            keyword in content for keyword in KnowledgeBaseDetector.RETRIEVAL_KEYWORDS
        )
        if keyword_found:
            logger.debug(f"KB retrieval keyword detected in: {content[:100]}...")
            return True

        # Check for retrieval question patterns
        pattern_found = any(
            re.search(pattern, content, re.IGNORECASE)
            for pattern in KnowledgeBaseDetector.RETRIEVAL_QUESTION_PATTERNS
        )
        if pattern_found:
            logger.debug(f"KB retrieval pattern detected in: {content[:100]}...")
            return True

        # Check for file-related patterns
        file_pattern_found = any(
            re.search(pattern, content, re.IGNORECASE)
            for pattern in KnowledgeBaseDetector.FILE_PATTERNS
        )
        if file_pattern_found:
            logger.debug(f"KB file pattern detected in: {content[:100]}...")
            return True

        # Check conversation context for retrieval needs
        return KnowledgeBaseDetector._analyze_conversation_context(user_messages)

    @staticmethod
    def _analyze_conversation_context(user_messages: list[Message]) -> bool:
        """
        Analyze conversation context for implicit retrieval needs.

        Args:
            user_messages: List of user messages

        Returns:
            bool: True if context suggests retrieval needs
        """
        if len(user_messages) < 2:
            return False

        # Check if previous messages mentioned documents/knowledge
        previous_content = " ".join(
            [msg.content.lower() for msg in user_messages[:-1] if msg.content]
        )

        document_mentions = [
            "document",
            "file",
            "documentation",
            "knowledge base",
            "database",
            "repository",
            "source",
            "reference",
            "uploaded",
            "attached",
        ]

        has_document_context = any(
            mention in previous_content for mention in document_mentions
        )

        if has_document_context:
            # Current message might be a follow-up question about the documents
            current_content = (
                user_messages[-1].content.lower() if user_messages[-1].content else ""
            )

            # Look for follow-up question indicators
            followup_indicators = [
                "what about",
                "how about",
                "tell me more",
                "explain",
                "elaborate",
                "give me",
                "show me",
                "where",
                "how",
                "why",
                "when",
                "what",
            ]

            has_followup = any(
                indicator in current_content for indicator in followup_indicators
            )

            if has_followup:
                logger.debug(
                    "KB usage detected from conversation context (document follow-up)"
                )
                return True

        return False

    @staticmethod
    def extract_knowledge_base_id_from_request(
        request_data: dict[str, Any],
    ) -> str | None:
        """
        Extract Knowledge Base ID from various possible locations in the request.

        Args:
            request_data: Raw request data dictionary

        Returns:
            Optional[str]: Knowledge Base ID if found
        """
        # Check common parameter names
        kb_id_fields = ["knowledge_base_id", "knowledgeBaseId", "kb_id", "kbId"]

        for field in kb_id_fields:
            if field in request_data and request_data[field]:
                return str(request_data[field])

        return None

    @staticmethod
    def get_retrieval_confidence_score(messages: list[Message]) -> float:
        """
        Calculate a confidence score (0.0 to 1.0) for retrieval intent.

        Args:
            messages: List of chat messages

        Returns:
            float: Confidence score between 0.0 and 1.0
        """
        if not messages:
            return 0.0

        user_messages = [msg for msg in messages if msg.role == "user"]
        if not user_messages:
            return 0.0

        latest_message = user_messages[-1]
        content = latest_message.content.lower() if latest_message.content else ""

        score = 0.0

        # Strong indicators (high confidence)
        strong_keywords = [
            "search",
            "find",
            "lookup",
            "retrieve",
            "according to",
            "based on",
        ]
        strong_matches = sum(1 for keyword in strong_keywords if keyword in content)
        score += min(strong_matches * 0.3, 0.6)

        # Medium indicators
        medium_keywords = ["what does", "from the", "in the", "document", "file"]
        medium_matches = sum(1 for keyword in medium_keywords if keyword in content)
        score += min(medium_matches * 0.2, 0.4)

        # Weak indicators
        weak_keywords = ["tell me", "explain", "show me", "how", "what", "where"]
        weak_matches = sum(1 for keyword in weak_keywords if keyword in content)
        score += min(weak_matches * 0.1, 0.2)

        # Question marks increase confidence slightly
        if "?" in content:
            score += 0.1

        # Conversation context boost
        if len(user_messages) > 1:
            prev_content = " ".join(
                [msg.content.lower() for msg in user_messages[:-1] if msg.content]
            )
            if any(word in prev_content for word in ["document", "file", "knowledge"]):
                score += 0.2

        return min(score, 1.0)

    @staticmethod
    def suggest_knowledge_base_query(messages: list[Message]) -> str | None:
        """
        Suggest an optimized query for Knowledge Base retrieval based on the conversation.

        Args:
            messages: List of chat messages

        Returns:
            Optional[str]: Suggested query string, or None if no clear query can be extracted
        """
        user_messages = [msg for msg in messages if msg.role == "user"]
        if not user_messages:
            return None

        latest_message = user_messages[-1]
        content = latest_message.content if latest_message.content else ""

        # Remove common question prefixes and suffixes for better retrieval
        query = content.strip()

        # Remove question words that don't help with retrieval
        query_words_to_remove = [
            "can you",
            "could you",
            "please",
            "tell me",
            "show me",
            "explain",
            "help me",
            "i want to",
            "i need to",
            "how do i",
            "what is the",
            "what are the",
            "where can i",
            "when should i",
        ]

        query_lower = query.lower()
        for phrase in query_words_to_remove:
            if query_lower.startswith(phrase):
                query = query[len(phrase) :].strip()
                break

        # Remove trailing question mark and punctuation
        query = query.rstrip("?!.,")

        # If the query is too short or too generic, return None
        if len(query.split()) < 2:
            return None

        generic_queries = [
            "help",
            "information",
            "details",
            "more",
            "something",
            "anything",
        ]
        if query.lower() in generic_queries:
            return None

        return query if query else None
