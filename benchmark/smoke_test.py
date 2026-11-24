"""
Smoke test completo para todas as 8 implementações (4 tecnologias x 2 linguagens).
Valida:
  - As 5 consultas obrigatórias do guia do professor
  - Ciclo CRUD completo (Usuário, Música, Playlist + associação música/playlist)
  - Limpeza automática dos registros criados durante o teste
"""

import asyncio
import sys
import httpx
import grpc
from lxml import etree

import music_streaming_pb2 as pb2
import music_streaming_pb2_grpc as pb2_grpc

SOAP_NS = "http://schemas.xmlsoap.org/soap/envelope/"
TNS = "http://streaming.example.com/soap"


def soap_envelope(op_request: str, inner_xml: str = "") -> str:
    return (
        f'<?xml version="1.0" encoding="UTF-8"?>'
        f'<soap:Envelope xmlns:soap="{SOAP_NS}" xmlns:tns="{TNS}">'
        f"<soap:Body><tns:{op_request}>{inner_xml}</tns:{op_request}></soap:Body>"
        f"</soap:Envelope>"
    )


def xml_find_all_local(root: etree._Element, local: str):
    return [el for el in root.iter() if (el.tag.rsplit("}", 1)[-1] if "}" in el.tag else el.tag) == local]


async def test_rest(name: str, base_url: str):
    async with httpx.AsyncClient(base_url=base_url, timeout=10.0) as client:
        # 5 consultas obrigatórias
        r_users = await client.get("/users")
        assert r_users.status_code == 200 and len(r_users.json()) >= 50, f"{name}: list users failed"

        r_songs = await client.get("/songs")
        assert r_songs.status_code == 200 and len(r_songs.json()) >= 100, f"{name}: list songs failed"

        r_upl = await client.get("/users/1/playlists")
        assert r_upl.status_code == 200 and len(r_upl.json()) >= 1, f"{name}: user playlists failed"

        r_pls = await client.get("/playlists/1/songs")
        assert r_pls.status_code == 200 and len(r_pls.json()) >= 1, f"{name}: playlist songs failed"

        r_sbp = await client.get("/songs/1/playlists")
        assert r_sbp.status_code == 200 and len(r_sbp.json()) >= 1, f"{name}: playlists by song failed"

        # CRUD Usuário
        u = (await client.post("/users", json={"name": "Smoke User", "age": 25})).json()
        assert u["id"] > 0
        u_upd = (await client.put(f"/users/{u['id']}", json={"name": "Smoke User Upd", "age": 26})).json()
        assert u_upd["name"] == "Smoke User Upd"

        # CRUD Música
        s = (await client.post("/songs", json={"name": "Smoke Song", "artist": "Smoke Artist"})).json()
        assert s["id"] > 0
        s_upd = (await client.put(f"/songs/{s['id']}", json={"name": "Smoke Song 2", "artist": "Artist 2"})).json()
        assert s_upd["artist"] == "Artist 2"

        # CRUD Playlist
        pl = (await client.post("/playlists", json={"name": "Smoke PL", "user_id": u["id"], "song_ids": [s["id"]]})).json()
        assert pl["id"] > 0 and len(pl["songs"]) == 1
        pl_upd = (await client.put(f"/playlists/{pl['id']}", json={"name": "Smoke PL 2"})).json()
        assert pl_upd["name"] == "Smoke PL 2"

        # Edge cases: 404, entrada inválida, FK inválida, invariante 1..*
        assert (await client.get("/users/999999")).status_code == 404
        assert (await client.get("/users/999999/playlists")).status_code == 404
        assert (await client.get("/songs/999999/playlists")).status_code == 404
        assert (await client.get("/users/abc")).status_code in (400, 422)
        assert (await client.post("/users", json={"name": "X", "age": -1})).status_code in (400, 422)
        assert (await client.post("/playlists", json={"name": "BadFK", "user_id": u["id"], "song_ids": [999999]})).status_code == 404
        # Não pode remover única música da playlist nem deletar a música enquanto for a única
        assert (await client.delete(f"/playlists/{pl['id']}/songs/{s['id']}")).status_code == 400
        assert (await client.delete(f"/songs/{s['id']}")).status_code == 400
        # Adiciona outra música, agora pode remover e depois limpar
        pl_add = (await client.post(f"/playlists/{pl['id']}/songs/1")).json()
        assert len(pl_add["songs"]) == 2
        pl_rem = (await client.delete(f"/playlists/{pl['id']}/songs/1")).json()
        assert len(pl_rem["songs"]) == 1

        # Cleanup
        assert (await client.delete(f"/playlists/{pl['id']}")).status_code == 200
        assert (await client.delete(f"/songs/{s['id']}")).status_code == 200
        assert (await client.delete(f"/users/{u['id']}")).status_code == 200

    print(f"[OK] {name} — 5 consultas + CRUD + casos de borda validados!")


