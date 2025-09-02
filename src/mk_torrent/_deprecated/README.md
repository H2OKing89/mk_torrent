# ⚠️ DEPRECATED MODULES

**Date Deprecated:** September 2, 2025  
**Reason:** RED modules refactor to tracker-agnostic architecture  
**Documentation:** See `docs/active/RED_MODULES_REFACTOR.md`

## 🔄 **Migration Guide**

### **Old → New Mappings**

| Old Module | New Module | Migration |
|------------|------------|-----------|
| `api/red_integration.py` | `api/trackers/red.py` | Use `get_tracker_api('red')` |
| `features/red_uploader.py` | `api/trackers/red.py` | Use `RedactedAPI` class |
| `utils/red_path_compliance.py` | `core/compliance/path_validator.py` | Use `PathValidator('red')` |
| `utils/red_compliance_rename.py` | `core/compliance/path_fixer.py` | Use `PathFixer` class |

### **New Usage Examples**

```python
# OLD WAY (deprecated)
from mk_torrent.api.red_integration import integrate_upload_workflow
from mk_torrent.features.red_uploader import REDUploader

# NEW WAY (current)
from mk_torrent.api.trackers import get_tracker_api
red_api = get_tracker_api('red', api_key='your_key')
```

### **Benefits of New Architecture**
- ✅ Tracker-agnostic design (easy to add MAM, OPS, etc.)
- ✅ Clean separation of concerns
- ✅ Better testing and maintainability
- ✅ Unified compliance system for all trackers

---

**These files are kept for reference but should not be used in new code.**  
**All functionality has been migrated to the new modular architecture.**
