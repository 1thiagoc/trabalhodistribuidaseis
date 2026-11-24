from contextlib import asynccontextmanager
from typing import List, Optional
import strawberry
from fastapi import FastAPI
from strawberry.fastapi import GraphQLRouter

from common import db


@strawberry.type(name="Song")
class SongType:
    id: int
    name: str
    artist: str

    @strawberry.field
    async def playlists(self) -> List["PlaylistType"]:
        rows = await db.list_playlists_by_song(self.id)
        return [PlaylistType(id=r["id"], name=r["name"], user_id=r["user_id"]) for r in rows]


@strawberry.type(name="Playlist")
class PlaylistType:
    id: int
    name: str
    user_id: int

    @strawberry.field
    async def user(self) -> "UserType":
        u = await db.get_user(self.user_id)
        return UserType(id=u["id"], name=u["name"], age=u["age"])

    @strawberry.field
    async def songs(self) -> List[SongType]:
        rows = await db.list_playlist_songs(self.id)
        return [SongType(id=r["id"], name=r["name"], artist=r["artist"]) for r in rows]


@strawberry.type(name="User")
class UserType:
    id: int
    name: str
    age: int

    @strawberry.field
    async def playlists(self) -> List[PlaylistType]:
        rows = await db.list_user_playlists(self.id, include_songs=False)
        return [PlaylistType(id=r["id"], name=r["name"], user_id=r["user_id"]) for r in rows]


@strawberry.type
class Query:
    @strawberry.field
    async def users(self) -> List[UserType]:
        rows = await db.list_users()
        return [UserType(id=r["id"], name=r["name"], age=r["age"]) for r in rows]

    @strawberry.field
    async def user(self, id: int) -> Optional[UserType]:
        try:
            r = await db.get_user(id)
            return UserType(id=r["id"], name=r["name"], age=r["age"])
        except db.NotFoundError:
            return None

    @strawberry.field
    async def songs(self) -> List[SongType]:
        rows = await db.list_songs()
        return [SongType(id=r["id"], name=r["name"], artist=r["artist"]) for r in rows]

    @strawberry.field
    async def song(self, id: int) -> Optional[SongType]:
        try:
            r = await db.get_song(id)
            return SongType(id=r["id"], name=r["name"], artist=r["artist"])
        except db.NotFoundError:
            return None

    @strawberry.field
    async def playlist(self, id: int) -> Optional[PlaylistType]:
        try:
            r = await db.get_playlist(id, include_songs=False)
            return PlaylistType(id=r["id"], name=r["name"], user_id=r["user_id"])
        except db.NotFoundError:
            return None

    @strawberry.field(name="userPlaylists")
    async def user_playlists(self, user_id: int) -> List[PlaylistType]:
        rows = await db.list_user_playlists(user_id, include_songs=False)
        return [PlaylistType(id=r["id"], name=r["name"], user_id=r["user_id"]) for r in rows]

    @strawberry.field(name="playlistSongs")
    async def playlist_songs(self, playlist_id: int) -> List[SongType]:
        rows = await db.list_playlist_songs(playlist_id)
        return [SongType(id=r["id"], name=r["name"], artist=r["artist"]) for r in rows]

    @strawberry.field(name="playlistsBySong")
    async def playlists_by_song(self, song_id: int) -> List[PlaylistType]:
        rows = await db.list_playlists_by_song(song_id)
        return [PlaylistType(id=r["id"], name=r["name"], user_id=r["user_id"]) for r in rows]


@strawberry.type
class Mutation:
    @strawberry.mutation(name="createUser")
    async def create_user(self, name: str, age: int) -> UserType:
        r = await db.create_user(name, age)
        return UserType(id=r["id"], name=r["name"], age=r["age"])

    @strawberry.mutation(name="updateUser")
    async def update_user(self, id: int, name: str, age: int) -> UserType:
        r = await db.update_user(id, name, age)
        return UserType(id=r["id"], name=r["name"], age=r["age"])

    @strawberry.mutation(name="deleteUser")
    async def delete_user(self, id: int) -> bool:
        return await db.delete_user(id)

    @strawberry.mutation(name="createSong")
    async def create_song(self, name: str, artist: str) -> SongType:
        r = await db.create_song(name, artist)
        return SongType(id=r["id"], name=r["name"], artist=r["artist"])

    @strawberry.mutation(name="updateSong")
    async def update_song(self, id: int, name: str, artist: str) -> SongType:
        r = await db.update_song(id, name, artist)
        return SongType(id=r["id"], name=r["name"], artist=r["artist"])

    @strawberry.mutation(name="deleteSong")
    async def delete_song(self, id: int) -> bool:
        return await db.delete_song(id)

    @strawberry.mutation(name="createPlaylist")
    async def create_playlist(self, user_id: int, name: str, song_ids: List[int]) -> PlaylistType:
        r = await db.create_playlist(user_id, name, song_ids)
        return PlaylistType(id=r["id"], name=r["name"], user_id=r["user_id"])

    @strawberry.mutation(name="updatePlaylist")
    async def update_playlist(
        self, id: int, name: str, song_ids: Optional[List[int]] = None
    ) -> PlaylistType:
        r = await db.update_playlist(id, name, song_ids)
        return PlaylistType(id=r["id"], name=r["name"], user_id=r["user_id"])

    @strawberry.mutation(name="deletePlaylist")
    async def delete_playlist(self, id: int) -> bool:
        return await db.delete_playlist(id)

    @strawberry.mutation(name="addSongToPlaylist")
    async def add_song_to_playlist(self, playlist_id: int, song_id: int) -> PlaylistType:
        r = await db.add_song_to_playlist(playlist_id, song_id)
        return PlaylistType(id=r["id"], name=r["name"], user_id=r["user_id"])

    @strawberry.mutation(name="removeSongFromPlaylist")
    async def remove_song_from_playlist(self, playlist_id: int, song_id: int) -> PlaylistType:
        r = await db.remove_song_from_playlist(playlist_id, song_id)
        return PlaylistType(id=r["id"], name=r["name"], user_id=r["user_id"])


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
