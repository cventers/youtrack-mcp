# LLM Security Best Practices Guide

## Overview

This guide outlines comprehensive security best practices for the LLM integration in the YouTrack MCP server. Security is paramount when handling AI requests, API keys, and user data to prevent unauthorized access, data breaches, and abuse of AI services.

## API Key Management

### Secure Key Storage

```python
class SecureKeyManager:
    def __init__(self):
        self.key_store = {}  # In production, use encrypted key vault
        self.key_rotation_scheduler = None

    async def store_api_key(self, provider: str, key: str):
        """Store API key securely with encryption."""
        encrypted_key = await self._encrypt_key(key)
        self.key_store[provider] = {
            'encrypted_key': encrypted_key,
            'created_at': datetime.now(),
            'last_used': None,
            'usage_count': 0
        }

    async def retrieve_api_key(self, provider: str) -> str:
        """Retrieve and decrypt API key."""
        if provider not in self.key_store:
            raise ValueError(f"No key found for provider: {provider}")

        encrypted_key = self.key_store[provider]['encrypted_key']
        decrypted_key = await self._decrypt_key(encrypted_key)

        # Update usage tracking
        self.key_store[provider]['last_used'] = datetime.now()
        self.key_store[provider]['usage_count'] += 1

        return decrypted_key
```

### Key Rotation Strategy

```python
class KeyRotationManager:
    def __init__(self, rotation_interval_days: int = 30):
        self.rotation_interval = timedelta(days=rotation_interval_days)
        self.rotation_queue = []

    async def schedule_key_rotation(self, provider: str):
        """Schedule automatic key rotation."""
        rotation_time = datetime.now() + self.rotation_interval
        self.rotation_queue.append({
            'provider': provider,
            'scheduled_time': rotation_time,
            'status': 'pending'
        })

    async def rotate_key(self, provider: str, new_key: str):
        """Perform key rotation with zero downtime."""
        # 1. Validate new key
        await self._validate_new_key(provider, new_key)

        # 2. Store new key
        await self.key_manager.store_api_key(provider, new_key)

        # 3. Update configuration
        await self._update_configuration(provider, new_key)

        # 4. Test new key
        await self._test_new_key(provider)

        # 5. Remove old key
        await self._cleanup_old_key(provider)

        logger.info(f"Successfully rotated key for provider: {provider}")
```

### Environment Variable Security

```bash
# Secure environment variable setup
export YOUTRACK_AI_PROVIDER="openai"
export OPENAI_API_KEY="$(aws secretsmanager get-secret-value --secret-id openai-key --query SecretString --output text)"
export ANTHROPIC_API_KEY="$(gcloud secrets versions access latest --secret=anthropic-key)"

# Never expose keys in logs or error messages
# Use key references instead
logger.info(f"Using API key for provider: {provider} (key_id: {key_id})")
```

## Input Validation and Sanitization

### Request Validation

```python
class InputValidator:
    def __init__(self):
        self.max_prompt_length = 10000
        self.allowed_characters = set(string.ascii_letters + string.digits + string.punctuation + " \n\t")
        self.suspicious_patterns = [
            r'<script[^>]*>.*?</script>',
            r'javascript:',
            r'on\w+\s*=',
            r'<iframe[^>]*>.*?</iframe>',
            r'<object[^>]*>.*?</object>'
        ]

    async def validate_request(self, request: LLMRequest) -> ValidationResult:
        """Comprehensive request validation."""
        result = ValidationResult()

        # Length validation
        if len(request.prompt) > self.max_prompt_length:
            result.add_error("Prompt exceeds maximum length")

        # Character validation
        if not all(c in self.allowed_characters for c in request.prompt):
            result.add_error("Prompt contains invalid characters")

        # Pattern validation
        for pattern in self.suspicious_patterns:
            if re.search(pattern, request.prompt, re.IGNORECASE):
                result.add_error(f"Suspicious pattern detected: {pattern}")

        # Content type validation
        if not self._validate_content_type(request.prompt):
            result.add_error("Invalid content type")

        # Rate limiting check
        if not await self._check_rate_limits(request.user_id):
            result.add_error("Rate limit exceeded")

        return result
```

