"""
Teste de Estresse até o Limite (Breakpoint / Curva de Saturação)
Sobe progressivamente a concorrência (VUs) para cada uma das 8 implementações
até atingir o critério de ruptura de SLA:
  - Taxa de erro >= 5.0% (timeouts de 5s / recusas de conexão / erros 5xx) OU
  - Latência p95 >= 3000 ms (3 segundos) OU
  - Teto máximo da rampa (1000 VUs)

Saídas:
  - /app/results/stress_results.json
  - /app/results/stress_summary.csv
"""

import argparse
import asyncio
import csv
import json
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Awaitable, Callable, Dict, List

import grpc
import httpx
import numpy as np

import music_streaming_pb2 as pb2
import music_streaming_pb2_grpc as pb2_grpc

SOAP_NS = "http://schemas.xmlsoap.org/soap/envelope/"
TNS = "http://streaming.example.com/soap"

SOAP_LIST_SONGS_BODY = (
    f'<?xml version="1.0" encoding="UTF-8"?>'
    f'<soap:Envelope xmlns:soap="{SOAP_NS}" xmlns:tns="{TNS}">'
    f"<soap:Body><tns:ListSongsRequest/></soap:Body>"
    f"</soap:Envelope>"
).encode("utf-8")

GQL_LIST_SONGS_PAYLOAD = {"query": "{ songs { id name artist } }"}

STEPS = [10, 25, 50, 100, 200, 350, 500, 750, 1000]
P95_BREAK_MS = 3000.0
ERROR_BREAK_PCT = 5.0
REQ_TIMEOUT_S = 5.0


@dataclass
class StressPoint:
    service_id: str
    language: str
    protocol: str
    concurrency: int
    duration_s: float
    total_requests: int
    errors: int
    error_rate_pct: float
    rps: float
    p50_ms: float
    p95_ms: float
    p99_ms: float
    breached: bool
    breach_reason: str


SERVICES = [
    ("python-rest", "Python", "REST", "http://python-rest:8001"),
    ("python-soap", "Python", "SOAP", "http://python-soap:8002/soap"),
    ("python-graphql", "Python", "GraphQL", "http://python-graphql:8003/graphql"),
    ("python-grpc", "Python", "gRPC", "python-grpc:50051"),
    ("node-rest", "Node.js (TS)", "REST", "http://node-rest:8101"),
    ("node-soap", "Node.js (TS)", "SOAP", "http://node-soap:8102/soap"),
    ("node-graphql", "Node.js (TS)", "GraphQL", "http://node-graphql:8103/graphql"),
    ("node-grpc", "Node.js (TS)", "gRPC", "node-grpc:50052"),
]


async def measure_step(
    op_fn: Callable[[int], Awaitable[None]],
    service_id: str,
    language: str,
    protocol: str,
    concurrency: int,
    duration_s: float,
) -> StressPoint:
    latencies_ms: List[float] = []
    errors = 0

    start = time.perf_counter()
    deadline = start + duration_s

    async def worker(wid: int):
        nonlocal errors
        idx = wid
        while time.perf_counter() < deadline:
            t0 = time.perf_counter()
            try:
                await asyncio.wait_for(op_fn(idx), timeout=REQ_TIMEOUT_S)
                latencies_ms.append((time.perf_counter() - t0) * 1000.0)
            except Exception:
                errors += 1
            idx += concurrency

    await asyncio.gather(*(worker(w) for w in range(concurrency)))
    elapsed = time.perf_counter() - start

    ok = len(latencies_ms)
    total = ok + errors
    err_pct = (errors / total * 100.0) if total > 0 else 100.0

    if ok > 0:
        arr = np.array(latencies_ms, dtype=np.float64)
        p50 = float(np.percentile(arr, 50))
        p95 = float(np.percentile(arr, 95))
        p99 = float(np.percentile(arr, 99))
    else:
        p50 = p95 = p99 = REQ_TIMEOUT_S * 1000.0

    reasons = []
    if err_pct >= ERROR_BREAK_PCT:
        reasons.append(f"err={err_pct:.1f}%>={ERROR_BREAK_PCT:.0f}%")
    if p95 >= P95_BREAK_MS:
        reasons.append(f"p95={p95:.0f}ms>={P95_BREAK_MS:.0f}ms")
    breached = len(reasons) > 0
    reason = " | ".join(reasons) if breached else "OK"

    pt = StressPoint(
        service_id=service_id,
        language=language,
        protocol=protocol,
        concurrency=concurrency,
        duration_s=round(elapsed, 2),
        total_requests=total,
        errors=errors,
        error_rate_pct=round(err_pct, 2),
        rps=round(ok / elapsed, 2),
        p50_ms=round(p50, 2),
        p95_ms=round(p95, 2),
        p99_ms=round(p99, 2),
        breached=breached,
        breach_reason=reason,
    )
    flag = f" <<< LIMITE ({reason})" if breached else ""
    print(
        f"[{service_id:14s}] VUs={concurrency:4d} | RPS={pt.rps:7.1f} | "
        f"p50={pt.p50_ms:7.1f}ms | p95={pt.p95_ms:7.1f}ms | err={pt.error_rate_pct:5.1f}%{flag}",
        flush=True,
    )
    return pt


