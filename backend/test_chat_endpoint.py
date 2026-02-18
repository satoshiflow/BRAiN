#!/usr/bin/env python3
"""
Test Script for /api/chat Endpoint

Tests the new chat endpoint locally before deployment.
"""

import asyncio
import httpx
import json
import os

# Test Configuration
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://docker-image-dgscsswg4g8gksgw40csgw4c:11434")


async def test_health_check():
    """Test /api/chat/health endpoint"""
    print("\n" + "="*60)
    print("TEST 1: Chat Health Check")
    print("="*60)

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{BACKEND_URL}/api/chat/health")
            print(f"Status: {response.status_code}")
            print(f"Response:\n{json.dumps(response.json(), indent=2)}")

            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "healthy":
                    print("✅ Health check PASSED")
                    return True
                else:
                    print("❌ Health check FAILED: Ollama not reachable")
                    return False
            else:
                print(f"❌ Health check FAILED: HTTP {response.status_code}")
                return False

        except Exception as e:
            print(f"❌ Health check ERROR: {e}")
            return False


async def test_chat_basic():
    """Test /api/chat with simple message"""
    print("\n" + "="*60)
    print("TEST 2: Basic Chat")
    print("="*60)

    payload = {
        "messages": [
            {"role": "user", "content": "Hallo! Wer bist du?"}
        ],
        "model": "qwen2.5:0.5b",
        "max_tokens": 100,
        "temperature": 0.7
    }

    print(f"Request:\n{json.dumps(payload, indent=2, ensure_ascii=False)}")

    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            response = await client.post(
                f"{BACKEND_URL}/api/chat",
                json=payload
            )

            print(f"\nStatus: {response.status_code}")
            print(f"Response:\n{json.dumps(response.json(), indent=2, ensure_ascii=False)}")

            if response.status_code == 200:
                data = response.json()
                if data.get("message") and data["message"].get("content"):
                    print("\n✅ Chat request PASSED")
                    print(f"✅ Got response: {data['message']['content'][:100]}...")
                    return True
                else:
                    print("❌ Chat request FAILED: Empty response")
                    return False
            else:
                print(f"❌ Chat request FAILED: HTTP {response.status_code}")
                print(f"Error: {response.text}")
                return False

        except Exception as e:
            print(f"❌ Chat request ERROR: {e}")
            return False


async def test_chat_conversation():
    """Test /api/chat with multi-turn conversation"""
    print("\n" + "="*60)
    print("TEST 3: Multi-Turn Conversation")
    print("="*60)

    payload = {
        "messages": [
            {"role": "system", "content": "Du bist ein hilfreicher Assistent."},
            {"role": "user", "content": "Was ist 2+2?"},
            {"role": "assistant", "content": "2+2 ist 4."},
            {"role": "user", "content": "Und was ist 4+4?"}
        ],
        "model": "qwen2.5:0.5b",
        "max_tokens": 50
    }

    print(f"Request:\n{json.dumps(payload, indent=2, ensure_ascii=False)}")

    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            response = await client.post(
                f"{BACKEND_URL}/api/chat",
                json=payload
            )

            print(f"\nStatus: {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                print(f"Response:\n{json.dumps(data, indent=2, ensure_ascii=False)}")
                print("\n✅ Multi-turn conversation PASSED")
                return True
            else:
                print(f"❌ Multi-turn conversation FAILED: HTTP {response.status_code}")
                return False

        except Exception as e:
            print(f"❌ Multi-turn conversation ERROR: {e}")
            return False


async def test_error_handling():
    """Test error handling"""
    print("\n" + "="*60)
    print("TEST 4: Error Handling")
    print("="*60)

    # Test with empty messages
    payload = {
        "messages": [],
        "model": "qwen2.5:0.5b"
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{BACKEND_URL}/api/chat",
                json=payload
            )

            print(f"Status: {response.status_code}")

            if response.status_code == 422 or response.status_code == 400:
                print("✅ Error handling PASSED (empty messages rejected)")
                return True
            else:
                print(f"❌ Error handling FAILED: Expected 400/422, got {response.status_code}")
                return False

        except Exception as e:
            print(f"❌ Error handling ERROR: {e}")
            return False


async def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("BRAiN Chat Endpoint Test Suite")
    print("="*60)
    print(f"Backend URL: {BACKEND_URL}")
    print(f"Ollama Host: {OLLAMA_HOST}")

    results = []

    # Run tests
    results.append(("Health Check", await test_health_check()))
    results.append(("Basic Chat", await test_chat_basic()))
    results.append(("Multi-Turn", await test_chat_conversation()))
    results.append(("Error Handling", await test_error_handling()))

    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{name:20s} {status}")

    print(f"\n{passed}/{total} tests passed")

    if passed == total:
        print("\n🎉 ALL TESTS PASSED! Ready for deployment!")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Check errors above.")
        return 1


if __name__ == "__main__":
    exit(asyncio.run(main()))