### Content Sanitization

```python
class ContentSanitizer:
    def __init__(self):
        self.html_sanitizer = None  # Initialize with appropriate sanitizer

    async def sanitize_input(self, content: str) -> str:
        """Sanitize user input to prevent injection attacks."""
        # Remove HTML tags
        content = re.sub(r'<[^>]+>', '', content)

        # Remove script tags and JavaScript
        content = re.sub(r'<script[^>]*>.*?</script>', '', content, flags=re.DOTALL | re.IGNORECASE)

        # Remove event handlers
        content = re.sub(r'on\w+\s*=', '', content, flags=re.IGNORECASE)

        # Remove data URLs
        content = re.sub(r'data:[^;]+;base64,[^\'"]*', '[DATA_URL_REMOVED]', content)

        # Limit consecutive whitespace
        content = re.sub(r'\s{3,}', ' ', content)

        # Remove null bytes
        content = content.replace('\x00', '')

        return content.strip()
```

### Output Validation

```python
class OutputValidator:
    def __init__(self):
        self.max_response_length = 50000
        self.allowed_response_types = ['text', 'json', 'markdown']

    async def validate_response(self, response: LLMResponse) -> bool:
        """Validate LLM response for safety."""
        # Length validation
        if len(response.content) > self.max_response_length:
            return False

        # Content type validation
        if response.content_type not in self.allowed_response_types:
            return False

        # Check for malicious content
        if self._contains_malicious_content(response.content):
            return False

        # Validate JSON structure if applicable
        if response.content_type == 'json':
            try:
                json.loads(response.content)
            except json.JSONDecodeError:
                return False

        return True
```

## Rate Limiting and Abuse Prevention

### Multi-Layer Rate Limiting

```python
class AdvancedRateLimiter:
    def __init__(self):
        self.user_limits = {}
        self.ip_limits = {}
        self.endpoint_limits = {}
        self.global_limits = TokenBucketLimiter(rate=1000, capacity=2000)

    async def check_request(self, request: LLMRequest) -> RateLimitResult:
        """Comprehensive rate limiting check."""
        user_id = request.user_id
        ip_address = request.ip_address
        endpoint = request.endpoint

        # User-based limiting
        if not await self._check_user_limit(user_id):
            return RateLimitResult(allowed=False, reason="User rate limit exceeded")

        # IP-based limiting
        if not await self._check_ip_limit(ip_address):
            return RateLimitResult(allowed=False, reason="IP rate limit exceeded")

        # Endpoint-based limiting
        if not await self._check_endpoint_limit(endpoint):
            return RateLimitResult(allowed=False, reason="Endpoint rate limit exceeded")

        # Global limiting
        if not await self.global_limits.check('global'):
            return RateLimitResult(allowed=False, reason="Global rate limit exceeded")

        return RateLimitResult(allowed=True)
```

### Abuse Detection

```python
class AbuseDetector:
    def __init__(self):
        self.suspicious_patterns = [
            r'repeat.{0,20}prompt',  # Prompt repetition
            r'\\x[0-9a-f]{2}',      # Hex encoding
            r'%[0-9a-f]{2}',        # URL encoding
            r'\\u[0-9a-f]{4}',      # Unicode encoding
        ]
        self.abuse_scores = {}

    async def analyze_request(self, request: LLMRequest) -> AbuseScore:
        """Analyze request for potential abuse."""
        score = 0

        # Pattern matching
        for pattern in self.suspicious_patterns:
            if re.search(pattern, request.prompt, re.IGNORECASE):
                score += 10

        # Length anomalies
        if len(request.prompt) > 5000:
            score += 5

        # Request frequency
        recent_requests = await self._get_recent_requests(request.user_id)
        if len(recent_requests) > 10:
            score += 5

        # Content analysis
        if self._contains_sensitive_keywords(request.prompt):
            score += 15

        return AbuseScore(score=score, risk_level=self._calculate_risk_level(score))
```

