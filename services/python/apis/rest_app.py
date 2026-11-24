from contextlib import asynccontextmanager
from typing import List, Optional
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field

from common import db


class UserIn(BaseModel):
    name: str
    age: int = Field(ge=0)


class SongIn(BaseModel):
    name: str
    artist: str


class PlaylistCreateIn(BaseModel):
    name: str
    user_id: int
    song_ids: List[int] = Field(min_length=1)


class PlaylistUpdateIn(BaseModel):
    name: str
    song_ids: Optional[List[int]] = None


@asynccontextmanager
async def lifespan(_: FastAPI):
    await db.init_db_pool()
    yield
    await db.close_db_pool()


app = FastAPI(
    title="Music Streaming API — Python REST",
    version="1.0.0",
    lifespan=lifespan,
)


def _handle_error(exc: Exception):
    if isinstance(exc, db.NotFoundError):
        raise HTTPException(status_code=404, detail=str(exc))
    if isinstance(exc, db.ValidationError):
        raise HTTPException(status_code=400, detail=str(exc))
    raise HTTPException(status_code=500, detail=str(exc))


@app.get("/health")
async def health():
    return {"status": "ok", "service": "python-rest"}


# -------------------- USUÁRIOS --------------------

@app.get("/users")
async def list_users():
    return await db.list_users()


@app.get("/users/{user_id}")
async def get_user(user_id: int):
    try:
        return await db.get_user(user_id)
    except Exception as exc:
        _handle_error(exc)


@app.post("/users", status_code=status.HTTP_201_CREATED)
async def create_user(payload: UserIn):
    try:
        return await db.create_user(payload.name, payload.age)
    except Exception as exc:
        _handle_error(exc)


@app.put("/users/{user_id}")
async def update_user(user_id: int, payload: UserIn):
    try:
        return await db.update_user(user_id, payload.name, payload.age)
    except Exception as exc:
        _handle_error(exc)


@app.delete("/users/{user_id}")
async def delete_user(user_id: int):
    deleted = await db.delete_user(user_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"User {user_id} not found")
    return {"deleted": True}


# Consulta #3: Listar todas as playlists de um determinado usuário
@app.get("/users/{user_id}/playlists")
async def list_user_playlists(user_id: int):
    try:
        return await db.list_user_playlists(user_id, include_songs=False)
    except Exception as exc:
        _handle_error(exc)


# -------------------- MÚSICAS --------------------

@app.get("/songs")
async def list_songs():
    return await db.list_songs()


@app.get("/songs/{song_id}")
async def get_song(song_id: int):
    try:
        return await db.get_song(song_id)
    except Exception as exc:
        _handle_error(exc)


@app.post("/songs", status_code=status.HTTP_201_CREATED)
async def create_song(payload: SongIn):
    try:
        return await db.create_song(payload.name, payload.artist)
    except Exception as exc:
        _handle_error(exc)


@app.put("/songs/{song_id}")
async def update_song(song_id: int, payload: SongIn):
    try:
        return await db.update_song(song_id, payload.name, payload.artist)
    except Exception as exc:
        _handle_error(exc)


@app.delete("/songs/{song_id}")
async def delete_song(song_id: int):
    try:
        deleted = await db.delete_song(song_id)
    except Exception as exc:
        _handle_error(exc)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Song {song_id} not found")
    return {"deleted": True}


# Consulta #5: Listar todas as playlists que contêm uma determinada música
@app.get("/songs/{song_id}/playlists")
async def list_playlists_by_song(song_id: int):
    try:
        return await db.list_playlists_by_song(song_id)
    except Exception as exc:
        _handle_error(exc)


# -------------------- PLAYLISTS --------------------

@app.get("/playlists/{playlist_id}")
async def get_playlist(playlist_id: int):
    try:
        return await db.get_playlist(playlist_id, include_songs=True)
    except Exception as exc:
        _handle_error(exc)


@app.post("/playlists", status_code=status.HTTP_201_CREATED)
async def create_playlist(payload: PlaylistCreateIn):
    try:
        return await db.create_playlist(payload.user_id, payload.name, payload.song_ids)
    except Exception as exc:
        _handle_error(exc)


@app.put("/playlists/{playlist_id}")
async def update_playlist(playlist_id: int, payload: PlaylistUpdateIn):
    try:
        return await db.update_playlist(playlist_id, payload.name, payload.song_ids)
    except Exception as exc:
        _handle_error(exc)


@app.delete("/playlists/{playlist_id}")
async def delete_playlist(playlist_id: int):
    deleted = await db.delete_playlist(playlist_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Playlist {playlist_id} not found")
    return {"deleted": True}


# Consulta #4: Listar todas as músicas de uma determinada playlist
@app.get("/playlists/{playlist_id}/songs")
async def list_playlist_songs(playlist_id: int):
    try:
        return await db.list_playlist_songs(playlist_id)
    except Exception as exc:
        _handle_error(exc)


@app.post("/playlists/{playlist_id}/songs/{song_id}")
async def add_song_to_playlist(playlist_id: int, song_id: int):
    try:
        return await db.add_song_to_playlist(playlist_id, song_id)
    except Exception as exc:
        _handle_error(exc)


@app.delete("/playlists/{playlist_id}/songs/{song_id}")
async def remove_song_from_playlist(playlist_id: int, song_id: int):
    try:
        return await db.remove_song_from_playlist(playlist_id, song_id)
    except Exception as exc:
        _handle_error(exc)
