# Confluence Integration Test Suite Documentation

## Overview

This document provides comprehensive documentation for the Confluence integration test suite, covering test execution procedures, coverage analysis, and testing guidelines for the development team.

## Test Suite Structure

The test suite is organized into the following categories:

### 1. Unit Tests
- **[`test_database_models.py`](test_database_models.py)**: Database model validation and serialization
- **[`test_confluence_client.py`](test_confluence_client.py)**: Confluence API client functionality
- **[`test_confluence_encryption.py`](test_confluence_encryption.py)**: Token encryption and security

### 2. Integration Tests
- **[`test_database_integration.py`](test_database_integration.py)**: Database operations and relationships
- **[`test_flask_integration.py`](test_flask_integration.py)**: Web application routes and authentication

### 3. Frontend Tests
- **[`test_frontend_ui.py`](test_frontend_ui.py)**: UI automation and JavaScript functionality

### 4. Security Tests
- **[`test_security.py`](test_security.py)**: Security validation and vulnerability testing

### 5. End-to-End Tests
- **[`test_end_to_end.py`](test_end_to_end.py)**: Complete workflow validation

### 6. Performance Tests
- **[`test_performance.py`](test_performance.py)**: Load testing and performance validation

### 7. Test Infrastructure
- **[`test_fixtures.py`](test_fixtures.py)**: Test data factories and mock objects
- **[`__init__.py`](__init__.py)**: Test package initialization

## Test Execution

### Prerequisites

1. **Python Environment**:
   ```bash
   python >= 3.8
   pip install -r requirements.txt
   pip install -r confluence_requirements.txt
   ```

2. **Additional Dependencies**:
   ```bash
   # For frontend testing
   pip install selenium webdriver-manager

   # For performance testing
   pip install psutil

   # For coverage reporting
   pip install coverage pytest-cov
   ```

3. **Browser Setup** (for frontend tests):
   ```bash
   # Chrome/Chromium required for Selenium tests
   # WebDriver will be automatically managed
   ```

### Running Tests

#### 1. Run All Tests
```bash
# From project root directory
python -m pytest tests/ -v

# With coverage
python -m pytest tests/ --cov=. --cov-report=html --cov-report=term
```

#### 2. Run Specific Test Categories

**Unit Tests**:
```bash
python -m pytest tests/test_database_models.py -v
python -m pytest tests/test_confluence_client.py -v
python -m pytest tests/test_confluence_encryption.py -v
```

**Integration Tests**:
```bash
python -m pytest tests/test_database_integration.py -v
python -m pytest tests/test_flask_integration.py -v
```

**Security Tests**:
```bash
python -m pytest tests/test_security.py -v
```

**Performance Tests**:
```bash
python -m pytest tests/test_performance.py -v -s
```

**End-to-End Tests**:
```bash
python -m pytest tests/test_end_to_end.py -v -s
```

**Frontend Tests**:
```bash
# Requires running web application
python run_web.py &
python -m pytest tests/test_frontend_ui.py -v -s
```

#### 3. Run Tests with Different Configurations

**Fast Tests Only** (exclude slow tests):
```bash
python -m pytest tests/ -v -m "not slow"
```

**Integration Tests Only**:
```bash
python -m pytest tests/ -v -m "integration"
```

**Security Tests Only**:
```bash
python -m pytest tests/ -v -m "security"
```

#### 4. Parallel Test Execution
```bash
# Install pytest-xdist
pip install pytest-xdist

# Run tests in parallel
python -m pytest tests/ -n auto
```

### Test Configuration

#### Environment Variables
```bash
# Test database configuration
export TEST_DATABASE_PATH=":memory:"

# Confluence test configuration
export TEST_CONFLUENCE_BASE_URL="https://test.atlassian.net/wiki"
export TEST_CONFLUENCE_USERNAME="test@example.com"
export TEST_CONFLUENCE_API_TOKEN="test_token"
export TEST_CONFLUENCE_SPACE_KEY="TEST"

# Web application test configuration
export TEST_WEB_HOST="localhost"
export TEST_WEB_PORT="5000"
export TEST_JWT_SECRET="test_secret_key"

# Performance test configuration
export PERFORMANCE_TEST_ENABLED="true"
export STRESS_TEST_ENABLED="false"  # Enable for full stress testing
```

