#!/usr/bin/env python3
"""
RED API Documentation Parser
Helper script to extract key information from RED API documentation
"""

import json
from pathlib import Path
from typing import Dict, Any, List

def extract_api_endpoints(docs_text: str) -> Dict[str, Any]:
    """Extract API endpoints from documentation text"""
    endpoints = {}

    # Look for common patterns
    lines = docs_text.split('\n')
    current_endpoint = None

    for line in lines:
        line = line.strip()

        # Look for endpoint patterns
        if any(method in line.upper() for method in ['GET', 'POST', 'PUT', 'DELETE']):
            if ' ' in line:
                method, path = line.split(' ', 1)
                current_endpoint = {
                    'method': method.upper(),
                    'path': path.strip(),
                    'description': '',
                    'parameters': [],
                    'response': {}
                }
                endpoints[path.strip()] = current_endpoint

        # Look for descriptions
        elif current_endpoint is not None and line and not line.startswith('-'):
            if not current_endpoint['description']:
                current_endpoint['description'] = line

        # Look for parameters
        elif current_endpoint is not None and (line.startswith('-') or line.startswith('*')):
            param = line.lstrip('-* ').strip()
            if param:
                current_endpoint['parameters'].append(param)

    return endpoints

def create_api_summary(docs_file: Path) -> Dict[str, Any]:
    """Create a summary of the API documentation"""
    if not docs_file.exists():
        return {"error": "Documentation file not found"}

    with open(docs_file, 'r') as f:
        content = f.read()

    # Extract basic information
    summary = {
        "total_length": len(content),
        "lines_count": len(content.split('\n')),
        "endpoints_found": len(extract_api_endpoints(content)),
        "has_authentication": any(term in content.lower() for term in ['auth', 'token', 'key', 'login']),
        "has_upload": any(term in content.lower() for term in ['upload', 'torrent', 'file']),
        "has_rate_limit": any(term in content.lower() for term in ['rate', 'limit', 'throttle'])
    }

    return summary

if __name__ == "__main__":
    docs_file = Path(__file__).parent.parent / "docs" / "RED_API_REFERENCE.md"

    if docs_file.exists():
        summary = create_api_summary(docs_file)
        print("📊 RED API Documentation Summary:")
        print(f"   📄 Total length: {summary['total_length']} characters")
        print(f"   📝 Lines: {summary['lines_count']}")
        print(f"   🔗 Endpoints found: {summary['endpoints_found']}")
        print(f"   🔐 Has authentication: {'✅' if summary['has_authentication'] else '❌'}")
        print(f"   📤 Has upload endpoints: {'✅' if summary['has_upload'] else '❌'}")
        print(f"   ⏱️  Has rate limiting: {'✅' if summary['has_rate_limit'] else '❌'}")
    else:
        print("❌ RED_API_REFERENCE.md not found. Please add your API documentation first.")
