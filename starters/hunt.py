#!/usr/bin/env python3
"""Hunt for coin/currency functions in Il2CppDumper metadata.

Searches dump.cs and stringliteral.json for economy-related terms.
Cross-references classes appearing in multiple searches.
No GhidraMCP connection needed — works on metadata files alone.

Usage:
    python hunt.py [--metadata-dir ../metadata]
"""

import argparse
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

SEARCH_TERMS = [
    "coin", "currency", "balance", "purchase", "iap",
    "reward", "score", "wallet", "inventory", "money",
    "shop", "store", "transaction", "payment", "price",
]


def search_dump_cs(dump_path: Path, terms: list[str]) -> dict[str, dict]:
    """Search dump.cs for classes matching search terms.

    Returns {class_name: {"methods": int, "matched_terms": set, "lines": [str]}}
    """
    classes = defaultdict(lambda: {"methods": 0, "matched_terms": set(), "lines": []})
    current_class = None

    with open(dump_path) as f:
        for line in f:
            # Detect class definitions (handles modifiers like static, abstract, sealed)
            class_match = re.match(r'\s*(?:public|private|internal)?\s*(?:static|abstract|sealed)?\s*class\s+(\w+)', line)
            if class_match:
                current_class = class_match.group(1)

            # Count methods in current class
            if current_class and re.match(r'\s+(?:public|private|protected|internal|static|\s)*\s+\w+\s+\w+\s*\(', line):
                classes[current_class]["methods"] += 1

            # Search for terms
            lower = line.lower()
            for term in terms:
                if term in lower:
                    # Attribute to current class or extract from line
                    target_class = current_class or "(global)"
                    classes[target_class]["matched_terms"].add(term)
                    classes[target_class]["lines"].append(line.strip())

    return dict(classes)


def search_string_literals(stringlit_path: Path, terms: list[str]) -> list[dict]:
    """Search stringliteral.json for matching strings."""
    with open(stringlit_path) as f:
        data = json.load(f)

    matches = []
    for entry in data:
        value = entry.get("value", "")
        lower = value.lower()
        matched = [t for t in terms if t in lower]
        if matched:
            matches.append({
                "value": value,
                "address": entry.get("address", "unknown"),
                "matched_terms": matched,
            })

    return matches


def search_script_json(script_path: Path, terms: list[str]) -> dict[str, list[str]]:
    """Search script.json for methods with matching names.

    Returns {class_name: [method_names]}
    """
    with open(script_path) as f:
        data = json.load(f)

    classes = defaultdict(list)
    for method in data.get("ScriptMethod", []):
        name = method.get("Name", "")
        lower = name.lower()
        if any(term in lower for term in terms):
            if "$$" in name:
                cls, method_name = name.split("$$", 1)
                classes[cls].append(method_name)
            else:
                classes["(unknown)"].append(name)

    return dict(classes)


def main():
    parser = argparse.ArgumentParser(description="Hunt for coin/currency functions in metadata")
    parser.add_argument("--metadata-dir", default="../metadata",
                        help="Path to Il2CppDumper output directory")
    parser.add_argument("--terms", nargs="+", default=SEARCH_TERMS,
                        help="Search terms (default: coin currency balance ...)")
    args = parser.parse_args()

    metadata_dir = Path(args.metadata_dir)

    print(f"Searching metadata in: {metadata_dir}")
    print(f"Terms: {', '.join(args.terms)}\n")

    # Search each available file
    results_by_class = defaultdict(lambda: {"term_hits": Counter(), "methods": [], "strings": []})

    # dump.cs
    dump_path = metadata_dir / "dump.cs"
    if dump_path.exists():
        print(f"Searching {dump_path}...")
        dump_results = search_dump_cs(dump_path, args.terms)
        for cls, info in dump_results.items():
            for term in info["matched_terms"]:
                results_by_class[cls]["term_hits"][term] += 1
    else:
        print(f"Not found: {dump_path} (skipping)")

    # script.json
    script_path = metadata_dir / "script.json"
    if script_path.exists():
        print(f"Searching {script_path}...")
        script_results = search_script_json(script_path, args.terms)
        for cls, methods in script_results.items():
            results_by_class[cls]["methods"] = methods
            for method in methods:
                for term in args.terms:
                    if term in method.lower():
                        results_by_class[cls]["term_hits"][term] += 1
    else:
        print(f"Not found: {script_path} (skipping)")

    # stringliteral.json
    stringlit_path = metadata_dir / "stringliteral.json"
    string_matches = []
    if stringlit_path.exists():
        print(f"Searching {stringlit_path}...")
        string_matches = search_string_literals(stringlit_path, args.terms)
    else:
        print(f"Not found: {stringlit_path} (skipping)")

    # Rank classes by number of distinct term matches
    ranked = sorted(results_by_class.items(),
                    key=lambda x: len(x[1]["term_hits"]),
                    reverse=True)

    # Output
    print(f"\n{'='*60}")
    print("RESULTS")
    print(f"{'='*60}\n")

    high = [(cls, info) for cls, info in ranked if len(info["term_hits"]) >= 3]
    medium = [(cls, info) for cls, info in ranked if len(info["term_hits"]) == 2]
    low = [(cls, info) for cls, info in ranked if len(info["term_hits"]) == 1]

    if high:
        print("High-relevance classes (3+ term matches):")
        for cls, info in high:
            terms = ", ".join(f'"{t}"' for t in info["term_hits"])
            methods = info["methods"]
            method_str = f"{len(methods)} methods" if methods else "methods unknown"
            print(f"  {cls:<35} — {method_str:<15} | matched: {terms}")
        print()

    if medium:
        print("Medium-relevance classes (2 term matches):")
        for cls, info in medium[:10]:
            terms = ", ".join(f'"{t}"' for t in info["term_hits"])
            print(f"  {cls:<35} — matched: {terms}")
        print()

    if low:
        print(f"Low-relevance classes (1 term match): {len(low)} classes")
        for cls, info in low[:5]:
            terms = ", ".join(f'"{t}"' for t in info["term_hits"])
            print(f"  {cls:<35} — matched: {terms}")
        if len(low) > 5:
            print(f"  ... and {len(low) - 5} more")
        print()

    if string_matches:
        print(f"String literals ({len(string_matches)} matches):")
        for match in string_matches[:15]:
            addr = match["address"]
            val = match["value"][:60]
            print(f"  {addr}: \"{val}\"")
        if len(string_matches) > 15:
            print(f"  ... and {len(string_matches) - 15} more")
        print()

    if not ranked:
        print("No matches found. Check that metadata files exist in the metadata directory.")
        print(f"Expected: {metadata_dir}/dump.cs, script.json, stringliteral.json")


if __name__ == "__main__":
    main()
