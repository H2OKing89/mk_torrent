#!/usr/bin/env python3
"""Comprehensive tests for qBittorrent API integration"""

import unittest
import json
from unittest.mock import patch, MagicMock, Mock
from pathlib import Path
import tempfile

from src.mk_torrent.api.qbittorrent import (
    QBittorrentAPI,
    run_health_check,
    check_docker_connectivity,
    validate_qbittorrent_config,
    sync_qbittorrent_metadata
)


class TestQBittorrentAPI(unittest.TestCase):
    """Test QBittorrentAPI core functionality"""

    def setUp(self):
        """Set up test fixtures"""
        self.api_client = QBittorrentAPI(
            host="localhost",
            port=8080,
            username="admin",
            password="test_password",
            use_https=False
        )
        self.https_api_client = QBittorrentAPI(
            host="localhost",
            port=8080,
            username="admin",
            password="test_password",
            use_https=True
        )

    def test_initialization(self):
        """Test API client initialization"""
        self.assertEqual(self.api_client.host, "localhost")
        self.assertEqual(self.api_client.port, 8080)
        self.assertEqual(self.api_client.username, "admin")
        self.assertEqual(self.api_client.password, "test_password")
        self.assertFalse(self.api_client.use_https)
        self.assertFalse(self.api_client.logged_in)
        self.assertIsNone(self.api_client.api_version)
        self.assertIsNone(self.api_client.sid_cookie)

    def test_base_url_http(self):
        """Test base URL generation for HTTP"""
        self.assertEqual(self.api_client.base_url, "http://localhost:8080")

    def test_base_url_https(self):
        """Test base URL generation for HTTPS"""
        self.assertEqual(self.https_api_client.base_url, "https://localhost:8080")

    def test_successful_login(self):
        """Test successful login"""
        # Mock the login response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "Ok."

        # Mock the session cookies to include SID
        mock_cookies = MagicMock()
        mock_cookies.__contains__ = lambda self, key: key == 'SID'
        mock_cookies.__getitem__ = lambda self, key: "test_session_id" if key == 'SID' else None

        with patch.object(self.api_client.session, 'post', return_value=mock_response):
            with patch.object(self.api_client.session, 'cookies', mock_cookies):
                result = self.api_client.login()

                self.assertTrue(result)
                self.assertTrue(self.api_client.logged_in)
                self.assertEqual(self.api_client.sid_cookie, "test_session_id")

    def test_failed_login_invalid_credentials(self):
        """Test login failure with invalid credentials"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "Fails."

        with patch.object(self.api_client.session, 'post', return_value=mock_response):
            result = self.api_client.login()

            self.assertFalse(result)
            self.assertFalse(self.api_client.logged_in)

    def test_login_connection_error(self):
        """Test login with connection error"""
        with patch.object(self.api_client.session, 'post', side_effect=Exception("Connection refused")):
            result = self.api_client.login()

            self.assertFalse(result)
            self.assertFalse(self.api_client.logged_in)

    def test_verify_login_success(self):
        """Test login verification"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "v4.4.0"

        with patch.object(self.api_client.session, 'get', return_value=mock_response):
            result = self.api_client._verify_login()

            self.assertTrue(result)

    def test_verify_login_failure(self):
        """Test login verification failure"""
        mock_response = MagicMock()
        mock_response.status_code = 403

        with patch.object(self.api_client.session, 'get', return_value=mock_response):
            result = self.api_client._verify_login()

            self.assertFalse(result)

    def test_test_connection_success(self):
        """Test successful connection"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "2.8.14"

        with patch.object(self.api_client.session, 'get', return_value=mock_response):
            success, message = self.api_client.test_connection()

            self.assertTrue(success)
            self.assertIn("Connected", message)
            self.assertEqual(self.api_client.api_version, "2.8.14")

    def test_test_connection_failure(self):
        """Test connection failure"""
        mock_response = MagicMock()
        mock_response.status_code = 500

        with patch.object(self.api_client.session, 'get', return_value=mock_response):
            success, message = self.api_client.test_connection()

            self.assertFalse(success)
            self.assertIn("HTTP 500", message)

    def test_get_preferences_success(self):
        """Test successful preferences retrieval"""
        mock_prefs = {
            "save_path": "/downloads",
            "web_ui_domain_list": "localhost"
        }

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_prefs

        with patch.object(self.api_client.session, 'get', return_value=mock_response):
            with patch.object(self.api_client, 'login', return_value=True):
                result = self.api_client.get_preferences()

                self.assertEqual(result, mock_prefs)

    def test_get_default_save_path(self):
        """Test default save path retrieval"""
        mock_prefs = {"save_path": "/downloads"}

        with patch.object(self.api_client, 'get_preferences', return_value=mock_prefs):
            result = self.api_client.get_default_save_path()

            self.assertEqual(result, "/downloads")

    def test_get_default_save_path_no_prefs(self):
        """Test default save path when preferences unavailable"""
        with patch.object(self.api_client, 'get_preferences', return_value=None):
            result = self.api_client.get_default_save_path()

            self.assertIsNone(result)

    def test_create_torrent_not_supported(self):
        """Test torrent creation (not supported via Web API)"""
        with patch.object(self.api_client, 'login', return_value=True):
            success, data = self.api_client.create_torrent("/path/to/file")

            self.assertFalse(success)
            self.assertEqual(data, b"")

    def test_health_check_connection_failure(self):
        """Test health check with connection failure"""
        with patch.object(self.api_client, 'test_connection', return_value=(False, "Connection refused")):
            result = self.api_client.health_check()

            self.assertFalse(result["connection"])
            self.assertIn("Connection failed", result["errors"][0])

    def test_health_check_full_success(self):
        """Test comprehensive health check success"""
        # Mock all successful responses
        with patch.object(self.api_client, 'test_connection', return_value=(True, "Connected")):
            with patch.object(self.api_client, 'login', return_value=True):
                with patch.object(self.api_client, 'get_preferences', return_value={"save_path": "/downloads"}):
                    result = self.api_client.health_check()

                    self.assertTrue(result["connection"])
                    self.assertTrue(result["authenticated"])
                    self.assertTrue(result["preferences_accessible"])
                    self.assertEqual(result["default_save_path"], "/downloads")
                    self.assertEqual(len(result["errors"]), 0)

    def test_get_categories_success(self):
        """Test successful categories retrieval"""
        mock_categories = {
            "audiobooks": {"savePath": "/downloads/audiobooks"},
            "music": {"savePath": "/downloads/music"}
        }

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_categories

        with patch.object(self.api_client.session, 'get', return_value=mock_response):
            with patch.object(self.api_client, 'login', return_value=True):
                result = self.api_client.get_categories()

                self.assertEqual(result, mock_categories)

    def test_create_category_success(self):
        """Test successful category creation"""
        mock_response = MagicMock()
        mock_response.status_code = 200

        with patch.object(self.api_client.session, 'post', return_value=mock_response):
            with patch.object(self.api_client, 'login', return_value=True):
                result = self.api_client.create_category("test_category", "/downloads/test")

                self.assertTrue(result)

    def test_get_tags_success(self):
        """Test successful tags retrieval"""
        mock_tags = ["audiobook", "flac", "lossless"]

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_tags

        with patch.object(self.api_client.session, 'get', return_value=mock_response):
            with patch.object(self.api_client, 'login', return_value=True):
                result = self.api_client.get_tags()

                self.assertEqual(result, mock_tags)

    def test_create_tags_success(self):
        """Test successful tag creation"""
        mock_response = MagicMock()
        mock_response.status_code = 200

        with patch.object(self.api_client.session, 'post', return_value=mock_response):
            with patch.object(self.api_client, 'login', return_value=True):
                result = self.api_client.create_tags(["tag1", "tag2"])

                self.assertTrue(result)

    def test_create_tags_empty_list(self):
        """Test creating empty tag list"""
        # For empty list, the method should return True without making HTTP calls
        # This tests the early return logic
        self.api_client.logged_in = True  # Ensure we're logged in
        
        with patch.object(self.api_client.session, 'post') as mock_post:
            result = self.api_client.create_tags([])

            # Should return True for empty list without making any HTTP calls
            self.assertTrue(result)
            mock_post.assert_not_called()

    def test_sync_categories_and_tags(self):
        """Test synchronization of categories and tags"""
        config = {
            "categories": ["audiobooks", "music"],
            "common_tags": ["flac", "lossless", "new_tag"]
        }

        # Mock existing data
        with patch.object(self.api_client, 'get_categories', return_value={"existing": {}}):
            with patch.object(self.api_client, 'create_category', return_value=True):
                with patch.object(self.api_client, 'get_tags', return_value=["flac"]):
                    with patch.object(self.api_client, 'create_tags', return_value=True):
                        self.api_client.sync_categories_and_tags(config)


class TestGlobalFunctions(unittest.TestCase):
    """Test global utility functions"""

    @patch('src.mk_torrent.api.qbittorrent.QBittorrentAPI')
    @patch('src.mk_torrent.api.qbittorrent.get_qbittorrent_password')
    def test_run_health_check_success(self, mock_get_password, mock_api_class):
        """Test successful health check run"""
        # Mock config
        config = {
            "qbit_host": "localhost",
            "qbit_port": 8080,
            "qbit_username": "admin"
        }

        # Mock password retrieval
        mock_get_password.return_value = "test_password"

        # Mock API instance
        mock_api = MagicMock()
        mock_api.base_url = "http://localhost:8080"
        mock_api.health_check.return_value = {
            "connection": True,
            "authenticated": True,
            "api_version": "2.8.14",
            "preferences_accessible": True,
            "default_save_path": "/downloads",
            "errors": [],
            "warnings": []
        }
        mock_api_class.return_value = mock_api

        result = run_health_check(config)

        self.assertTrue(result)
        mock_api.health_check.assert_called_once()

    @patch('src.mk_torrent.api.qbittorrent.get_qbittorrent_password', return_value=None)
    def test_run_health_check_no_password(self, mock_get_password):
        """Test health check with no stored password"""
        config = {
            "qbit_host": "localhost",
            "qbit_port": 8080,
            "qbit_username": "admin"
        }

        result = run_health_check(config)

        self.assertFalse(result)

    @patch('subprocess.run')
    def test_test_docker_connectivity_success(self, mock_subprocess):
        """Test successful Docker connectivity"""
        # Mock container running
        mock_result = MagicMock()
        mock_result.stdout = "qbittorrent_container\n"
        mock_result.returncode = 0

        # Mock successful exec
        mock_exec_result = MagicMock()
        mock_exec_result.returncode = 0

        mock_subprocess.side_effect = [mock_result, mock_exec_result]

        result = check_docker_connectivity("qbittorrent_container")

        self.assertTrue(result)

    @patch('subprocess.run')
    def test_test_docker_connectivity_container_not_running(self, mock_subprocess):
        """Test Docker connectivity when container not running"""
        # Mock container not running
        mock_result = MagicMock()
        mock_result.stdout = ""
        mock_result.returncode = 0

        # Mock list containers
        mock_list_result = MagicMock()
        mock_list_result.stdout = "NAMES\nother_container"

        mock_subprocess.side_effect = [mock_result, mock_list_result]

        result = check_docker_connectivity("qbittorrent_container")

        self.assertFalse(result)

    @patch('subprocess.run', side_effect=FileNotFoundError)
    def test_test_docker_connectivity_docker_not_found(self, mock_subprocess):
        """Test Docker connectivity when Docker not installed"""
        result = check_docker_connectivity("qbittorrent_container")

        self.assertFalse(result)

    @patch('src.mk_torrent.api.qbittorrent.Client')
    def test_validate_qbittorrent_config_success(self, mock_client_class):
        """Test successful qBittorrent config validation"""
        config = {
            "qbit_host": "localhost",
            "qbit_port": 8080,
            "qbit_username": "admin",
            "qbit_password": "test_password"
        }

        mock_client = MagicMock()
        mock_client.app_version.return_value = "v4.4.0"
        mock_client_class.return_value = mock_client

        # Mock the get_qbittorrent_password function
        with patch('src.mk_torrent.api.qbittorrent.get_qbittorrent_password', return_value="test_password"):
            result = validate_qbittorrent_config(config)

            self.assertTrue(result)

    @patch('src.mk_torrent.api.qbittorrent.Client')
    def test_validate_qbittorrent_config_failure(self, mock_client_class):
        """Test qBittorrent config validation failure"""
        config = {
            "qbit_host": "localhost",
            "qbit_port": 8080,
            "qbit_username": "admin",
            "qbit_password": "wrong_password"
        }

        mock_client_class.side_effect = Exception("Connection failed")

        result = validate_qbittorrent_config(config)

        self.assertFalse(result)

    @patch('src.mk_torrent.api.qbittorrent.Client')
    def test_sync_qbittorrent_metadata_success(self, mock_client_class):
        """Test successful metadata synchronization"""
        config = {
            "qbit_host": "localhost",
            "qbit_port": 8080,
            "qbit_username": "admin",
            "qbit_password": "test_password",
            "default_category": "audiobooks",
            "default_tags": ["flac", "lossless", "new_tag"]
        }

        mock_client = MagicMock()
        mock_client.torrents_categories.return_value = {}
        mock_client.torrents_tags.return_value = ["flac"]
        mock_client_class.return_value = mock_client

        sync_qbittorrent_metadata(config)

        # Verify category creation
        mock_client.torrents_create_category.assert_called_once_with("audiobooks")

        # Verify tag creation
        mock_client.torrents_create_tags.assert_called_once_with(["lossless", "new_tag"])

    @patch('src.mk_torrent.api.qbittorrent.Client')
    def test_sync_qbittorrent_metadata_failure(self, mock_client_class):
        """Test metadata synchronization failure"""
        config = {
            "qbit_host": "localhost",
            "qbit_port": 8080,
            "qbit_username": "admin",
            "qbit_password": "test_password"
        }

        mock_client_class.side_effect = Exception("Connection failed")

        # Should not raise exception, just log warning
        sync_qbittorrent_metadata(config)


class TestErrorHandling(unittest.TestCase):
    """Test error handling and edge cases"""

    def setUp(self):
        """Set up test fixtures"""
        self.api_client = QBittorrentAPI(
            host="localhost",
            port=8080,
            username="admin",
            password="test_password",
            use_https=False
        )

    def test_login_with_invalid_response(self):
        """Test login with unexpected response"""
        with patch.object(self.api_client.session, 'post') as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.text = "Unexpected response"
            mock_post.return_value = mock_response

            result = self.api_client.login()

            self.assertFalse(result)

    def test_health_check_with_malformed_results(self):
        """Test health check with malformed results structure"""
        # This tests the defensive programming in health_check method
        with patch.object(self.api_client, 'test_connection', return_value=(False, "Failed")):
            result = self.api_client.health_check()

            # Should handle the case gracefully even if results structure is unexpected
            self.assertIsInstance(result, dict)
            self.assertIn("errors", result)
            self.assertIn("warnings", result)

    def test_api_call_with_session_expiry_retry(self):
        """Test API call retry on session expiry"""
        # First call fails with 403 (session expired)
        mock_response_403 = MagicMock()
        mock_response_403.status_code = 403

        # Second call succeeds
        mock_response_200 = MagicMock()
        mock_response_200.status_code = 200
        mock_response_200.json.return_value = {"save_path": "/downloads"}

        with patch.object(self.api_client.session, 'get', side_effect=[mock_response_403, mock_response_200]):
            with patch.object(self.api_client, 'login', return_value=True):
                result = self.api_client.get_preferences()

                self.assertEqual(result, {"save_path": "/downloads"})

    def test_base_url_construction_edge_cases(self):
        """Test base URL construction with edge cases"""
        # Test with port 0
        api = QBittorrentAPI("example.com", 0, "user", "pass", False)
        self.assertEqual(api.base_url, "http://example.com:0")

        # Test with IPv6-like host
        api = QBittorrentAPI("::1", 8080, "user", "pass", False)
        self.assertEqual(api.base_url, "http://::1:8080")

        # Test with very long host
        long_host = "a" * 100
        api = QBittorrentAPI(long_host, 8080, "user", "pass", False)
        self.assertEqual(api.base_url, f"http://{long_host}:8080")


if __name__ == '__main__':
    unittest.main()
