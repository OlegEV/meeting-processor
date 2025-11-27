# Confluence Integration Documentation

## Overview

This document describes the comprehensive Confluence integration for the Meeting Processor application. The integration allows automatic publication of meeting protocols to Confluence Server/Cloud with secure token management, content conversion, and robust error handling.

## Architecture Components

### 1. Database Layer
- **Migration**: `database/migrations/003_confluence_integration.sql`
- **Models**: `database/models.py` (ConfluencePublication class)
- **Database Manager**: Extended `database/db_manager.py` with Confluence methods

### 2. API Client Layer
- **Main Client**: `confluence_client.py`
  - `ConfluenceServerClient` - REST API communication
  - `ConfluencePublicationService` - High-level publication operations
  - `ConfluenceContentProcessor` - Markdown to Confluence conversion

### 3. Security Layer
- **Encryption**: `confluence_encryption.py`
  - `ConfluenceTokenManager` - Secure PAT storage
  - `ConfluenceTokenCLI` - Command-line token management

### 4. Configuration
- **Settings**: Updated `config.json` with Confluence section
- **Requirements**: `confluence_requirements.txt`

## Features

### Core Functionality
- ✅ **Automatic Publication**: Convert and publish meeting protocols to Confluence
- ✅ **Content Conversion**: Markdown to Confluence Storage Format
- ✅ **Secure Authentication**: Encrypted Personal Access Token storage
- ✅ **Error Handling**: Comprehensive exception hierarchy with retry logic
- ✅ **Publication Tracking**: Database tracking of all publications
- ✅ **Title Generation**: Automatic page titles in format "YYYYMMDD - Topic"

### Advanced Features
- ✅ **Retry Mechanism**: Automatic retry for failed publications
- ✅ **Space Management**: Support for multiple Confluence spaces
- ✅ **Page Hierarchy**: Parent-child page relationships
- ✅ **Statistics**: Publication analytics and reporting
- ✅ **CLI Tools**: Command-line utilities for token management

## Installation and Setup

### 1. Install Dependencies
```bash
pip install -r confluence_requirements.txt
```

### 2. Database Migration
Run the migration to create the confluence_publications table:
```sql
-- Execute database/migrations/003_confluence_integration.sql
```

### 3. Configuration
Update `config.json` with your Confluence settings:
```json
{
  "confluence": {
    "enabled": true,
    "base_url": "https://your-domain.atlassian.net/wiki",
    "username": "your-email@domain.com",
    "space_key": "MEETINGS",
    "parent_page_id": null,
    "auto_publish": false
  }
}
```

### 4. Token Management
Add your Confluence API token securely:
```bash
python confluence_encryption.py add
```

## Usage Examples

### Basic Publication
```python
from confluence_client import create_confluence_publication_service
from database.db_manager import DatabaseManager

# Initialize components
config = load_config()
db_manager = DatabaseManager(config['database'])
publication_service = create_confluence_publication_service(config, db_manager)

# Publish a meeting protocol
protocol_content = """# Meeting Protocol
Date: 2025-09-02
Topic: Confluence Integration

## Participants
- John Doe
- Jane Smith

## Decisions
- Implement Confluence integration
- Test all components
"""

publication = publication_service.publish_meeting_protocol(
    job_id="job_123",
    protocol_content=protocol_content,
    filename="meeting_20250902.md"
)

print(f"Published to: {publication.confluence_page_url}")
```

### Token Management
```python
from confluence_encryption import create_token_manager

# Create token manager
token_manager = create_token_manager()

# Save encrypted token
token_manager.save_encrypted_token(
    token="your_api_token",
    password="encryption_password",
    confluence_url="https://your-domain.atlassian.net/wiki",
    username="your-email@domain.com"
)

# Load token for use
decrypted_token = token_manager.load_encrypted_token(
    password="encryption_password",
    confluence_url="https://your-domain.atlassian.net/wiki",
    username="your-email@domain.com"
)
```