async def test_soap(name: str, url: str):
    async with httpx.AsyncClient(timeout=10.0) as client:
        # WSDL check
        wsdl = await client.get(f"{url}?wsdl")
        assert wsdl.status_code == 200 and "MusicStreamingService" in wsdl.text, f"{name}: WSDL failed"

        async def call(op: str, inner: str = ""):
            resp = await client.post(
                url,
                content=soap_envelope(f"{op}Request", inner),
                headers={"Content-Type": "text/xml; charset=utf-8", "SOAPAction": f'"{op}"'},
            )
            assert resp.status_code == 200, f"{name} {op} failed: {resp.status_code} {resp.text[:300]}"
            return etree.fromstring(resp.content)

        # 5 consultas obrigatórias
        assert len(xml_find_all_local(await call("ListUsers"), "users")) >= 50
        assert len(xml_find_all_local(await call("ListSongs"), "songs")) >= 100
        assert len(xml_find_all_local(await call("ListUserPlaylists", "<tns:userId>1</tns:userId>"), "playlists")) >= 1
        assert len(xml_find_all_local(await call("ListPlaylistSongs", "<tns:playlistId>1</tns:playlistId>"), "songs")) >= 1
        assert len(xml_find_all_local(await call("ListPlaylistsBySong", "<tns:songId>1</tns:songId>"), "playlists")) >= 1

        # CRUD Usuário
        u_xml = await call("CreateUser", "<tns:name>Smoke SOAP</tns:name><tns:age>28</tns:age>")
        uid = int(xml_find_all_local(u_xml, "id")[0].text)
        await call("UpdateUser", f"<tns:id>{uid}</tns:id><tns:name>Smoke SOAP 2</tns:name><tns:age>29</tns:age>")

        # CRUD Música
        s_xml = await call("CreateSong", "<tns:name>SOAP Song</tns:name><tns:artist>SOAP Band</tns:artist>")
        sid = int(xml_find_all_local(s_xml, "id")[0].text)
        await call("UpdateSong", f"<tns:id>{sid}</tns:id><tns:name>SOAP Song 2</tns:name><tns:artist>Band 2</tns:artist>")

        # CRUD Playlist
        pl_xml = await call(
            "CreatePlaylist",
            f"<tns:name>SOAP PL</tns:name><tns:userId>{uid}</tns:userId><tns:songIds>{sid}</tns:songIds><tns:songIds>1</tns:songIds>",
        )
        pl_el = xml_find_all_local(pl_xml, "playlist")[0]
        pl_id = int([c for c in pl_el if c.tag.rsplit("}", 1)[-1] == "id"][0].text)

        # Cleanup
        await call("DeletePlaylist", f"<tns:id>{pl_id}</tns:id>")
        await call("DeleteSong", f"<tns:id>{sid}</tns:id>")
        await call("DeleteUser", f"<tns:id>{uid}</tns:id>")

    print(f"[OK] {name} — WSDL + 5 consultas + CRUD completo validados!")


