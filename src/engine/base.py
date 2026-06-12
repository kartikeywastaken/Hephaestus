# -*- coding: utf-8 -*-
"""
Extraction Layer Base Module
Defines interfaces, error standards, versioned output models, and retry logic.
"""

import abc
import json
import logging
import time
from typing import Dict, Any, Optional, Callable, TypeVar, List

# Setup Structured Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s - %(filename)s:%(lineno)d: %(message)s'
)
logger = logging.getLogger("BinaryReconstruction.BaseExtractor")

T = TypeVar('T')

class ExtractorError(Exception):
    """Base custom exception representing non-recoverable extraction errors."""
    pass

class ExtractorRecoverableError(ExtractorError):
    """Errors where retry logic might succeed (e.g., lock failures, temporary storage issues)."""
    pass

def execute_with_retry(
    func: Callable[[], T],
    retries: int = 3,
    initial_delay: float = 1.0,
    backoff_factor: float = 2.0,
    allowed_exceptions: tuple = (ExtractorRecoverableError,)
) -> T:
    """
    Executes a callable with exponential backoff retry.
    """
    delay = initial_delay
    last_exception = None
    for attempt in range(1, retries + 1):
        try:
            return func()
        except allowed_exceptions as e:
            last_exception = e
            logger.warning(
                f"Attempt {attempt}/{retries} failed with recoverable exception: {e}. "
                f"Retrying in {delay}s..."
            )
            time.sleep(delay)
            delay *= backoff_factor
        except Exception as e:
            logger.error(f"Attempt {attempt}/{retries} aborted. Non-recoverable error: {e}")
            raise e
    logger.error(f"All {retries} retry attempts exhausted.")
    raise ExtractorError(f"Operation failed after {retries} attempts. Last error: {last_exception}")

class BaseExtractor(abc.ABC):
    """
    Abstract Base Class representing a schema-conforming Extractor client.
    Handles artifact versioning, configuration injection, and structured evidence.
    """

    SCHEMA_VERSION = "1.0.0"

    def __init__(self, binary_path: str, output_path: str, config: Optional[Dict[str, Any]] = None):
        self.binary_path = binary_path
        self.output_path = output_path
        self.config = config or {}
        self.logger = logging.getLogger(f"BinaryReconstruction.{self.__class__.__name__}")

    @abc.abstractmethod
    def validate_environment(self) -> bool:
        """Verifies that necessary tool paths (e.g., Ghidra, IDA) and file privileges are present."""
        pass

    @abc.abstractmethod
    def extract(self) -> Dict[str, Any]:
        """
        Executes the extraction process to retrieve artifacts.
        Must return a dict conforming to the versioned output schemas.
        """
        pass

    def generate_envelope(self, payload: Dict[str, Any], tool_name: str) -> Dict[str, Any]:
        """
        Wraps extracted elements in a standardized, versioned telemetry and provenance metadata block.
        Ensures machine-readable evidence validation.
        """
        return {
            "schema_version": self.SCHEMA_VERSION,
            "provenance": {
                "tool_name": tool_name,
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S-07:00"),
                "binary_path": self.binary_path,
                "config": self.config
            },
            "data": payload
        }

    def save_artifact(self, envelope: Dict[str, Any]) -> None:
        """Saves completed, validated evidence to the target file path."""
        try:
            with open(self.output_path, 'w', encoding='utf-8') as f:
                json.dump(envelope, f, indent=2, ensure_ascii=False)
            self.logger.info(f"Artifact successfully committed to resource path: {self.output_path}")
        except IOError as e:
            self.logger.error(f"Failed to save artifact trace file: {e}")
            raise ExtractorError(f"I/O Error while committing artifact: {e}")
