#!/usr/bin/env python3
"""
Knowledge Base Integration Example

This example demonstrates how to use the Open Bedrock Server
with Bedrock Knowledge Bases for Retrieval-Augmented Generation (RAG).

Prerequisites:
1. AWS credentials configured
2. A Bedrock Knowledge Base created with data sources
3. The server running locally or accessible via URL

Usage:
    python examples/knowledge_base_example.py
"""

import asyncio
import logging
import os
from typing import Any

import aiohttp
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
SERVER_URL = os.getenv("CHAT_SERVER_URL", "http://localhost:8000")
API_KEY = os.getenv("CHAT_API_KEY", "your-api-key")
KNOWLEDGE_BASE_ID = os.getenv("KNOWLEDGE_BASE_ID", "kb-example-123456")

console = Console()


class KnowledgeBaseClient:
    """Client for interacting with Knowledge Base endpoints."""

    def __init__(self, server_url: str, api_key: str):
        self.server_url = server_url.rstrip("/")
        self.api_key = api_key
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

    async def list_knowledge_bases(self, max_results: int = 10) -> dict[str, Any]:
        """List available knowledge bases."""
        url = f"{self.server_url}/v1/knowledge-bases"
        params = {"max_results": max_results}

        async with aiohttp.ClientSession() as session, session.get(
            url, headers=self.headers, params=params
        ) as response:
            if response.status == 200:
                return await response.json()
            else:
                raise Exception(
                    f"API error: {response.status} - {await response.text()}"
                )

    async def get_knowledge_base(self, kb_id: str) -> dict[str, Any]:
        """Get details of a specific knowledge base."""
        url = f"{self.server_url}/v1/knowledge-bases/{kb_id}"

        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=self.headers) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    raise Exception(
                        f"API error: {response.status} - {await response.text()}"
                    )

    async def query_knowledge_base(
        self, kb_id: str, query: str, max_results: int = 5
    ) -> dict[str, Any]:
        """Query a knowledge base directly (retrieve-only)."""
        url = f"{self.server_url}/v1/knowledge-bases/{kb_id}/query"
        params = {"query": query, "max_results": max_results}

        async with aiohttp.ClientSession() as session, session.post(
            url, headers=self.headers, params=params
        ) as response:
            if response.status == 200:
                return await response.json()
            else:
                raise Exception(
                    f"API error: {response.status} - {await response.text()}"
                )

    async def retrieve_and_generate(
        self, kb_id: str, query: str, model_arn: str
    ) -> dict[str, Any]:
        """Use native retrieve-and-generate."""
        url = f"{self.server_url}/v1/knowledge-bases/{kb_id}/retrieve-and-generate"
        payload = {
            "query": query,
            "modelArn": model_arn,
            "retrievalConfiguration": {
                "vectorSearchConfiguration": {"numberOfResults": 5}
            },
        }

        async with aiohttp.ClientSession() as session, session.post(
            url, headers=self.headers, json=payload
        ) as response:
            if response.status == 200:
                return await response.json()
            else:
                raise Exception(
                    f"API error: {response.status} - {await response.text()}"
                )

    async def enhanced_chat_completion(
        self,
        model: str,
        messages: list[dict[str, str]],
        kb_id: str = None,
        auto_kb: bool = False,
    ) -> dict[str, Any]:
        """Chat completion with Knowledge Base enhancement."""
        url = f"{self.server_url}/v1/chat/completions"
        payload = {
            "model": model,
            "messages": messages,
            "knowledge_base_id": kb_id,
            "auto_kb": auto_kb,
            "citation_format": "openai",
        }

        async with aiohttp.ClientSession() as session, session.post(
            url, headers=self.headers, json=payload
        ) as response:
            if response.status == 200:
                return await response.json()
            else:
                raise Exception(
                    f"API error: {response.status} - {await response.text()}"
                )


async def demo_knowledge_base_listing():
    """Demonstrate listing knowledge bases."""
    console.print(Panel.fit("📋 Knowledge Base Listing Demo", style="bold blue"))

    try:
        client = KnowledgeBaseClient(SERVER_URL, API_KEY)
        kbs = await client.list_knowledge_bases()

        if not kbs.get("knowledgeBaseSummaries"):
            console.print("No knowledge bases found.", style="yellow")
            return None

        table = Table(title="Available Knowledge Bases")
        table.add_column("ID", style="cyan", no_wrap=True)
        table.add_column("Name", style="green")
        table.add_column("Status", style="yellow")
        table.add_column("Updated", style="blue")

        for kb in kbs["knowledgeBaseSummaries"]:
            table.add_row(
                kb.get("knowledgeBaseId", "N/A"),
                kb.get("name", "N/A"),
                kb.get("status", "N/A"),
                kb.get("updatedAt", "N/A")[:10] if kb.get("updatedAt") else "N/A",
            )

        console.print(table)
        console.print()

        # Return first KB ID for use in other demos
        return kbs["knowledgeBaseSummaries"][0]["knowledgeBaseId"]

    except Exception as e:
        console.print(f"[red]Error listing knowledge bases: {e}[/red]")
        return None


