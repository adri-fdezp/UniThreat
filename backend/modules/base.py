"""
Base module interface for all UniThreat OSINT modules.

Every module must subclass BaseModule and implement run().
This enforces a uniform interface across all data-collection modules
and makes it straightforward to register new modules in the future.
"""

from abc import ABC, abstractmethod


class BaseModule(ABC):
    """Abstract base class for all OSINT modules.

    Attributes:
        name (str): Unique identifier for this module (e.g. ``"github"``).
                    Must match the key used in the backend module registry
                    inside ``app.py``.
    """

    name = "base"

    @abstractmethod
    def run(self, target: dict) -> dict:
        """Execute OSINT gathering against the provided target.

        Args:
            target (dict): Target descriptor with the following keys:

                - ``name``     (str) — Full name; always present.
                - ``username`` (str) — Social media handle; may be empty.
                - ``email``    (str) — Email address; may be empty.

        Returns:
            dict: Module-specific structured data.  On failure the dict
            should contain an ``"error"`` key with a human-readable message
            so the frontend can display it gracefully instead of crashing.
        """
