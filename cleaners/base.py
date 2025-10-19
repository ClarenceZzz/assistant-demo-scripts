"""Abstract base class for document cleaners."""

from __future__ import annotations

from abc import ABC, abstractmethod


class BaseCleaner(ABC):
    """Define the interface for document cleaners."""

    @abstractmethod
    def clean(self, file_path: str) -> str:
        """Clean the provided file and return normalized text output."""

