"""
Suite de Testes de Carga — Comparação das 8 Implementações (4 Tecnologias x 2 Linguagens)
Computação Distribuída — Serviço de Streaming de Músicas

Cenários de Carga:
  1. W1_list_songs (Listagem completa de 100 músicas):
     Executado em 3 níveis de concorrência: 10 VUs (Leve), 50 VUs (Moderada), 100 VUs (Alta).
  2. W2_relational_profile (Perfil relacional: Usuário + suas Playlists + Músicas da 1a Playlist):
     Executado a 50 VUs — evidencia N+1 round-trips (REST/SOAP/gRPC) vs 1 query aninhada (GraphQL).
  3. W3_mixed_crud (Mix realista: 70% consultas relacionais + 30% escrita/alteração/remoção):
     Executado a 50 VUs — avalia comportamento sob leitura + mutação concorrente no PostgreSQL.

Saídas:
  - /app/results/benchmark_results.json
  - /app/results/benchmark_summary.csv
"""

import argparse
import asyncio
import csv
import datetime
import json
import os
import platform
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Awaitable, Callable, Dict, List, Tuple

import grpc
import httpx
import numpy as np
from lxml import etree

import music_streaming_pb2 as pb2
import music_streaming_pb2_grpc as pb2_grpc

SOAP_NS = "http://schemas.xmlsoap.org/soap/envelope/"
TNS = "http://streaming.example.com/soap"


def soap_xml(op_req: str, inner: str = "") -> bytes:
    return (
        f'<?xml version="1.0" encoding="UTF-8"?>'
        f'<soap:Envelope xmlns:soap="{SOAP_NS}" xmlns:tns="{TNS}">'
        f"<soap:Body><tns:{op_req}>{inner}</tns:{op_req}></soap:Body>"
        f"</soap:Envelope>"
    ).encode("utf-8")


def all_local_texts(xml_bytes: bytes, parent_local: str, child_local: str) -> List[str]:
    root = etree.fromstring(xml_bytes)
    out = []
    for el in root.iter():
        tag = el.tag.rsplit("}", 1)[-1] if "}" in el.tag else el.tag
        if tag == parent_local:
            for ch in el:
                ctag = ch.tag.rsplit("}", 1)[-1] if "}" in ch.tag else ch.tag
                if ctag == child_local and ch.text:
                    out.append(ch.text.strip())
    return out


def first_local_text(xml_bytes: bytes, local_name: str) -> str:
    root = etree.fromstring(xml_bytes)
    for el in root.iter():
        tag = el.tag.rsplit("}", 1)[-1] if "}" in el.tag else el.tag
        if tag == local_name and el.text:
            return el.text.strip()
    return ""


@dataclass
class ScenarioMetrics:
    service_id: str
    language: str
    protocol: str
    workload: str
    concurrency: int
    runs: int
    duration_s: float
    total_requests: int
    errors: int
    error_rate_pct: float
    rps: float
    rps_std: float
    mean_ms: float
    p50_ms: float
    p95_ms: float
    p95_std: float
    p99_ms: float
    min_ms: float
    max_ms: float
    avg_payload_bytes: float
    error_samples: str = ""


# ==================== CLIENTES DE OPERAÇÃO ====================

