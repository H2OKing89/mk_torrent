#!/usr/bin/env python3
"""Secure credential management for sensitive data"""

from pathlib import Path
from typing import Dict, Any, Optional, List
import json
import os
import base64
import getpass
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import keyring
import secrets

from rich.console import Console
from rich.prompt import Prompt, Confirm

console = Console()

class SecureCredentialManager:
    """Secure credential storage using encryption and keyring"""

    def __init__(self, app_name: str = "torrent_creator"):
        self.app_name = app_name
        self.config_dir = Path.home() / ".config" / app_name
        self.secure_config_file = self.config_dir / "secure_config.enc"
        self.key_file = self.config_dir / "master_key"
        self.salt_file = self.config_dir / "salt"

        # Ensure config directory exists with proper permissions
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.config_dir.chmod(0o700)

    def _generate_master_key(self) -> bytes:
        """Generate or load master encryption key"""
        if self.key_file.exists():
            with open(self.key_file, 'rb') as f:
                return f.read()

        # Generate new key
        key = Fernet.generate_key()
        with open(self.key_file, 'wb') as f:
            f.write(key)
        self.key_file.chmod(0o600)
        return key

    def _get_salt(self) -> bytes:
        """Get or generate salt for key derivation"""
        if self.salt_file.exists():
            with open(self.salt_file, 'rb') as f:
                return f.read()

        # Generate new salt
        salt = secrets.token_bytes(16)
        with open(self.salt_file, 'wb') as f:
            f.write(salt)
        self.salt_file.chmod(0o600)
        return salt

    def _derive_key(self, password: str) -> bytes:
        """Derive encryption key from password"""
        salt = self._get_salt()
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        return base64.urlsafe_b64encode(kdf.derive(password.encode()))

    def _get_fernet(self, password: Optional[str] = None) -> Fernet:
        """Get Fernet cipher instance"""
        if password:
            key = self._derive_key(password)
        else:
            key = self._generate_master_key()
        return Fernet(key)

    def setup_master_password(self) -> bool:
        """Setup master password for encryption"""
        console.print("[bold cyan]🔐 Setting up secure credential storage[/bold cyan]")

        if self.key_file.exists():
            console.print("[yellow]Master key already exists[/yellow]")
            return True

        console.print("[dim]A master password will be used to encrypt sensitive data[/dim]")
        console.print("[dim]This password will be required to access stored credentials[/dim]\n")

        while True:
            password = getpass.getpass("Enter master password: ")
            if len(password) < 8:
                console.print("[red]Password must be at least 8 characters[/red]")
                continue

            confirm = getpass.getpass("Confirm master password: ")
            if password != confirm:
                console.print("[red]Passwords don't match[/red]")
                continue

            # Generate and save master key
            master_key = self._derive_key(password)
            with open(self.key_file, 'wb') as f:
                f.write(master_key)
            self.key_file.chmod(0o600)

            console.print("[green]✅ Master password setup complete[/green]")
            return True

    def store_qbittorrent_credentials(self, host: str, port: int, username: str, password: str):
        """Securely store qBittorrent credentials"""
        service_name = f"{self.app_name}_qbittorrent"

        # Store in system keyring
        try:
            keyring.set_password(service_name, f"{username}@{host}:{port}", password)
            console.print("[green]✅ qBittorrent password stored securely[/green]")
        except Exception as e:
            console.print(f"[yellow]⚠️ Keyring not available, using encrypted storage: {e}[/yellow]")
            self._store_encrypted_credential("qbittorrent", f"{username}@{host}:{port}", password)

    def get_qbittorrent_password(self, host: str, port: int, username: str) -> Optional[str]:
        """Retrieve qBittorrent password securely"""
        service_name = f"{self.app_name}_qbittorrent"

        # Try system keyring first
        try:
            password = keyring.get_password(service_name, f"{username}@{host}:{port}")
            if password:
                return password
        except:
            pass

        # Fallback to encrypted storage
        return self._get_encrypted_credential("qbittorrent", f"{username}@{host}:{port}")

    def store_tracker_passkey(self, tracker_url: str, passkey: str):
        """Store private tracker passkey securely"""
        # Extract tracker domain for identification
        from urllib.parse import urlparse
        domain = urlparse(tracker_url).netloc

        service_name = f"{self.app_name}_tracker_{domain}"
        try:
            keyring.set_password(service_name, "passkey", passkey)
            console.print(f"[green]✅ Passkey for {domain} stored securely[/green]")
        except Exception as e:
            console.print(f"[yellow]⚠️ Keyring not available, using encrypted storage: {e}[/yellow]")
            self._store_encrypted_credential(f"tracker_{domain}", "passkey", passkey)

    def get_tracker_passkey(self, tracker_url: str) -> Optional[str]:
        """Retrieve tracker passkey securely"""
        from urllib.parse import urlparse
        domain = urlparse(tracker_url).netloc

        service_name = f"{self.app_name}_tracker_{domain}"
        try:
            passkey = keyring.get_password(service_name, "passkey")
            if passkey:
                return passkey
        except:
            pass

        # Fallback to encrypted storage
        return self._get_encrypted_credential(f"tracker_{domain}", "passkey")

    def _store_encrypted_credential(self, service: str, username: str, password: str):
        """Store credential in encrypted file"""
        # Load existing credentials
        credentials = self._load_encrypted_credentials()

        # Add/update credential
        if service not in credentials:
            credentials[service] = {}
        credentials[service][username] = password

        # Save encrypted
        self._save_encrypted_credentials(credentials)

    def _get_encrypted_credential(self, service: str, username: str) -> Optional[str]:
        """Retrieve credential from encrypted file"""
        credentials = self._load_encrypted_credentials()
        return credentials.get(service, {}).get(username)

    def _load_encrypted_credentials(self) -> Dict[str, Dict[str, str]]:
        """Load encrypted credentials file"""
        if not self.secure_config_file.exists():
            return {}

        try:
            with open(self.secure_config_file, 'rb') as f:
                encrypted_data = f.read()

            # Try with master key first
            try:
                fernet = self._get_fernet()
                decrypted_data = fernet.decrypt(encrypted_data)
                return json.loads(decrypted_data.decode())
            except:
                # If master key fails, prompt for password
                console.print("[yellow]Master password required to access encrypted credentials[/yellow]")
                password = getpass.getpass("Enter master password: ")
                fernet = self._get_fernet(password)
                decrypted_data = fernet.decrypt(encrypted_data)
                return json.loads(decrypted_data.decode())

        except Exception as e:
            console.print(f"[red]Error loading encrypted credentials: {e}[/red]")
            return {}

    def _save_encrypted_credentials(self, credentials: Dict[str, Dict[str, str]]):
        """Save credentials to encrypted file"""
        try:
            fernet = self._get_fernet()
            encrypted_data = fernet.encrypt(json.dumps(credentials).encode())

            with open(self.secure_config_file, 'wb') as f:
                f.write(encrypted_data)
            self.secure_config_file.chmod(0o600)

        except Exception as e:
            console.print(f"[red]Error saving encrypted credentials: {e}[/red]")

    def migrate_plain_text_credentials(self, config_file: Path):
        """Migrate plain text credentials to secure storage"""
        if not config_file.exists():
            return

        console.print("[cyan]🔄 Migrating plain text credentials to secure storage...[/cyan]")

        try:
            with open(config_file, 'r') as f:
                config = json.load(f)

            # Migrate qBittorrent credentials
            if 'qbit_password' in config and config['qbit_password']:
                host = config.get('qbit_host', 'localhost')
                port = config.get('qbit_port', 8080)
                username = config.get('qbit_username', 'admin')

                self.store_qbittorrent_credentials(
                    host, port, username, config['qbit_password']
                )

                # Remove plain text password
                del config['qbit_password']
                console.print("[green]✅ qBittorrent password migrated[/green]")

            # Save updated config without passwords
            with open(config_file, 'w') as f:
                json.dump(config, f, indent=2)

        except Exception as e:
            console.print(f"[red]Error migrating credentials: {e}[/red]")

    def migrate_tracker_passkeys(self, trackers_file: Path):
        """Migrate tracker passkeys to secure storage"""
        if not trackers_file.exists():
            return

        console.print("[cyan]🔄 Migrating tracker passkeys to secure storage...[/cyan]")

        try:
            with open(trackers_file, 'r') as f:
                trackers = [line.strip() for line in f if line.strip()]

            migrated_trackers = []
            for tracker in trackers:
                if '/announce' in tracker and len(tracker.split('/')) >= 4:
                    # Extract passkey from URL
                    parts = tracker.split('/')
                    if len(parts) >= 4 and parts[-2] and len(parts[-2]) > 10:  # Likely a passkey
                        passkey = parts[-2]
                        base_url = '/'.join(parts[:-2]) + '/announce'

                        self.store_tracker_passkey(base_url, passkey)

                        # Replace with placeholder
                        migrated_trackers.append(f"{base_url}  # SECURE_PASSKEY_STORED")
                        console.print(f"[green]✅ Passkey for {base_url} migrated[/green]")
                    else:
                        migrated_trackers.append(tracker)
                else:
                    migrated_trackers.append(tracker)

            # Save updated trackers file
            with open(trackers_file, 'w') as f:
                f.write('\n'.join(migrated_trackers) + '\n')

        except Exception as e:
            console.print(f"[red]Error migrating tracker passkeys: {e}[/red]")

    def get_secure_tracker_url(self, tracker_url: str) -> str:
        """Get tracker URL with passkey inserted from secure storage"""
        if 'SECURE_PASSKEY_STORED' in tracker_url:
            # Extract base URL
            base_url = tracker_url.split('  #')[0]
            passkey = self.get_tracker_passkey(base_url)
            if passkey:
                # Insert passkey back into URL
                return base_url.replace('/announce', f'/{passkey}/announce')
        return tracker_url

    def get_tracker_credential(self, tracker_name: str, credential_type: str) -> Optional[str]:
        """Public method to get tracker-specific credential from secure storage"""
        if not tracker_name or not tracker_name.strip():
            raise ValueError("Tracker name cannot be empty")
        if not credential_type or not credential_type.strip():
            raise ValueError("Credential type cannot be empty")

        service = f"torrent_creator_tracker_{tracker_name.strip()}"
        return self._get_encrypted_credential(service, credential_type.strip())

    def store_tracker_credential(self, tracker_name: str, credential_type: str, value: str):
        """Public method to store tracker-specific credential securely"""
        if not tracker_name or not tracker_name.strip():
            raise ValueError("Tracker name cannot be empty")
        if not credential_type or not credential_type.strip():
            raise ValueError("Credential type cannot be empty")
        if not value:
            raise ValueError("Credential value cannot be empty")

        service = f"torrent_creator_tracker_{tracker_name.strip()}"
        self._store_encrypted_credential(service, credential_type.strip(), value)

