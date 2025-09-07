# 📊 Performance Guide

**Optimize mk_torrent for speed, efficiency, and reliability**

---

## 📋 **Table of Contents**

- [Quick Performance Wins](#-quick-performance-wins)
- [System Requirements](#-system-requirements)
- [CPU Optimization](#-cpu-optimization)
- [Memory Management](#-memory-management)
- [Disk I/O Optimization](#-disk-io-optimization)
- [Network Performance](#-network-performance)
- [Monitoring & Profiling](#-monitoring--profiling)
- [Troubleshooting Performance Issues](#-troubleshooting-performance-issues)

updated: 2025-09-06T19:14:05-05:00
---

## 🚀 **Quick Performance Wins**

### **Immediate Optimizations**

```json
{
  "processing": {
    "parallel_processing": true,
    "max_workers": 8,                    // CPU cores * 2
    "memory_limit": "4GB",               // 25% of system RAM
    "io_buffer_size": "64KB"
  },

  "caching": {
    "metadata_cache_size": "500MB",
    "api_response_cache": true,
    "cache_compression": true
  },

  "torrent": {
    "piece_size_auto": true,             // Optimal piece sizes
    "include_md5": false                 // Skip MD5 unless required
  }
}
```

### **Storage Optimization**

```bash
# Use SSD for working directory
export MK_TORRENT_WORKING_DIR="/fast/ssd/mk_torrent"

# Use separate disk for output
export MK_TORRENT_OUTPUT_DIR="/bulk/storage/torrents"

# Enable compression for cache
mkdir -p ~/.cache/mk_torrent
```

---

## 💻 **System Requirements**

### **Minimum Requirements**

- **CPU**: 2 cores, 2.0 GHz
- **RAM**: 2 GB available
- **Storage**: 10 GB free space
- **Network**: Stable internet connection

### **Recommended Requirements**

- **CPU**: 4+ cores, 3.0+ GHz (Intel i5/AMD Ryzen 5 or better)
- **RAM**: 8+ GB available (16 GB total system)
- **Storage**: 50+ GB free SSD space
- **Network**: High-speed broadband (100+ Mbps)

### **High-Performance Setup**

- **CPU**: 8+ cores, 3.5+ GHz (Intel i7/AMD Ryzen 7 or better)
- **RAM**: 16+ GB available (32 GB total system)
- **Storage**: NVMe SSD with 200+ GB free
- **Network**: Gigabit connection with low latency

### **System Configuration Check**

```python
# Run system performance check
from mk_torrent.utils.system_info import check_system_performance

results = check_system_performance()
print(f"CPU Cores: {results['cpu_cores']}")
print(f"Available RAM: {results['ram_gb']} GB")
print(f"Disk Speed: {results['disk_speed_mbps']} MB/s")
print(f"Network Speed: {results['network_speed_mbps']} Mbps")
print(f"Recommended Workers: {results['recommended_workers']}")
```

---

## ⚡ **CPU Optimization**

### **Worker Configuration**

```python
import multiprocessing
import psutil

# Calculate optimal worker count
cpu_cores = multiprocessing.cpu_count()
system_load = psutil.getloadavg()[0] if hasattr(psutil, 'getloadavg') else 0
available_cores = max(1, cpu_cores - int(system_load))

# Configuration based on workload
config = {
    "processing": {
        "max_workers": min(available_cores * 2, 16),  # Cap at 16
        "parallel_processing": True,
        "cpu_affinity": list(range(available_cores))  # Linux only
    }
}
```

### **CPU-Intensive Task Optimization**

```json
{
  "metadata": {
    "parallel_file_processing": true,
    "batch_size": 50,                    // Files per batch
    "audio_analysis_threads": 4
  },

  "torrent": {
    "hash_calculation_threads": 4,       // Parallel hash calculation
    "piece_size_auto": true,             // Reduces computation
    "chunk_size": "1MB"                  // Balance memory vs CPU
  }
}
```

### **Process Priority**

```bash
# Linux: Run with higher priority
nice -n -10 python -m mk_torrent process /path/to/audiobooks

# Windows: Set high priority
start /high python -m mk_torrent process /path/to/audiobooks

# Alternative: Use taskset for CPU affinity (Linux)
taskset -c 0,1,2,3 python -m mk_torrent process /path/to/audiobooks
```

---

## 🧠 **Memory Management**

### **Memory Configuration**

```json
{
  "processing": {
    "memory_limit": "4GB",               // Hard limit per process
    "memory_warning_threshold": "3GB",   // Warning threshold
    "memory_cleanup_interval": 300,     // Cleanup every 5 minutes
    "large_file_threshold": "1GB"       // Stream large files
  },

  "caching": {
    "metadata_cache_size": "500MB",
    "file_cache_size": "1GB",
    "cache_cleanup_policy": "lru",      // Least Recently Used
    "cache_persist": true               // Persist between runs
  }
}
```

### **Memory Usage Patterns**

```python
# Monitor memory usage during processing
import psutil
import gc

def monitor_memory_usage():
    """Monitor and optimize memory usage."""
    process = psutil.Process()
    memory_info = process.memory_info()

    print(f"RSS: {memory_info.rss / 1024 / 1024:.1f} MB")
    print(f"VMS: {memory_info.vms / 1024 / 1024:.1f} MB")

    # Force garbage collection if memory usage is high
    if memory_info.rss > 4 * 1024 * 1024 * 1024:  # 4GB
        gc.collect()
```

### **Large File Handling**

```python
# Stream large files instead of loading into memory
def process_large_audiobook(file_path: Path, chunk_size: int = 1024*1024):
    """Process large files in chunks to reduce memory usage."""
    with open(file_path, 'rb') as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break

            # Process chunk
            yield process_chunk(chunk)
```

---

## 💾 **Disk I/O Optimization**

### **Storage Strategy**

```json
{
  "storage": {
    "working_directory": "/fast/ssd/mk_torrent",    // SSD for temp files
    "output_directory": "/bulk/hdd/torrents",       // HDD for final output
    "cache_directory": "/fast/ssd/cache",           // SSD for cache
    "log_directory": "/var/log/mk_torrent"          // Any storage for logs
  },

  "io": {
    "buffer_size": "64KB",               // Optimal for most SSDs
    "read_ahead": true,                  // Enable OS read-ahead
    "sync_writes": false,                // Async writes for speed
    "compression": {
      "temp_files": false,               // Don't compress temp files
      "cache_files": true                // Compress cache files
    }
  }
}
```

### **Disk Performance Monitoring**

```python
import shutil

def check_disk_performance():
    """Check disk space and performance."""
    # Check free space
    working_space = shutil.disk_usage("/tmp/mk_torrent")
    output_space = shutil.disk_usage("~/torrents")

    print(f"Working dir free: {working_space.free / 1024**3:.1f} GB")
    print(f"Output dir free: {output_space.free / 1024**3:.1f} GB")

    # Recommend minimum free space
    recommended_free = 50 * 1024**3  # 50 GB
    if working_space.free < recommended_free:
        print("WARNING: Low disk space in working directory")
```

### **I/O Optimization Techniques**

```python
# Use memory mapping for large files
import mmap

def process_with_mmap(file_path: Path):
    """Use memory mapping for efficient file access."""
    with open(file_path, 'rb') as f:
        with mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as mm:
            # Process file through memory mapping
            return analyze_audio_data(mm)

# Batch file operations
def batch_file_operations(file_list: List[Path], batch_size: int = 100):
    """Process files in batches to reduce I/O overhead."""
    for i in range(0, len(file_list), batch_size):
        batch = file_list[i:i + batch_size]
        yield process_batch(batch)
```

---

## 🌐 **Network Performance**

### **Connection Optimization**

```json
{
  "network": {
    "timeout": 30,
    "connect_timeout": 10,
    "read_timeout": 60,
    "retry_attempts": 3,
    "retry_delay": 1.0,
    "exponential_backoff": true,

    "connection_pool": {
      "max_connections": 20,
      "max_connections_per_host": 5,
      "pool_keepalive": 300
    },

    "http_optimization": {
      "http2": true,
      "compression": true,
      "keep_alive": true,
      "tcp_nodelay": true
    }
  }
}
```

### **API Rate Limiting**

```python
import asyncio
import aiohttp
from aiohttp import ClientSession

class RateLimitedAPI:
    """API client with built-in rate limiting."""

    def __init__(self, rate_limit: int = 5, window: int = 60):
        self.rate_limit = rate_limit
        self.window = window
        self.requests = []

    async def make_request(self, url: str, **kwargs):
        """Make rate-limited API request."""
        await self._enforce_rate_limit()

        async with ClientSession() as session:
            async with session.get(url, **kwargs) as response:
                return await response.json()

    async def _enforce_rate_limit(self):
        """Enforce rate limiting."""
        now = asyncio.get_event_loop().time()

        # Remove old requests outside window
        self.requests = [req_time for req_time in self.requests
                        if now - req_time < self.window]

        # Wait if rate limit exceeded
        if len(self.requests) >= self.rate_limit:
            sleep_time = self.window - (now - self.requests[0])
            if sleep_time > 0:
                await asyncio.sleep(sleep_time)

        self.requests.append(now)
```

### **Concurrent API Requests**

```python
import asyncio
import aiohttp

async def fetch_metadata_concurrently(audiobook_ids: List[str]):
    """Fetch metadata for multiple audiobooks concurrently."""
    semaphore = asyncio.Semaphore(5)  # Limit concurrent requests

    async def fetch_one(session, audiobook_id):
        async with semaphore:
            url = f"https://api.audnex.us/books/{audiobook_id}"
            async with session.get(url) as response:
                return await response.json()

    async with aiohttp.ClientSession() as session:
        tasks = [fetch_one(session, id) for id in audiobook_ids]
        results = await asyncio.gather(*tasks, return_exceptions=True)

    return results
```

---

## 📊 **Monitoring & Profiling**

### **Performance Metrics**

```python
import time
import psutil
from dataclasses import dataclass
from typing import Dict, Any

@dataclass
class PerformanceMetrics:
    """Performance metrics collection."""
    execution_time: float
    cpu_usage: float
    memory_usage: float
    disk_io: Dict[str, int]
    network_io: Dict[str, int]

def measure_performance(func):
    """Decorator to measure function performance."""
    def wrapper(*args, **kwargs):
        start_time = time.time()
        start_cpu = psutil.cpu_percent()
        start_memory = psutil.virtual_memory().used

        result = func(*args, **kwargs)

        end_time = time.time()
        end_cpu = psutil.cpu_percent()
        end_memory = psutil.virtual_memory().used

        metrics = PerformanceMetrics(
            execution_time=end_time - start_time,
            cpu_usage=end_cpu - start_cpu,
            memory_usage=end_memory - start_memory,
            disk_io=psutil.disk_io_counters()._asdict(),
            network_io=psutil.net_io_counters()._asdict()
        )

        print(f"Performance: {func.__name__}")
        print(f"  Time: {metrics.execution_time:.2f}s")
        print(f"  CPU: {metrics.cpu_usage:.1f}%")
        print(f"  Memory: {metrics.memory_usage / 1024 / 1024:.1f} MB")

        return result

    return wrapper
```

### **Profiling Tools**

```python
# CPU profiling with cProfile
import cProfile
import pstats

def profile_cpu_usage():
    """Profile CPU usage of mk_torrent operations."""
    profiler = cProfile.Profile()
    profiler.enable()

    # Run your mk_torrent operation here
    result = process_audiobook("/path/to/audiobook")

    profiler.disable()

    # Analyze results
    stats = pstats.Stats(profiler)
    stats.sort_stats('cumulative')
    stats.print_stats(20)  # Top 20 functions

    return result

# Memory profiling with memory_profiler
from memory_profiler import profile

@profile
def process_with_memory_profiling():
    """Profile memory usage line by line."""
    # Your processing code here
    pass
```

### **Real-time Monitoring**

```python
import threading
import time

class PerformanceMonitor:
    """Real-time performance monitoring."""

    def __init__(self, interval: int = 5):
        self.interval = interval
        self.monitoring = False
        self.stats = []

    def start_monitoring(self):
        """Start performance monitoring."""
        self.monitoring = True
        thread = threading.Thread(target=self._monitor_loop)
        thread.daemon = True
        thread.start()

    def stop_monitoring(self):
        """Stop performance monitoring."""
        self.monitoring = False

    def _monitor_loop(self):
        """Monitoring loop."""
        while self.monitoring:
            stats = {
                'timestamp': time.time(),
                'cpu_percent': psutil.cpu_percent(),
                'memory_percent': psutil.virtual_memory().percent,
                'disk_usage': psutil.disk_usage('/').percent,
                'network_sent': psutil.net_io_counters().bytes_sent,
                'network_recv': psutil.net_io_counters().bytes_recv
            }
            self.stats.append(stats)
            time.sleep(self.interval)

    def get_summary(self):
        """Get performance summary."""
        if not self.stats:
            return None

        avg_cpu = sum(s['cpu_percent'] for s in self.stats) / len(self.stats)
        max_memory = max(s['memory_percent'] for s in self.stats)

        return {
            'average_cpu': avg_cpu,
            'peak_memory': max_memory,
            'duration': self.stats[-1]['timestamp'] - self.stats[0]['timestamp']
        }
```

---

## 🚨 **Troubleshooting Performance Issues**

### **Common Performance Problems**

#### **Slow Metadata Extraction**

```python
# Problem: Metadata extraction taking too long
# Solutions:
config = {
    "metadata": {
        "cache_enabled": True,           # Cache results
        "parallel_processing": True,     # Process files in parallel
        "timeout": 10,                   # Reduce API timeouts
        "batch_size": 20                 # Process in smaller batches
    }
}
```

#### **High Memory Usage**

```python
# Problem: Memory usage growing over time
# Solutions:
import gc

def cleanup_memory():
    """Force memory cleanup."""
    gc.collect()                         # Force garbage collection

# Use streaming for large files
def process_large_files_streaming(files: List[Path]):
    """Process large files without loading into memory."""
    for file_path in files:
        with open(file_path, 'rb') as f:
            # Process in chunks
            while chunk := f.read(1024*1024):  # 1MB chunks
                process_chunk(chunk)
```

#### **Slow Torrent Creation**

```python
# Problem: Torrent creation is slow
# Solutions:
config = {
    "torrent": {
        "piece_size_auto": True,         # Use optimal piece size
        "parallel_hashing": True,        # Hash pieces in parallel
        "include_md5": False,            # Skip MD5 unless required
        "chunk_size": "2MB"              # Larger chunks for speed
    }
}
```

#### **Network Timeouts**

```python
# Problem: API requests timing out
# Solutions:
config = {
    "network": {
        "timeout": 60,                   # Increase timeout
        "retry_attempts": 5,             # More retries
        "exponential_backoff": True,     # Better retry strategy
        "connection_pool_size": 10       # Reuse connections
    }
}
```

### **Performance Diagnostics**

```python
def diagnose_performance_issues():
    """Diagnose common performance issues."""
    issues = []

    # Check system resources
    cpu_percent = psutil.cpu_percent(interval=1)
    memory_percent = psutil.virtual_memory().percent
    disk_usage = psutil.disk_usage('/').percent

    if cpu_percent > 90:
        issues.append("High CPU usage - consider reducing worker count")

    if memory_percent > 85:
        issues.append("High memory usage - enable memory cleanup")

    if disk_usage > 95:
        issues.append("Low disk space - clean up temporary files")

    # Check network connectivity
    try:
        import requests
        response = requests.get("https://api.audnex.us", timeout=5)
        if response.status_code != 200:
            issues.append("API connectivity issues")
    except:
        issues.append("Network connectivity problems")

    return issues
```

### **Optimization Recommendations**

```python
def get_optimization_recommendations():
    """Get personalized optimization recommendations."""
    cpu_cores = psutil.cpu_count()
    memory_gb = psutil.virtual_memory().total / (1024**3)

    recommendations = []

    # CPU recommendations
    if cpu_cores >= 8:
        recommendations.append("Enable high-performance parallel processing")
    elif cpu_cores >= 4:
        recommendations.append("Use moderate parallel processing")
    else:
        recommendations.append("Disable parallel processing for stability")

    # Memory recommendations
    if memory_gb >= 16:
        recommendations.append("Enable large cache sizes for better performance")
    elif memory_gb >= 8:
        recommendations.append("Use moderate cache sizes")
    else:
        recommendations.append("Minimize cache usage to prevent OOM errors")

    return recommendations
```

---

## 📈 **Performance Benchmarks**

### **Typical Performance Metrics**

| Operation | Small Audiobook (< 1GB) | Large Audiobook (5-10GB) | Batch (20 books) |
|-----------|-------------------------|---------------------------|-------------------|
| Metadata Extraction | 2-5 seconds | 10-30 seconds | 1-5 minutes |
| Torrent Creation | 30-60 seconds | 5-15 minutes | 20-60 minutes |
| Full Processing | 1-2 minutes | 10-20 minutes | 30-90 minutes |

### **Performance Targets**

- **Metadata Extraction**: < 10 seconds per audiobook
- **Torrent Creation**: < 1 minute per GB
- **Memory Usage**: < 2 GB peak usage
- **CPU Usage**: 60-80% during processing
- **Network**: < 5 API calls per audiobook

---

**🚀 For optimal performance, start with the Quick Performance Wins and gradually apply more advanced optimizations based on your specific use case and system capabilities.**