def make_rest_ops(client: httpx.AsyncClient) -> Dict[str, Callable[[int], Awaitable[int]]]:
    async def w1_list_songs(_iter: int) -> int:
        r = await client.get("/songs")
        r.raise_for_status()
        return len(r.content)

    async def w2_relational(i: int) -> int:
        uid = (i % 500) + 1
        r1 = await client.get(f"/users/{uid}")
        r1.raise_for_status()
        r2 = await client.get(f"/users/{uid}/playlists")
        r2.raise_for_status()
        pls = r2.json()
        total = len(r1.content) + len(r2.content)
        for pl in pls:
            r3 = await client.get(f"/playlists/{pl['id']}/songs")
            r3.raise_for_status()
            total += len(r3.content)
        return total

    async def w3_mixed(i: int) -> int:
        bucket = i % 10
        if bucket < 3:
            r = await client.get(f"/users/{(i % 500) + 1}/playlists")
            r.raise_for_status()
            return len(r.content)
        if bucket < 5:
            r = await client.get(f"/playlists/{(i % 1000) + 1}/songs")
            r.raise_for_status()
            return len(r.content)
        if bucket < 7:
            r = await client.get(f"/songs/{(i % 1000) + 1}/playlists")
            r.raise_for_status()
            return len(r.content)
        # 30% escrita (Create -> Update -> Delete para manter base estável)
        r1 = await client.post("/users", json={"name": f"Bench REST {i}", "age": 24})
        r1.raise_for_status()
        uid = r1.json()["id"]
        r2 = await client.put(f"/users/{uid}", json={"name": f"Bench REST Upd {i}", "age": 25})
        r2.raise_for_status()
        r3 = await client.delete(f"/users/{uid}")
        r3.raise_for_status()
        return len(r1.content) + len(r2.content) + len(r3.content)

    return {
        "W1_list_songs": w1_list_songs,
        "W2_relational_profile": w2_relational,
        "W3_mixed_crud": w3_mixed,
    }


def make_soap_ops(client: httpx.AsyncClient, url: str) -> Dict[str, Callable[[int], Awaitable[int]]]:
    async def post_soap(op: str, inner: str = "") -> bytes:
        r = await client.post(
            url,
            content=soap_xml(f"{op}Request", inner),
            headers={"Content-Type": "text/xml; charset=utf-8", "SOAPAction": f'"{op}"'},
        )
        r.raise_for_status()
        return r.content

    async def w1_list_songs(_iter: int) -> int:
        content = await post_soap("ListSongs")
        return len(content)

    async def w2_relational(i: int) -> int:
        uid = (i % 500) + 1
        c1 = await post_soap("GetUser", f"<tns:id>{uid}</tns:id>")
        c2 = await post_soap("ListUserPlaylists", f"<tns:userId>{uid}</tns:userId>")
        pl_ids = all_local_texts(c2, "playlists", "id")
        total = len(c1) + len(c2)
        for pl_id in pl_ids:
            c3 = await post_soap("ListPlaylistSongs", f"<tns:playlistId>{pl_id}</tns:playlistId>")
            total += len(c3)
        return total

    async def w3_mixed(i: int) -> int:
        bucket = i % 10
        if bucket < 3:
            return len(await post_soap("ListUserPlaylists", f"<tns:userId>{(i % 500) + 1}</tns:userId>"))
        if bucket < 5:
            return len(await post_soap("ListPlaylistSongs", f"<tns:playlistId>{(i % 1000) + 1}</tns:playlistId>"))
        if bucket < 7:
            return len(await post_soap("ListPlaylistsBySong", f"<tns:songId>{(i % 1000) + 1}</tns:songId>"))
        c1 = await post_soap("CreateUser", f"<tns:name>Bench SOAP {i}</tns:name><tns:age>24</tns:age>")
        uid = first_local_text(c1, "id")
        c2 = await post_soap("UpdateUser", f"<tns:id>{uid}</tns:id><tns:name>Bench SOAP Upd {i}</tns:name><tns:age>25</tns:age>")
        c3 = await post_soap("DeleteUser", f"<tns:id>{uid}</tns:id>")
        return len(c1) + len(c2) + len(c3)

    return {
        "W1_list_songs": w1_list_songs,
        "W2_relational_profile": w2_relational,
        "W3_mixed_crud": w3_mixed,
    }


