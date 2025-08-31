#!/usr/bin/env python3
"""Comprehensive health checks for the torrent creator system"""

from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional
import subprocess
import shutil
import psutil  # Add to requirements.txt
import json
import time
import sys
import socket

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.syntax import Syntax

console = Console()

class SystemHealthCheck:
    """System-level health checks"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.results = {
            "disk_space": {},
            "permissions": {},
            "dependencies": {},
            "network": {},
            "docker": {},
            "qbittorrent": {},
            "performance": {}
        }
    
    def check_disk_space(self) -> Dict[str, Any]:
        """Check available disk space for critical paths"""
        results: Dict[str, Any] = {}
        
        # Check output directory
        output_dir = Path(self.config.get("output_directory", "."))
        if output_dir.exists():
            usage = psutil.disk_usage(str(output_dir))
            results["output_directory"] = {
                "path": str(output_dir),
                "free_gb": usage.free / (1024**3),
                "percent_used": usage.percent,
                "healthy": usage.percent < 90 and usage.free > 1024**3  # >1GB free and <90% used
            }
        
        # Check qBittorrent default save path
        save_path = self.config.get("qbit_default_save_path")
        if save_path and Path(save_path).exists():
            usage = psutil.disk_usage(save_path)
            results["qbit_save_path"] = {
                "path": save_path,
                "free_gb": usage.free / (1024**3),
                "percent_used": usage.percent,
                "healthy": usage.percent < 90
            }
        
        # Check /tmp for temporary operations
        tmp_usage = psutil.disk_usage("/tmp")
        results["temp_space"] = {
            "path": "/tmp",
            "free_gb": tmp_usage.free / (1024**3),
            "healthy": tmp_usage.free > 500 * 1024**2  # >500MB free
        }
        
        self.results["disk_space"] = results
        return results
    
    def check_permissions(self) -> Dict[str, Any]:
        """Check read/write permissions for critical paths"""
        results: Dict[str, Any] = {}
        
        # Paths to check
        paths_to_check = [
            ("config", Path.home() / ".config" / "torrent_creator"),
            ("output", Path(self.config.get("output_directory", "."))),
            ("backup", Path(self.config.get("backup_directory", Path.home() / "torrent_backups")))
        ]
        
        for name, path in paths_to_check:
            if not path.exists():
                try:
                    path.mkdir(parents=True, exist_ok=True)
                    results[name] = {"exists": True, "writable": True, "readable": True}
                except PermissionError:
                    results[name] = {"exists": False, "writable": False, "error": "Cannot create"}
            else:
                results[name] = {
                    "exists": True,
                    "readable": path.exists() and path.stat().st_mode & 0o400,
                    "writable": path.exists() and path.stat().st_mode & 0o200
                }
        
        self.results["permissions"] = results
        return results
    
    def check_dependencies(self) -> Dict[str, Any]:
        """Check for required external tools and Python packages"""
        results: Dict[str, Any] = {
            "python_version": {
                "version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
                "healthy": sys.version_info >= (3, 8)
            },
            "required_tools": {},
            "python_packages": {}
        }
        
        # Check external tools
        tools = ["docker", "curl", "wget"]
        for tool in tools:
            results["required_tools"][tool] = shutil.which(tool) is not None
        
        # Check Python packages
        required_packages = [
            "qbittorrentapi",
            "rich",
            "typer",
            "requests"
        ]
        
        for package in required_packages:
            try:
                __import__(package)
                results["python_packages"][package] = True
            except ImportError:
                results["python_packages"][package] = False
        
        self.results["dependencies"] = results
        return results
    
    def check_network_connectivity(self) -> Dict[str, Any]:
        """Check network connectivity to trackers and qBittorrent"""
        results: Dict[str, Any] = {
            "qbittorrent": {},
            "trackers": {},
            "dns": {}
        }
        
        # Check qBittorrent connectivity
        import socket
        host = self.config.get("qbit_host", "localhost")
        port = self.config.get("qbit_port", 8080)
        
        try:
            sock = socket.create_connection((host, port), timeout=5)
            sock.close()
            results["qbittorrent"] = {
                "reachable": True,
                "host": host,
                "port": port
            }
        except (socket.timeout, socket.error) as e:
            results["qbittorrent"] = {
                "reachable": False,
                "host": host,
                "port": port,
                "error": str(e)
            }
        
        # Check DNS resolution for common trackers
        test_domains = [
            "tracker.opentrackr.org",
            "open.stealth.si",
            "tracker.torrent.eu.org"
        ]
        
        for domain in test_domains:
            try:
                socket.gethostbyname(domain)
                results["dns"][domain] = True
            except socket.gaierror:
                results["dns"][domain] = False
        
        self.results["network"] = results
        return results
    
    def check_docker_health(self) -> Dict[str, Any]:
        """Check Docker daemon and container health if using Docker mode"""
        results: Dict[str, Any] = {
            "daemon_running": False,
            "container_status": None,
            "path_mappings": {}
        }
        
        if not self.config.get("docker_mode", False):
            results["enabled"] = False
            self.results["docker"] = results
            return results
        
        results["enabled"] = True
        
        # Check Docker daemon
        try:
            result = subprocess.run(
                ["docker", "info"],
                capture_output=True,
                text=True,
                timeout=5
            )
            results["daemon_running"] = result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            results["daemon_running"] = False
        
        # Check container status
        if results["daemon_running"]:
            container_name = self.config.get("docker_container", "qbittorrent")
            try:
                result = subprocess.run(
                    ["docker", "inspect", container_name],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0:
                    info = json.loads(result.stdout)[0]
                    results["container_status"] = {
                        "running": info["State"]["Running"],
                        "health": info.get("State", {}).get("Health", {}).get("Status", "unknown"),
                        "restart_count": info["RestartCount"]
                    }
            except (subprocess.TimeoutExpired, json.JSONDecodeError, KeyError):
                results["container_status"] = {"error": "Failed to inspect container"}
        
        # Verify path mappings
        mappings = self.config.get("docker_mappings", {})
        if isinstance(mappings, dict):
            for host_path, container_path in mappings.items():
                results["path_mappings"][host_path] = {
                    "exists": Path(host_path).exists(),
                    "container_path": container_path
                }
        
        self.results["docker"] = results
        return results
    
    def check_qbittorrent_health(self) -> Dict[str, Any]:
        """Detailed qBittorrent health checks"""
        from qbit_api import QBittorrentAPI

        results: Dict[str, Any] = {
            "api_accessible": False,
            "version": None,
            "free_space": None,
            "torrents_count": None,
            "active_downloads": None,
            "upload_rate": None,
            "download_rate": None
        }

        # Get password securely
        try:
            from config import get_qbittorrent_password
            password = get_qbittorrent_password(self.config)
            if not password:
                results["error"] = "No password found in secure storage"
                return results
        except ImportError:
            # Fallback to plain text if secure storage not available
            password = self.config.get("qbit_password", "adminadmin")

        try:
            api = QBittorrentAPI(
                self.config.get("qbit_host", "localhost"),
                self.config.get("qbit_port", 8080),
                self.config.get("qbit_username", "admin"),
                password,
                self.config.get("qbit_https", False)
            )

            if api.login():
                results["api_accessible"] = True

                # Get preferences for more info
                prefs = api.get_preferences()
                if prefs:
                    results["version"] = prefs.get("version", "unknown")
                    results["free_space"] = prefs.get("free_space_on_disk", None)

                # Get transfer info via qbittorrent-api client
                from qbittorrentapi import Client
                client = Client(
                    host=f"{self.config['qbit_host']}:{self.config['qbit_port']}",
                    username=self.config.get("qbit_username"),
                    password=password,
                    VERIFY_WEBUI_CERTIFICATE=not self.config.get("qbit_https", False)
                )
                
                # Get torrent statistics
                torrents = client.torrents_info()
                results["torrents_count"] = len(torrents)
                results["active_downloads"] = sum(1 for t in torrents if t.state == "downloading")
                
                # Get transfer rates
                transfer_info = client.transfer_info()
                results["upload_rate"] = transfer_info.up_info_speed / 1024  # KB/s
                results["download_rate"] = transfer_info.dl_info_speed / 1024  # KB/s
                
        except Exception as e:
            results["error"] = str(e)
        
        self.results["qbittorrent"] = results
        return results
    
    def check_performance_metrics(self) -> Dict[str, Any]:
        """Check system performance metrics"""
        cpu_percent = psutil.cpu_percent(interval=1)
        memory_info = psutil.virtual_memory()
        load_avg = psutil.getloadavg() if hasattr(psutil, "getloadavg") else [0, 0, 0]
        cpu_count = psutil.cpu_count()
        
        results: Dict[str, Any] = {
            "cpu_percent": cpu_percent,
            "memory": {
                "percent": memory_info.percent,
                "available_gb": memory_info.available / (1024**3)
            },
            "load_average": load_avg,
            "process_count": len(psutil.pids()),
            "healthy": True
        }
        
        # Determine if healthy
        results["healthy"] = (
            cpu_percent < 80 and
            memory_info.percent < 80 and
            (load_avg[0] < (cpu_count * 2) if cpu_count else True)
        )
        
        self.results["performance"] = results
        return results
    
    def run_all_checks(self) -> Dict[str, Any]:
        """Run all health checks with progress indicator"""
        checks = [
            ("Disk Space", self.check_disk_space),
            ("Permissions", self.check_permissions),
            ("Dependencies", self.check_dependencies),
            ("Network", self.check_network_connectivity),
            ("Docker", self.check_docker_health),
            ("qBittorrent", self.check_qbittorrent_health),
            ("Performance", self.check_performance_metrics)
        ]
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Running health checks...", total=len(checks))
            
            for name, check_func in checks:
                progress.update(task, description=f"Checking {name}...")
                try:
                    check_func()
                except Exception as e:
                    self.results[name.lower().replace(" ", "_")] = {"error": str(e)}
                progress.advance(task)
        
        return self.results
    
    def display_results(self):
        """Display health check results in a formatted table"""
        console.print(Panel.fit("[bold cyan]🏥 System Health Check Results[/bold cyan]", border_style="cyan"))
        
        # Summary table
        table = Table(title="Health Check Summary", show_lines=True)
        table.add_column("Component", style="cyan")
        table.add_column("Status", style="green")
        table.add_column("Details", style="yellow")
        
        # Disk space
        disk_healthy = all(v.get("healthy", False) for v in self.results["disk_space"].values())
        table.add_row(
            "Disk Space",
            "✅" if disk_healthy else "⚠️",
            f"{len([v for v in self.results['disk_space'].values() if v.get('healthy')])} / {len(self.results['disk_space'])} paths OK"
        )
        
        # Permissions
        perm_healthy = all(v.get("writable", False) for v in self.results["permissions"].values())
        table.add_row(
            "Permissions",
            "✅" if perm_healthy else "❌",
            f"{len([v for v in self.results['permissions'].values() if v.get('writable')])} / {len(self.results['permissions'])} paths writable"
        )
        
        # Dependencies
        deps_healthy = all(self.results["dependencies"]["required_tools"].values())
        table.add_row(
            "Dependencies",
            "✅" if deps_healthy else "⚠️",
            f"Tools: {sum(self.results['dependencies']['required_tools'].values())} / {len(self.results['dependencies']['required_tools'])}"
        )
        
        # Network
        net_healthy = self.results["network"].get("qbittorrent", {}).get("reachable", False)
        table.add_row(
            "Network",
            "✅" if net_healthy else "❌",
            f"qBittorrent: {'reachable' if net_healthy else 'unreachable'}"
        )
        
        # Docker (if enabled)
        if self.results["docker"].get("enabled"):
            docker_healthy = self.results["docker"].get("daemon_running", False)
            table.add_row(
                "Docker",
                "✅" if docker_healthy else "❌",
                f"Container: {self.results['docker'].get('container_status', {}).get('running', 'unknown')}"
            )
        
        # qBittorrent
        qbit_healthy = self.results["qbittorrent"].get("api_accessible", False)
        table.add_row(
            "qBittorrent",
            "✅" if qbit_healthy else "❌",
            f"Torrents: {self.results['qbittorrent'].get('torrents_count', 'N/A')}"
        )
        
        # Performance
        perf_healthy = self.results["performance"].get("healthy", False)
        table.add_row(
            "Performance",
            "✅" if perf_healthy else "⚠️",
            f"CPU: {self.results['performance'].get('cpu_percent', 0):.1f}%, Mem: {self.results['performance'].get('memory', {}).get('percent', 0):.1f}%"
        )
        
        console.print(table)
        
        # Show warnings
        warnings = []
        
        # Check for low disk space
        for name, info in self.results["disk_space"].items():
            if not info.get("healthy", True):
                warnings.append(f"Low disk space on {info.get('path', name)}: {info.get('free_gb', 0):.1f} GB free")
        
        # Check for high resource usage
        if self.results["performance"].get("cpu_percent", 0) > 70:
            warnings.append(f"High CPU usage: {self.results['performance']['cpu_percent']:.1f}%")
        
        if self.results["performance"].get("memory", {}).get("percent", 0) > 70:
            warnings.append(f"High memory usage: {self.results['performance']['memory']['percent']:.1f}%")
        
        if warnings:
            console.print("\n[yellow]⚠️ Warnings:[/yellow]")
            for warning in warnings:
                console.print(f"  • {warning}")
        
        return all([
            disk_healthy,
            perm_healthy,
            qbit_healthy,
            self.results["performance"].get("healthy", False)
        ])

def run_comprehensive_health_check(config: Dict[str, Any]) -> bool:
    """Run comprehensive health checks"""
    checker = SystemHealthCheck(config)
    checker.run_all_checks()
    return checker.display_results()

def run_quick_health_check(config: Dict[str, Any]) -> bool:
    """Run a quick health check (essential checks only)"""
    console.print("[cyan]Running quick health check...[/cyan]")
    
    checker = SystemHealthCheck(config)
    
    # Only run essential checks
    checker.check_disk_space()
    checker.check_qbittorrent_health()
    checker.check_performance_metrics()
    
    # Simple output
    all_healthy = True
    
    if checker.results["disk_space"]:
        for name, info in checker.results["disk_space"].items():
            if not info.get("healthy", True):
                console.print(f"[yellow]⚠️ Low disk space: {name}[/yellow]")
                all_healthy = False
    
    if not checker.results["qbittorrent"].get("api_accessible", False):
        console.print("[red]❌ qBittorrent not accessible[/red]")
        all_healthy = False
    
    if not checker.results["performance"].get("healthy", True):
        console.print("[yellow]⚠️ High system resource usage[/yellow]")
    
    if all_healthy:
        console.print("[green]✅ Quick health check passed[/green]")
    
    return all_healthy

# Add monitoring capabilities
class ContinuousMonitor:
    """Continuous health monitoring"""
    
    def __init__(self, config: Dict[str, Any], interval: int = 60):
        self.config = config
        self.interval = interval
        self.history = []
    
    def monitor(self, duration: int = 300):
        """Monitor health for specified duration (seconds)"""
        console.print(f"[cyan]Starting health monitoring for {duration} seconds...[/cyan]")
        
        start_time = time.time()
        while time.time() - start_time < duration:
            checker = SystemHealthCheck(self.config)
            checker.check_qbittorrent_health()
            checker.check_performance_metrics()
            checker.check_disk_space()
            
            self.history.append({
                "timestamp": time.time(),
                "results": checker.results
            })
            
            # Display current status
            console.print(f"\r[{time.strftime('%H:%M:%S')}] "
                         f"CPU: {checker.results['performance']['cpu_percent']:.1f}% "
                         f"Mem: {checker.results['performance']['memory']['percent']:.1f}% "
                         f"Torrents: {checker.results['qbittorrent'].get('torrents_count', 'N/A')} ",
                         end="")
            
            time.sleep(self.interval)
        
        console.print("\n[green]Monitoring complete[/green]")
        self.display_summary()
    
    def display_summary(self):
        """Display monitoring summary"""
        if not self.history:
            return
        
        # Calculate averages
        avg_cpu = sum(h["results"]["performance"]["cpu_percent"] for h in self.history) / len(self.history)
        avg_mem = sum(h["results"]["performance"]["memory"]["percent"] for h in self.history) / len(self.history)
        
        console.print(f"\n[cyan]Monitoring Summary:[/cyan]")
        console.print(f"  Average CPU: {avg_cpu:.1f}%")
        console.print(f"  Average Memory: {avg_mem:.1f}%")
