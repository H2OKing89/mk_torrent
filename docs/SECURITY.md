# 🔐 Security Guide

## Overview

This guide covers security best practices for using mk_torrent, including credential management, data protection, and secure configuration.

## Credential Management

### Secure Storage

#### Encrypted Configuration
```json
{
  "credentials": {
    "qbittorrent": {
      "username": "encrypted_value",
      "password": "encrypted_value"
    },
    "trackers": {
      "red": {
        "api_key": "encrypted_value",
        "username": "encrypted_value"
      }
    }
  }
}
```

#### Keyring Integration
```bash
# Store credentials securely
python scripts/run_new.py credentials store qbittorrent_password

# Retrieve encrypted credentials
python scripts/run_new.py credentials get qbittorrent_password
```

### API Key Security

#### Environment Variables (Recommended)
```bash
# Set API keys securely
export RED_API_KEY="your_secure_api_key"
export AUDNEXUS_API_KEY="your_audnexus_key"

# Never hardcode in scripts
# ❌ BAD
api_key = "hardcoded_key"

# ✅ GOOD
import os
api_key = os.getenv('RED_API_KEY')
```

#### File Permissions
```bash
# Secure configuration files
chmod 600 ~/.config/mk_torrent/config.json
chmod 700 ~/.config/mk_torrent/

# Secure credential files
chmod 600 ~/.config/mk_torrent/secure_config.enc
```

## Data Protection

### File Encryption

#### Torrent Data Encryption
```bash
# Encrypt sensitive files before torrenting
python scripts/run_new.py encrypt /path/to/sensitive/ \
  --algorithm aes256 \
  --output /path/to/encrypted/

# Decrypt after download
python scripts/run_new.py decrypt /path/to/encrypted/ \
  --key-file ~/.keys/decryption.key
```

#### Metadata Sanitization
```bash
# Remove sensitive metadata
python scripts/run_new.py sanitize file.mp3 \
  --remove-location \
  --remove-device-info \
  --remove-personal-data
```

### Network Security

#### HTTPS Only
```bash
# Force HTTPS connections
export REQUESTS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt

# Verify SSL certificates
python scripts/run_new.py config --ssl-verify true
```

#### VPN Usage
```bash
# Recommended: Use VPN for tracker communications
# Configure VPN endpoint
export VPN_ENDPOINT="your.vpn.server"
export VPN_USERNAME="your_vpn_user"

# Auto-connect before uploads
python scripts/run_new.py upload torrent.torrent --vpn-auto
```

## Secure Configuration

### qBittorrent Security

#### Web UI Configuration
```json
{
  "qbittorrent": {
    "web_ui": {
      "https": true,
      "certificate": "/path/to/cert.pem",
      "key": "/path/to/key.pem",
      "username": "secure_username",
      "password": "strong_password"
    },
    "authentication": {
      "bypass_local_auth": false,
      "bypass_auth_subnet_whitelist": "192.168.1.0/24"
    }
  }
}
```

#### Access Control
```bash
# Restrict qBittorrent access
# Only allow local network
iptables -A INPUT -p tcp -s 192.168.1.0/24 --dport 8080 -j ACCEPT
iptables -A INPUT -p tcp --dport 8080 -j DROP
```

### Docker Security

#### Container Hardening
```yaml
version: '3.8'
services:
  qbittorrent:
    image: qbittorrentofficial/qbittorrent-nox:latest
    security_opt:
      - no-new-privileges:true
    read_only: true
    tmpfs:
      - /tmp
    volumes:
      - ./config:/config:ro
      - ./downloads:/downloads
    cap_drop:
      - ALL
    cap_add:
      - NET_ADMIN
```

#### User Namespace
```bash
# Run with user namespace
docker run --userns=host \
  --user $(id -u):$(id -g) \
  qbittorrent-nox
```

## Best Practices

### Password Security

#### Strong Passwords
```bash
# Generate secure passwords
python scripts/run_new.py generate-password \
  --length 32 \
  --symbols \
  --numbers \
  --uppercase \
  --lowercase
```

#### Password Rotation
```bash
# Rotate qBittorrent password
python scripts/run_new.py rotate-password qbittorrent

# Update stored credentials
python scripts/run_new.py credentials update qbittorrent_password
```

### Audit Logging

#### Enable Logging
```bash
# Enable security logging
python scripts/run_new.py config --logging security

# Log all API calls
export MK_TORRENT_LOG_API=true

# Log credential access
export MK_TORRENT_LOG_CREDENTIALS=true
```

#### Log Analysis
```bash
# View security logs
python scripts/run_new.py logs security --tail 100

# Search for suspicious activity
python scripts/run_new.py logs security --grep "failed_login"

# Generate security report
python scripts/run_new.py security-report --period 30d
```

### Backup Security

