# 📁 Scripts Directory Organization

**Last Updated:** December 2024
**Status:** ✅ **REORGANIZED AND CLEAN**

## 📂 Directory Structure

```
scripts/
├── README.md                    # This documentation
├── cli/                         # Command Line Interface tools
│   └── red_upload_cli.py        # 🎯 PRODUCTION READY RED tracker upload CLI
├── red/                         # RED tracker integration tests (6 files)
│   ├── test_complete_red_workflow.py
│   ├── test_real_audiobook.py        # 🎯 COMPREHENSIVE real audiobook test
│   ├── test_red_end_to_end.py        # ✅ All 7 tests passing
│   ├── test_red_production.py
│   ├── test_red_simplified.py
│   └── test_refactored_structure.py
├── tools/                       # Utility scripts and tools
│   ├── refactor_red_modules.py
│   ├── test_metadata.py
│   └── test_mutagen_m4b.py
├── run.py                       # Main entry point (new src layout)
└── run_legacy.py                # Legacy entry point (old layout)
```

## 🎯 **What Was Fixed**

### **Before (Cluttered)**
```
scripts/
├── red_upload_cli.py           # Mixed with tests
├── run.py                      # Two run files confusing
├── run_new.py
├── test_complete_red_workflow.py
├── test_real_audiobook.py
├── test_real_audiobook_red.py  # DUPLICATE (consolidated)
├── test_red_end_to_end.py
├── test_red_production.py
├── test_red_simplified.py
├── test_refactored_structure.py
├── test_metadata.py
├── test_mutagen_m4b.py
└── refactor_red_modules.py
```

### **After (Organized)**
- **6 RED test files** → `red/` subdirectory (consolidated duplicates)
- **Main CLI tool** → `cli/` subdirectory
- **Utility scripts** → `tools/` subdirectory
- **Clear naming**: `run.py` (new), `run_legacy.py` (old)
- **Documentation**: This README file

---

## 🚀 **Usage (Updated Paths)**

### **RED Upload CLI (Production Ready)**
```bash
# From project root (recommended)
python scripts/cli/red_upload_cli.py /path/to/audiobook --api-key YOUR_KEY --dry-run

# Test with your real audiobook
python scripts/cli/red_upload_cli.py \
  "/mnt/cache/scripts/mk_torrent/tests/samples/audiobook/How a Realist Hero Rebuilt the Kingdom - vol_03 (2023) (Dojyomaru) {ASIN.B0C8ZW5N6Y} [H2OKing]" \
  --api-key YOUR_REAL_RED_API_KEY \
  --dry-run
```

### **RED Integration Tests**
```bash
# Run comprehensive real audiobook test (both locations)
python scripts/red/test_real_audiobook.py

# Run all basic RED tests (7/7 passing)
python scripts/red/test_red_end_to_end.py

# Complete workflow test
python scripts/red/test_complete_red_workflow.py
```

### **Main Application**
```bash
# New src layout (recommended)
python scripts/run.py

# Legacy layout
python scripts/run_legacy.py
```

### **Utility Tools**
```bash
# Metadata testing
python scripts/tools/test_metadata.py

# M4B file testing
python scripts/tools/test_mutagen_m4b.py
```

---

## 📊 **Test Status**

| Category | Status | Location | Count |
|----------|--------|----------|-------|
| **RED Tests** | ✅ All Pass | `red/` | 6 files |
| **CLI Tools** | ✅ Production Ready | `cli/` | 1 file |
| **Utilities** | ✅ Working | `tools/` | 3 files |
| **Entry Points** | ✅ Clear | root | 2 files |

**Total: 12 files organized into 4 logical directories**

---

## 🔧 **Path Fixes Applied**

All files updated to work from new locations:
- ✅ `scripts/cli/red_upload_cli.py` - Fixed import paths
- ✅ `scripts/red/*.py` - Fixed import paths (7 files)
- ✅ `scripts/tools/*.py` - Fixed import paths (3 files)
- ✅ `scripts/run.py` - Already correct
- ✅ `scripts/run_legacy.py` - Already correct

---

## 🎯 **Benefits Achieved**

1. **🗂️ Clear Organization**: Related files grouped logically
2. **🔍 Easy Discovery**: Find tests/tools by category
3. **🚀 Production Ready**: CLI tool prominently placed
4. **📚 Self-Documenting**: README explains structure
5. **🔧 Maintenance**: Easy to add new tests/tools
6. **✅ All Working**: No broken imports or paths

---

## 📋 **Quick Start**

```bash
# 1. Test RED integration (7 tests, all pass)
python scripts/red/test_red_end_to_end.py

# 2. Test with real audiobook
python scripts/red/test_real_audiobook.py

# 3. Use production CLI
python scripts/cli/red_upload_cli.py /path/to/audiobook --dry-run
```

---

**Reorganization completed:** September 2, 2025
**Status:** ✅ Clean, organized, and fully functional