## Data Privacy

### Data Minimization

```python
class DataMinimizer:
    def __init__(self):
        self.retention_policies = {
            'request_logs': timedelta(days=30),
            'error_logs': timedelta(days=90),
            'audit_logs': timedelta(days=365)
        }

    async def minimize_request_data(self, request: LLMRequest) -> MinimalRequest:
        """Remove unnecessary data from requests."""
        minimal = MinimalRequest()

        # Keep only essential fields
        minimal.user_id = self._anonymize_user_id(request.user_id)
        minimal.prompt_hash = self._hash_prompt(request.prompt)
        minimal.endpoint = request.endpoint
        minimal.timestamp = request.timestamp

        # Remove sensitive data
        minimal.prompt = None  # Don't store actual prompts
        minimal.context = None  # Don't store context unless necessary

        return minimal
```

### Data Encryption

```python
class DataEncryptor:
    def __init__(self, encryption_key: str):
        self.key = encryption_key
        self.cipher = AES.new(self.key.encode(), AES.MODE_GCM)

    async def encrypt_sensitive_data(self, data: str) -> EncryptedData:
        """Encrypt sensitive data before storage."""
        nonce = os.urandom(12)
        cipher = AES.new(self.key.encode(), AES.MODE_GCM, nonce=nonce)

        ciphertext, tag = cipher.encrypt_and_digest(data.encode())

        return EncryptedData(
            ciphertext=ciphertext,
            nonce=nonce,
            tag=tag
        )

    async def decrypt_sensitive_data(self, encrypted: EncryptedData) -> str:
        """Decrypt sensitive data for processing."""
        cipher = AES.new(self.key.encode(), AES.MODE_GCM, nonce=encrypted.nonce)

        plaintext = cipher.decrypt_and_verify(encrypted.ciphertext, encrypted.tag)

        return plaintext.decode()
```

## Secure Communication

### TLS Configuration

```python
class SecureHTTPClient:
    def __init__(self):
        self.ssl_context = ssl.create_default_context()
        self.ssl_context.check_hostname = True
        self.ssl_context.verify_mode = ssl.CERT_REQUIRED

        # Configure cipher suites
        self.ssl_context.set_ciphers(
            'ECDHE+AESGCM:ECDHE+CHACHA20:DHE+AESGCM:DHE+CHACHA20'
        )

        # Certificate pinning (optional)
        self.ssl_context.load_verify_locations(cafile='/path/to/ca-bundle.crt')

    async def make_secure_request(self, url: str, **kwargs) -> httpx.Response:
        """Make secure HTTP request with proper TLS configuration."""
        async with httpx.AsyncClient(
            verify=self.ssl_context,
            timeout=httpx.Timeout(30.0),
            follow_redirects=False
        ) as client:
            response = await client.request(
                method=kwargs.get('method', 'GET'),
                url=url,
                headers=self._get_secure_headers(),
                **kwargs
            )

            # Validate response
            await self._validate_response(response)

            return response
```

### API Endpoint Security

```python
class EndpointSecurity:
    def __init__(self):
        self.allowed_domains = [
            'api.openai.com',
            'api.anthropic.com',
            'api.groq.com'
        ]
        self.required_headers = [
            'Authorization',
            'Content-Type',
            'User-Agent'
        ]

    async def validate_endpoint(self, url: str) -> bool:
        """Validate API endpoint for security."""
        parsed = urlparse(url)

        # Domain validation
        if parsed.netloc not in self.allowed_domains:
            return False

        # HTTPS requirement
        if parsed.scheme != 'https':
            return False

        # Path validation
        if not self._is_safe_path(parsed.path):
            return False

        return True
```

## Logging and Monitoring

### Secure Logging