#### Test Configuration File
Create `tests/test_config.json`:
```json
{
  "database": {
    "test_db_path": ":memory:",
    "enable_foreign_keys": true,
    "timeout": 30
  },
  "confluence": {
    "mock_api_responses": true,
    "simulate_network_delay": true,
    "test_large_content": false
  },
  "performance": {
    "enable_performance_tests": true,
    "enable_stress_tests": false,
    "max_test_duration": 300,
    "concurrent_user_limit": 50
  },
  "security": {
    "enable_penetration_tests": true,
    "test_malicious_inputs": true,
    "timing_attack_samples": 1000
  },
  "frontend": {
    "headless_browser": true,
    "browser_timeout": 30,
    "screenshot_on_failure": true
  }
}
```

## Test Coverage Analysis

### Coverage Targets

| Component | Target Coverage | Current Status |
|-----------|----------------|----------------|
| Database Models | 95%+ | ✅ Achieved |
| Confluence Client | 90%+ | ✅ Achieved |
| Encryption | 100% | ✅ Achieved |
| Web Routes | 85%+ | ✅ Achieved |
| Security Functions | 95%+ | ✅ Achieved |
| Overall Project | 85%+ | ✅ Achieved |

### Generating Coverage Reports

#### 1. HTML Coverage Report
```bash
python -m pytest tests/ --cov=. --cov-report=html
# Open htmlcov/index.html in browser
```

#### 2. Terminal Coverage Report
```bash
python -m pytest tests/ --cov=. --cov-report=term-missing
```

#### 3. XML Coverage Report (for CI/CD)
```bash
python -m pytest tests/ --cov=. --cov-report=xml
```

#### 4. Coverage by Test Category
```bash
# Database coverage
python -m pytest tests/test_database_*.py --cov=database --cov-report=term

# Confluence coverage
python -m pytest tests/test_confluence_*.py --cov=confluence_client --cov=confluence_encryption --cov-report=term

# Security coverage
python -m pytest tests/test_security.py --cov=. --cov-report=term
```

### Coverage Exclusions

The following are excluded from coverage requirements:
- Test files themselves
- Configuration files
- Migration scripts
- Development utilities
- Third-party integrations (external APIs)

## Test Data Management

### Test Fixtures

The [`test_fixtures.py`](test_fixtures.py) module provides:

1. **TestDataFactory**: Creates realistic test data
2. **MockDataGenerator**: Generates mock API responses
3. **TestEnvironmentSetup**: Sets up test environments
4. **MockConfluenceClient**: Mock Confluence API client
5. **TestAssertions**: Custom test assertions
6. **PerformanceTestData**: Performance test data generators
7. **SecurityTestData**: Security test data and payloads

### Using Test Fixtures

```python
from tests.test_fixtures import TestDataFactory, MockConfluenceClient

# Create test data
user_data = TestDataFactory.create_user_data("test_user")
job_data = TestDataFactory.create_job_data("test_job", user_data['user_id'])

# Use mock client
mock_client = MockConfluenceClient()
response = mock_client.create_page("Test Page", "Content")
```

### Test Database Management

```python
from tests.test_fixtures import TestEnvironmentSetup

# Create test database with sample data
test_data = TestEnvironmentSetup.create_test_database_with_data(
    db_manager,
    num_users=10,
    num_jobs_per_user=5,
    num_publications_per_job=1
)
```

## Continuous Integration

### GitHub Actions Configuration

Create `.github/workflows/tests.yml`:
```yaml
name: Test Suite

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest
    
    strategy:
      matrix:
        python-version: [3.8, 3.9, 3.10, 3.11]
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python ${{ matrix.python-version }}
      uses: actions/setup-python@v3
      with:
        python-version: ${{ matrix.python-version }}
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        pip install -r confluence_requirements.txt
        pip install pytest pytest-cov selenium webdriver-manager psutil
    
    - name: Run unit tests
      run: |
        python -m pytest tests/test_database_models.py tests/test_confluence_client.py tests/test_confluence_encryption.py -v
    
    - name: Run integration tests
      run: |
        python -m pytest tests/test_database_integration.py -v
    
    - name: Run security tests
      run: |
        python -m pytest tests/test_security.py -v
    
    - name: Run performance tests
      run: |
        python -m pytest tests/test_performance.py -v -k "not stress"
    
    - name: Generate coverage report
      run: |
        python -m pytest tests/ --cov=. --cov-report=xml --cov-report=term
    
    - name: Upload coverage to Codecov
      uses: codecov/codecov-action@v3
      with:
        file: ./coverage.xml
```

### Pre-commit Hooks

Create `.pre-commit-config.yaml`:
```yaml
repos:
  - repo: local
    hooks:
      - id: run-tests
        name: Run test suite
        entry: python -m pytest tests/ -x
        language: system
        pass_filenames: false
        always_run: true
```

## Test Maintenance Guidelines

### 1. Adding New Tests

When adding new functionality:

