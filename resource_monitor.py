#!/usr/bin/env python3
"""
Resource monitoring for CPU and memory usage during simulation.
"""

import psutil
import time
from typing import Dict, List, Optional
from dataclasses import dataclass


@dataclass
class ResourceSnapshot:
    """Single snapshot of resource usage"""
    timestamp: float
    cpu_percent: float
    memory_percent: float
    memory_mb: float
    cpu_user: float
    cpu_system: float


class ResourceMonitor:
    """Monitor CPU and memory usage during simulation"""
    
    def __init__(self):
        self.process = psutil.Process()
        self.snapshots: List[ResourceSnapshot] = []
        self.start_time: Optional[float] = None
        self.end_time: Optional[float] = None
    
    def start(self):
        """Start monitoring"""
        self.start_time = time.time()
        self.snapshots.clear()
        self._take_snapshot()
    
    def stop(self):
        """Stop monitoring"""
        self.end_time = time.time()
        self._take_snapshot()
    
    def _take_snapshot(self):
        """Take a snapshot of current resource usage"""
        try:
            cpu_percent = self.process.cpu_percent(interval=0.1)
            memory_info = self.process.memory_info()
            memory_percent = self.process.memory_percent()
            cpu_times = self.process.cpu_times()
            
            snapshot = ResourceSnapshot(
                timestamp=time.time(),
                cpu_percent=cpu_percent,
                memory_percent=memory_percent,
                memory_mb=memory_info.rss / (1024 * 1024),  # Convert to MB
                cpu_user=cpu_times.user,
                cpu_system=cpu_times.system
            )
            self.snapshots.append(snapshot)
        except Exception as e:
            # If monitoring fails, continue silently
            pass
    
    def get_stats(self) -> Dict:
        """Get statistics about resource usage"""
        if not self.snapshots:
            return {
                'avg_cpu_percent': 0.0,
                'max_cpu_percent': 0.0,
                'avg_memory_mb': 0.0,
                'max_memory_mb': 0.0,
                'avg_memory_percent': 0.0,
                'max_memory_percent': 0.0,
                'total_cpu_time': 0.0,
                'duration': 0.0
            }
        
        cpu_percents = [s.cpu_percent for s in self.snapshots if s.cpu_percent > 0]
        memory_mbs = [s.memory_mb for s in self.snapshots]
        memory_percents = [s.memory_percent for s in self.snapshots]
        
        duration = 0.0
        if self.start_time and self.end_time:
            duration = self.end_time - self.start_time
        
        return {
            'avg_cpu_percent': sum(cpu_percents) / len(cpu_percents) if cpu_percents else 0.0,
            'max_cpu_percent': max(cpu_percents) if cpu_percents else 0.0,
            'avg_memory_mb': sum(memory_mbs) / len(memory_mbs) if memory_mbs else 0.0,
            'max_memory_mb': max(memory_mbs) if memory_mbs else 0.0,
            'avg_memory_percent': sum(memory_percents) / len(memory_percents) if memory_percents else 0.0,
            'max_memory_percent': max(memory_percents) if memory_percents else 0.0,
            'duration': duration,
            'num_snapshots': len(self.snapshots)
        }