```python
class SecureLogger:
    def __init__(self):
        self.logger = logging.getLogger('llm_security')
        self.logger.setLevel(logging.INFO)

        # Use secure formatter
        formatter = SecureFormatter()
        handler = logging.StreamHandler()
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)

    async def log_request(self, request: LLMRequest, user_id: str):
        """Log requests without exposing sensitive data."""
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'user_id': self._anonymize_user_id(user_id),
            'endpoint': request.endpoint,
            'prompt_length': len(request.prompt),
            'prompt_hash': self._hash_prompt(request.prompt),
            'ip_address': self._anonymize_ip(request.ip_address),
            'user_agent': request.user_agent
        }

        self.logger.info("LLM request processed", extra=log_entry)

    def _anonymize_user_id(self, user_id: str) -> str:
        """Anonymize user ID for privacy."""
        return hashlib.sha256(user_id.encode()).hexdigest()[:16]

    def _hash_prompt(self, prompt: str) -> str:
        """Hash prompt for logging without storing content."""
        return hashlib.sha256(prompt.encode()).hexdigest()
```

### Security Monitoring

```python
class SecurityMonitor:
    def __init__(self):
        self.alerts = []
        self.thresholds = {
            'failed_auth_attempts': 5,
            'suspicious_requests': 10,
            'rate_limit_hits': 20
        }

    async def monitor_security_events(self):
        """Monitor for security events and trigger alerts."""
        while True:
            events = await self._collect_security_events()

            for event in events:
                if self._is_security_threat(event):
                    await self._trigger_alert(event)

            await asyncio.sleep(60)  # Check every minute

    async def _trigger_alert(self, event: SecurityEvent):
        """Trigger security alert."""
        alert = SecurityAlert(
            event_type=event.type,
            severity=self._calculate_severity(event),
            description=self._generate_alert_description(event),
            timestamp=datetime.now()
        )

        self.alerts.append(alert)

        # Send alert to security team
        await self._send_alert_notification(alert)
```

## Compliance and Auditing

### Audit Logging

```python
class AuditLogger:
    def __init__(self):
        self.audit_log = []
        self.compliance_frameworks = ['GDPR', 'CCPA', 'SOC2']

    async def log_audit_event(self, event: AuditEvent):
        """Log audit event for compliance."""
        audit_entry = {
            'event_id': str(uuid.uuid4()),
            'timestamp': datetime.now().isoformat(),
            'event_type': event.type,
            'user_id': event.user_id,
            'action': event.action,
            'resource': event.resource,
            'ip_address': event.ip_address,
            'user_agent': event.user_agent,
            'compliance_tags': self._get_compliance_tags(event)
        }

        self.audit_log.append(audit_entry)

        # Write to immutable audit log
        await self._write_to_audit_log(audit_entry)

    def _get_compliance_tags(self, event: AuditEvent) -> List[str]:
        """Get compliance tags for the event."""
        tags = []

        if event.action in ['data_access', 'data_export']:
            tags.extend(['GDPR', 'CCPA'])

        if event.resource == 'api_key':
            tags.append('SOC2')

        return tags
```

### Compliance Checks

```python
class ComplianceChecker:
    def __init__(self):
        self.compliance_rules = {
            'GDPR': self._check_gdpr_compliance,
            'CCPA': self._check_ccpa_compliance,
            'SOC2': self._check_soc2_compliance
        }

    async def check_compliance(self, operation: str, data: Dict) -> ComplianceResult:
        """Check operation compliance with relevant frameworks."""
        results = {}

        for framework, checker in self.compliance_rules.items():
            results[framework] = await checker(operation, data)

        return ComplianceResult(
            compliant=all(results.values()),
            framework_results=results
        )

    async def _check_gdpr_compliance(self, operation: str, data: Dict) -> bool:
        """Check GDPR compliance for operation."""
        # GDPR-specific checks
        if operation == 'data_processing':
            return self._has_data_subject_consent(data)

        if operation == 'data_transfer':
            return self._is_adequate_protection(data)

        return True
```