#### Encrypted Backups
```bash
# Create encrypted backup
python scripts/run_new.py backup \
  --encrypt \
  --key-file ~/.keys/backup.key \
  --output ~/secure_backup.tar.gz.enc
```

#### Secure Storage
```bash
# Store backups securely
# Use encrypted external drive
sudo cryptsetup luksFormat /dev/sdb
sudo cryptsetup luksOpen /dev/sdb secure_backup

# Or cloud storage with encryption
aws s3 cp backup.tar.gz.enc s3://secure-backups/
```

## Threat Mitigation

### Common Threats

#### Man-in-the-Middle Attacks
```bash
# Use certificate pinning
python scripts/run_new.py config --cert-pinning true

# Verify tracker certificates
openssl s_client -connect tracker.example.com:443 -servername tracker.example.com
```

#### Credential Stuffing
```bash
# Implement rate limiting
python scripts/run_new.py config --rate-limit 5

# Use unique passwords per service
# Never reuse passwords across trackers
```

#### Malware in Torrents
```bash
# Scan files before torrenting
python scripts/run_new.py scan-malware /path/to/files/

# Verify file integrity
python scripts/run_new.py verify-integrity torrent.torrent
```

### Incident Response

#### Breach Detection
```bash
# Monitor for suspicious activity
python scripts/run_new.py monitor --alerts email

# Check for unauthorized access
python scripts/run_new.py logs access --anomalies
```

#### Recovery Procedures
```bash
# Emergency credential rotation
python scripts/run_new.py emergency-rotate-all

# Secure wipe of compromised data
python scripts/run_new.py secure-wipe /path/to/compromised/

# Generate incident report
python scripts/run_new.py incident-report --date 2024-01-15
```

## Compliance

### Privacy Regulations

#### GDPR Compliance
```bash
# Minimize data collection
python scripts/run_new.py config --privacy minimal

# Data retention policy
python scripts/run_new.py config --retention 90d

# Right to erasure
python scripts/run_new.py delete-user-data user@example.com
```

#### Data Encryption at Rest
```bash
# Encrypt all stored data
python scripts/run_new.py encrypt-storage \
  --algorithm aes256-gcm \
  --key-rotation 30d
```

### Security Standards

#### Industry Standards
- **AES-256**: For data encryption
- **PBKDF2**: For key derivation
- **TLS 1.3**: For network communications
- **OAuth 2.0**: For API authentication

#### Security Audits
```bash
# Run security audit
python scripts/run_new.py audit --full

# Check compliance
python scripts/run_new.py compliance --standard gdpr

# Generate security assessment
python scripts/run_new.py security-assessment --output report.pdf
```

## Monitoring & Alerts

### Security Monitoring
```bash
# Real-time monitoring
python scripts/run_new.py monitor \
  --alerts email \
  --thresholds "failed_logins:5,unusual_traffic:100MB"

# Log analysis
python scripts/run_new.py analyze-logs \
  --period 24h \
  --alert-patterns "suspicious,breach,unauthorized"
```

### Alert Configuration
```json
{
  "alerts": {
    "email": {
      "enabled": true,
      "recipients": ["admin@example.com"],
      "smtp": {
        "server": "smtp.gmail.com",
        "port": 587,
        "username": "alerts@example.com",
        "password": "encrypted"
      }
    },
    "webhook": {
      "enabled": true,
      "url": "https://api.example.com/webhooks/security",
      "headers": {
        "Authorization": "Bearer encrypted_token"
      }
    }
  }
}
```

## Emergency Procedures

### Lockdown Mode
```bash
# Emergency lockdown
python scripts/run_new.py lockdown \
  --disable-uploads \
  --disable-api \
  --alert-admins

# Restore normal operations
python scripts/run_new.py lockdown --restore
```

### Data Breach Response
```bash
# 1. Isolate affected systems
python scripts/run_new.py isolate --affected-systems

# 2. Preserve evidence
python scripts/run_new.py preserve-evidence --case incident_2024_001

# 3. Notify affected parties
python scripts/run_new.py notify-breach --template gdpr_breach

# 4. Recovery
python scripts/run_new.py recovery --from-backup latest_secure
```

## Resources

### Security Tools
- **OpenSSL**: Certificate management
- **GPG**: File encryption
- **Fail2Ban**: Brute force protection
- **OSSEC**: Host-based intrusion detection

### Further Reading
- [OWASP Security Guidelines](https://owasp.org/www-project-top-ten/)
- [NIST Cybersecurity Framework](https://www.nist.gov/cyberframework)
- [Privacy by Design](https://www.ipc.on.ca/wp-content/uploads/Resources/7foundationalprinciples.pdf)

### Support
- 🐛 [Security Issues](https://github.com/H2OKing89/mk_torrent/security/advisories)
- 📧 security@mk-torrent.dev
- 🔐 [Security Policy](https://github.com/H2OKing89/mk_torrent/blob/main/SECURITY.md)
