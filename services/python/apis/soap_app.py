from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Dict, List
from fastapi import FastAPI, Request, Response
from lxml import etree

from common import db

SOAP_ENV_NS = "http://schemas.xmlsoap.org/soap/envelope/"
TNS = "http://streaming.example.com/soap"
NSMAP = {"soap": SOAP_ENV_NS, "tns": TNS}

WSDL_PATH = Path("/app/contracts/music_streaming.wsdl")
WSDL_CONTENT = WSDL_PATH.read_text(encoding="utf-8") if WSDL_PATH.exists() else ""


@asynccontextmanager
async def lifespan(_: FastAPI):
    await db.init_db_pool()
    yield
    await db.close_db_pool()


app = FastAPI(title="Music Streaming API — Python SOAP 1.1", lifespan=lifespan)


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1] if "}" in tag else tag


def _get_text(el: etree._Element, field: str) -> str:
    for child in el:
        if _local_name(child.tag) == field:
            return (child.text or "").strip()
    return ""


def _get_int(el: etree._Element, field: str) -> int:
    val = _get_text(el, field)
    if not val:
        raise db.ValidationError(f"Missing integer field: {field}")
    try:
        return int(val)
    except ValueError as exc:
        raise db.ValidationError(f"Invalid integer for field '{field}': {val}") from exc


def _get_int_list(el: etree._Element, field: str) -> List[int]:
    result = []
    for child in el:
        if _local_name(child.tag) == field and child.text and child.text.strip():
            raw = child.text.strip()
            try:
                result.append(int(raw))
            except ValueError as exc:
                raise db.ValidationError(f"Invalid integer in field '{field}': {raw}") from exc
    return result


def _append_user(parent: etree._Element, tag: str, u: Dict[str, Any]) -> None:
    el = etree.SubElement(parent, f"{{{TNS}}}{tag}")
    etree.SubElement(el, f"{{{TNS}}}id").text = str(u["id"])
    etree.SubElement(el, f"{{{TNS}}}name").text = str(u["name"])
    etree.SubElement(el, f"{{{TNS}}}age").text = str(u["age"])


def _append_song(parent: etree._Element, tag: str, s: Dict[str, Any]) -> None:
    el = etree.SubElement(parent, f"{{{TNS}}}{tag}")
    etree.SubElement(el, f"{{{TNS}}}id").text = str(s["id"])
    etree.SubElement(el, f"{{{TNS}}}name").text = str(s["name"])
    etree.SubElement(el, f"{{{TNS}}}artist").text = str(s["artist"])


def _append_playlist(parent: etree._Element, tag: str, p: Dict[str, Any]) -> None:
    el = etree.SubElement(parent, f"{{{TNS}}}{tag}")
    etree.SubElement(el, f"{{{TNS}}}id").text = str(p["id"])
    etree.SubElement(el, f"{{{TNS}}}name").text = str(p["name"])
    etree.SubElement(el, f"{{{TNS}}}userId").text = str(p["user_id"])
    for s in p.get("songs", []):
        _append_song(el, "songs", s)


def _wrap_envelope(response_tag: str) -> tuple[etree._Element, etree._Element]:
    env = etree.Element(f"{{{SOAP_ENV_NS}}}Envelope", nsmap=NSMAP)
    body = etree.SubElement(env, f"{{{SOAP_ENV_NS}}}Body")
    resp = etree.SubElement(body, f"{{{TNS}}}{response_tag}")
    return env, resp


def _fault_response(code: str, message: str, status_code: int = 500) -> Response:
    env = etree.Element(f"{{{SOAP_ENV_NS}}}Envelope", nsmap={"soap": SOAP_ENV_NS})
    body = etree.SubElement(env, f"{{{SOAP_ENV_NS}}}Body")
    fault = etree.SubElement(body, f"{{{SOAP_ENV_NS}}}Fault")
    etree.SubElement(fault, "faultcode").text = code
    etree.SubElement(fault, "faultstring").text = message
    xml_bytes = etree.tostring(env, xml_declaration=True, encoding="UTF-8")
    return Response(content=xml_bytes, status_code=status_code, media_type="text/xml; charset=utf-8")


@app.get("/health")
async def health():
    return {"status": "ok", "service": "python-soap"}


@app.get("/soap")
async def get_wsdl():
    return Response(content=WSDL_CONTENT, media_type="text/xml; charset=utf-8")


