#!/usr/bin/env python3
"""Comprehensive tests for secure credential management"""

import pytest
import json
from unittest.mock import patch
from cryptography.fernet import Fernet

from src.mk_torrent.core.secure_credentials import (
    SecureCredentialManager,
    setup_secure_storage,
    get_secure_qbittorrent_password,
    get_secure_tracker_url,
    get_secure_tracker_credential,
    store_secure_tracker_credential,
)


@pytest.fixture
def temp_config_dir(tmp_path):
    """Create a temporary config directory for testing"""
    config_dir = tmp_path / ".config" / "torrent_creator"
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir


@pytest.fixture
def secure_manager(temp_config_dir):
    """Create a SecureCredentialManager instance with temp directory"""
    with patch("pathlib.Path.home", return_value=temp_config_dir.parent.parent):
        manager = SecureCredentialManager()
        return manager


class TestSecureCredentialManager:
    """Test SecureCredentialManager core functionality"""

    def test_initialization(self, secure_manager, temp_config_dir):
        """Test manager initialization creates proper directory structure"""
        assert secure_manager.config_dir.exists()
        assert secure_manager.config_dir == temp_config_dir
        assert (
            secure_manager.secure_config_file == temp_config_dir / "secure_config.enc"
        )
        assert secure_manager.key_file == temp_config_dir / "master_key"
        assert secure_manager.salt_file == temp_config_dir / "salt"

    def test_master_key_generation(self, secure_manager):
        """Test master key generation and storage"""
        # First call should generate new key
        key1 = secure_manager._generate_master_key()
        assert len(key1) == 44  # Fernet key length
        assert secure_manager.key_file.exists()

        # Second call should return same key
        key2 = secure_manager._generate_master_key()
        assert key1 == key2

    def test_salt_generation(self, secure_manager):
        """Test salt generation and storage"""
        salt1 = secure_manager._get_salt()
        assert len(salt1) == 16
        assert secure_manager.salt_file.exists()

        salt2 = secure_manager._get_salt()
        assert salt1 == salt2

    def test_key_derivation(self, secure_manager):
        """Test password-based key derivation"""
        password = "test_password_123"
        key1 = secure_manager._derive_key(password)
        key2 = secure_manager._derive_key(password)

        assert key1 == key2
        assert len(key1) == 44  # Fernet key length

        # Different password should give different key
        key3 = secure_manager._derive_key("different_password")
        assert key1 != key3

    def test_fernet_creation(self, secure_manager):
        """Test Fernet cipher creation"""
        # Test with master key
        fernet1 = secure_manager._get_fernet()
        assert isinstance(fernet1, Fernet)

        # Test with password
        fernet2 = secure_manager._get_fernet("test_password")
        assert isinstance(fernet2, Fernet)

        # Different passwords should give different Fernet instances
        fernet3 = secure_manager._get_fernet("different_password")
        assert fernet1 is not fernet2
        assert fernet2 is not fernet3

    @patch("getpass.getpass")
    def test_setup_master_password_success(self, mock_getpass, secure_manager):
        """Test successful master password setup"""
        mock_getpass.side_effect = ["test_password_123", "test_password_123"]

        result = secure_manager.setup_master_password()
        assert result is True
        assert secure_manager.key_file.exists()

    @patch("getpass.getpass")
    def test_setup_master_password_validation(self, mock_getpass, secure_manager):
        """Test password validation during setup"""
        # Test short password
        mock_getpass.side_effect = [
            "short",
            "short",
            "valid_password_123",
            "valid_password_123",
        ]

        result = secure_manager.setup_master_password()
        assert result is True

    @patch("getpass.getpass")
    def test_setup_master_password_mismatch(self, mock_getpass, secure_manager):
        """Test password mismatch handling"""
        mock_getpass.side_effect = ["password1", "password2", "password1", "password1"]

        result = secure_manager.setup_master_password()
        assert result is True

    @patch("keyring.set_password")
    def test_store_qbittorrent_credentials_keyring(
        self, mock_set_password, secure_manager
    ):
        """Test qBittorrent credential storage with keyring"""
        mock_set_password.return_value = None

        secure_manager.store_qbittorrent_credentials(
            "localhost", 8080, "admin", "test_password"
        )

        mock_set_password.assert_called_once_with(
            "torrent_creator_qbittorrent", "admin@localhost:8080", "test_password"
        )

    @patch("keyring.get_password")
    def test_get_qbittorrent_password_keyring(self, mock_get_password, secure_manager):
        """Test qBittorrent password retrieval from keyring"""
        mock_get_password.return_value = "retrieved_password"

        result = secure_manager.get_qbittorrent_password("localhost", 8080, "admin")

        assert result == "retrieved_password"
        mock_get_password.assert_called_once_with(
            "torrent_creator_qbittorrent", "admin@localhost:8080"
        )

    @patch("keyring.get_password", side_effect=Exception("Keyring not available"))
    def test_get_qbittorrent_password_fallback(self, mock_get_password, secure_manager):
        """Test fallback to encrypted storage when keyring fails"""
        # Mock encrypted credential retrieval
        with patch.object(
            secure_manager,
            "_get_encrypted_credential",
            return_value="fallback_password",
        ) as mock_get_encrypted:
            result = secure_manager.get_qbittorrent_password("localhost", 8080, "admin")

            assert result == "fallback_password"
            mock_get_encrypted.assert_called_once_with(
                "qbittorrent", "admin@localhost:8080"
            )

    @patch("keyring.set_password")
    def test_store_tracker_passkey_keyring(self, mock_set_password, secure_manager):
        """Test tracker passkey storage with keyring"""
        mock_set_password.return_value = None

        secure_manager.store_tracker_passkey(
            "https://tracker.example.com/announce", "test_passkey_123"
        )

        mock_set_password.assert_called_once_with(
            "torrent_creator_tracker_tracker.example.com", "passkey", "test_passkey_123"
        )

    @patch("keyring.get_password")
    def test_get_tracker_passkey_keyring(self, mock_get_password, secure_manager):
        """Test tracker passkey retrieval from keyring"""
        mock_get_password.return_value = "retrieved_passkey"

        result = secure_manager.get_tracker_passkey(
            "https://tracker.example.com/announce"
        )

        assert result == "retrieved_passkey"
        mock_get_password.assert_called_once_with(
            "torrent_creator_tracker_tracker.example.com", "passkey"
        )

    def test_encrypted_credential_storage(self, secure_manager):
        """Test encrypted credential storage and retrieval"""
        # Store credential
        secure_manager._store_encrypted_credential(
            "test_service", "test_user", "test_password"
        )

        # Retrieve credential
        result = secure_manager._get_encrypted_credential("test_service", "test_user")

        assert result == "test_password"

    def test_encrypted_credential_different_services(self, secure_manager):
        """Test encrypted credentials for different services"""
        # Store credentials for different services
        secure_manager._store_encrypted_credential("service1", "user1", "pass1")
        secure_manager._store_encrypted_credential("service2", "user2", "pass2")

        # Retrieve and verify
        assert secure_manager._get_encrypted_credential("service1", "user1") == "pass1"
        assert secure_manager._get_encrypted_credential("service2", "user2") == "pass2"
        assert secure_manager._get_encrypted_credential("service1", "user2") is None

    def test_encrypted_credentials_persistence(self, secure_manager):
        """Test that encrypted credentials persist across manager instances"""
        # Store credential
        secure_manager._store_encrypted_credential("test", "user", "password")

        # Create new manager instance (simulating app restart)
        with patch(
            "pathlib.Path.home", return_value=secure_manager.config_dir.parent.parent
        ):
            new_manager = SecureCredentialManager()

        # Should be able to retrieve the credential
        result = new_manager._get_encrypted_credential("test", "user")
        assert result == "password"

    @patch("keyring.set_password", side_effect=Exception("Keyring not available"))
    def test_qbittorrent_fallback_to_encrypted(self, mock_set_password, secure_manager):
        """Test qBittorrent credential storage falls back to encrypted when keyring fails"""
        secure_manager.store_qbittorrent_credentials(
            "localhost", 8080, "admin", "test_password"
        )

        # Should be stored in encrypted file
        result = secure_manager._get_encrypted_credential(
            "qbittorrent", "admin@localhost:8080"
        )
        assert result == "test_password"

    @patch("keyring.set_password", side_effect=Exception("Keyring not available"))
    def test_tracker_fallback_to_encrypted(self, mock_set_password, secure_manager):
        """Test tracker passkey storage falls back to encrypted when keyring fails"""
        secure_manager.store_tracker_passkey(
            "https://tracker.example.com/announce", "test_passkey"
        )

        # Should be stored in encrypted file
        result = secure_manager._get_encrypted_credential(
            "tracker_tracker.example.com", "passkey"
        )
        assert result == "test_passkey"

    def test_migrate_plain_text_credentials(self, secure_manager, tmp_path):
        """Test migration of plain text credentials"""
        # Create a mock config file with plain text credentials
        config_file = tmp_path / "config.json"
        config_data = {
            "qbit_host": "localhost",
            "qbit_port": 8080,
            "qbit_username": "admin",
            "qbit_password": "plain_text_password",
            "other_setting": "value",
        }

        with open(config_file, "w") as f:
            json.dump(config_data, f)

        # Migrate credentials
        with patch("keyring.set_password") as mock_set_password:
            secure_manager.migrate_plain_text_credentials(config_file)

            # Should have stored the password securely
            mock_set_password.assert_called_once_with(
                "torrent_creator_qbittorrent",
                "admin@localhost:8080",
                "plain_text_password",
            )

        # Check that password was removed from config file
        with open(config_file, "r") as f:
            updated_config = json.load(f)

        assert "qbit_password" not in updated_config
        assert updated_config["other_setting"] == "value"

    def test_migrate_tracker_passkeys(self, secure_manager, tmp_path):
        """Test migration of tracker passkeys"""
        # Create a mock trackers file
        trackers_file = tmp_path / "trackers.txt"
        tracker_content = "https://tracker.example.com/test_passkey/announce\nhttps://another.tracker.com/announce"

        with open(trackers_file, "w") as f:
            f.write(tracker_content)

        # Migrate passkeys
        with patch("keyring.set_password") as mock_set_password:
            secure_manager.migrate_tracker_passkeys(trackers_file)

            # Should have stored the passkey securely
            mock_set_password.assert_called_once_with(
                "torrent_creator_tracker_tracker.example.com", "passkey", "test_passkey"
            )

        # Check that passkey was replaced in trackers file
        with open(trackers_file, "r") as f:
            updated_content = f.read()

        assert "SECURE_PASSKEY_STORED" in updated_content
        assert "test_passkey" not in updated_content

    def test_get_secure_tracker_url_red_format(self, secure_manager):
        """Test secure tracker URL generation for RED tracker"""
        tracker_url = "https://flacsfor.me  # SECURE_PASSKEY_STORED"

        with patch.object(
            secure_manager, "get_tracker_credential", return_value="test_passkey"
        ) as mock_get_cred:
            result = secure_manager.get_secure_tracker_url(tracker_url)

            assert result == "https://flacsfor.me/test_passkey/announce"
            mock_get_cred.assert_called_once_with("RED", "passkey")

    def test_get_secure_tracker_url_generic_format(self, secure_manager):
        """Test secure tracker URL generation for generic trackers"""
        tracker_url = "https://tracker.example.com  # SECURE_PASSKEY_STORED"

        with patch.object(
            secure_manager, "get_tracker_passkey", return_value="generic_passkey"
        ) as mock_get_passkey:
            result = secure_manager.get_secure_tracker_url(tracker_url)

            assert result == "https://tracker.example.com/generic_passkey/announce"
            mock_get_passkey.assert_called_once_with("https://tracker.example.com")

    def test_store_tracker_credential_validation(self, secure_manager):
        """Test tracker credential storage validation"""
        # Test empty tracker name
        with pytest.raises(ValueError, match="Tracker name cannot be empty"):
            secure_manager.store_tracker_credential("", "passkey", "value")

        # Test empty credential type
        with pytest.raises(ValueError, match="Credential type cannot be empty"):
            secure_manager.store_tracker_credential("RED", "", "value")

        # Test empty value
        with pytest.raises(ValueError, match="Credential value cannot be empty"):
            secure_manager.store_tracker_credential("RED", "passkey", "")

    def test_get_tracker_credential_validation(self, secure_manager):
        """Test tracker credential retrieval validation"""
        # Test empty tracker name
        with pytest.raises(ValueError, match="Tracker name cannot be empty"):
            secure_manager.get_tracker_credential("", "passkey")

        # Test empty credential type
        with pytest.raises(ValueError, match="Credential type cannot be empty"):
            secure_manager.get_tracker_credential("RED", "")

    def test_tracker_credential_roundtrip(self, secure_manager):
        """Test storing and retrieving tracker credentials"""
        # Store credential
        secure_manager.store_tracker_credential("RED", "passkey", "test_value_123")

        # Retrieve credential
        result = secure_manager.get_tracker_credential("RED", "passkey")

        assert result == "test_value_123"

    def test_multiple_tracker_credentials(self, secure_manager):
        """Test multiple tracker credentials"""
        # Store credentials for different trackers
        secure_manager.store_tracker_credential("RED", "passkey", "red_passkey")
        secure_manager.store_tracker_credential("RED", "api_key", "red_api_key")
        secure_manager.store_tracker_credential("OPS", "passkey", "ops_passkey")

        # Retrieve and verify
        assert secure_manager.get_tracker_credential("RED", "passkey") == "red_passkey"
        assert secure_manager.get_tracker_credential("RED", "api_key") == "red_api_key"
        assert secure_manager.get_tracker_credential("OPS", "passkey") == "ops_passkey"


