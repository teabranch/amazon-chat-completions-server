"""
File Processing Service for extracting text content from various file types.
"""

import csv
import json
import logging
from typing import Any
from xml.etree import ElementTree as ET

logger = logging.getLogger(__name__)


class FileProcessingService:
    """Service for processing different file types and extracting text content."""

    def __init__(self):
        self.supported_types = {
            "text/plain": self._process_text,
            "text/csv": self._process_csv,
            "application/json": self._process_json,
            "application/xml": self._process_xml,
            "text/xml": self._process_xml,
            "text/markdown": self._process_text,
            "text/x-python": self._process_text,
            "application/javascript": self._process_text,
            "text/html": self._process_html,
        }

    def can_process(self, content_type: str) -> bool:
        """Check if the file type can be processed."""
        return content_type in self.supported_types

    async def process_file(
        self, content: bytes, content_type: str, filename: str
    ) -> dict[str, Any]:
        """
        Process a file and extract text content.

        Args:
            content: File content as bytes
            content_type: MIME type of the file
            filename: Original filename

        Returns:
            Dict containing processed information
        """
        try:
            if not self.can_process(content_type):
                return {
                    "success": False,
                    "error": f"Unsupported file type: {content_type}",
                    "text_content": None,
                    "metadata": {"filename": filename, "content_type": content_type},
                }

            processor = self.supported_types[content_type]
            text_content = await processor(content, filename)

            return {
                "success": True,
                "text_content": text_content,
                "metadata": {
                    "filename": filename,
                    "content_type": content_type,
                    "character_count": len(text_content) if text_content else 0,
                    "processed": True,
                },
            }

        except Exception as e:
            logger.error(f"Failed to process file {filename}: {e}")
            return {
                "success": False,
                "error": str(e),
                "text_content": None,
                "metadata": {"filename": filename, "content_type": content_type},
            }

    async def _process_text(self, content: bytes, filename: str) -> str:
        """Process plain text files."""
        try:
            # Try UTF-8 first, then fall back to other encodings
            for encoding in ["utf-8", "latin-1", "cp1252"]:
                try:
                    return content.decode(encoding)
                except UnicodeDecodeError:
                    continue

            # If all encodings fail, use utf-8 with error handling
            return content.decode("utf-8", errors="replace")

        except Exception as e:
            logger.error(f"Failed to process text file {filename}: {e}")
            raise

    async def _process_csv(self, content: bytes, filename: str) -> str:
        """Process CSV files."""
        try:
            text_content = content.decode("utf-8", errors="replace")

            # Parse CSV and convert to readable format
            csv_reader = csv.reader(text_content.splitlines())
            rows = list(csv_reader)

            if not rows:
                return "Empty CSV file"

            # Format as a readable table
            result = []
            if rows:
                headers = rows[0]
                result.append(f"CSV File: {filename}")
                result.append(f"Headers: {', '.join(headers)}")
                result.append(f"Total rows: {len(rows) - 1}")
                result.append("")

                # Include first few rows as sample data
                for i, row in enumerate(rows[:6]):  # Headers + 5 data rows
                    if i == 0:
                        result.append(f"Row {i} (Headers): {', '.join(row)}")
                    else:
                        result.append(f"Row {i}: {', '.join(row)}")

                if len(rows) > 6:
                    result.append(f"... and {len(rows) - 6} more rows")

            return "\n".join(result)

        except Exception as e:
            logger.error(f"Failed to process CSV file {filename}: {e}")
            # Fall back to plain text processing
            return await self._process_text(content, filename)

    async def _process_json(self, content: bytes, filename: str) -> str:
        """Process JSON files."""
        try:
            text_content = content.decode("utf-8", errors="replace")

            # Parse JSON and format it nicely
            json_data = json.loads(text_content)

            # Create a readable summary
            result = [f"JSON File: {filename}"]

            def describe_json_structure(obj, path="", level=0):
                indent = "  " * level
                if isinstance(obj, dict):
                    result.append(
                        f"{indent}Object at {path or 'root'} with {len(obj)} keys:"
                    )
                    for key, value in obj.items():
                        current_path = f"{path}.{key}" if path else key
                        if isinstance(value, dict | list):
                            result.append(f"{indent}  {key}: {type(value).__name__}")
                            if level < 2:  # Limit depth to avoid too much detail
                                describe_json_structure(value, current_path, level + 1)
                        else:
                            result.append(
                                f"{indent}  {key}: {type(value).__name__} = {str(value)[:50]}{'...' if len(str(value)) > 50 else ''}"
                            )
                elif isinstance(obj, list):
                    result.append(
                        f"{indent}Array at {path or 'root'} with {len(obj)} items"
                    )
                    if obj and level < 2:
                        result.append(
                            f"{indent}  Sample item type: {type(obj[0]).__name__}"
                        )
                        if isinstance(obj[0], dict | list):
                            describe_json_structure(obj[0], f"{path}[0]", level + 1)

            describe_json_structure(json_data)

            # Also include the raw JSON (truncated if too long)
            formatted_json = json.dumps(json_data, indent=2)
            if len(formatted_json) > 2000:
                result.append("\nJSON Content (truncated):")
                result.append(formatted_json[:2000] + "\n... (truncated)")
            else:
                result.append("\nJSON Content:")
                result.append(formatted_json)

            return "\n".join(result)

        except json.JSONDecodeError as e:
            logger.warning(f"Invalid JSON in file {filename}: {e}")
            # Fall back to plain text processing
            return await self._process_text(content, filename)
        except Exception as e:
            logger.error(f"Failed to process JSON file {filename}: {e}")
            return await self._process_text(content, filename)

    async def _process_xml(self, content: bytes, filename: str) -> str:
        """Process XML files."""
        try:
            text_content = content.decode("utf-8", errors="replace")

            # Parse XML and create a readable summary
            root = ET.fromstring(text_content)

            result = [f"XML File: {filename}"]
            result.append(f"Root element: {root.tag}")

            def describe_xml_structure(element, path="", level=0):
                indent = "  " * level
                if level < 3:  # Limit depth
                    current_path = f"{path}/{element.tag}" if path else element.tag

                    # Count children
                    children = list(element)
                    if children:
                        result.append(
                            f"{indent}{element.tag}: {len(children)} child elements"
                        )
                        # Get unique child tag names
                        child_tags = list({child.tag for child in children})
                        if child_tags:
                            result.append(
                                f"{indent}  Child types: {', '.join(child_tags)}"
                            )

                        # Recursively describe some children
                        for child in children[:3]:  # Only first 3 children
                            describe_xml_structure(child, current_path, level + 1)
                    else:
                        text = element.text.strip() if element.text else ""
                        if text:
                            result.append(
                                f"{indent}{element.tag}: {text[:100]}{'...' if len(text) > 100 else ''}"
                            )
                        else:
                            result.append(f"{indent}{element.tag}: (empty)")

            describe_xml_structure(root)

            # Also include raw XML (truncated if too long)
            if len(text_content) > 2000:
                result.append("\nXML Content (truncated):")
                result.append(text_content[:2000] + "\n... (truncated)")
            else:
                result.append("\nXML Content:")
                result.append(text_content)

            return "\n".join(result)

        except ET.ParseError as e:
            logger.warning(f"Invalid XML in file {filename}: {e}")
            # Fall back to plain text processing
            return await self._process_text(content, filename)
        except Exception as e:
            logger.error(f"Failed to process XML file {filename}: {e}")
            return await self._process_text(content, filename)

    async def _process_html(self, content: bytes, filename: str) -> str:
        """Process HTML files."""
        try:
            text_content = content.decode("utf-8", errors="replace")

            # Simple HTML text extraction (basic approach)
            import re

            # Remove script and style elements
            text_content = re.sub(
                r"<script[^>]*>.*?</script>",
                "",
                text_content,
                flags=re.DOTALL | re.IGNORECASE,
            )
            text_content = re.sub(
                r"<style[^>]*>.*?</style>",
                "",
                text_content,
                flags=re.DOTALL | re.IGNORECASE,
            )

            # Remove HTML tags
            text_content = re.sub(r"<[^>]+>", "", text_content)

            # Clean up whitespace
            text_content = re.sub(r"\s+", " ", text_content)
            text_content = text_content.strip()

            result = [f"HTML File: {filename}"]
            result.append("Extracted text content:")
            result.append(text_content)

            return "\n".join(result)

        except Exception as e:
            logger.error(f"Failed to process HTML file {filename}: {e}")
            return await self._process_text(content, filename)

    def get_supported_types(self) -> list[str]:
        """Get list of supported file types."""
        return list(self.supported_types.keys())


# Global instance
file_processing_service = FileProcessingService()


def get_file_processing_service() -> FileProcessingService:
    """Get the global file processing service instance."""
    return file_processing_service