## Incident Response

### Incident Detection

```python
class IncidentDetector:
    def __init__(self):
        self.incident_patterns = [
            r'multiple.*failed.*auth',
            r'unusual.*traffic.*pattern',
            r'suspicious.*api.*call',
            r'potential.*data.*breach'
        ]

    async def detect_incidents(self, events: List[SecurityEvent]) -> List[Incident]:
        """Detect security incidents from events."""
        incidents = []

        for event in events:
            if self._matches_incident_pattern(event):
                incident = Incident(
                    id=str(uuid.uuid4()),
                    type=self._classify_incident(event),
                    severity=self._calculate_severity(event),
                    description=self._generate_description(event),
                    affected_resources=self._identify_resources(event),
                    timestamp=datetime.now()
                )
                incidents.append(incident)

        return incidents
```

### Incident Response Plan

```python
class IncidentResponsePlan:
    def __init__(self):
        self.response_actions = {
            'api_key_compromise': self._handle_api_key_compromise,
            'data_breach': self._handle_data_breach,
            'unauthorized_access': self._handle_unauthorized_access,
            'dos_attack': self._handle_dos_attack
        }

    async def execute_response(self, incident: Incident):
        """Execute incident response plan."""
        if incident.type in self.response_actions:
            await self.response_actions[incident.type](incident)

        # Always perform these actions
        await self._isolate_affected_systems(incident)
        await self._notify_security_team(incident)
        await self._preserve_evidence(incident)
        await self._document_incident(incident)
```

## Security Best Practices Implementation

### Configuration Security

```python
# Secure configuration template
security_config = {
    'api_keys': {
        'encryption_enabled': True,
        'rotation_interval_days': 30,
        'key_vault_provider': 'aws_secrets_manager'
    },
    'input_validation': {
        'max_prompt_length': 10000,
        'sanitize_html': True,
        'detect_injection': True
    },
    'rate_limiting': {
        'user_limit_per_minute': 10,
        'ip_limit_per_minute': 100,
        'global_limit_per_minute': 1000
    },
    'logging': {
        'anonymize_user_data': True,
        'log_security_events': True,
        'retention_days': 90
    },
    'monitoring': {
        'alert_on_suspicious_activity': True,
        'real_time_threat_detection': True,
        'automated_response': False  # Manual review required
    }
}
```

### Security Headers

```python
def get_security_headers(self) -> Dict[str, str]:
    """Get security headers for HTTP requests."""
    return {
        'X-Content-Type-Options': 'nosniff',
        'X-Frame-Options': 'DENY',
        'X-XSS-Protection': '1; mode=block',
        'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
        'Content-Security-Policy': "default-src 'self'",
        'Referrer-Policy': 'strict-origin-when-cross-origin',
        'Permissions-Policy': 'geolocation=(), microphone=(), camera=()'
    }
```

### Regular Security Audits

```python
class SecurityAuditor:
    def __init__(self):
        self.audit_schedule = {
            'daily': self._daily_security_check,
            'weekly': self._weekly_security_audit,
            'monthly': self._monthly_compliance_review
        }

    async def run_scheduled_audits(self):
        """Run scheduled security audits."""
        while True:
            current_time = datetime.now()

            for frequency, audit_func in self.audit_schedule.items():
                if self._should_run_audit(frequency, current_time):
                    await audit_func()

            await asyncio.sleep(3600)  # Check every hour

    async def _daily_security_check(self):
        """Perform daily security checks."""
        checks = [
            self._check_api_key_expiration(),
            self._check_failed_auth_attempts(),
            self._check_suspicious_activity(),
            self._check_system_integrity()
        ]

        results = await asyncio.gather(*checks)
        await self._report_daily_findings(results)
```

This comprehensive security guide provides the foundation for implementing robust security measures in LLM integrations. Regular security audits, monitoring, and updates are essential for maintaining a secure AI system.