async def demo_knowledge_base_details(kb_id: str):
    """Demonstrate getting knowledge base details."""
    console.print(Panel.fit("🔍 Knowledge Base Details Demo", style="bold blue"))

    try:
        client = KnowledgeBaseClient(SERVER_URL, API_KEY)
        kb_details = await client.get_knowledge_base(kb_id)

        console.print(
            f"[bold green]Knowledge Base: {kb_details.get('name', 'N/A')}[/bold green]"
        )
        console.print(f"ID: {kb_details.get('knowledgeBaseId', 'N/A')}")
        console.print(f"Description: {kb_details.get('description', 'N/A')}")
        console.print(f"Status: {kb_details.get('status', 'N/A')}")
        console.print(f"ARN: {kb_details.get('knowledgeBaseArn', 'N/A')}")
        console.print()

    except Exception as e:
        console.print(f"[red]Error getting knowledge base details: {e}[/red]")


async def demo_direct_query(kb_id: str):
    """Demonstrate direct knowledge base querying."""
    console.print(Panel.fit("🔎 Direct Knowledge Base Query Demo", style="bold blue"))

    try:
        client = KnowledgeBaseClient(SERVER_URL, API_KEY)

        # Example queries
        queries = [
            "What is the return policy?",
            "How do I contact customer support?",
            "What are the shipping options?",
        ]

        for query in queries:
            console.print(f"[bold cyan]Query:[/bold cyan] {query}")

            results = await client.query_knowledge_base(kb_id, query, max_results=3)

            if not results.get("retrievalResults"):
                console.print("No results found.", style="yellow")
                continue

            for i, result in enumerate(results["retrievalResults"], 1):
                content = (
                    result.get("content", "")[:200] + "..."
                    if len(result.get("content", "")) > 200
                    else result.get("content", "")
                )
                score = result.get("score", 0)

                console.print(f"[dim]Result {i} (Score: {score:.3f}):[/dim]")
                console.print(f"  {content}")

                if result.get("metadata"):
                    source = result["metadata"].get("source", "Unknown")
                    console.print(f"  [dim]Source: {source}[/dim]")

            console.print("-" * 50)

        console.print()

    except Exception as e:
        console.print(f"[red]Error querying knowledge base: {e}[/red]")


async def demo_native_rag(kb_id: str):
    """Demonstrate native retrieve-and-generate."""
    console.print(Panel.fit("🧠 Native RAG Demo", style="bold blue"))

    try:
        client = KnowledgeBaseClient(SERVER_URL, API_KEY)

        query = "What is your refund policy and how long does it take?"
        model_arn = "arn:aws:bedrock:us-east-1::foundation-model/anthropic.claude-3-5-haiku-20241022-v1:0"

        console.print(f"[bold cyan]Query:[/bold cyan] {query}")
        console.print(f"[dim]Using model: {model_arn}[/dim]")
        console.print()

        response = await client.retrieve_and_generate(kb_id, query, model_arn)

        console.print("[bold green]Generated Response:[/bold green]")
        console.print(response.get("output", "No response generated"))

        if response.get("citations"):
            console.print(
                f"\n[bold yellow]Citations ({len(response['citations'])}):[/bold yellow]"
            )
            for i, citation in enumerate(response["citations"], 1):
                console.print(f"[dim]Citation {i}:[/dim]")
                for ref in citation.get("retrievedReferences", []):
                    location = ref.get("location", {})
                    if "s3Location" in location:
                        console.print(
                            f"  Source: {location['s3Location'].get('uri', 'Unknown')}"
                        )

        console.print()

    except Exception as e:
        console.print(f"[red]Error in native RAG: {e}[/red]")