class TestGlobalFunctions:
    """Test global convenience functions"""

    @patch("src.mk_torrent.core.secure_credentials.secure_manager")
    def test_setup_secure_storage(self, mock_manager):
        """Test global setup function"""
        mock_manager.setup_master_password.return_value = True

        result = setup_secure_storage()
        assert result is True
        mock_manager.setup_master_password.assert_called_once()

    @patch("src.mk_torrent.core.secure_credentials.secure_manager")
    def test_get_secure_qbittorrent_password(self, mock_manager):
        """Test global qBittorrent password function"""
        mock_manager.get_qbittorrent_password.return_value = "test_password"

        result = get_secure_qbittorrent_password("localhost", 8080, "admin")

        assert result == "test_password"
        mock_manager.get_qbittorrent_password.assert_called_once_with(
            "localhost", 8080, "admin"
        )

    @patch("src.mk_torrent.core.secure_credentials.secure_manager")
    def test_get_secure_tracker_url(self, mock_manager):
        """Test global secure tracker URL function"""
        mock_manager.get_secure_tracker_url.return_value = (
            "https://tracker.com/passkey/announce"
        )

        result = get_secure_tracker_url("https://tracker.com  # SECURE_PASSKEY_STORED")

        assert result == "https://tracker.com/passkey/announce"
        mock_manager.get_secure_tracker_url.assert_called_once_with(
            "https://tracker.com  # SECURE_PASSKEY_STORED"
        )

    @patch("src.mk_torrent.core.secure_credentials.secure_manager")
    def test_get_secure_tracker_credential(self, mock_manager):
        """Test global tracker credential function"""
        mock_manager.get_tracker_credential.return_value = "credential_value"

        result = get_secure_tracker_credential("RED", "passkey")

        assert result == "credential_value"
        mock_manager.get_tracker_credential.assert_called_once_with("RED", "passkey")

    @patch("src.mk_torrent.core.secure_credentials.secure_manager")
    def test_store_secure_tracker_credential(self, mock_manager):
        """Test global store tracker credential function"""
        store_secure_tracker_credential("RED", "passkey", "test_value")

        mock_manager.store_tracker_credential.assert_called_once_with(
            "RED", "passkey", "test_value"
        )


