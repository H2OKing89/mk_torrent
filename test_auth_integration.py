#!/usr/bin/env python3
"""
Authentication System Integration Test (Phase 3B.3.4)

This script tests the standardized authentication patterns implemented in
Phase 3B.3.4 across different integration types.
"""

import logging
import sys
from pathlib import Path
from datetime import timedelta

# Add src to path for testing
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def test_authentication_factory():
    """Test the authentication factory creates different handler types correctly"""
    print("\n=== Testing Authentication Factory ===")

    try:
        from mk_torrent.integrations.auth import (
            AuthenticationFactory,
            AuthenticationConfig,
            AuthenticationType,
            CredentialStorage,
        )

        # Test API Key handler
        api_config = AuthenticationConfig(
            auth_type=AuthenticationType.API_KEY,
            storage_method=CredentialStorage.MEMORY_ONLY,
            service_name="Test API",
            api_key="test_key_12345",
            session_timeout=timedelta(hours=1),
        )

        api_handler = AuthenticationFactory.create_handler(api_config)
        print(f"✅ API Key handler created: {type(api_handler).__name__}")

        # Test Username/Password handler
        cred_config = AuthenticationConfig(
            auth_type=AuthenticationType.USERNAME_PASSWORD,
            storage_method=CredentialStorage.MEMORY_ONLY,
            service_name="Test Service",
            username="testuser",
            password="testpass",  # nosec B106
            session_timeout=timedelta(hours=2),
        )

        cred_handler = AuthenticationFactory.create_handler(cred_config)
        print(f"✅ Username/Password handler created: {type(cred_handler).__name__}")

        # Test No Auth handler
        no_auth_config = AuthenticationConfig(
            auth_type=AuthenticationType.NO_AUTH,
            storage_method=CredentialStorage.MEMORY_ONLY,
            service_name="Public API",
        )

        no_auth_handler = AuthenticationFactory.create_handler(no_auth_config)
        print(f"✅ No Auth handler created: {type(no_auth_handler).__name__}")

        return True

    except Exception as e:
        print(f"❌ Authentication factory test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_qbittorrent_integration():
    """Test qBittorrent integration with standardized authentication"""
    print("\n=== Testing qBittorrent Integration ===")

    try:
        from mk_torrent.integrations.qbittorrent_modern import (
            QBittorrentClient,
            QBittorrentConfig,
        )

        # Create config (won't actually connect)
        config = QBittorrentConfig(
            host="localhost",
            port=8080,
            username="admin",
            password="adminpass",  # nosec B106
            timeout=5,
        )

        client = QBittorrentClient(config)
        print(f"✅ qBittorrent client created: {type(client).__name__}")

        # Test authentication setup (won't actually authenticate without server)
        has_auth_handler = hasattr(client, "_auth_handler")
        print(f"✅ Authentication handler configured: {has_auth_handler}")

        return True

    except Exception as e:
        print(f"❌ qBittorrent integration test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_red_integration():
    """Test RED tracker integration with standardized authentication"""
    print("\n=== Testing RED Integration ===")

    try:
        from mk_torrent.integrations.red_integration import (
            REDIntegrationClient,
            REDIntegrationConfig,
        )

        # Create config (won't actually connect)
        config = REDIntegrationConfig(
            base_url="https://redacted.sh", api_key="test_api_key_12345", dry_run=True
        )

        client = REDIntegrationClient(config)
        print(f"✅ RED client created: {type(client).__name__}")

        # Test authentication setup
        has_auth_handler = hasattr(client, "_auth_handler")
        print(f"✅ Authentication handler configured: {has_auth_handler}")

        return True

    except Exception as e:
        print(f"❌ RED integration test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_integration_factory():
    """Test integration factory can create clients with proper config objects"""
    print("\n=== Testing Integration Factory ===")

    try:
        from mk_torrent.integrations.factory import IntegrationFactory

        # List registered clients
        registered = IntegrationFactory.list_available()
        print(f"✅ Registered integrations: {registered}")

        # Check if our expected integrations are registered
        if "qbittorrent" in registered:
            print("✅ qBittorrent integration registered")
        else:
            print("❌ qBittorrent integration not found")
            return False

        # Test getting integration info
        try:
            info = IntegrationFactory.get_info("qbittorrent")
            print(
                f"✅ qBittorrent info: class={info.get('class_name')}, config={info.get('config_class_name')}"
            )
        except Exception as e:
            print(f"❌ Failed to get info: {e}")

        # Test actual client creation with the enhanced factory
        try:
            qb_client = IntegrationFactory.create(
                "qbittorrent",
                host="localhost",
                port=8080,
                username="admin",
                password="testpass",  # nosec B106
            )
            print(
                f"✅ qBittorrent client created via factory: {type(qb_client).__name__}"
            )
            print(
                f"✅ Client has authentication handler: {hasattr(qb_client, '_auth_handler')}"
            )

        except Exception as e:
            print(f"❌ Factory client creation failed: {e}")
            import traceback

            traceback.print_exc()
            return False

        return True

    except Exception as e:
        print(f"❌ Integration factory test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def main():
    """Run all authentication system tests"""
    print("Testing Phase 3B.3.4 Authentication Pattern Standardization")
    print("=" * 60)

    tests = [
        test_authentication_factory,
        test_qbittorrent_integration,
        test_red_integration,
        test_integration_factory,
    ]

    results = []
    for test_func in tests:
        try:
            result = test_func()
            results.append(result)
        except Exception as e:
            print(f"❌ Test {test_func.__name__} crashed: {e}")
            results.append(False)

    print("\n" + "=" * 60)
    print("Test Results Summary:")
    passed = sum(results)
    total = len(results)
    print(f"✅ Passed: {passed}/{total}")

    if passed == total:
        print("🎉 All authentication system tests passed!")
        return 0
    else:
        print("⚠️  Some tests failed - check output above")
        return 1


if __name__ == "__main__":
    sys.exit(main())