def make_graphql_ops(client: httpx.AsyncClient, url: str) -> Dict[str, Callable[[int], Awaitable[int]]]:
    async def post_gql(query: str) -> Tuple[dict, int]:
        r = await client.post(url, json={"query": query})
        r.raise_for_status()
        body = r.json()
        if "errors" in body:
            raise RuntimeError(str(body["errors"]))
        return body["data"], len(r.content)

    async def w1_list_songs(_iter: int) -> int:
        _, n = await post_gql("{ songs { id name artist album genre durationSec releaseYear } }")
        return n

    async def w2_relational(i: int) -> int:
        # GraphQL resolve o perfil + playlists + músicas (todos os 6-7 atributos) em UMA ÚNICA requisição!
        uid = (i % 500) + 1
        _, n = await post_gql(
            f"{{ user(id: {uid}) {{ id name age email country planType createdAt "
            f"playlists {{ id name description isPublic createdAt "
            f"songs {{ id name artist album genre durationSec releaseYear }} }} }} }}"
        )
        return n

    async def w3_mixed(i: int) -> int:
        bucket = i % 10
        if bucket < 3:
            _, n = await post_gql(f"{{ userPlaylists(userId: {(i % 500) + 1}) {{ id name userId description isPublic createdAt }} }}")
            return n
        if bucket < 5:
            _, n = await post_gql(f"{{ playlistSongs(playlistId: {(i % 1000) + 1}) {{ id name artist album genre durationSec releaseYear }} }}")
            return n
        if bucket < 7:
            _, n = await post_gql(f"{{ playlistsBySong(songId: {(i % 1000) + 1}) {{ id name userId description isPublic createdAt }} }}")
            return n
        d1, n1 = await post_gql(f'mutation {{ createUser(name: "Bench GQL {i}", age: 24) {{ id name age email country planType createdAt }} }}')
        uid = d1["createUser"]["id"]
        _, n2 = await post_gql(f'mutation {{ updateUser(id: {uid}, name: "Bench GQL Upd {i}", age: 25) {{ id name age email country planType createdAt }} }}')
        _, n3 = await post_gql(f"mutation {{ deleteUser(id: {uid}) }}")
        return n1 + n2 + n3

    return {
        "W1_list_songs": w1_list_songs,
        "W2_relational_profile": w2_relational,
        "W3_mixed_crud": w3_mixed,
    }


def make_grpc_ops(stubs: List[pb2_grpc.MusicStreamingServiceStub]) -> Dict[str, Callable[[int], Awaitable[int]]]:
    async def w1_list_songs(i: int) -> int:
        resp = await stubs[i % len(stubs)].ListSongs(pb2.Empty())
        return resp.ByteSize()

    async def w2_relational(i: int) -> int:
        stub = stubs[i % len(stubs)]
        uid = (i % 500) + 1
        u = await stub.GetUser(pb2.IdRequest(id=uid))
        pls = await stub.ListUserPlaylists(pb2.IdRequest(id=uid))
        total = u.ByteSize() + pls.ByteSize()
        for pl in pls.playlists:
            songs = await stub.ListPlaylistSongs(pb2.IdRequest(id=pl.id))
            total += songs.ByteSize()
        return total

    async def w3_mixed(i: int) -> int:
        stub = stubs[i % len(stubs)]
        bucket = i % 10
        if bucket < 3:
            r = await stub.ListUserPlaylists(pb2.IdRequest(id=(i % 500) + 1))
            return r.ByteSize()
        if bucket < 5:
            r = await stub.ListPlaylistSongs(pb2.IdRequest(id=(i % 1000) + 1))
            return r.ByteSize()
        if bucket < 7:
            r = await stub.ListPlaylistsBySong(pb2.IdRequest(id=(i % 1000) + 1))
            return r.ByteSize()
        r1 = await stub.CreateUser(pb2.CreateUserRequest(name=f"Bench gRPC {i}", age=24))
        r2 = await stub.UpdateUser(pb2.UpdateUserRequest(id=r1.id, name=f"Bench gRPC Upd {i}", age=25))
        r3 = await stub.DeleteUser(pb2.IdRequest(id=r1.id))
        return r1.ByteSize() + r2.ByteSize() + r3.ByteSize()

    return {
        "W1_list_songs": w1_list_songs,
        "W2_relational_profile": w2_relational,
        "W3_mixed_crud": w3_mixed,
    }


# ==================== MOTOR DE EXECUÇÃO ====================

