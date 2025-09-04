# Security Policy

## Supported Versions

We provide security updates for the following versions:

| Version | Supported          |
| ------- | ------------------ |
| 1.0.x   | :white_check_mark: |
| < 1.0   | :x:                |

## Reporting a Vulnerability

We take security vulnerabilities seriously. If you discover a security issue, please follow these steps:

### For Critical Security Issues

**DO NOT** create a public GitHub issue for security vulnerabilities.

Instead, please:

1. **Email**: Send details to the maintainer privately
2. **Include**:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact
   - Any suggested fixes

### Response Timeline

- **Initial Response**: Within 48 hours
- **Status Update**: Within 1 week
- **Resolution**: Varies by severity, typically 2-4 weeks

### What Happens Next

1. We'll acknowledge receipt of your report
2. We'll investigate and validate the issue
3. We'll develop and test a fix
4. We'll coordinate the release and disclosure
5. We'll credit you for the discovery (if desired)

## Security Best Practices

When using mk_torrent:

### API Keys and Credentials
- Store credentials securely (use environment variables)
- Never commit API keys to version control
- Rotate credentials regularly
- Use minimum required permissions

### File Handling
- Validate all file inputs
- Be cautious with file paths and permissions
- Scan uploaded content when possible

### Network Security
- Use HTTPS for all API communications
- Validate SSL certificates
- Implement request rate limiting
- Monitor for unusual API usage patterns

## Security Features

mk_torrent includes several security features:

- **Input validation**: All user inputs are validated
- **Path sanitization**: File paths are cleaned to prevent directory traversal
- **API rate limiting**: Built-in protection against API abuse
- **Secure defaults**: Conservative security settings by default

## Automated Security Scanning

This repository uses:

- **CodeQL**: GitHub's semantic code analysis
- **Bandit**: Python security linter
- **pip-audit**: Dependency vulnerability scanning
- **Dependabot**: Automated dependency updates

## Disclosure Policy

We follow responsible disclosure practices:

- Vulnerabilities are fixed before public disclosure
- We coordinate with reporters on disclosure timing
- Security advisories are published through GitHub Security Advisories
- We provide credit to security researchers (with permission)

## Contact

For security-related questions or concerns:
- Review our [documentation](./docs/SECURITY.md) for detailed security guidelines
- Check [GitHub Security Advisories](https://github.com/H2OKing89/mk_torrent/security/advisories) for known issues
- File security issues through GitHub's private reporting feature
