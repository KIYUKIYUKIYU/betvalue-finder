# -*- coding: utf-8 -*-
from fastapi import APIRouter, Request, HTTPException
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from app.logging_system import log_manager
import json
from datetime import datetime, timedelta

router = APIRouter(prefix="/api/v1/log", tags=["logging"])

class FrontendLogEntry(BaseModel):
    session_id: str
    user_id: str
    timestamp: str
    level: str
    type: str
    message: Optional[str] = None
    # その他のフィールドは動的に追加

class BatchLogRequest(BaseModel):
    logs: List[Dict[str, Any]]

@router.post("/frontend")
async def log_frontend_event(log_entry: Dict[str, Any]):
    """フロントエンドからのログエントリー受信"""
    try:
        # フロントエンドログを構造化ログに記録
        log_manager.main_logger.info(
            f"Frontend: {log_entry.get('type', 'unknown')} - {log_entry.get('message', '')}",
            extra={'extra_data': {
                'event_type': 'frontend_log',
                'frontend_data': log_entry
            }}
        )

        return {"status": "logged", "timestamp": datetime.utcnow().isoformat()}

    except Exception as e:
        log_manager.log_error("Frontend logging failed", e, {"log_entry": log_entry})
        raise HTTPException(status_code=500, detail="Logging failed")

@router.post("/frontend/batch")
async def log_frontend_batch(batch_request: BatchLogRequest):
    """フロントエンドからのバッチログ受信"""
    try:
        processed_count = 0
        for log_entry in batch_request.logs:
            log_manager.main_logger.info(
                f"Frontend Batch: {log_entry.get('type', 'unknown')}",
                extra={'extra_data': {
                    'event_type': 'frontend_batch_log',
                    'frontend_data': log_entry
                }}
            )
            processed_count += 1

        return {"status": "batch_logged", "count": processed_count}

    except Exception as e:
        log_manager.log_error("Frontend batch logging failed", e)
        raise HTTPException(status_code=500, detail="Batch logging failed")

@router.get("/metrics")
async def get_metrics():
    """システムメトリクス取得"""
    try:
        metrics = log_manager.get_metrics()
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "metrics": metrics
        }
    except Exception as e:
        log_manager.log_error("Metrics retrieval failed", e)
        raise HTTPException(status_code=500, detail="Metrics unavailable")

@router.get("/health")
async def health_check():
    """システム健全性チェック"""
    try:
        metrics = log_manager.get_metrics()
        system_health = metrics.get('system_health', {})

        # 健全性判定
        cpu_ok = system_health.get('cpu_percent', 100) < 90
        memory_ok = system_health.get('memory_percent', 100) < 90
        disk_ok = system_health.get('disk_percent', 100) < 95

        overall_status = "healthy" if (cpu_ok and memory_ok and disk_ok) else "warning"

        # エラー率チェック
        error_rate = metrics.get('error_rate', 0)
        if error_rate > 10:  # 10%以上のエラー率
            overall_status = "error"

        return {
            "status": overall_status,
            "system_health": system_health,
            "error_rate": error_rate,
            "pipeline_success_rate": metrics.get('pipeline_success_rate', 0),
            "timestamp": datetime.utcnow().isoformat(),
            "checks": {
                "cpu_ok": cpu_ok,
                "memory_ok": memory_ok,
                "disk_ok": disk_ok,
                "error_rate_ok": error_rate <= 10
            }
        }

    except Exception as e:
        log_manager.log_error("Health check failed", e)
        return {
            "status": "error",
            "message": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }

@router.get("/errors/recent")
async def get_recent_errors(hours: int = 24):
    """最近のエラー取得"""
    try:
        metrics = log_manager.get_metrics()
        return {
            "message": f"Recent errors from last {hours} hours",
            "total_errors": metrics.get('errors', 0),
            "error_rate": f"{metrics.get('error_rate', 0):.2f}%",
            "pipeline_failures": metrics.get('pipeline_failures', 0),
            "timestamp": datetime.utcnow().isoformat(),
            "note": "Detailed error parsing requires log file analysis"
        }
    except Exception as e:
        log_manager.log_error("Recent errors retrieval failed", e)
        raise HTTPException(status_code=500, detail="Error retrieval failed")

@router.get("/export")
async def export_logs(hours: int = 24, format: str = 'json'):
    """ログエクスポート"""
    try:
        exported_data = log_manager.export_logs(hours, format)
        return {
            "export_time": datetime.utcnow().isoformat(),
            "hours": hours,
            "format": format,
            "data": json.loads(exported_data) if format == 'json' else exported_data
        }
    except Exception as e:
        log_manager.log_error("Log export failed", e)
        raise HTTPException(status_code=500, detail="Export failed")

@router.get("/stats")
async def get_system_stats():
    """詳細システム統計"""
    try:
        metrics = log_manager.get_metrics()

        # 追加統計計算
        total_requests = metrics.get('requests', 0)
        total_errors = metrics.get('errors', 0)
        pipeline_total = metrics.get('pipeline_total', 0)

        return {
            "timestamp": datetime.utcnow().isoformat(),
            "requests": {
                "total": total_requests,
                "errors": total_errors,
                "success_rate": ((total_requests - total_errors) / total_requests * 100) if total_requests > 0 else 100,
                "avg_response_time": metrics.get('avg_response_time', 0)
            },
            "pipeline": {
                "total_executions": pipeline_total,
                "successes": metrics.get('pipeline_successes', 0),
                "failures": metrics.get('pipeline_failures', 0),
                "success_rate": metrics.get('pipeline_success_rate', 0)
            },
            "system": metrics.get('system_health', {}),
            "uptime_since": metrics.get('startup_time')
        }
    except Exception as e:
        log_manager.log_error("System stats retrieval failed", e)
        raise HTTPException(status_code=500, detail="Stats retrieval failed")