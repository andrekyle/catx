#!/usr/bin/env python3
"""
Test script to verify search functionality is working correctly
"""
import requests
import json
from urllib.parse import urlencode

BASE_URL = "http://localhost:5004"

def test_search_functionality():
    """Test various search scenarios"""
    print("🔍 Testing Search Functionality")
    print("=" * 50)
    
    # Test cases
    test_cases = [
        {
            "query": "product",
            "description": "Search for products"
        },
        {
            "query": "privacy",
            "description": "Search for privacy policy page"
        },
        {
            "query": "terms",
            "description": "Search for terms and conditions"
        },
        {
            "query": "contact",
            "description": "Search for contact page"
        },
        {
            "query": "about",
            "description": "Search for about page"
        },
        {
            "query": "nonexistent123",
            "description": "Search for non-existent content"
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        query = test_case["query"]
        description = test_case["description"]
        
        print(f"\n{i}. {description}")
        print(f"   Query: '{query}'")
        
        try:
            # Test the search endpoint
            search_url = f"{BASE_URL}/search?q={urlencode({'': query})[1:]}"
            response = requests.get(search_url, timeout=5)
            
            if response.status_code == 200:
                print(f"   ✅ Status: {response.status_code} (OK)")
                
                # Check if the response contains expected elements
                content = response.text.lower()
                if 'search results' in content:
                    print("   ✅ Search results page loaded correctly")
                else:
                    print("   ⚠️  Search results page may not be loading correctly")
                    
                if query.lower() in content:
                    print(f"   ✅ Query '{query}' found in response")
                else:
                    print(f"   ⚠️  Query '{query}' not found in response")
                    
            else:
                print(f"   ❌ Status: {response.status_code}")
                print(f"   Error: {response.text[:200]}...")
                
        except requests.exceptions.RequestException as e:
            print(f"   ❌ Request failed: {e}")
        except Exception as e:
            print(f"   ❌ Unexpected error: {e}")
    
    print("\n" + "=" * 50)
    print("🎯 Testing search types (products, pages, all)")
    
    # Test search type filtering
    type_tests = [
        {"type": "all", "description": "All results"},
        {"type": "products", "description": "Products only"},
        {"type": "pages", "description": "Pages only"}
    ]
    
    for test in type_tests:
        search_type = test["type"]
        description = test["description"]
        
        print(f"\n• {description}")
        try:
            search_url = f"{BASE_URL}/search?q=test&type={search_type}"
            response = requests.get(search_url, timeout=5)
            
            if response.status_code == 200:
                print(f"   ✅ Search type '{search_type}' works")
            else:
                print(f"   ❌ Search type '{search_type}' failed: {response.status_code}")
                
        except Exception as e:
            print(f"   ❌ Error testing search type '{search_type}': {e}")
    
    print("\n" + "=" * 50)
    print("✅ Search functionality testing completed!")

if __name__ == "__main__":
    test_search_functionality()
