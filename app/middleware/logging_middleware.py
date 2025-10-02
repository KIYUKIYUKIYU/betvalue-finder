# -*- coding: utf-8 -*-
from fastapi import FastAPI, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
import time
import uuid
from typing import Callable
from app.logging_system import log_manager

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """リクエストログミドルウェア"""

    def __init__(self, app: FastAPI):
        super().__init__(app)
        self.log_manager = log_manager

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # リクエストIDの生成
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id

        # 開始時間の記録
        start_time = time.time()

        # リクエスト情報の収集
        request_info = {
            'request_id': request_id,
            'method': request.method,
            'path': request.url.path,
            'query_params': str(request.query_params) if request.query_params else None,
            'user_agent': request.headers.get('User-Agent'),
            'ip_address': request.client.host if request.client else None,
            'content_length': request.headers.get('Content-Length'),
        }

        try:
            # リクエスト処理
            response = await call_next(request)

            # 処理時間計算
            processing_time = time.time() - start_time

            # レスポンス情報追加
            request_info.update({
                'status_code': response.status_code,
                'processing_time': processing_time,
                'response_size': response.headers.get('Content-Length')
            })

            # ログ記録
            self.log_manager.log_request(request_info)

            # レスポンスヘッダーに情報追加
            response.headers['X-Request-ID'] = request_id
            response.headers['X-Processing-Time'] = f"{processing_time:.3f}s"

            return response

        except Exception as e:
            processing_time = time.time() - start_time
            request_info.update({
                'status_code': 500,
                'processing_time': processing_time
            })

            self.log_manager.log_request(request_info)
            self.log_manager.log_error("Request processing failed", e, request_info)
            raise

def setup_logging_middleware(app: FastAPI):
    """FastAPIアプリにログミドルウェアを追加"""
    app.add_middleware(RequestLoggingMiddleware)
    log_manager.main_logger.info("📊 Request logging middleware initialized")