async def run_stress(duration_s: float):
    all_points: List[StressPoint] = []
    breakpoints: Dict[str, Dict] = {}

    limits = httpx.Limits(max_connections=1200, max_keepalive_connections=600)

    print("=" * 108)
    print(
        f"INICIANDO TESTE DE ESTRESSE ATE O LIMITE (rampa={STEPS}, "
        f"SLA: p95<{P95_BREAK_MS:.0f}ms e erro<{ERROR_BREAK_PCT:.0f}%, timeout={REQ_TIMEOUT_S}s)"
    )
    print("=" * 108)

    for service_id, language, protocol, endpoint in SERVICES:
        service_pts: List[StressPoint] = []

        if protocol == "gRPC":
            # Pool de 8 canais HTTP/2 para não limitar artificialmente o cliente em 100 streams
            channels = [
                grpc.aio.insecure_channel(
                    endpoint,
                    options=[("grpc.use_local_subchannel_pool", 1)],
                )
                for _ in range(8)
            ]
            stubs = [pb2_grpc.MusicStreamingServiceStub(ch) for ch in channels]

            async def op_grpc(idx: int):
                await stubs[idx % len(stubs)].ListSongs(pb2.Empty(), timeout=REQ_TIMEOUT_S)

            # Warmup rápido
            for i in range(10):
                try:
                    await op_grpc(i)
                except Exception:
                    pass

            for vus in STEPS:
                pt = await measure_step(op_grpc, service_id, language, protocol, vus, duration_s)
                service_pts.append(pt)
                all_points.append(pt)
                if pt.breached:
                    break
                await asyncio.sleep(0.5)

            for ch in channels:
                await ch.close()
        else:
            base = endpoint if protocol == "REST" else ""
            async with httpx.AsyncClient(base_url=base, limits=limits, timeout=REQ_TIMEOUT_S) as client:
                if protocol == "REST":
                    async def op_http(_idx: int):
                        r = await client.get("/songs")
                        r.raise_for_status()
                elif protocol == "SOAP":
                    async def op_http(_idx: int):
                        r = await client.post(
                            endpoint,
                            content=SOAP_LIST_SONGS_BODY,
                            headers={"Content-Type": "text/xml; charset=utf-8", "SOAPAction": '"ListSongs"'},
                        )
                        r.raise_for_status()
                else:
                    async def op_http(_idx: int):
                        r = await client.post(endpoint, json=GQL_LIST_SONGS_PAYLOAD)
                        r.raise_for_status()
                        if "errors" in r.json():
                            raise RuntimeError("GraphQL error")

                # Warmup rápido
                for i in range(10):
                    try:
                        await op_http(i)
                    except Exception:
                        pass

                for vus in STEPS:
                    pt = await measure_step(op_http, service_id, language, protocol, vus, duration_s)
                    service_pts.append(pt)
                    all_points.append(pt)
                    if pt.breached:
                        break
                    await asyncio.sleep(0.5)

        ok_pts = [p for p in service_pts if not p.breached]
        peak_rps = max((p.rps for p in service_pts), default=0.0)
        max_ok_vus = max((p.concurrency for p in ok_pts), default=0)
        last_pt = service_pts[-1]
        breakpoints[service_id] = {
            "language": language,
            "protocol": protocol,
            "max_sustainable_vus": max_ok_vus,
            "breakpoint_vus": last_pt.concurrency if last_pt.breached else None,
            "breach_reason": last_pt.breach_reason if last_pt.breached else "Não atingiu ruptura até 1000 VUs",
            "peak_rps": peak_rps,
            "last_p95_ms": last_pt.p95_ms,
            "last_error_pct": last_pt.error_rate_pct,
        }
        await asyncio.sleep(1.0)

    out_dir = Path("/app/results")
    out_dir.mkdir(parents=True, exist_ok=True)

    json_path = out_dir / "stress_results.json"
    with json_path.open("w", encoding="utf-8") as f:
        json.dump(
            {
                "metadata": {
                    "steps": STEPS,
                    "duration_s": duration_s,
                    "sla_p95_ms": P95_BREAK_MS,
                    "sla_error_pct": ERROR_BREAK_PCT,
                    "req_timeout_s": REQ_TIMEOUT_S,
                },
                "breakpoints": breakpoints,
                "points": [asdict(p) for p in all_points],
            },
            f,
            indent=2,
            ensure_ascii=False,
        )

    csv_path = out_dir / "stress_summary.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(asdict(all_points[0]).keys()))
        writer.writeheader()
        for p in all_points:
            writer.writerow(asdict(p))

    print("\n" + "=" * 108)
    print("RESUMO DOS PONTOS DE RUPTURA (BREAKPOINTS)")
    print("=" * 108)
    for sid, b in breakpoints.items():
        bp_txt = f"{b['breakpoint_vus']} VUs ({b['breach_reason']})" if b["breakpoint_vus"] else "SUSTENTOU 1000 VUs!"
        print(
            f"{sid:14s} | Peak RPS={b['peak_rps']:7.1f} | Máx SLA OK={b['max_sustainable_vus']:4d} VUs | Ruptura: {bp_txt}"
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--duration", type=float, default=4.0)
    args = parser.parse_args()
    asyncio.run(run_stress(args.duration))
