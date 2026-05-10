# Base class for all OSINT modules.
# Every module must inherit from this and implement run().

from abc import ABC, abstractmethod


class BaseModule(ABC):
    # Each subclass sets this to its module ID (e.g. "github", "duckduckgo")
    name = "base"

    @abstractmethod
    def run(self, target: dict) -> dict:
        """
        Run the module against the target.

        target always has these keys:
            name     (str) — full name, always present
            username (str) — social handle, may be empty
            email    (str) — email address, may be empty

        Return a dict with the results, or {"error": "message"} on failure.
        """