class TestErrorHandling:
    """Test error handling and edge cases"""

    def test_corrupted_encrypted_file(self, secure_manager):
        """Test handling of corrupted encrypted credential file"""
        # Create a corrupted encrypted file
        with open(secure_manager.secure_config_file, "wb") as f:
            f.write(b"corrupted_data")

        # Should handle gracefully and return empty dict
        result = secure_manager._load_encrypted_credentials()
        assert result == {}

    def test_missing_encrypted_file(self, secure_manager):
        """Test handling when encrypted file doesn't exist"""
        # Ensure file doesn't exist
        if secure_manager.secure_config_file.exists():
            secure_manager.secure_config_file.unlink()

        # Should return empty dict
        result = secure_manager._load_encrypted_credentials()
        assert result == {}

    @patch(
        "cryptography.fernet.Fernet.decrypt", side_effect=Exception("Decryption failed")
    )
    def test_decryption_failure_fallback(self, mock_decrypt, secure_manager):
        """Test fallback when decryption fails"""
        # Create a valid encrypted file first
        test_data = {"test": {"user": "password"}}
        secure_manager._save_encrypted_credentials(test_data)

        # Mock decryption failure
        with patch("builtins.input", return_value="wrong_password"):
            result = secure_manager._load_encrypted_credentials()

        # Should return empty dict on failure
        assert result == {}

    def test_file_permission_errors(self, secure_manager):
        """Test handling of file permission errors"""
        # Make config directory read-only
        secure_manager.config_dir.chmod(0o444)

        try:
            # This should handle permission errors gracefully
            result = secure_manager._load_encrypted_credentials()
            assert result == {}
        finally:
            # Restore permissions for cleanup
            secure_manager.config_dir.chmod(0o700)
