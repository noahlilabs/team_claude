#!/usr/bin/env python3
"""
Metrics Collector for Multi-Agent Claude System

This module provides a centralized metrics collection and monitoring
system for the multi-agent architecture, with support for performance
tracking, agent activity, and system health monitoring.
"""

import os
import sys
import json
import time
import datetime
import uuid
from pathlib import Path
from typing import Dict, List, Any, Optional, Union
import threading
import sqlite3
import psutil

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from src.utils.structured_logger import get_logger

# Set up logger
logger = get_logger("MetricsCollector", log_dir="logs")

# Constants
DEFAULT_DB_PATH = "metrics.db"
METRICS_INTERVAL = 60  # seconds
RETENTION_DAYS = 7  # days to keep metrics data


class MetricsCollector:
    """
    Collects and stores performance metrics for the multi-agent system.
    """
    
    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize the metrics collector.
        
        Args:
            db_path: Optional path to SQLite database file
        """
        self.db_path = db_path or DEFAULT_DB_PATH
        
        # Initialize the database
        self._init_db()
        
        # Background collection thread
        self.collection_thread = None
        self.stop_collection = False
        
        logger.info("Metrics collector initialized", {"db_path": self.db_path})
    
    def _init_db(self) -> None:
        """Initialize the metrics database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create system metrics table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS system_metrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            cpu_percent REAL,
            memory_used REAL,
            memory_total REAL,
            disk_used REAL,
            disk_total REAL,
            load_avg TEXT
        )
        """)
        
        # Create agent metrics table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS agent_metrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            agent_id TEXT,
            tasks_completed INTEGER,
            tasks_in_progress INTEGER,
            avg_task_duration REAL,
            api_calls INTEGER,
            status TEXT
        )
        """)
        
        # Create task metrics table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS task_metrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            task_id TEXT,
            agent_id TEXT,
            task_type TEXT,
            duration REAL,
            status TEXT,
            subtask_count INTEGER
        )
        """)
        
        # Create API metrics table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS api_metrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            agent_id TEXT,
            endpoint TEXT,
            response_time REAL,
            status_code INTEGER,
            tokens_used INTEGER,
            success BOOLEAN
        )
        """)
        
        conn.commit()
        conn.close()
        
        logger.debug("Database initialized")
    
    def start_collection(self) -> None:
        """Start the background metrics collection thread."""
        if self.collection_thread and self.collection_thread.is_alive():
            logger.warning("Metrics collection already running")
            return
        
        self.stop_collection = False
        self.collection_thread = threading.Thread(
            target=self._collection_worker,
            daemon=True
        )
        self.collection_thread.start()
        
        logger.info("Started metrics collection thread")
    
    def stop_collection(self) -> None:
        """Stop the background metrics collection thread."""
        if not self.collection_thread or not self.collection_thread.is_alive():
            logger.warning("Metrics collection not running")
            return
        
        self.stop_collection = True
        self.collection_thread.join(timeout=5)
        
        if self.collection_thread.is_alive():
            logger.warning("Metrics collection thread did not exit gracefully")
        else:
            logger.info("Stopped metrics collection thread")
    
    def _collection_worker(self) -> None:
        """Background worker to collect metrics at regular intervals."""
        while not self.stop_collection:
            try:
                # Collect system metrics
                self.collect_system_metrics()
                
                # Collect agent metrics (when implemented)
                # self.collect_agent_metrics()
                
                # Clean up old data
                self._clean_old_data()
                
                # Sleep until next collection
                time.sleep(METRICS_INTERVAL)
                
            except Exception as e:
                logger.error("Error in metrics collection", str(e))
                time.sleep(METRICS_INTERVAL)  # Sleep even if there's an error
    
    def collect_system_metrics(self) -> None:
        """Collect and store system-level metrics."""
        try:
            # Get system metrics
            cpu_percent = psutil.cpu_percent(interval=1)
            
            memory = psutil.virtual_memory()
            memory_used = memory.used / (1024 * 1024)  # MB
            memory_total = memory.total / (1024 * 1024)  # MB
            
            disk = psutil.disk_usage('/')
            disk_used = disk.used / (1024 * 1024 * 1024)  # GB
            disk_total = disk.total / (1024 * 1024 * 1024)  # GB
            
            load_avg = os.getloadavg() if hasattr(os, 'getloadavg') else (0, 0, 0)
            load_avg_json = json.dumps(load_avg)
            
            # Store in database
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
            INSERT INTO system_metrics 
            (cpu_percent, memory_used, memory_total, disk_used, disk_total, load_avg)
            VALUES (?, ?, ?, ?, ?, ?)
            """, (cpu_percent, memory_used, memory_total, disk_used, disk_total, load_avg_json))
            
            conn.commit()
            conn.close()
            
            logger.debug("Collected system metrics", {
                "cpu": cpu_percent,
                "memory_used_mb": memory_used,
                "disk_used_gb": disk_used
            })
            
        except Exception as e:
            logger.error("Failed to collect system metrics", str(e))
    
    def collect_agent_metrics(self, agent_id: str, metrics: Dict[str, Any]) -> None:
        """
        Collect and store agent-specific metrics.
        
        Args:
            agent_id: Agent identifier
            metrics: Dictionary of metric values
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
            INSERT INTO agent_metrics 
            (agent_id, tasks_completed, tasks_in_progress, avg_task_duration, api_calls, status)
            VALUES (?, ?, ?, ?, ?, ?)
            """, (
                agent_id,
                metrics.get('tasks_completed', 0),
                metrics.get('tasks_in_progress', 0),
                metrics.get('avg_task_duration', 0.0),
                metrics.get('api_calls', 0),
                metrics.get('status', 'unknown')
            ))
            
            conn.commit()
            conn.close()
            
            logger.debug(f"Collected metrics for agent {agent_id}")
            
        except Exception as e:
            logger.error(f"Failed to collect metrics for agent {agent_id}", str(e))
    
    def record_task_completion(
        self,
        task_id: str,
        agent_id: str,
        task_type: str,
        duration: float,
        status: str,
        subtask_count: int = 0
    ) -> None:
        """
        Record metrics for a completed task.
        
        Args:
            task_id: Task identifier
            agent_id: Agent identifier
            task_type: Type of task
            duration: Task duration in seconds
            status: Final task status
            subtask_count: Number of subtasks
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
            INSERT INTO task_metrics 
            (task_id, agent_id, task_type, duration, status, subtask_count)
            VALUES (?, ?, ?, ?, ?, ?)
            """, (task_id, agent_id, task_type, duration, status, subtask_count))
            
            conn.commit()
            conn.close()
            
            logger.info(f"Recorded task completion: {task_id}", {
                "agent": agent_id,
                "duration": duration,
                "status": status
            })
            
        except Exception as e:
            logger.error(f"Failed to record task completion for {task_id}", str(e))
    
    def record_api_call(
        self,
        agent_id: str,
        endpoint: str,
        response_time: float,
        status_code: int,
        tokens_used: int,
        success: bool
    ) -> None:
        """
        Record metrics for an API call.
        
        Args:
            agent_id: Agent identifier
            endpoint: API endpoint called
            response_time: Response time in seconds
            status_code: HTTP status code
            tokens_used: Number of tokens used
            success: Whether the call was successful
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
            INSERT INTO api_metrics 
            (agent_id, endpoint, response_time, status_code, tokens_used, success)
            VALUES (?, ?, ?, ?, ?, ?)
            """, (agent_id, endpoint, response_time, status_code, tokens_used, success))
            
            conn.commit()
            conn.close()
            
            logger.debug(f"Recorded API call by {agent_id} to {endpoint}", {
                "response_time": response_time,
                "status_code": status_code,
                "tokens": tokens_used
            })
            
        except Exception as e:
            logger.error(f"Failed to record API call for {agent_id}", str(e))
    
    def get_system_metrics(self, hours: int = 24) -> List[Dict[str, Any]]:
        """
        Get system metrics for the specified time range.
        
        Args:
            hours: Number of hours to look back
            
        Returns:
            List of system metric entries
        """
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("""
            SELECT * FROM system_metrics 
            WHERE timestamp >= datetime('now', '-' || ? || ' hours')
            ORDER BY timestamp
            """, (hours,))
            
            # Convert to list of dictionaries
            results = [dict(row) for row in cursor.fetchall()]
            
            conn.close()
            return results
            
        except Exception as e:
            logger.error(f"Failed to retrieve system metrics", str(e))
            return []
    
    def get_agent_metrics(
        self,
        agent_id: Optional[str] = None,
        hours: int = 24
    ) -> List[Dict[str, Any]]:
        """
        Get agent metrics for the specified time range and agent.
        
        Args:
            agent_id: Optional agent identifier to filter by
            hours: Number of hours to look back
            
        Returns:
            List of agent metric entries
        """
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            if agent_id:
                cursor.execute("""
                SELECT * FROM agent_metrics 
                WHERE timestamp >= datetime('now', '-' || ? || ' hours')
                AND agent_id = ?
                ORDER BY timestamp
                """, (hours, agent_id))
            else:
                cursor.execute("""
                SELECT * FROM agent_metrics 
                WHERE timestamp >= datetime('now', '-' || ? || ' hours')
                ORDER BY timestamp, agent_id
                """, (hours,))
            
            # Convert to list of dictionaries
            results = [dict(row) for row in cursor.fetchall()]
            
            conn.close()
            return results
            
        except Exception as e:
            logger.error(f"Failed to retrieve agent metrics", str(e))
            return []
    
    def get_task_metrics(
        self,
        agent_id: Optional[str] = None,
        task_type: Optional[str] = None,
        hours: int = 24
    ) -> List[Dict[str, Any]]:
        """
        Get task metrics for the specified filters.
        
        Args:
            agent_id: Optional agent identifier to filter by
            task_type: Optional task type to filter by
            hours: Number of hours to look back
            
        Returns:
            List of task metric entries
        """
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            query = """
            SELECT * FROM task_metrics 
            WHERE timestamp >= datetime('now', '-' || ? || ' hours')
            """
            params = [hours]
            
            if agent_id:
                query += " AND agent_id = ?"
                params.append(agent_id)
            
            if task_type:
                query += " AND task_type = ?"
                params.append(task_type)
            
            query += " ORDER BY timestamp"
            
            cursor.execute(query, params)
            
            # Convert to list of dictionaries
            results = [dict(row) for row in cursor.fetchall()]
            
            conn.close()
            return results
            
        except Exception as e:
            logger.error(f"Failed to retrieve task metrics", str(e))
            return []
    
    def get_api_metrics(
        self,
        agent_id: Optional[str] = None,
        hours: int = 24
    ) -> List[Dict[str, Any]]:
        """
        Get API call metrics for the specified filters.
        
        Args:
            agent_id: Optional agent identifier to filter by
            hours: Number of hours to look back
            
        Returns:
            List of API metric entries
        """
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            if agent_id:
                cursor.execute("""
                SELECT * FROM api_metrics 
                WHERE timestamp >= datetime('now', '-' || ? || ' hours')
                AND agent_id = ?
                ORDER BY timestamp
                """, (hours, agent_id))
            else:
                cursor.execute("""
                SELECT * FROM api_metrics 
                WHERE timestamp >= datetime('now', '-' || ? || ' hours')
                ORDER BY timestamp
                """, (hours,))
            
            # Convert to list of dictionaries
            results = [dict(row) for row in cursor.fetchall()]
            
            conn.close()
            return results
            
        except Exception as e:
            logger.error(f"Failed to retrieve API metrics", str(e))
            return []
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """
        Get a summary of system and agent performance.
        
        Returns:
            Dictionary with performance summary data
        """
        summary = {
            "system": {
                "cpu_avg": 0.0,
                "memory_pct_avg": 0.0,
                "disk_pct_avg": 0.0
            },
            "agents": {},
            "tasks": {
                "completed_count": 0,
                "avg_duration": 0.0,
                "success_rate": 0.0
            },
            "api": {
                "calls_count": 0,
                "avg_response_time": 0.0,
                "success_rate": 0.0,
                "total_tokens": 0
            }
        }
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # System metrics
            cursor.execute("""
            SELECT AVG(cpu_percent) as cpu_avg, 
                   AVG(memory_used/memory_total)*100 as memory_pct,
                   AVG(disk_used/disk_total)*100 as disk_pct
            FROM system_metrics
            WHERE timestamp >= datetime('now', '-24 hours')
            """)
            
            row = cursor.fetchone()
            if row:
                summary["system"]["cpu_avg"] = row[0] or 0.0
                summary["system"]["memory_pct_avg"] = row[1] or 0.0
                summary["system"]["disk_pct_avg"] = row[2] or 0.0
            
            # Agent metrics
            cursor.execute("""
            SELECT agent_id, 
                   AVG(tasks_completed) as avg_completed,
                   AVG(tasks_in_progress) as avg_in_progress,
                   AVG(avg_task_duration) as avg_duration
            FROM agent_metrics
            WHERE timestamp >= datetime('now', '-24 hours')
            GROUP BY agent_id
            """)
            
            for row in cursor.fetchall():
                summary["agents"][row[0]] = {
                    "avg_tasks_completed": row[1] or 0.0,
                    "avg_tasks_in_progress": row[2] or 0.0,
                    "avg_task_duration": row[3] or 0.0
                }
            
            # Task metrics
            cursor.execute("""
            SELECT COUNT(*) as task_count,
                   AVG(duration) as avg_duration,
                   SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) * 100.0 / COUNT(*) as success_rate
            FROM task_metrics
            WHERE timestamp >= datetime('now', '-24 hours')
            """)
            
            row = cursor.fetchone()
            if row:
                summary["tasks"]["completed_count"] = row[0] or 0
                summary["tasks"]["avg_duration"] = row[1] or 0.0
                summary["tasks"]["success_rate"] = row[2] or 0.0
            
            # API metrics
            cursor.execute("""
            SELECT COUNT(*) as call_count,
                   AVG(response_time) as avg_response_time,
                   SUM(CASE WHEN success THEN 1 ELSE 0 END) * 100.0 / COUNT(*) as success_rate,
                   SUM(tokens_used) as total_tokens
            FROM api_metrics
            WHERE timestamp >= datetime('now', '-24 hours')
            """)
            
            row = cursor.fetchone()
            if row:
                summary["api"]["calls_count"] = row[0] or 0
                summary["api"]["avg_response_time"] = row[1] or 0.0
                summary["api"]["success_rate"] = row[2] or 0.0
                summary["api"]["total_tokens"] = row[3] or 0
            
            conn.close()
            
        except Exception as e:
            logger.error(f"Failed to get performance summary", str(e))
        
        return summary
    
    def _clean_old_data(self) -> None:
        """Clean up data older than the retention period."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            for table in ["system_metrics", "agent_metrics", "task_metrics", "api_metrics"]:
                cursor.execute(f"""
                DELETE FROM {table}
                WHERE timestamp < datetime('now', '-{RETENTION_DAYS} days')
                """)
            
            conn.commit()
            conn.close()
            
            logger.debug(f"Cleaned up data older than {RETENTION_DAYS} days")
            
        except Exception as e:
            logger.error(f"Failed to clean up old metrics data", str(e))


# Singleton instance
metrics_collector = MetricsCollector()

# Example usage
if __name__ == "__main__":
    # Start background collection
    metrics_collector.start_collection()
    
    # Add some sample metrics
    metrics_collector.record_api_call("agent1", "messages", 1.2, 200, 150, True)
    metrics_collector.record_task_completion("task123", "agent1", "data_analysis", 45.6, "completed", 3)
    
    # Show summary
    time.sleep(2)  # Wait for collection
    summary = metrics_collector.get_performance_summary()
    print(json.dumps(summary, indent=2))
    
    # Keep running for a bit to collect metrics
    try:
        print("Press Ctrl+C to exit")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        metrics_collector.stop_collection()
        print("Metrics collection stopped")