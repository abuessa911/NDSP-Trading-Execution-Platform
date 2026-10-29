"""Isolated SDK/transport probe; never certifies deployed observability."""
from __future__ import annotations
import asyncio
import gzip
import json
import os
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit
from uuid import uuid4

def run():
    import sentry_sdk
    from sentry_sdk.integrations.fastapi import FastApiIntegration
    from sentry_sdk.integrations.starlette import StarletteIntegration
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from nex_api.config import Settings
    from nex_api.main import create_app
    from opentelemetry import trace
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import SimpleSpanProcessor
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
    from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
    from opentelemetry.proto.collector.trace.v1.trace_service_pb2 import ExportTraceServiceRequest
    from sqlalchemy import text
    from sqlalchemy.pool import NullPool
    from sqlalchemy.ext.asyncio import create_async_engine

    received = []
    checks = []
    def check(name, condition):
        checks.append({"check": name, "passed": bool(condition)})
        return bool(condition)
    class Receiver(BaseHTTPRequestHandler):
        def do_POST(self):
            body = self.rfile.read(int(self.headers.get("Content-Length", "0")))
            if self.headers.get("Content-Encoding") == "gzip":
                body = gzip.decompress(body)
            received.append((self.path, body))
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"{}")
        def log_message(self, *_):
            pass

    receiver = ThreadingHTTPServer(("127.0.0.1", 0), Receiver)
    threading.Thread(target=receiver.serve_forever, daemon=True).start()
    address = "http://127.0.0.1:" + str(receiver.server_port)
    service = "hunter-isolated-qa"
    provider = TracerProvider(resource=Resource.create({"service.name": service}))
    exporter = OTLPSpanExporter(endpoint=address + "/v1/traces", timeout=4)
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    trace.set_tracer_provider(provider)
    def scrub(event, hint):
        for key in ("request", "user", "breadcrumbs", "extra"):
            event.pop(key, None)
        return event
    sentry_sdk.init(
        dsn=address.replace("http://", "http://qa@") + "/1",
        default_integrations=False,
        integrations=[StarletteIntegration(), FastApiIntegration()],
        send_default_pii=False, include_local_variables=False,
        before_send=scrub, traces_sample_rate=0.0,
        environment="isolated-qa", release="qa-only",
    )

    app = create_app(Settings(
        _env_file=None, environment="test", database_url=None,
        migration_database_url=None, redis_url=None, oidc_issuer=None,
        oidc_jwks_url=None, oidc_audience=None, oidc_browser_login_enabled=False,
        hunter_market_monitor_enabled=False, hunter_paper_enabled=False,
        hunter_testnet_execution_enabled=False, secret_provider="env",
    ))
    FastAPIInstrumentor.instrument_app(app, tracer_provider=provider)
    @app.get("/__qa__/controlled-failure", include_in_schema=False)
    async def controlled_failure():
        # Only this disposable app instance has this endpoint.
        raise RuntimeError("QA_CONTROLLED_FAILURE")
    @app.middleware("http")
    async def record_correlation(request, call_next):
        response = await call_next(request)
        correlation = response.headers.get("x-correlation-id")
        if correlation:
            trace.get_current_span().set_attribute("qa.correlation_id", correlation)
        return response

    engine = None
    database_url = os.environ.get("QA_OTEL_DATABASE_URL")
    if database_url:
        parsed = urlsplit(database_url)
        if (parsed.hostname not in {"127.0.0.1", "localhost"}
                or parsed.port != 15432 or parsed.path != "/ndsp_qa_telemetry"):
            raise RuntimeError("Only the dedicated disposable QA database is allowed")
        engine = create_async_engine(database_url, poolclass=NullPool)
        SQLAlchemyInstrumentor().instrument(engine=engine.sync_engine)
        @app.get("/__qa__/database", include_in_schema=False)
        async def database_roundtrip():
            marker = str(uuid4())
            async with engine.begin() as connection:
                await connection.execute(text(
                    "CREATE TABLE IF NOT EXISTS qa_telemetry_roundtrip "
                    "(id text PRIMARY KEY, value text NOT NULL)"
                ))
                await connection.execute(text(
                    "INSERT INTO qa_telemetry_roundtrip(id,value) VALUES (:id,:value)"
                ), {"id": marker, "value": "isolated-probe"})
            async with engine.connect() as connection:
                restored = (await connection.execute(text(
                    "SELECT value FROM qa_telemetry_roundtrip WHERE id=:id"
                ), {"id": marker})).scalar_one()
            async with engine.begin() as connection:
                await connection.execute(text(
                    "DELETE FROM qa_telemetry_roundtrip WHERE id=:id"
                ), {"id": marker})
            return {"persisted": restored == "isolated-probe"}

    health_trace = "11111111111111111111111111111111"
    error_trace = "22222222222222222222222222222222"
    db_trace = "33333333333333333333333333333333"
    def headers(trace_id):
        return {"traceparent": "00-" + trace_id + "-4444444444444444-01",
                "sentry-trace": trace_id + "-4444444444444444-1",
                "Authorization": "Bearer QA_CANARY_NEVER_EXPORT"}
    baseline = FastAPI()
    @baseline.get("/__qa__/framework-control")
    async def framework_control():
        raise RuntimeError("QA_FRAMEWORK_CONTROL")
    try:
        with TestClient(baseline, raise_server_exceptions=False) as baseline_client:
            baseline_client.get("/__qa__/framework-control")
        with TestClient(app, raise_server_exceptions=False) as client:
            health = client.get("/api/health/live", headers=headers(health_trace))
            check("actual API health handler HTTP 200", health.status_code == 200)
            check("application correlation header exists",
                  bool(health.headers.get("x-correlation-id")))
            failure = client.get("/__qa__/controlled-failure", headers=headers(error_trace))
            check("controlled failure returns HTTP 500", failure.status_code == 500)
            check("error response excludes exception internals",
                  "QA_CONTROLLED_FAILURE" not in failure.text)
            if engine is not None:
                db_response = client.get("/__qa__/database", headers=headers(db_trace))
                check("dedicated PostgreSQL commit and independent read",
                      db_response.status_code == 200 and db_response.json().get("persisted"))
        sentry_sdk.capture_message("QA_TRANSPORT_CONTROL")
        provider.force_flush()
        sentry_sdk.flush(timeout=8)
        time.sleep(0.1)
        spans = []
        service_found = False
        events = []
        transport_controls = []
        framework_events = []
        for path, body in received:
            if path == "/v1/traces":
                message = ExportTraceServiceRequest()
                message.ParseFromString(body)
                for resource in message.resource_spans:
                    service_found |= any(
                        a.key == "service.name" and a.value.string_value == service
                        for a in resource.resource.attributes
                    )
                    for scope in resource.scope_spans:
                        spans.extend(scope.spans)
            elif "/envelope/" in path:
                for line in body.splitlines():
                    try:
                        event = json.loads(line)
                    except (ValueError, UnicodeDecodeError):
                        continue
                    if isinstance(event, dict) and event.get("message") == "QA_TRANSPORT_CONTROL":
                        transport_controls.append(event)
                    if isinstance(event, dict) and "exception" in event:
                        exception_text = json.dumps(event["exception"])
                        if "QA_CONTROLLED_FAILURE" in exception_text:
                            events.append(event)
                        elif "QA_FRAMEWORK_CONTROL" in exception_text:
                            framework_events.append(event)
        health_spans = [s for s in spans if s.trace_id.hex() == health_trace]
        error_spans = [s for s in spans if s.trace_id.hex() == error_trace]
        check("OTLP protobuf delivered to local HTTP receiver", bool(spans))
        check("exported service.name identifies isolated app", service_found)
        check("incoming W3C trace ID preserved", bool(health_spans))
        check("application correlation ID joined to health trace",
              any(a.key == "qa.correlation_id"
                  and a.value.string_value == health.headers.get("x-correlation-id")
                  for s in health_spans for a in s.attributes))
        check("error trace exported with ERROR status",
              any(s.status.code == 2 for s in error_spans))
        check("Sentry HTTP transport positive control delivered", bool(transport_controls))
        check("reference FastAPI automatic exception capture works", bool(framework_events))
        check("Sentry automatically captures controlled application exception", bool(events))
        check("Sentry error envelope delivered with matching trace ID",
              any(e.get("contexts", {}).get("trace", {}).get("trace_id") == error_trace
                  for e in events))
        check("Sentry event contains useful exception cause",
              any("QA_CONTROLLED_FAILURE" in json.dumps(e) for e in events))
        check("authorization canary absent from Sentry payload",
              bool(events) and all("QA_CANARY_NEVER_EXPORT" not in json.dumps(e) for e in events))
        if engine is not None:
            db_spans = [s for s in spans if s.trace_id.hex() == db_trace]
            db_statements = [a.value.string_value for s in db_spans for a in s.attributes
                             if a.key in {"db.statement", "db.query.text"}]
            check("database spans share the API trace ID",
                  any("INSERT INTO" in s for s in db_statements)
                  and any("SELECT value" in s for s in db_statements))
            check("SQL query values stay parameterized",
                  all("isolated-probe" not in s for s in db_statements))
        result = {"scope": "isolated source app plus QA-only error/database routes",
                  "deployed_telemetry_certified": False,
                  "database_probe_run": engine is not None,
                  "otlp_span_count": len(spans), "sentry_error_count": len(events),
                  "sentry_transport_control_count": len(transport_controls),
                  "sentry_framework_control_count": len(framework_events),
                  "checks": checks,
                  "passed": all(c["passed"] for c in checks)}
        destination = Path(os.environ.get("QA_TELEMETRY_RESULT", "telemetry-verdict.json"))
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps(result, indent=2) + "\n")
        print(json.dumps(result, indent=2))
        return 0 if result["passed"] else 1
    finally:
        if engine is not None:
            asyncio.run(engine.dispose())
        provider.shutdown()
        sentry_sdk.get_client().close(timeout=2)
        receiver.shutdown()
        receiver.server_close()

if __name__ == "__main__":
    raise SystemExit(run())