# Global instance
secure_manager = SecureCredentialManager()

def setup_secure_storage():
    """Setup secure credential storage"""
    return secure_manager.setup_master_password()

def migrate_to_secure_storage():
    """Migrate existing plain text credentials to secure storage"""
    config_file = Path.home() / ".config" / "torrent_creator" / "config.json"
    trackers_file = Path.home() / ".config" / "torrent_creator" / "trackers.txt"

    secure_manager.migrate_plain_text_credentials(config_file)
    secure_manager.migrate_tracker_passkeys(trackers_file)

def get_secure_qbittorrent_password(host: str, port: int, username: str) -> Optional[str]:
    """Get qBittorrent password from secure storage"""
    return secure_manager.get_qbittorrent_password(host, port, username)

def get_secure_tracker_url(tracker_url: str) -> str:
    """Get tracker URL with secure passkey"""
    return secure_manager.get_secure_tracker_url(tracker_url)

def get_secure_tracker_credential(tracker_name: str, credential_type: str) -> Optional[str]:
    """Get tracker-specific credential from secure storage"""
    return secure_manager.get_tracker_credential(tracker_name, credential_type)

def store_secure_tracker_credential(tracker_name: str, credential_type: str, value: str):
    """Store tracker-specific credential securely"""
    secure_manager.store_tracker_credential(tracker_name, credential_type, value)
