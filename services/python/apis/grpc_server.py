import asyncio
import os
import grpc

from common import db
import music_streaming_pb2 as pb2
import music_streaming_pb2_grpc as pb2_grpc


def _to_user(u: dict) -> pb2.User:
    return pb2.User(
        id=u["id"],
        name=u["name"],
        age=u["age"],
        email=u["email"],
        country=u["country"],
        plan_type=u["plan_type"],
        created_at=u["created_at"],
    )


def _to_song(s: dict) -> pb2.Song:
    return pb2.Song(
        id=s["id"],
        name=s["name"],
        artist=s["artist"],
        album=s["album"],
        genre=s["genre"],
        duration_sec=s["duration_sec"],
        release_year=s["release_year"],
    )


def _to_playlist(p: dict) -> pb2.Playlist:
    return pb2.Playlist(
        id=p["id"],
        name=p["name"],
        user_id=p["user_id"],
        description=p["description"],
        is_public=p["is_public"],
        created_at=p["created_at"],
        songs=[_to_song(s) for s in p.get("songs", [])],
    )


class MusicStreamingServicer(pb2_grpc.MusicStreamingServiceServicer):
    async def _abort(self, context, exc: Exception):
        if isinstance(exc, db.NotFoundError):
            await context.abort(grpc.StatusCode.NOT_FOUND, str(exc))
        if isinstance(exc, db.ValidationError):
            await context.abort(grpc.StatusCode.INVALID_ARGUMENT, str(exc))
        await context.abort(grpc.StatusCode.INTERNAL, str(exc))

    async def ListUsers(self, request, context):
        users = await db.list_users()
        return pb2.UserList(users=[_to_user(u) for u in users])

    async def GetUser(self, request, context):
        try:
            return _to_user(await db.get_user(request.id))
        except Exception as exc:
            await self._abort(context, exc)

    async def CreateUser(self, request, context):
        try:
            return _to_user(
                await db.create_user(
                    request.name,
                    request.age,
                    request.email or None,
                    request.country or None,
                    request.plan_type or None,
                )
            )
        except Exception as exc:
            await self._abort(context, exc)

    async def UpdateUser(self, request, context):
        try:
            return _to_user(
                await db.update_user(
                    request.id,
                    request.name,
                    request.age,
                    request.email or None,
                    request.country or None,
                    request.plan_type or None,
                )
            )
        except Exception as exc:
            await self._abort(context, exc)

    async def DeleteUser(self, request, context):
        deleted = await db.delete_user(request.id)
        return pb2.DeleteResponse(deleted=deleted)

    async def ListSongs(self, request, context):
        songs = await db.list_songs()
        return pb2.SongList(songs=[_to_song(s) for s in songs])

    async def GetSong(self, request, context):
        try:
            return _to_song(await db.get_song(request.id))
        except Exception as exc:
            await self._abort(context, exc)

    async def CreateSong(self, request, context):
        try:
            return _to_song(
                await db.create_song(
                    request.name,
                    request.artist,
                    request.album or None,
                    request.genre or None,
                    request.duration_sec or None,
                    request.release_year or None,
                )
            )
        except Exception as exc:
            await self._abort(context, exc)

    async def UpdateSong(self, request, context):
        try:
            return _to_song(
                await db.update_song(
                    request.id,
                    request.name,
                    request.artist,
                    request.album or None,
                    request.genre or None,
                    request.duration_sec or None,
                    request.release_year or None,
                )
            )
        except Exception as exc:
            await self._abort(context, exc)

    async def DeleteSong(self, request, context):
        try:
            deleted = await db.delete_song(request.id)
            return pb2.DeleteResponse(deleted=deleted)
        except Exception as exc:
            await self._abort(context, exc)

    async def GetPlaylist(self, request, context):
        try:
            return _to_playlist(await db.get_playlist(request.id, include_songs=True))
        except Exception as exc:
            await self._abort(context, exc)

    async def CreatePlaylist(self, request, context):
        try:
            pl = await db.create_playlist(
                request.user_id,
                request.name,
                list(request.song_ids),
                request.description or "",
                request.is_public,
            )
            return _to_playlist(pl)
        except Exception as exc:
            await self._abort(context, exc)

    async def UpdatePlaylist(self, request, context):
        try:
            song_ids = list(request.song_ids) if len(request.song_ids) > 0 else None
            pl = await db.update_playlist(
                request.id,
                request.name,
                song_ids,
                request.description or None,
                request.is_public,
            )
            return _to_playlist(pl)
        except Exception as exc:
            await self._abort(context, exc)

    async def DeletePlaylist(self, request, context):
        deleted = await db.delete_playlist(request.id)
        return pb2.DeleteResponse(deleted=deleted)

    async def AddSongToPlaylist(self, request, context):
        try:
            pl = await db.add_song_to_playlist(request.playlist_id, request.song_id)
            return _to_playlist(pl)
        except Exception as exc:
            await self._abort(context, exc)

    async def RemoveSongFromPlaylist(self, request, context):
        try:
            pl = await db.remove_song_from_playlist(request.playlist_id, request.song_id)
            return _to_playlist(pl)
        except Exception as exc:
            await self._abort(context, exc)

    async def ListUserPlaylists(self, request, context):
        try:
            pls = await db.list_user_playlists(request.id, include_songs=False)
            return pb2.PlaylistList(playlists=[_to_playlist(p) for p in pls])
        except Exception as exc:
            await self._abort(context, exc)

    async def ListPlaylistSongs(self, request, context):
        try:
            songs = await db.list_playlist_songs(request.id)
            return pb2.SongList(songs=[_to_song(s) for s in songs])
        except Exception as exc:
            await self._abort(context, exc)

    async def ListPlaylistsBySong(self, request, context):
        try:
            pls = await db.list_playlists_by_song(request.id)
            return pb2.PlaylistList(playlists=[_to_playlist(p) for p in pls])
        except Exception as exc:
            await self._abort(context, exc)


async def serve():
    await db.init_db_pool()
    port = os.environ.get("PORT", "50051")
    server = grpc.aio.server()
    pb2_grpc.add_MusicStreamingServiceServicer_to_server(MusicStreamingServicer(), server)
    server.add_insecure_port(f"0.0.0.0:{port}")
    await server.start()
    print(f"Python gRPC server listening on 0.0.0.0:{port}", flush=True)
    try:
        await server.wait_for_termination()
    finally:
        await db.close_db_pool()


if __name__ == "__main__":
    asyncio.run(serve())
