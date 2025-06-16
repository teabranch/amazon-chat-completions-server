import logging
import time

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

logger = logging.getLogger(
    __name__
)  # Using root logger for simplicity, configure as needed


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        start_time = time.time()

        # Log request details before processing
        # logger.info(f"Incoming request: {request.method} {request.url.path} from {request.client.host}")
        # To avoid logging body for now due to potential size/sensitivity, and reading it consumes it.

        response = await call_next(request)

        process_time = (time.time() - start_time) * 1000
        formatted_process_time = f"{process_time:.2f}ms"

        client_host = request.client.host if request.client else "unknown"
        logger.info(
            f"Request: {request.method} {request.url.path} from {client_host} - Response: {response.status_code} - Time: {formatted_process_time}"
        )
        return response