### Content Processing
```python
from confluence_client import ConfluenceContentProcessor

processor = ConfluenceContentProcessor()

# Convert Markdown to Confluence Storage Format
markdown_content = "# Title\n\n**Bold text** and *italic text*"
confluence_content = processor.markdown_to_confluence(markdown_content)

# Extract meeting information
date, topic = processor.extract_meeting_info(markdown_content)

# Generate page title
title = processor.generate_page_title(date, topic)
```

## API Reference

### ConfluenceServerClient

#### Methods
- `test_connection()` - Test Confluence connectivity
- `create_page(title, content, parent_page_id)` - Create new page
- `update_page(page_id, title, content, version)` - Update existing page
- `get_page_info(page_id)` - Get page information
- `search_pages(query, space_key)` - Search pages

### ConfluencePublicationService

#### Methods
- `publish_meeting_protocol(job_id, content, filename)` - Publish protocol
- `retry_failed_publication(publication_id)` - Retry failed publication
- `get_job_publications(job_id)` - Get publications for job
- `delete_publication(publication_id)` - Delete publication

### ConfluenceTokenManager

#### Methods
- `save_encrypted_token(token, password, url, username)` - Save token
- `load_encrypted_token(password, url, username)` - Load token
- `delete_token(url, username)` - Delete token
- `list_saved_tokens()` - List all tokens

## Database Schema

### confluence_publications Table
```sql
CREATE TABLE confluence_publications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id TEXT NOT NULL,
    confluence_page_id TEXT NOT NULL,
    confluence_page_url TEXT NOT NULL,
    confluence_space_key TEXT NOT NULL,
    parent_page_id TEXT,
    page_title TEXT NOT NULL,
    publication_status TEXT NOT NULL DEFAULT 'published',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    last_retry_at TIMESTAMP,
    FOREIGN KEY (job_id) REFERENCES jobs (job_id) ON DELETE CASCADE
);
```

## Configuration Reference

### Complete Confluence Configuration
```json
{
  "confluence": {
    "enabled": false,
    "base_url": "https://your-domain.atlassian.net/wiki",
    "username": "your-email@domain.com",
    "api_token": "",
    "encrypted_token": "",
    "encryption_key": "",
    "space_key": "MEETINGS",
    "parent_page_id": null,
    "auto_publish": false,
    "timeout": 30,
    "max_retries": 3,
    "retry_delay": 1.0,
    "page_title_format": "YYYYMMDD - {topic}",
    "content_format": "storage",
    "include_metadata": true,
    "notification_settings": {
      "notify_on_publish": false,
      "notify_on_error": true,
      "notification_recipients": []
    },
    "advanced_settings": {
      "use_page_hierarchy": true,
      "create_index_page": false,
      "archive_old_pages": false,
      "archive_after_days": 90,
      "page_labels": ["meeting-protocol", "auto-generated"],
      "content_macros": {
        "add_toc": true,
        "add_date_macro": true,
        "add_info_panel": false
      }
    }
  }
}
```

## Error Handling

### Exception Hierarchy
- `ConfluenceError` - Base exception
- `ConfluenceAuthenticationError` - Authentication issues
- `ConfluencePermissionError` - Permission denied
- `ConfluenceNotFoundError` - Resource not found
- `ConfluenceValidationError` - Data validation errors
- `ConfluenceNetworkError` - Network connectivity issues

### Retry Logic
The system implements automatic retry for transient failures:
- Maximum retries: 3 (configurable)
- Retry delay: 1.0 seconds (configurable)
- Exponential backoff for network errors

## Security Considerations

### Token Storage
- Tokens are encrypted using Fernet (AES 128)
- PBKDF2-SHA256 key derivation with 100,000 iterations
- Unique salt per token
- File permissions restricted to owner only (Unix systems)

### Best Practices
1. Use strong passwords for token encryption
2. Regularly rotate API tokens
3. Limit Confluence permissions to minimum required
4. Monitor publication logs for suspicious activity
5. Use HTTPS for all Confluence communications

