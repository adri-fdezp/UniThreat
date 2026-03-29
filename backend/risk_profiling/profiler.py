import json
import sys
import os
from typing import List, Dict, Any, Optional

# Ensure backend path is in sys.path
backend_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_path not in sys.path:
    sys.path.append(backend_path)

class RiskProfiler:
    """
    Unified logic for OSINT information gathering.
    Clean slate: Basic Google Search only.
    """

    # Basic starting strategy
    STRATEGIES = {
        "google": (
            "Google Search", 
            '{target}'
        )
    }

    def __init__(self):
        self.engines = []

    def add_engine(self, engine: Any) -> None:
        """Register a search engine module (e.g., GoogleSearch)."""
        self.engines.append(engine)

    def _calculate_relevance(self, item: Dict[str, str], target_name: str) -> int:
        """
        Placeholder for relevance scoring. 
        Currently treats all results as equal.
        """
        return 1

    def profile(self, target_name: str, selected_modules: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Executes the profiling process.
        Raw search, no filtering.

        :param target_name: The name of the target to search for.
        :param selected_modules: Optional list of strategy keys to execute.
        :return: A dictionary containing the target name and grouped search results.
        """
        full_profile = {
            "target": target_name,
            "sources": {}
        }

        # Determine which strategies to run
        active_strategies = {}
        if selected_modules:
            for mod_key in selected_modules:
                if mod_key in self.STRATEGIES:
                    label, query_template = self.STRATEGIES[mod_key]
                    active_strategies[label] = query_template.format(target=target_name)
        else:
            # Default to all if nothing selected
            for label, query_template in self.STRATEGIES.values():
                active_strategies[label] = query_template.format(target=target_name)

        # Execute searches across all registered engines
        for engine in self.engines:
            for label, query in active_strategies.items():
                category_name = f"{engine.engine_name}: {label}"
                try:
                    print(f"[*] Executing Selected Module: {category_name}")
                    data = engine.search(query)
                    
                    if data:
                        # No filtering, just collection
                        full_profile["sources"][category_name] = data
                    else:
                        full_profile["sources"][category_name] = []
                        
                except Exception as e:
                    print(f"[!] Error in {category_name}: {e}")
                    full_profile["sources"][category_name] = [{"error": str(e)}]

        return full_profile

def main():
    import argparse
    from search_engines.google_engine import GoogleSearch
    
    parser = argparse.ArgumentParser(description="CLI tool for Risk Profiling")
    parser.add_argument("name", help="Target name to profile")
    args = parser.parse_args()

    profiler = RiskProfiler()
    profiler.add_engine(GoogleSearch(headless=False))
    
    report = profiler.profile(args.name)
    print(json.dumps(report, indent=2))

if __name__ == "__main__":
    main()