async def demo_enhanced_chat(kb_id: str):
    """Demonstrate enhanced chat completions with Knowledge Base."""
    console.print(Panel.fit("💬 Enhanced Chat Completion Demo", style="bold blue"))

    try:
        client = KnowledgeBaseClient(SERVER_URL, API_KEY)

        # Test scenarios
        scenarios = [
            {
                "name": "Explicit KB Usage",
                "messages": [
                    {
                        "role": "user",
                        "content": "What does the documentation say about returns?",
                    }
                ],
                "kb_id": kb_id,
                "auto_kb": False,
            },
            {
                "name": "Auto-Detection Mode",
                "messages": [
                    {
                        "role": "user",
                        "content": "I need to find information about your shipping policies",
                    }
                ],
                "kb_id": kb_id,
                "auto_kb": True,
            },
            {
                "name": "Regular Chat (No KB)",
                "messages": [{"role": "user", "content": "Hello! How are you today?"}],
                "kb_id": None,
                "auto_kb": False,
            },
        ]

        model = "anthropic.claude-3-5-haiku-20241022-v1:0"

        for scenario in scenarios:
            console.print(f"[bold magenta]Scenario: {scenario['name']}[/bold magenta]")
            console.print(f"Query: {scenario['messages'][0]['content']}")
            console.print(f"KB ID: {scenario['kb_id'] or 'None'}")
            console.print(f"Auto KB: {scenario['auto_kb']}")
            console.print()

            response = await client.enhanced_chat_completion(
                model=model,
                messages=scenario["messages"],
                kb_id=scenario["kb_id"],
                auto_kb=scenario["auto_kb"],
            )

            if response.get("choices") and len(response["choices"]) > 0:
                message_content = response["choices"][0]["message"]["content"]
                console.print("[bold green]Response:[/bold green]")
                console.print(message_content)

                # Show KB metadata if available
                if response.get("kb_metadata"):
                    metadata = response["kb_metadata"]
                    console.print("\n[dim]KB Metadata:[/dim]")
                    console.print(
                        f"  Knowledge base used: {metadata.get('knowledge_base_used', False)}"
                    )
                    console.print(
                        f"  Citations count: {metadata.get('citations_count', 0)}"
                    )
                    if metadata.get("session_id"):
                        console.print(f"  Session ID: {metadata['session_id']}")
            else:
                console.print("[red]No response received[/red]")

            console.print("-" * 70)

        console.print()

    except Exception as e:
        console.print(f"[red]Error in enhanced chat: {e}[/red]")


async def demo_conversation_with_kb(kb_id: str):
    """Demonstrate a multi-turn conversation with Knowledge Base."""
    console.print(Panel.fit("🗣️ Multi-turn KB Conversation Demo", style="bold blue"))

    try:
        client = KnowledgeBaseClient(SERVER_URL, API_KEY)

        # Simulate a customer support conversation
        conversation = [
            {"role": "user", "content": "I want to return an item I bought last week"},
            {"role": "user", "content": "How long do returns usually take to process?"},
            {
                "role": "user",
                "content": "What if the item was damaged during shipping?",
            },
        ]

        model = "anthropic.claude-3-5-haiku-20241022-v1:0"
        messages = []

        for turn in conversation:
            messages.append(turn)

            console.print(f"[bold blue]User:[/bold blue] {turn['content']}")

            response = await client.enhanced_chat_completion(
                model=model, messages=messages, kb_id=kb_id, auto_kb=True
            )

            if response.get("choices") and len(response["choices"]) > 0:
                assistant_content = response["choices"][0]["message"]["content"]
                console.print(
                    f"[bold green]Assistant:[/bold green] {assistant_content}"
                )

                # Add assistant response to conversation
                messages.append({"role": "assistant", "content": assistant_content})

                # Show KB usage indicator
                if response.get("kb_metadata", {}).get("knowledge_base_used"):
                    citations = response["kb_metadata"].get("citations_count", 0)
                    console.print(
                        f"[dim]✓ Knowledge base used • {citations} citations[/dim]"
                    )

            console.print()

    except Exception as e:
        console.print(f"[red]Error in conversation demo: {e}[/red]")


async def main():
    """Main demo function."""
    console.print(Text("🚀 Knowledge Base Integration Demo", style="bold magenta"))
    console.print(Text(f"Server: {SERVER_URL}", style="dim"))
    console.print(Text(f"KB ID: {KNOWLEDGE_BASE_ID}", style="dim"))
    console.print()

    # Try to list KBs and get a valid ID
    kb_id = await demo_knowledge_base_listing()

    if not kb_id:
        console.print(
            "[yellow]Using configured KB ID since no KBs were listed[/yellow]"
        )
        kb_id = KNOWLEDGE_BASE_ID

    if not kb_id or kb_id == "kb-example-123456":
        console.print(
            "[red]Please set KNOWLEDGE_BASE_ID environment variable to a valid KB ID[/red]"
        )
        return

    # Run all demo scenarios
    await demo_knowledge_base_details(kb_id)
    await demo_direct_query(kb_id)
    await demo_native_rag(kb_id)
    await demo_enhanced_chat(kb_id)
    await demo_conversation_with_kb(kb_id)

    console.print(Panel.fit("✅ Demo Complete!", style="bold green"))
    console.print("Try the CLI commands:")
    console.print("  accs kb list")
    console.print(f"  accs kb get {kb_id}")
    console.print(f"  accs kb query {kb_id} 'your question here'")
    console.print(f"  accs kb chat {kb_id}")


if __name__ == "__main__":
    # Check for required dependencies
    try:
        import aiohttp
        from rich.console import Console
    except ImportError as e:
        print(f"Missing required dependency: {e}")
        print("Install with: pip install aiohttp rich")
        exit(1)

    # Run the demo
    asyncio.run(main())
