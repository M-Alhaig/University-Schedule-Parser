"""
Simple metrics collection for monitoring
Metrics are logged and can be sent to CloudWatch
"""

import json
import logging
import time
from datetime import datetime
from functools import wraps
from typing import Any, Callable, Dict, List

import numpy as np

logger = logging.getLogger(__name__)


class Metrics:
    """Simple metrics collector with stage-level performance tracking"""

    def __init__(self):
        self.metrics: Dict[str, Any] = {
            "requests_total": 0,
            "requests_success": 0,
            "requests_failed": 0,
            "processing_times": [],
            "errors": [],
            "request_history": [],  # For dashboard visualization
            # Stage-specific timings
            "pdf_processing_times": [],
            "box_extraction_times": [],
            "ocr_processing_times": [],
            "calendar_generation_times": [],
        }

    def increment(self, metric_name: str, value: int = 1):
        """Increment a counter metric"""
        if metric_name not in self.metrics:
            self.metrics[metric_name] = 0
        self.metrics[metric_name] += value
        logger.debug(f"Metric {metric_name} incremented to {self.metrics[metric_name]}")

    def record_time(self, metric_name: str, duration_ms: float):
        """Record a timing metric"""
        if metric_name not in self.metrics:
            self.metrics[metric_name] = []
        self.metrics[metric_name].append(duration_ms)
        logger.debug(f"Recorded {metric_name}: {duration_ms:.2f}ms")

    def record_error(self, error_type: str, error_message: str):
        """Record an error"""
        error_entry = {"type": error_type, "message": error_message, "timestamp": datetime.now().isoformat()}
        self.metrics["errors"].append(error_entry)
        logger.info(f"Error recorded: {error_type} - {error_message}")

    def _calculate_percentiles(self, times: List[float]) -> Dict[str, float]:
        """Calculate percentiles for timing data"""
        if not times:
            return {}

        times_array = np.array(times)
        return {
            "p50": float(np.percentile(times_array, 50)),
            "p95": float(np.percentile(times_array, 95)),
            "p99": float(np.percentile(times_array, 99)),
        }

    def get_stats(self) -> Dict[str, Any]:
        """Get current metrics statistics"""
        stats = {
            "requests_total": self.metrics.get("requests_total", 0),
            "requests_success": self.metrics.get("requests_success", 0),
            "requests_failed": self.metrics.get("requests_failed", 0),
            "success_rate": 0.0,
        }

        # Calculate success rate
        total = stats["requests_total"]
        if total > 0:
            stats["success_rate"] = (stats["requests_success"] / total) * 100

        # Calculate average processing times
        processing_times = self.metrics.get("processing_times", [])
        if processing_times:
            stats["avg_processing_time_ms"] = sum(processing_times) / len(processing_times)
            stats["min_processing_time_ms"] = min(processing_times)
            stats["max_processing_time_ms"] = max(processing_times)

        # Recent errors
        stats["recent_errors_count"] = len(self.metrics.get("errors", []))

        return stats

    def get_detailed_stats(self) -> Dict[str, Any]:
        """Get detailed metrics with stage-level breakdown and percentiles"""
        stats = self.get_stats()

        # Add stage-specific timing breakdowns
        stages = {
            "pdf_processing": self.metrics.get("pdf_processing_times", []),
            "box_extraction": self.metrics.get("box_extraction_times", []),
            "ocr_processing": self.metrics.get("ocr_processing_times", []),
            "calendar_generation": self.metrics.get("calendar_generation_times", []),
        }

        stage_stats = {}
        for stage_name, times in stages.items():
            if times:
                stage_stats[stage_name] = {
                    "count": len(times),
                    "avg_ms": sum(times) / len(times),
                    "min_ms": min(times),
                    "max_ms": max(times),
                    **self._calculate_percentiles(times),
                }
            else:
                stage_stats[stage_name] = {"count": 0, "avg_ms": 0, "min_ms": 0, "max_ms": 0}

        stats["stages"] = stage_stats

        # Add overall percentiles
        processing_times = self.metrics.get("processing_times", [])
        if processing_times:
            stats["percentiles"] = self._calculate_percentiles(processing_times)

        return stats

    def log_metrics(self):
        """Log current metrics (for CloudWatch Logs Insights)"""
        stats = self.get_stats()
        logger.info(f"METRICS: {json.dumps(stats)}")

    def get_request_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get recent request history for dashboard display.

        Args:
            limit: Maximum number of recent requests to return

        Returns:
            List of request history entries
        """
        history = self.metrics.get("request_history", [])
        return history[-limit:]

    def add_request_to_history(self, status: str, duration_ms: float, error_type: str = None):
        """
        Add a request to the history tracking.

        Args:
            status: "success" or "failed"
            duration_ms: Processing time in milliseconds
            error_type: Type of error if failed
        """
        if "request_history" not in self.metrics:
            self.metrics["request_history"] = []

        entry = {
            "timestamp": datetime.now().isoformat(),
            "status": status,
            "duration_ms": duration_ms,
            "error_type": error_type,
        }

        self.metrics["request_history"].append(entry)

        # Keep only last 100 entries to avoid memory bloat
        if len(self.metrics["request_history"]) > 100:
            self.metrics["request_history"] = self.metrics["request_history"][-100:]

    def reset(self):
        """Reset all metrics"""
        self.metrics = {
            "requests_total": 0,
            "requests_success": 0,
            "requests_failed": 0,
            "processing_times": [],
            "errors": [],
            "request_history": [],
            "pdf_processing_times": [],
            "box_extraction_times": [],
            "ocr_processing_times": [],
            "calendar_generation_times": [],
        }
        logger.info("Metrics reset")


# Global metrics instance
metrics = Metrics()


def track_time(metric_name: str = "processing_time"):
    """
    Decorator to track execution time of a function

    Usage:
        @track_time("pdf_processing_time")
        async def process_pdf():
            ...
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                duration_ms = (time.time() - start_time) * 1000
                metrics.record_time(metric_name, duration_ms)
                logger.info(f"{func.__name__} completed in {duration_ms:.2f}ms")
                return result
            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000
                metrics.record_time(f"{metric_name}_failed", duration_ms)
                raise

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                duration_ms = (time.time() - start_time) * 1000
                metrics.record_time(metric_name, duration_ms)
                logger.info(f"{func.__name__} completed in {duration_ms:.2f}ms")
                return result
            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000
                metrics.record_time(f"{metric_name}_failed", duration_ms)
                raise

        # Return appropriate wrapper based on function type
        import inspect

        if inspect.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator
