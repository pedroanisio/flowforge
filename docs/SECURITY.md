# Security Guide

## Overview

This document outlines security best practices, known considerations, and recommendations for deploying the Neural Plugin System.

## Security Features Implemented

### ✅ Authentication & Authorization
- **JWT Token-based Authentication**: Industry-standard OAuth2 with JWT tokens
- **Password Hashing**: Bcrypt algorithm for secure password storage
- **Configurable Authentication**: Can be enabled/disabled via `ENABLE_AUTH` environment variable
- **Token Expiration**: Configurable token lifetime (default: 30 minutes)

### ✅ Input Validation
- **Pydantic Models**: All inputs validated against strict Pydantic schemas
- **File Upload Size Limits**: Configurable maximum upload size (default: 100MB)
- **Type Safety**: Strong typing throughout the application
- **Manifest Validation**: Plugin inputs validated against manifest definitions

### ✅ Rate Limiting
- **API Rate Limiting**: Prevents abuse through slowapi integration
- **Configurable Limits**: Adjustable per-minute request limits
- **Per-IP Tracking**: Rate limits applied per client IP address

### ✅ Safe Code Execution
- **No eval() Usage**: Replaced with `simpleeval` for safe expression evaluation
- **Sandboxed Conditions**: Chain conditions use restricted evaluation context
- **Subprocess Safety**: Commands use list format instead of shell=True

### ✅ Logging & Monitoring
- **Structured Logging**: JSON-formatted logs for easy parsing
- **Security Events**: Authentication attempts and failures logged
- **Audit Trail**: Plugin execution tracking

## Security Considerations

### ⚠️ Docker Socket Mounting

**Risk Level**: MEDIUM-HIGH

The application mounts the Docker socket (`/var/run/docker.sock`) to enable container orchestration for specialized plugins (e.g., pdf2html).

**Risks:**
- Container has elevated privileges to control host Docker daemon
- Potential for container escape if application is compromised
- Can start/stop other containers on the host

**Mitigations:**
1. **Network Isolation**: Use dedicated Docker networks
2. **Read-Only Mounts**: Use read-only volumes where possible
3. **Service-Specific Access**: Only specific plugins use Docker features
4. **Authentication Required**: Enable auth before public deployment

**Recommendations for Production:**
```yaml
# Option 1: Use Docker API with restricted permissions
# Install docker-socket-proxy
services:
  docker-proxy:
    image: tecnativa/docker-socket-proxy
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
    environment:
      CONTAINERS: 1
      EXEC: 1
    networks:
      - plugin-network

  web:
    environment:
      DOCKER_HOST: tcp://docker-proxy:2375
```

```yaml
# Option 2: Use rootless Docker
# Configure Docker daemon to run in rootless mode
# See: https://docs.docker.com/engine/security/rootless/
```

### ⚠️ File Upload Handling

**Current Implementation:**
- Files streamed to temporary directory
- Size limits enforced during upload
- Automatic cleanup of old downloads

**Recommendations:**
1. **Virus Scanning**: Integrate ClamAV or similar for uploaded files
2. **File Type Validation**: Verify file signatures, not just extensions
3. **Sandboxed Processing**: Process uploads in isolated containers
4. **Storage Quotas**: Implement per-user storage limits

### ⚠️ Container-Based Plugins

Plugins like `pdf2html` execute commands in Docker containers.

**Security Measures:**
1. Use official, trusted base images
2. Scan images for vulnerabilities (Trivy, Clair)
3. Run containers with minimal privileges
4. Use read-only file systems where possible

Example secure container configuration:
```yaml
services:
  pdf2htmlex-service:
    image: pdf2htmlex/pdf2htmlex:0.18.8.rc2-master-20200820-ubuntu-20.04-x86_64
    security_opt:
      - no-new-privileges:true
    read_only: true
    tmpfs:
      - /tmp
    cap_drop:
      - ALL
    cap_add:
      - CHOWN
      - DAC_OVERRIDE
```