@app.post("/soap")
async def soap_endpoint(request: Request):
    raw_body = await request.body()
    try:
        root = etree.fromstring(raw_body)
        body = root.find(f"{{{SOAP_ENV_NS}}}Body")
        if body is None or len(body) == 0:
            return _fault_response("soap:Client", "Missing SOAP Body", 400)

        op_el = body[0]
        op_name = _local_name(op_el.tag)
        # Aceita tanto "ListUsersRequest" quanto "ListUsers"
        op_key = op_name[:-7] if op_name.endswith("Request") else op_name

        if op_key == "ListUsers":
            users = await db.list_users()
            env, resp = _wrap_envelope("ListUsersResponse")
            for u in users:
                _append_user(resp, "users", u)

        elif op_key == "GetUser":
            user = await db.get_user(_get_int(op_el, "id"))
            env, resp = _wrap_envelope("GetUserResponse")
            _append_user(resp, "user", user)

        elif op_key == "CreateUser":
            user = await db.create_user(_get_text(op_el, "name"), _get_int(op_el, "age"))
            env, resp = _wrap_envelope("CreateUserResponse")
            _append_user(resp, "user", user)

        elif op_key == "UpdateUser":
            user = await db.update_user(
                _get_int(op_el, "id"), _get_text(op_el, "name"), _get_int(op_el, "age")
            )
            env, resp = _wrap_envelope("UpdateUserResponse")
            _append_user(resp, "user", user)

        elif op_key == "DeleteUser":
            deleted = await db.delete_user(_get_int(op_el, "id"))
            env, resp = _wrap_envelope("DeleteUserResponse")
            etree.SubElement(resp, f"{{{TNS}}}deleted").text = "true" if deleted else "false"

        elif op_key == "ListSongs":
            songs = await db.list_songs()
            env, resp = _wrap_envelope("ListSongsResponse")
            for s in songs:
                _append_song(resp, "songs", s)

        elif op_key == "GetSong":
            song = await db.get_song(_get_int(op_el, "id"))
            env, resp = _wrap_envelope("GetSongResponse")
            _append_song(resp, "song", song)

        elif op_key == "CreateSong":
            song = await db.create_song(_get_text(op_el, "name"), _get_text(op_el, "artist"))
            env, resp = _wrap_envelope("CreateSongResponse")
            _append_song(resp, "song", song)

        elif op_key == "UpdateSong":
            song = await db.update_song(
                _get_int(op_el, "id"), _get_text(op_el, "name"), _get_text(op_el, "artist")
            )
            env, resp = _wrap_envelope("UpdateSongResponse")
            _append_song(resp, "song", song)

        elif op_key == "DeleteSong":
            deleted = await db.delete_song(_get_int(op_el, "id"))
            env, resp = _wrap_envelope("DeleteSongResponse")
            etree.SubElement(resp, f"{{{TNS}}}deleted").text = "true" if deleted else "false"

        elif op_key == "GetPlaylist":
            pl = await db.get_playlist(_get_int(op_el, "id"), include_songs=True)
            env, resp = _wrap_envelope("GetPlaylistResponse")
            _append_playlist(resp, "playlist", pl)

        elif op_key == "CreatePlaylist":
            pl = await db.create_playlist(
                _get_int(op_el, "userId"),
                _get_text(op_el, "name"),
                _get_int_list(op_el, "songIds"),
            )
            env, resp = _wrap_envelope("CreatePlaylistResponse")
            _append_playlist(resp, "playlist", pl)

        elif op_key == "UpdatePlaylist":
            song_ids = _get_int_list(op_el, "songIds")
            pl = await db.update_playlist(
                _get_int(op_el, "id"),
                _get_text(op_el, "name"),
                song_ids if song_ids else None,
            )
            env, resp = _wrap_envelope("UpdatePlaylistResponse")
            _append_playlist(resp, "playlist", pl)

        elif op_key == "DeletePlaylist":
            deleted = await db.delete_playlist(_get_int(op_el, "id"))
            env, resp = _wrap_envelope("DeletePlaylistResponse")
            etree.SubElement(resp, f"{{{TNS}}}deleted").text = "true" if deleted else "false"

        elif op_key == "AddSongToPlaylist":
            pl = await db.add_song_to_playlist(
                _get_int(op_el, "playlistId"), _get_int(op_el, "songId")
            )
            env, resp = _wrap_envelope("AddSongToPlaylistResponse")
            _append_playlist(resp, "playlist", pl)

        elif op_key == "RemoveSongFromPlaylist":
            pl = await db.remove_song_from_playlist(
                _get_int(op_el, "playlistId"), _get_int(op_el, "songId")
            )
            env, resp = _wrap_envelope("RemoveSongFromPlaylistResponse")
            _append_playlist(resp, "playlist", pl)

        elif op_key == "ListUserPlaylists":
            pls = await db.list_user_playlists(_get_int(op_el, "userId"), include_songs=False)
            env, resp = _wrap_envelope("ListUserPlaylistsResponse")
            for p in pls:
                _append_playlist(resp, "playlists", p)

        elif op_key == "ListPlaylistSongs":
            songs = await db.list_playlist_songs(_get_int(op_el, "playlistId"))
            env, resp = _wrap_envelope("ListPlaylistSongsResponse")
            for s in songs:
                _append_song(resp, "songs", s)

        elif op_key == "ListPlaylistsBySong":
            pls = await db.list_playlists_by_song(_get_int(op_el, "songId"))
            env, resp = _wrap_envelope("ListPlaylistsBySongResponse")
            for p in pls:
                _append_playlist(resp, "playlists", p)

        else:
            return _fault_response("soap:Client", f"Unknown SOAP operation: {op_name}", 400)

        xml_bytes = etree.tostring(env, xml_declaration=True, encoding="UTF-8")
        return Response(content=xml_bytes, media_type="text/xml; charset=utf-8")

    except etree.XMLSyntaxError as exc:
        return _fault_response("soap:Client", f"Malformed XML: {exc}", 400)
    except db.NotFoundError as exc:
        return _fault_response("soap:Client", str(exc), 404)
    except db.ValidationError as exc:
        return _fault_response("soap:Client", str(exc), 400)
    except Exception as exc:
        return _fault_response("soap:Server", str(exc), 500)