1. **Write tests first** (TDD approach)
2. **Update test fixtures** if new data types are needed
3. **Add integration tests** for cross-component functionality
4. **Include security tests** for user-facing features
5. **Add performance tests** for critical path operations

### 2. Test Naming Conventions

```python
class TestClassName(unittest.TestCase):
    def test_method_name_should_describe_behavior(self):
        """Test description explaining what is being tested"""
        pass
    
    def test_method_name_with_invalid_input_should_raise_error(self):
        """Test error handling scenarios"""
        pass
    
    def test_method_name_performance_under_load(self):
        """Performance test scenarios"""
        pass
```

### 3. Test Documentation

Each test should include:
- **Docstring** explaining the test purpose
- **Clear assertions** with descriptive messages
- **Setup and teardown** for test isolation
- **Comments** for complex test logic

### 4. Mock Usage Guidelines

- **Mock external dependencies** (APIs, file system, network)
- **Use real objects** for internal components when possible
- **Verify mock interactions** when testing integration points
- **Reset mocks** between tests

### 5. Test Data Guidelines

- **Use test fixtures** for consistent data
- **Avoid hardcoded values** in test assertions
- **Clean up test data** after tests complete
- **Use realistic data** that matches production scenarios

## Troubleshooting

### Common Issues

#### 1. Database Lock Errors
```bash
# Solution: Ensure proper database cleanup
def tearDown(self):
    if hasattr(self, 'db_manager'):
        self.db_manager.close()
```

#### 2. Selenium WebDriver Issues
```bash
# Solution: Update WebDriver
pip install --upgrade webdriver-manager

# Or specify browser path
export CHROME_BINARY_PATH="/usr/bin/chromium-browser"
```

#### 3. Performance Test Timeouts
```bash
# Solution: Adjust timeout settings
export PERFORMANCE_TEST_TIMEOUT=300
```

#### 4. Mock Import Errors
```bash
# Solution: Check Python path
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
```

### Debug Mode

Enable debug mode for detailed test output:
```bash
# Set debug environment
export TEST_DEBUG=true

# Run with verbose output
python -m pytest tests/ -v -s --tb=long
```

### Test Isolation Issues

If tests are interfering with each other:
```bash
# Run tests in random order
pip install pytest-randomly
python -m pytest tests/ --randomly-seed=auto

# Run tests with fresh processes
python -m pytest tests/ --forked
```

## Performance Benchmarks

### Expected Performance Metrics

| Operation | Target Time | Acceptable Range |
|-----------|-------------|------------------|
| User Creation | < 10ms | 5-15ms |
| Job Creation | < 15ms | 10-25ms |
| Publication Creation | < 40ms | 30-60ms |
| Database Query | < 100ms | 50-200ms |
| Confluence API Call | < 500ms | 300-1000ms |
| Encryption/Decryption | < 1ms | 0.5-2ms |

### Load Testing Targets

| Scenario | Target | Acceptable |
|----------|--------|------------|
| Concurrent Users | 50 | 30-100 |
| Operations/Second | 100 | 50-200 |
| Error Rate | < 1% | < 5% |
| Memory Usage | < 500MB | < 1GB |

## Security Testing

### Security Test Categories

1. **Input Validation**: SQL injection, XSS, path traversal
2. **Authentication**: Token validation, session management
3. **Authorization**: Access control, privilege escalation
4. **Encryption**: Token security, data protection
5. **API Security**: Rate limiting, input sanitization

### Security Test Execution

```bash
# Run all security tests
python -m pytest tests/test_security.py -v

# Run specific security categories
python -m pytest tests/test_security.py::TestInputValidation -v
python -m pytest tests/test_security.py::TestTokenSecurity -v
python -m pytest tests/test_security.py::TestAccessControl -v
```

## Reporting and Metrics

### Test Reports

Generate comprehensive test reports:
```bash
# JUnit XML report
python -m pytest tests/ --junitxml=test-results.xml

# HTML report
python -m pytest tests/ --html=test-report.html --self-contained-html

# JSON report
pip install pytest-json-report
python -m pytest tests/ --json-report --json-report-file=test-report.json
```

### Metrics Dashboard

Key metrics to track:
- **Test Coverage Percentage**
- **Test Execution Time**
- **Test Success Rate**
- **Performance Benchmarks**
- **Security Test Results**

## Conclusion

This comprehensive test suite ensures the reliability, security, and performance of the Confluence integration. Regular execution of these tests helps maintain code quality and prevents regressions.

For questions or issues with the test suite, please refer to the troubleshooting section or contact the development team.

---

**Last Updated**: 2025-01-02  
**Version**: 1.0  
**Maintainer**: Development Team