## Production Deployment Checklist

### 🔒 Before Going Live

- [ ] **Enable Authentication**
  ```bash
  export ENABLE_AUTH=true
  ```

- [ ] **Generate Strong Secret Key**
  ```bash
  export SECRET_KEY=$(openssl rand -hex 32)
  ```

- [ ] **Configure HTTPS**
  - Use reverse proxy (Nginx, Traefik, Caddy)
  - Obtain SSL/TLS certificates (Let's Encrypt)
  - Force HTTPS redirects

- [ ] **Update CORS Settings**
  ```python
  # app/main.py
  app.add_middleware(
      CORSMiddleware,
      allow_origins=["https://yourdomain.com"],  # Restrict to your domain
      allow_credentials=True,
      allow_methods=["GET", "POST", "PUT", "DELETE"],
      allow_headers=["*"],
  )
  ```

- [ ] **Enable Rate Limiting**
  ```bash
  export RATE_LIMIT_ENABLED=true
  export RATE_LIMIT_PER_MINUTE=30  # Adjust as needed
  ```

- [ ] **Configure File Upload Limits**
  ```bash
  export MAX_UPLOAD_SIZE_MB=50  # Adjust based on your needs
  ```

- [ ] **Set Production Environment**
  ```bash
  export FASTAPI_ENV=production
  export DEBUG=false
  ```

- [ ] **Review Docker Permissions**
  - Implement Docker socket proxy or rootless Docker
  - Audit container capabilities
  - Enable AppArmor/SELinux profiles

- [ ] **Database Migration** (Future)
  - Replace file-based storage with PostgreSQL
  - Implement proper user management
  - Add role-based access control (RBAC)

- [ ] **Logging & Monitoring**
  ```bash
  export LOG_FORMAT=json
  export LOG_LEVEL=INFO
  ```
  - Send logs to centralized system (ELK, Splunk, Datadog)
  - Set up alerts for security events
  - Monitor rate limit violations

- [ ] **Backup Strategy**
  - Regular backups of /app/data volume
  - Automated backup testing
  - Disaster recovery plan

## Default Credentials

**⚠️ CRITICAL: Change these immediately in production!**

Default test accounts (defined in `app/core/auth.py`):
```
Username: admin
Password: secret

Username: testuser
Password: secret
```

**To change passwords:**
```python
from app.core.auth import get_password_hash

new_password_hash = get_password_hash("your_secure_password_here")
# Update fake_users_db in app/core/auth.py
```

**Production Recommendation:**
Replace in-memory user database with proper database:
- PostgreSQL with proper schema
- Password policies (minimum length, complexity)
- Account lockout after failed attempts
- Password reset mechanism
- Two-factor authentication (2FA)

## Vulnerability Reporting

If you discover a security vulnerability:

1. **DO NOT** open a public GitHub issue
2. Email security concerns to: [your-security-email]
3. Provide detailed reproduction steps
4. Allow reasonable time for patching before disclosure

## Security Updates

### Dependency Scanning

Run regular dependency audits:
```bash
# Python dependencies
pip install safety
safety check -r requirements.txt

# Node dependencies
npm audit

# Container images
docker scan [image-name]
```

### Update Schedule

- **Critical Security Patches**: Immediately
- **High Priority Updates**: Within 1 week
- **Regular Updates**: Monthly review
- **Dependency Upgrades**: Quarterly

## Additional Resources

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [FastAPI Security Best Practices](https://fastapi.tiangolo.com/tutorial/security/)
- [Docker Security](https://docs.docker.com/engine/security/)
- [CIS Docker Benchmark](https://www.cisecurity.org/benchmark/docker)

## Compliance Considerations

For regulated environments (HIPAA, GDPR, PCI-DSS):

- Implement audit logging for all data access
- Add data encryption at rest and in transit
- Implement data retention policies
- Add user consent management
- Regular security assessments and penetration testing
- Incident response plan

---

**Last Updated**: 2025-01-23
**Version**: 2.0.0