async def run_load_scenario(
    op_fn: Callable[[int], Awaitable[int]],
    service_id: str,
    language: str,
    protocol: str,
    workload: str,
    concurrency: int,
    warmup_s: float,
    duration_s: float,
    runs: int = 1,
) -> ScenarioMetrics:
    # Aquecimento único antes das repetições
    warm_end = time.perf_counter() + warmup_s

    async def warmup_worker(wid: int):
        idx = wid
        while time.perf_counter() < warm_end:
            try:
                await op_fn(idx)
            except Exception:
                pass
            idx += concurrency

    await asyncio.gather(*(warmup_worker(w) for w in range(min(concurrency, 20))))

    all_latencies_ms: List[float] = []
    all_payloads: List[int] = []
    run_rps: List[float] = []
    run_p95: List[float] = []
    total_errors = 0
    total_elapsed = 0.0
    error_samples: List[str] = []

    for r_idx in range(runs):
        latencies_ms: List[float] = []
        payloads: List[int] = []
        errors = 0

        start = time.perf_counter()
        deadline = start + duration_s

        async def worker(wid: int):
            nonlocal errors
            idx = wid + r_idx * 10000
            while time.perf_counter() < deadline:
                t0 = time.perf_counter()
                try:
                    nbytes = await op_fn(idx)
                    dt = (time.perf_counter() - t0) * 1000.0
                    latencies_ms.append(dt)
                    payloads.append(nbytes)
                except Exception as exc:
                    errors += 1
                    if len(error_samples) < 5:
                        error_samples.append(f"{type(exc).__name__}: {str(exc)[:120]}")
                idx += concurrency

        await asyncio.gather(*(worker(w) for w in range(concurrency)))
        elapsed = time.perf_counter() - start
        total_elapsed += elapsed
        total_errors += errors
        all_latencies_ms.extend(latencies_ms)
        all_payloads.extend(payloads)

        run_rps.append(len(latencies_ms) / elapsed if elapsed > 0 else 0.0)
        run_p95.append(float(np.percentile(latencies_ms, 95)) if latencies_ms else 0.0)
        if r_idx + 1 < runs:
            await asyncio.sleep(0.5)

    ok_count = len(all_latencies_ms)
    total = ok_count + total_errors
    if ok_count > 0:
        arr = np.array(all_latencies_ms, dtype=np.float64)
        mean_ms = float(np.mean(arr))
        p50_ms = float(np.percentile(arr, 50))
        p95_ms = float(np.mean(run_p95))
        p99_ms = float(np.percentile(arr, 99))
        min_ms = float(np.min(arr))
        max_ms = float(np.max(arr))
        avg_payload = float(np.mean(all_payloads))
    else:
        mean_ms = p50_ms = p95_ms = p99_ms = min_ms = max_ms = avg_payload = 0.0

    rps_mean = float(np.mean(run_rps)) if run_rps else 0.0
    rps_std = float(np.std(run_rps, ddof=1)) if len(run_rps) > 1 else 0.0
    p95_std = float(np.std(run_p95, ddof=1)) if len(run_p95) > 1 else 0.0

    metrics = ScenarioMetrics(
        service_id=service_id,
        language=language,
        protocol=protocol,
        workload=workload,
        concurrency=concurrency,
        runs=runs,
        duration_s=round(total_elapsed, 2),
        total_requests=total,
        errors=total_errors,
        error_rate_pct=round((total_errors / total * 100.0) if total else 0.0, 3),
        rps=round(rps_mean, 2),
        rps_std=round(rps_std, 2),
        mean_ms=round(mean_ms, 2),
        p50_ms=round(p50_ms, 2),
        p95_ms=round(p95_ms, 2),
        p95_std=round(p95_std, 2),
        p99_ms=round(p99_ms, 2),
        min_ms=round(min_ms, 2),
        max_ms=round(max_ms, 2),
        avg_payload_bytes=round(avg_payload, 1),
        error_samples=" | ".join(error_samples),
    )
    print(
        f"[{service_id:14s}] {workload:21s} | VUs={concurrency:3d} | runs={runs} | "
        f"OPS={metrics.rps:7.1f}±{metrics.rps_std:5.1f} | p50={metrics.p50_ms:6.2f}ms | "
        f"p95={metrics.p95_ms:6.2f}±{metrics.p95_std:5.1f}ms | payload={metrics.avg_payload_bytes:8.0f}B | err={metrics.errors}",
        flush=True,
    )
    return metrics


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