## Testing

### Run Integration Tests
```bash
python test_confluence_integration.py
```

### Test Components
- ✅ Database models and operations
- ✅ Content processing and conversion
- ✅ Token encryption and decryption
- ✅ Configuration validation
- ✅ Client creation and setup

## Troubleshooting

### Common Issues

#### Authentication Errors
```
ConfluenceAuthenticationError: Ошибка аутентификации
```
**Solution**: Check API token validity and user permissions

#### Permission Errors
```
ConfluencePermissionError: Недостаточно прав доступа
```
**Solution**: Verify user has write permissions to the target space

#### Network Errors
```
ConfluenceNetworkError: Ошибка сети
```
**Solution**: Check network connectivity and Confluence URL

#### Validation Errors
```
ConfluenceValidationError: Некорректный формат base_url
```
**Solution**: Verify configuration format and required fields

### Debug Mode
Enable debug logging for detailed troubleshooting:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Performance Considerations

### Optimization Tips
1. **Batch Operations**: Group multiple publications when possible
2. **Content Caching**: Cache converted content for repeated publications
3. **Connection Pooling**: Reuse HTTP connections for multiple requests
4. **Async Processing**: Consider async publication for large volumes

### Monitoring
- Track publication success rates
- Monitor API response times
- Set up alerts for failed publications
- Regular cleanup of old publication records

## Integration with Flask Application

### Web Interface Integration
The Confluence integration is designed to work seamlessly with the existing Flask web interface:

1. **Job Processing**: Automatic publication after successful protocol generation
2. **User Interface**: Add Confluence publication status to job details
3. **Manual Retry**: Allow users to retry failed publications
4. **Settings Page**: Confluence configuration management

### Example Flask Route
```python
@app.route('/api/jobs/<job_id>/publish-confluence', methods=['POST'])
def publish_to_confluence(job_id):
    try:
        job = db_manager.get_job_by_id(job_id)
        if not job or not job.get('summary_file'):
            return jsonify({'error': 'Job or protocol not found'}), 404
        
        with open(job['summary_file'], 'r', encoding='utf-8') as f:
            content = f.read()
        
        publication = publication_service.publish_meeting_protocol(
            job_id=job_id,
            protocol_content=content,
            filename=job.get('filename')
        )
        
        return jsonify({
            'success': True,
            'publication_id': publication.id,
            'page_url': publication.confluence_page_url
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
```

## Future Enhancements

### Planned Features
- [ ] **Bulk Publication**: Publish multiple protocols at once
- [ ] **Template System**: Custom Confluence page templates
- [ ] **Webhook Integration**: Real-time notifications
- [ ] **Advanced Search**: Full-text search in published protocols
- [ ] **Version Control**: Track page version history
- [ ] **Multi-Space Support**: Publish to different spaces based on content
- [ ] **Approval Workflow**: Review before publication
- [ ] **Analytics Dashboard**: Publication metrics and insights

### API Extensions
- [ ] **REST API**: Full REST API for external integrations
- [ ] **GraphQL**: GraphQL interface for flexible queries
- [ ] **Webhooks**: Outbound webhooks for publication events

## Support and Maintenance

### Logging
All operations are logged with appropriate levels:
- `INFO`: Successful operations
- `WARNING`: Recoverable issues
- `ERROR`: Failed operations
- `DEBUG`: Detailed debugging information

### Monitoring Endpoints
Consider implementing health check endpoints:
- `/health/confluence` - Test Confluence connectivity
- `/metrics/confluence` - Publication statistics
- `/status/confluence` - Service status

### Backup and Recovery
- Regular backup of confluence_publications table
- Export/import functionality for publication data
- Disaster recovery procedures

---

## Conclusion

The Confluence integration provides a robust, secure, and scalable solution for automatically publishing meeting protocols to Confluence. With comprehensive error handling, secure token management, and extensive configuration options, it's ready for production use in enterprise environments.

For additional support or feature requests, please refer to the project documentation or contact the development team.