async def test_graphql(name: str, url: str):
    async with httpx.AsyncClient(timeout=10.0) as client:
        async def gql(query: str, variables=None):
            resp = await client.post(url, json={"query": query, "variables": variables or {}})
            assert resp.status_code == 200, f"{name} HTTP {resp.status_code}: {resp.text[:300]}"
            body = resp.json()
            assert "errors" not in body, f"{name} GraphQL errors: {body['errors']}"
            return body["data"]

        # 5 consultas obrigatórias + consulta aninhada
        d = await gql("{ users { id name age } songs { id name artist } }")
        assert len(d["users"]) >= 50 and len(d["songs"]) >= 100

        d2 = await gql("{ userPlaylists(userId: 1) { id name } playlistSongs(playlistId: 1) { id name } playlistsBySong(songId: 1) { id name } }")
        assert len(d2["userPlaylists"]) >= 1 and len(d2["playlistSongs"]) >= 1 and len(d2["playlistsBySong"]) >= 1

        # Nested query (vantagem GraphQL)
        nested = await gql("{ user(id: 1) { id name playlists { id name songs { id name artist } } } }")
        assert nested["user"]["id"] == 1 and len(nested["user"]["playlists"][0]["songs"]) >= 1

        # CRUD completo
        u = (await gql('mutation { createUser(name: "GQL User", age: 22) { id name age } }'))["createUser"]
        await gql(f'mutation {{ updateUser(id: {u["id"]}, name: "GQL User 2", age: 23) {{ id name }} }}')

        s = (await gql('mutation { createSong(name: "GQL Song", artist: "GQL Artist") { id name } }'))["createSong"]
        pl = (await gql(f'mutation {{ createPlaylist(userId: {u["id"]}, name: "GQL PL", songIds: [{s["id"]}, 1]) {{ id name songs {{ id }} }} }}'))["createPlaylist"]
        assert len(pl["songs"]) == 2

        await gql(f'mutation {{ deletePlaylist(id: {pl["id"]}) }}')
        await gql(f'mutation {{ deleteSong(id: {s["id"]}) }}')
        await gql(f'mutation {{ deleteUser(id: {u["id"]}) }}')

    print(f"[OK] {name} — 5 consultas + Nested Query + CRUD completo validados!")


async def test_grpc(name: str, target: str):
    async with grpc.aio.insecure_channel(target) as channel:
        stub = pb2_grpc.MusicStreamingServiceStub(channel)

        # 5 consultas obrigatórias
        assert len((await stub.ListUsers(pb2.Empty())).users) >= 50
        assert len((await stub.ListSongs(pb2.Empty())).songs) >= 100
        assert len((await stub.ListUserPlaylists(pb2.IdRequest(id=1))).playlists) >= 1
        assert len((await stub.ListPlaylistSongs(pb2.IdRequest(id=1))).songs) >= 1
        assert len((await stub.ListPlaylistsBySong(pb2.IdRequest(id=1))).playlists) >= 1

        # CRUD completo
        u = await stub.CreateUser(pb2.CreateUserRequest(name="gRPC User", age=30))
        u2 = await stub.UpdateUser(pb2.UpdateUserRequest(id=u.id, name="gRPC User 2", age=31))
        assert u2.name == "gRPC User 2"

        s = await stub.CreateSong(pb2.CreateSongRequest(name="gRPC Song", artist="gRPC Artist"))
        pl = await stub.CreatePlaylist(pb2.CreatePlaylistRequest(name="gRPC PL", user_id=u.id, song_ids=[s.id, 1]))
        assert len(pl.songs) == 2

        assert (await stub.DeletePlaylist(pb2.IdRequest(id=pl.id))).deleted
        assert (await stub.DeleteSong(pb2.IdRequest(id=s.id))).deleted
        assert (await stub.DeleteUser(pb2.IdRequest(id=u.id))).deleted

    print(f"[OK] {name} — 5 consultas + CRUD completo validados!")


async def main():
    print("=" * 72)
    print("INICIANDO SMOKE TEST DAS 8 IMPLEMENTAÇÕES (PYTHON + NODE.JS)")
    print("=" * 72)

    await test_rest("Python REST", "http://python-rest:8001")
    await test_soap("Python SOAP", "http://python-soap:8002/soap")
    await test_graphql("Python GraphQL", "http://python-graphql:8003/graphql")
    await test_grpc("Python gRPC", "python-grpc:50051")

    await test_rest("Node.js REST", "http://node-rest:8101")
    await test_soap("Node.js SOAP", "http://node-soap:8102/soap")
    await test_graphql("Node.js GraphQL", "http://node-graphql:8103/graphql")
    await test_grpc("Node.js gRPC", "node-grpc:50052")

    print("=" * 72)
    print("SUCESSO TOTAL! TODAS AS 8 IMPLEMENTAÇÕES PASSARAM NOS TESTES!")
    print("=" * 72)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as exc:
        print(f"ERRO NO SMOKE TEST: {exc}", file=sys.stderr)
        raise
