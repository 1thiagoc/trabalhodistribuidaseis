from contextlib import asynccontextmanager
from typing import List, Optional
import strawberry
from fastapi import FastAPI
from strawberry.fastapi import GraphQLRouter

from common import db


def _to_song(r: dict) -> "SongType":
    return SongType(
        id=r["id"],
        name=r["name"],
        artist=r["artist"],
        album=r["album"],
        genre=r["genre"],
        duration_sec=r["duration_sec"],
        release_year=r["release_year"],
    )


def _to_playlist(r: dict) -> "PlaylistType":
    return PlaylistType(
        id=r["id"],
        name=r["name"],
        user_id=r["user_id"],
        description=r["description"],
        is_public=r["is_public"],
        created_at=r["created_at"],
    )


def _to_user(r: dict) -> "UserType":
    return UserType(
        id=r["id"],
        name=r["name"],
        age=r["age"],
        email=r["email"],
        country=r["country"],
        plan_type=r["plan_type"],
        created_at=r["created_at"],
    )


@strawberry.type(name="Song")
class SongType:
    id: int
    name: str
    artist: str
    album: str
    genre: str
    duration_sec: int
    release_year: int

    @strawberry.field
    async def playlists(self) -> List["PlaylistType"]:
        rows = await db.list_playlists_by_song(self.id)
        return [_to_playlist(r) for r in rows]


@strawberry.type(name="Playlist")
class PlaylistType:
    id: int
    name: str
    user_id: int
    description: str
    is_public: bool
    created_at: str

    @strawberry.field
    async def user(self) -> "UserType":
        return _to_user(await db.get_user(self.user_id))

    @strawberry.field
    async def songs(self) -> List[SongType]:
        rows = await db.list_playlist_songs(self.id)
        return [_to_song(r) for r in rows]


@strawberry.type(name="User")
class UserType:
    id: int
    name: str
    age: int
    email: str
    country: str
    plan_type: str
    created_at: str

    @strawberry.field
    async def playlists(self) -> List[PlaylistType]:
        rows = await db.list_user_playlists(self.id, include_songs=False)
        return [_to_playlist(r) for r in rows]


@strawberry.type
class Query:
    @strawberry.field
    async def users(self) -> List[UserType]:
        return [_to_user(r) for r in await db.list_users()]

    @strawberry.field
    async def user(self, id: int) -> Optional[UserType]:
        try:
            return _to_user(await db.get_user(id))
        except db.NotFoundError:
            return None

    @strawberry.field
    async def songs(self) -> List[SongType]:
        return [_to_song(r) for r in await db.list_songs()]

    @strawberry.field
    async def song(self, id: int) -> Optional[SongType]:
        try:
            return _to_song(await db.get_song(id))
        except db.NotFoundError:
            return None

    @strawberry.field
    async def playlist(self, id: int) -> Optional[PlaylistType]:
        try:
            return _to_playlist(await db.get_playlist(id, include_songs=False))
        except db.NotFoundError:
            return None

    @strawberry.field(name="userPlaylists")
    async def user_playlists(self, user_id: int) -> List[PlaylistType]:
        return [_to_playlist(r) for r in await db.list_user_playlists(user_id, include_songs=False)]

    @strawberry.field(name="playlistSongs")
    async def playlist_songs(self, playlist_id: int) -> List[SongType]:
        return [_to_song(r) for r in await db.list_playlist_songs(playlist_id)]

    @strawberry.field(name="playlistsBySong")
    async def playlists_by_song(self, song_id: int) -> List[PlaylistType]:
        return [_to_playlist(r) for r in await db.list_playlists_by_song(song_id)]


@strawberry.type
class Mutation:
    @strawberry.mutation(name="createUser")
    async def create_user(
        self,
        name: str,
        age: int,
        email: Optional[str] = None,
        country: Optional[str] = None,
        plan_type: Optional[str] = None,
    ) -> UserType:
        return _to_user(await db.create_user(name, age, email, country, plan_type))

    @strawberry.mutation(name="updateUser")
    async def update_user(
        self,
        id: int,
        name: str,
        age: int,
        email: Optional[str] = None,
        country: Optional[str] = None,
        plan_type: Optional[str] = None,
    ) -> UserType:
        return _to_user(await db.update_user(id, name, age, email, country, plan_type))

    @strawberry.mutation(name="deleteUser")
    async def delete_user(self, id: int) -> bool:
        return await db.delete_user(id)

    @strawberry.mutation(name="createSong")
    async def create_song(
        self,
        name: str,
        artist: str,
        album: Optional[str] = None,
        genre: Optional[str] = None,
        duration_sec: Optional[int] = None,
        release_year: Optional[int] = None,
    ) -> SongType:
        return _to_song(
            await db.create_song(name, artist, album, genre, duration_sec, release_year)
        )

    @strawberry.mutation(name="updateSong")
    async def update_song(
        self,
        id: int,
        name: str,
        artist: str,
        album: Optional[str] = None,
        genre: Optional[str] = None,
        duration_sec: Optional[int] = None,
        release_year: Optional[int] = None,
    ) -> SongType:
        return _to_song(
            await db.update_song(id, name, artist, album, genre, duration_sec, release_year)
        )

    @strawberry.mutation(name="deleteSong")
    async def delete_song(self, id: int) -> bool:
        return await db.delete_song(id)

    @strawberry.mutation(name="createPlaylist")
    async def create_playlist(
        self,
        user_id: int,
        name: str,
        song_ids: List[int],
        description: Optional[str] = None,
        is_public: Optional[bool] = None,
    ) -> PlaylistType:
        return _to_playlist(
            await db.create_playlist(user_id, name, song_ids, description, is_public)
        )

    @strawberry.mutation(name="updatePlaylist")
    async def update_playlist(
        self,
        id: int,
        name: str,
        song_ids: Optional[List[int]] = None,
        description: Optional[str] = None,
        is_public: Optional[bool] = None,
    ) -> PlaylistType:
        return _to_playlist(
            await db.update_playlist(id, name, song_ids, description, is_public)
        )

    @strawberry.mutation(name="deletePlaylist")
    async def delete_playlist(self, id: int) -> bool:
        return await db.delete_playlist(id)

    @strawberry.mutation(name="addSongToPlaylist")
    async def add_song_to_playlist(self, playlist_id: int, song_id: int) -> PlaylistType:
        return _to_playlist(await db.add_song_to_playlist(playlist_id, song_id))

    @strawberry.mutation(name="removeSongFromPlaylist")
    async def remove_song_from_playlist(self, playlist_id: int, song_id: int) -> PlaylistType:
        return _to_playlist(await db.remove_song_from_playlist(playlist_id, song_id))


schema = strawberry.Schema(query=Query, mutation=Mutation)


@asynccontextmanager
async def lifespan(_: FastAPI):
    await db.init_db_pool()
    yield
    await db.close_db_pool()


app = FastAPI(title="Music Streaming API — Python GraphQL", lifespan=lifespan)
app.include_router(GraphQLRouter(schema), prefix="/graphql")


@app.get("/health")
async def health():
    return {"status": "ok", "service": "python-graphql"}
