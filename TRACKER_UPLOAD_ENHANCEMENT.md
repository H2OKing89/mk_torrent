# 🚀 Future Enhancement: Direct Tracker Upload Integration

## 🎯 **Implementation Strategy**

### **Phase 1: Foundation (Current - Ready)**
- ✅ **Secure Credential Storage**: AES-256 encrypted passwords and passkeys
- ✅ **qBittorrent API Integration**: Direct torrent creation via API
- ✅ **Configuration System**: Extensible config for upload settings

### **Phase 2: Core Upload System (Next Implementation)**

#### **2.1 Enhanced Directory Structure**
```
~/torrents/           # Current: User-accessible torrents
~/torrent_uploads/    # NEW: Upload queue for automation
├── pending/         # Torrents waiting for upload
├── uploaded/        # Successfully uploaded torrents
├── failed/         # Failed uploads (for retry)
└── metadata/        # JSON metadata for each torrent
```

#### **2.2 Upload Manager Architecture**
```python
class UploadManager:
    def __init__(self):
        self.trackers = {
            'redacted': RedactedUploader(),
            'orpheus': OrpheusUploader(),
            'btn': BTNUploader(),
            # Extensible for new trackers
        }

    def upload_torrent(self, torrent_path, metadata):
        """Upload to all configured trackers"""
        results = {}
        for tracker_name, uploader in self.trackers.items():
            if tracker_name in self.config['upload_trackers']:
                results[tracker_name] = uploader.upload(torrent_path, metadata)
        return results
```

#### **2.3 Torrent Retrieval Strategy**

**Option A: Hybrid Approach (Recommended)**
```python
# 1. Save locally for user access
torrent_path = save_torrent_locally(torrent_bytes, output_dir)

# 2. Queue for upload (if auto-upload enabled)
if config['auto_upload_to_trackers']:
    queue_for_upload(torrent_path, metadata)

# 3. Upload in background or on-demand
upload_manager.upload_queued_torrents()
```

**Option B: API-Only (Future when qBittorrent supports export)**
```python
# Direct from qBittorrent (when API supports it)
torrent_bytes = qbittorrent_api.export_torrent(torrent_hash)
upload_manager.upload_bytes(torrent_bytes, metadata)
```

### **Phase 3: Tracker-Specific Implementations**

#### **3.1 RED (Redacted) Integration**
```python
class RedactedUploader:
    def upload(self, torrent_path, metadata):
        api_url = "https://redacted.sh/ajax.php?action=upload"
        headers = {"Authorization": self.get_api_key()}

        with open(torrent_path, 'rb') as f:
            response = requests.post(api_url, headers=headers,
                                   files={'file_input': f},
                                   data=self.format_metadata(metadata))
        return self.parse_response(response)
```

#### **3.2 OPS (Orpheus) Integration**
```python
class OrpheusUploader:
    def upload(self, torrent_path, metadata):
        # Similar structure but OPS-specific API
        pass
```

#### **3.3 BTN (BroadcastTheNet) Integration**
```python
class BTNUploader:
    def upload(self, torrent_path, metadata):
        # BTN-specific upload logic
        pass
```

### **Phase 4: User Experience Enhancements**

#### **4.1 Configuration Options**
```json
{
  "auto_upload_to_trackers": true,
  "upload_trackers": ["redacted", "orpheus"],
  "upload_on_creation": true,
  "upload_retry_failed": true,
  "upload_notification": true
}
```

#### **4.2 CLI Commands**
```bash
# Upload specific torrent
python run.py upload /path/to/torrent.torrent --trackers red,ops

# Upload queued torrents
python run.py upload --queue

# Configure upload settings
python run.py config --upload-settings

# Check upload status
python run.py upload --status
```

#### **4.3 Interactive Prompts**
```
🎯 Torrent created successfully!

📤 Upload to trackers?
• Redacted (API key configured)
• Orpheus (API key needed)
• BTN (API key configured)

Upload now? [Y/n]: y
Select trackers: 1,3

🚀 Uploading to Redacted...
✅ Successfully uploaded to Redacted
🚀 Uploading to BTN...
✅ Successfully uploaded to BTN

📊 Upload Summary: 2/2 successful
```

## 🔧 **Technical Implementation Details**

### **API Key Management**
- Store tracker API keys in secure storage
- Support multiple keys per tracker (main + alt)
- Automatic key rotation for rate limiting

### **Error Handling & Retry Logic**
```python
class UploadRetryManager:
    def __init__(self):
        self.max_retries = 3
        self.retry_delay = 60  # seconds

    def upload_with_retry(self, uploader, torrent_path, metadata):
        for attempt in range(self.max_retries):
            try:
                return uploader.upload(torrent_path, metadata)
            except RateLimitError:
                time.sleep(self.retry_delay * (2 ** attempt))
            except TemporaryError:
                time.sleep(self.retry_delay)
        return False
```

### **Metadata Collection**
```python
def collect_upload_metadata(torrent_creator):
    """Collect metadata for tracker uploads"""
    return {
        'title': torrent_creator.get_torrent_name(),
        'category': torrent_creator.category,
        'tags': torrent_creator.tags,
        'description': torrent_creator.comment,
        'source': torrent_creator.source,
        'size': torrent_creator.get_total_size(),
        'file_count': torrent_creator.get_file_count(),
        'trackers': torrent_creator.trackers,
        'created_at': datetime.now().isoformat(),
        'creator_version': '2.0.0'
    }
```

### **Progress Tracking**
```python
class UploadProgressTracker:
    def __init__(self):
        self.upload_history = load_upload_history()

    def track_upload(self, torrent_path, tracker, success, response=None):
        entry = {
            'torrent': str(torrent_path),
            'tracker': tracker,
            'timestamp': datetime.now().isoformat(),
            'success': success,
            'response': response,
            'retry_count': 0
        }
        self.upload_history.append(entry)
        save_upload_history(self.upload_history)
```

## 📋 **Development Roadmap**

### **Week 1-2: Core Upload System**
- [ ] Implement UploadManager base class
- [ ] Create RED tracker integration
- [ ] Add upload queue system
- [ ] Update configuration schema

### **Week 3-4: Tracker Integrations**
- [ ] Implement OPS uploader
- [ ] Implement BTN uploader
- [ ] Add API key management UI
- [ ] Test integrations with real trackers

### **Week 5-6: User Experience**
- [ ] Add CLI upload commands
- [ ] Implement interactive upload prompts
- [ ] Create upload status dashboard
- [ ] Add retry and error recovery

### **Week 7-8: Advanced Features**
- [ ] Background upload processing
- [ ] Rate limiting and throttling
- [ ] Upload analytics and reporting
- [ ] Integration with existing workflows

## 🎯 **Success Metrics**

- ✅ **Upload Success Rate**: >95% for configured trackers
- ✅ **User Experience**: One-click upload from torrent creation
- ✅ **Error Recovery**: Automatic retry for failed uploads
- ✅ **Security**: All credentials encrypted and secure
- ✅ **Extensibility**: Easy to add new tracker support

## 🚀 **Ready for Implementation**

The foundation is solid with:
- ✅ Secure credential storage
- ✅ qBittorrent API integration
- ✅ Extensible configuration system
- ✅ Clean architecture for expansion

**Next Step**: Begin Phase 2 implementation with the UploadManager and RED tracker integration.