# Matriz de cenários: 3 cargas em W1 (até centenas de usuários: 50, 200, 400 VUs) + 100 VUs em W2 e W3
TEST_MATRIX = [
    ("W1_list_songs", 50),
    ("W1_list_songs", 200),
    ("W1_list_songs", 400),
    ("W2_relational_profile", 100),
    ("W3_mixed_crud", 100),
]


async def run_all(duration_s: float, warmup_s: float, runs: int):
    results: List[ScenarioMetrics] = []
    limits = httpx.Limits(max_connections=500, max_keepalive_connections=400)

    print("=" * 115)
    print(f"INICIANDO TESTES DE CARGA (duration={duration_s}s x {runs} runs, warmup={warmup_s}s)")
    print("=" * 115)

    for service_id, language, protocol, endpoint in SERVICES:
        if protocol == "gRPC":
            channels = [
                grpc.aio.insecure_channel(
                    endpoint,
                    options=[("grpc.use_local_subchannel_pool", 1)],
                )
                for _ in range(4)
            ]
            stubs = [pb2_grpc.MusicStreamingServiceStub(ch) for ch in channels]
            ops = make_grpc_ops(stubs)
            try:
                for workload, vus in TEST_MATRIX:
                    m = await run_load_scenario(
                        ops[workload], service_id, language, protocol, workload, vus, warmup_s, duration_s, runs
                    )
                    results.append(m)
                    await asyncio.sleep(0.5)
            finally:
                for ch in channels:
                    await ch.close()
        else:
            base = endpoint if protocol == "REST" else ""
            async with httpx.AsyncClient(base_url=base, limits=limits, timeout=30.0) as client:
                if protocol == "REST":
                    ops = make_rest_ops(client)
                elif protocol == "SOAP":
                    ops = make_soap_ops(client, endpoint)
                else:
                    ops = make_graphql_ops(client, endpoint)

                for workload, vus in TEST_MATRIX:
                    m = await run_load_scenario(
                        ops[workload], service_id, language, protocol, workload, vus, warmup_s, duration_s, runs
                    )
                    results.append(m)
                    await asyncio.sleep(0.5)

        await asyncio.sleep(1.0)

    out_dir = Path("/app/results")
    out_dir.mkdir(parents=True, exist_ok=True)

    json_path = out_dir / "benchmark_results.json"
    with json_path.open("w", encoding="utf-8") as f:
        json.dump(
            {
                "metadata": {
                    "timestamp_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                    "platform": platform.platform(),
                    "machine": platform.machine(),
                    "cpu_count": os.cpu_count(),
                    "duration_s": duration_s,
                    "warmup_s": warmup_s,
                    "runs": runs,
                    "dataset": {"users": 500, "songs": 1000, "playlists": 1000, "attrs_per_entity": "6-7"},
                    "database": "PostgreSQL 16 (Docker, pool max=20)",
                    "container_limits": {"cpus": 1.0, "memory": "512m"},
                },
                "results": [asdict(r) for r in results],
            },
            f,
            indent=2,
            ensure_ascii=False,
        )

    csv_path = out_dir / "benchmark_summary.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(asdict(results[0]).keys()))
        writer.writeheader()
        for r in results:
            writer.writerow(asdict(r))

    print("=" * 115)
    print(f"RESULTADOS SALVOS EM:\n  - {json_path}\n  - {csv_path}")
    print("=" * 115)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--duration", type=float, default=15.0)
    parser.add_argument("--warmup", type=float, default=3.0)
    parser.add_argument("--runs", type=int, default=3)
    args = parser.parse_args()
    asyncio.run(run_all(args.duration, args.warmup, args.runs))
