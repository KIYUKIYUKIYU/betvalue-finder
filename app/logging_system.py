# -*- coding: utf-8 -*-
import logging
import logging.handlers
import json
import traceback
from datetime import datetime
from typing import Dict, Any, Optional
from contextlib import contextmanager
import time
import psutil
import threading
from pathlib import Path
import os

# カスタムログレベル定義
PIPELINE_SUCCESS = 25  # INFO と WARNING の間
BUSINESS_WARNING = 35  # WARNING と ERROR の間

logging.addLevelName(PIPELINE_SUCCESS, "PIPELINE_SUCCESS")
logging.addLevelName(BUSINESS_WARNING, "BUSINESS_WARNING")

class BetValueLogManager:
    def __init__(self,
                 log_dir: str = "logs",
                 max_file_size: int = 10*1024*1024,  # 10MB
                 backup_count: int = 5,
                 enable_console: bool = True,
                 enable_file: bool = True,
                 enable_structured: bool = True):

        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)

        # ログ設定
        self.setup_loggers(max_file_size, backup_count, enable_console,
                          enable_file, enable_structured)

        # メトリクス収集
        self.metrics = {
            'requests': 0,
            'errors': 0,
            'pipeline_successes': 0,
            'pipeline_failures': 0,
            'avg_response_time': 0.0,
            'system_health': {},
            'startup_time': datetime.utcnow().isoformat()
        }

        # パフォーマンス監視スレッド
        self.monitoring_active = True
        self.monitoring_thread = threading.Thread(target=self._system_monitoring, daemon=True)
        self.monitoring_thread.start()

        # 初期化ログ
        self.main_logger.info("🚀 BetValue Finder Logging System initialized")
        self.main_logger.info(f"📁 Log directory: {self.log_dir.absolute()}")

    def setup_loggers(self, max_file_size, backup_count, enable_console, enable_file, enable_structured):
        # メインロガー
        self.main_logger = logging.getLogger('betvalue.main')
        self.main_logger.setLevel(logging.DEBUG)

        # Pipeline専用ロガー
        self.pipeline_logger = logging.getLogger('betvalue.pipeline')
        self.pipeline_logger.setLevel(logging.DEBUG)

        # API専用ロガー
        self.api_logger = logging.getLogger('betvalue.api')
        self.api_logger.setLevel(logging.DEBUG)

        # エラー専用ロガー
        self.error_logger = logging.getLogger('betvalue.errors')
        self.error_logger.setLevel(logging.WARNING)

        # 既存ハンドラーをクリア
        for logger in [self.main_logger, self.pipeline_logger, self.api_logger, self.error_logger]:
            logger.handlers.clear()

        # フォーマッター
        detailed_formatter = logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(name)s:%(lineno)d | %(message)s'
        )

        json_formatter = self.JSONFormatter()

        # コンソールハンドラー
        if enable_console:
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(detailed_formatter)
            console_handler.setLevel(logging.INFO)  # コンソールは INFO 以上のみ
            self.main_logger.addHandler(console_handler)

        # ファイルハンドラー
        if enable_file:
            # ローテーションファイルハンドラー
            main_file_handler = logging.handlers.RotatingFileHandler(
                self.log_dir / 'betvalue_main.log',
                maxBytes=max_file_size,
                backupCount=backup_count,
                encoding='utf-8'
            )
            main_file_handler.setFormatter(detailed_formatter)
            self.main_logger.addHandler(main_file_handler)

            # Pipeline専用ファイル
            pipeline_file_handler = logging.handlers.RotatingFileHandler(
                self.log_dir / 'pipeline.log',
                maxBytes=max_file_size,
                backupCount=backup_count,
                encoding='utf-8'
            )
            pipeline_file_handler.setFormatter(detailed_formatter)
            self.pipeline_logger.addHandler(pipeline_file_handler)

            # エラー専用ファイル
            error_file_handler = logging.handlers.RotatingFileHandler(
                self.log_dir / 'errors.log',
                maxBytes=max_file_size,
                backupCount=backup_count,
                encoding='utf-8'
            )
            error_file_handler.setFormatter(detailed_formatter)
            self.error_logger.addHandler(error_file_handler)

        # 構造化JSONログ
        if enable_structured:
            json_handler = logging.handlers.RotatingFileHandler(
                self.log_dir / 'structured.jsonl',
                maxBytes=max_file_size,
                backupCount=backup_count,
                encoding='utf-8'
            )
            json_handler.setFormatter(json_formatter)

            # 全ロガーに構造化ログハンドラーを追加
            for logger in [self.main_logger, self.pipeline_logger, self.api_logger, self.error_logger]:
                logger.addHandler(json_handler)

    class JSONFormatter(logging.Formatter):
        def format(self, record):
            log_entry = {
                'timestamp': datetime.utcnow().isoformat(),
                'level': record.levelname,
                'logger': record.name,
                'module': record.module,
                'function': record.funcName,
                'line': record.lineno,
                'message': record.getMessage(),
                'thread': record.thread,
                'process': record.process
            }

            # 追加のカスタムフィールド
            if hasattr(record, 'extra_data'):
                log_entry.update(record.extra_data)

            # 例外情報
            if record.exc_info and record.exc_info[0] is not None:
                log_entry['exception'] = {
                    'type': record.exc_info[0].__name__,
                    'message': str(record.exc_info[1]),
                    'traceback': traceback.format_exception(*record.exc_info)
                }

            return json.dumps(log_entry, ensure_ascii=False)

    @contextmanager
    def log_performance(self, operation_name: str, logger_name: str = 'main'):
        """パフォーマンス測定付きログ"""
        logger = getattr(self, f'{logger_name}_logger')
        start_time = time.time()

        logger.info(f"🚀 Starting {operation_name}")

        try:
            yield
            elapsed = time.time() - start_time
            logger.info(f"✅ Completed {operation_name} in {elapsed:.3f}s")

        except Exception as e:
            elapsed = time.time() - start_time
            logger.error(f"❌ Failed {operation_name} after {elapsed:.3f}s: {str(e)}")
            self.log_error(f"Performance tracking error in {operation_name}", e)
            raise

    def log_request(self, request_info: Dict[str, Any]):
        """APIリクエストログ"""
        extra_data = {
            'event_type': 'api_request',
            'request_id': request_info.get('request_id'),
            'method': request_info.get('method'),
            'path': request_info.get('path'),
            'query_params': request_info.get('query_params'),
            'user_agent': request_info.get('user_agent'),
            'ip_address': request_info.get('ip_address'),
            'processing_time': request_info.get('processing_time')
        }

        status_code = request_info.get('status_code', 0)
        processing_time = request_info.get('processing_time', 0)

        self.api_logger.info(
            f"API {request_info['method']} {request_info['path']} - "
            f"{status_code} ({processing_time:.3f}s)",
            extra={'extra_data': extra_data}
        )

        # メトリクス更新
        self.metrics['requests'] += 1
        if status_code >= 400:
            self.metrics['errors'] += 1

        # 平均応答時間更新
        if self.metrics['avg_response_time'] == 0:
            self.metrics['avg_response_time'] = processing_time
        else:
            self.metrics['avg_response_time'] = (
                (self.metrics['avg_response_time'] * (self.metrics['requests'] - 1) + processing_time) /
                self.metrics['requests']
            )

    def log_pipeline_stage(self, stage_info: Dict[str, Any]):
        """Pipeline段階ログ"""
        extra_data = {
            'event_type': 'pipeline_stage',
            'stage_name': stage_info.get('stage_name'),
            'success': stage_info.get('success'),
            'processing_time': stage_info.get('processing_time'),
            'input_data': stage_info.get('input_summary'),
            'output_data': stage_info.get('output_summary'),
            'quality_metrics': stage_info.get('quality_metrics'),
            'error_message': stage_info.get('error_message')
        }

        stage_name = stage_info.get('stage_name', 'Unknown')
        processing_time = stage_info.get('processing_time', 0)

        if stage_info.get('success'):
            self.pipeline_logger.log(
                PIPELINE_SUCCESS,
                f"✅ {stage_name} completed successfully ({processing_time:.3f}s)",
                extra={'extra_data': extra_data}
            )
            self.metrics['pipeline_successes'] += 1
        else:
            error_msg = stage_info.get('error_message', 'Unknown error')
            self.pipeline_logger.error(
                f"❌ {stage_name} failed: {error_msg}",
                extra={'extra_data': extra_data}
            )
            self.metrics['pipeline_failures'] += 1

    def log_error(self, message: str, error: Exception,
                  context: Optional[Dict[str, Any]] = None):
        """エラーログ（トレースバック付き）"""
        extra_data = {
            'event_type': 'error',
            'error_type': type(error).__name__,
            'error_message': str(error),
            'context': context or {}
        }

        self.error_logger.error(
            f"🚨 {message}: {str(error)}",
            exc_info=True,
            extra={'extra_data': extra_data}
        )

    def log_business_event(self, event_type: str, details: Dict[str, Any]):
        """ビジネスロジック関連のログ"""
        extra_data = {
            'event_type': 'business',
            'business_event': event_type,
            'details': details
        }

        if event_type in ['low_confidence_mapping', 'unusual_odds', 'api_limit_warning']:
            self.main_logger.log(
                BUSINESS_WARNING,
                f"⚠️ Business Warning: {event_type}",
                extra={'extra_data': extra_data}
            )
        else:
            self.main_logger.info(
                f"📊 Business Event: {event_type}",
                extra={'extra_data': extra_data}
            )

    def pipeline_success(self, message, extra=None):
        """Pipeline成功ログ"""
        self.pipeline_logger.log(PIPELINE_SUCCESS, message, extra=extra)

    def business_warning(self, message, extra=None):
        """ビジネス警告ログ"""
        self.main_logger.log(BUSINESS_WARNING, message, extra=extra)

    def _system_monitoring(self):
        """システム監視バックグラウンドタスク"""
        while self.monitoring_active:
            try:
                # システムメトリクス収集
                cpu_percent = psutil.cpu_percent(interval=1)
                memory = psutil.virtual_memory()
                disk = psutil.disk_usage('/')

                self.metrics['system_health'] = {
                    'cpu_percent': cpu_percent,
                    'memory_percent': memory.percent,
                    'memory_used_gb': round(memory.used / (1024**3), 2),
                    'memory_total_gb': round(memory.total / (1024**3), 2),
                    'disk_percent': disk.percent,
                    'disk_used_gb': round(disk.used / (1024**3), 2),
                    'disk_total_gb': round(disk.total / (1024**3), 2),
                    'timestamp': datetime.utcnow().isoformat()
                }

                # 異常値チェック
                if cpu_percent > 80:
                    self.main_logger.warning(f"🔥 High CPU usage: {cpu_percent}%")

                if memory.percent > 85:
                    self.main_logger.warning(f"🧠 High memory usage: {memory.percent}%")

                if disk.percent > 90:
                    self.main_logger.warning(f"💾 High disk usage: {disk.percent}%")

                time.sleep(60)  # 1分間隔で監視

            except Exception as e:
                self.main_logger.error(f"System monitoring error: {str(e)}")
                time.sleep(60)

    def get_metrics(self) -> Dict[str, Any]:
        """メトリクス取得"""
        metrics = self.metrics.copy()

        # 追加情報
        metrics['pipeline_total'] = metrics['pipeline_successes'] + metrics['pipeline_failures']
        metrics['pipeline_success_rate'] = (
            (metrics['pipeline_successes'] / metrics['pipeline_total'] * 100)
            if metrics['pipeline_total'] > 0 else 0
        )
        metrics['error_rate'] = (
            (metrics['errors'] / metrics['requests'] * 100)
            if metrics['requests'] > 0 else 0
        )

        return metrics

    def export_logs(self, hours: int = 24, format: str = 'json') -> str:
        """ログエクスポート"""
        export_data = {
            'export_time': datetime.utcnow().isoformat(),
            'hours_requested': hours,
            'format': format,
            'metrics': self.get_metrics(),
            'note': 'Full log parsing implementation requires additional development'
        }

        if format == 'json':
            return json.dumps(export_data, indent=2, ensure_ascii=False)
        else:
            return str(export_data)

    def shutdown(self):
        """ログシステム終了"""
        self.monitoring_active = False
        self.main_logger.info("🔚 BetValue Finder Logging System shutdown")

        # ハンドラーのクリーンアップ
        for logger in [self.main_logger, self.pipeline_logger, self.api_logger, self.error_logger]:
            for handler in logger.handlers:
                handler.close()

# グローバルログマネージャーインスタンス
log_manager = BetValueLogManager()

def get_log_manager() -> BetValueLogManager:
    """ログマネージャーを取得"""
    return log_manager