import os
import re
from typing import Any, Dict, List, Optional
import asyncpg

_pool: Optional[asyncpg.Pool] = None

USER_COLS = "id, name, age, email, country, plan_type, TO_CHAR(created_at, 'YYYY-MM-DD') AS created_at"
SONG_COLS = "id, name, artist, album, genre, duration_sec, release_year"
PLAYLIST_COLS = "id, name, user_id, description, is_public, TO_CHAR(created_at, 'YYYY-MM-DD') AS created_at"


class NotFoundError(Exception):
    pass


class ValidationError(Exception):
    pass


def _default_email(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", ".", name.strip().lower()).strip(".") or "user"
    return f"{slug}@musicstream.io"


async def init_db_pool() -> asyncpg.Pool:
    global _pool
    if _pool is None:
        dsn = os.environ.get(
            "DATABASE_URL",
            "postgresql://streaming:streaming@postgres:5432/music_streaming",
        )
        _pool = await asyncpg.create_pool(dsn=dsn, min_size=5, max_size=20)
    return _pool


async def close_db_pool() -> None:
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None


def get_pool() -> asyncpg.Pool:
    if _pool is None:
        raise RuntimeError("Database pool not initialized")
    return _pool


# -------------------- USERS (7 atributos) --------------------

async def list_users() -> List[Dict[str, Any]]:
    rows = await get_pool().fetch(f"SELECT {USER_COLS} FROM users ORDER BY id")
    return [dict(r) for r in rows]


async def get_user(user_id: int) -> Dict[str, Any]:
    row = await get_pool().fetchrow(f"SELECT {USER_COLS} FROM users WHERE id = $1", user_id)
    if not row:
        raise NotFoundError(f"User {user_id} not found")
    return dict(row)


async def create_user(
    name: str,
    age: int,
    email: Optional[str] = None,
    country: Optional[str] = None,
    plan_type: Optional[str] = None,
) -> Dict[str, Any]:
    if not name or not name.strip():
        raise ValidationError("User name is required")
    if age < 0:
        raise ValidationError("User age must be non-negative")
    clean_name = name.strip()
    clean_email = (email or "").strip() or _default_email(clean_name)
    clean_country = (country or "").strip() or "BR"
    clean_plan = (plan_type or "").strip() or "free"
    row = await get_pool().fetchrow(
        f"INSERT INTO users (name, age, email, country, plan_type) VALUES ($1, $2, $3, $4, $5) RETURNING {USER_COLS}",
        clean_name,
        age,
        clean_email,
        clean_country,
        clean_plan,
    )
    return dict(row)


async def update_user(
    user_id: int,
    name: str,
    age: int,
    email: Optional[str] = None,
    country: Optional[str] = None,
    plan_type: Optional[str] = None,
) -> Dict[str, Any]:
    if not name or not name.strip():
        raise ValidationError("User name is required")
    if age < 0:
        raise ValidationError("User age must be non-negative")
    clean_name = name.strip()
    clean_email = (email or "").strip() or None
    clean_country = (country or "").strip() or None
    clean_plan = (plan_type or "").strip() or None
    row = await get_pool().fetchrow(
        f"""
        UPDATE users
        SET name = $1,
            age = $2,
            email = COALESCE($3, email),
            country = COALESCE($4, country),
            plan_type = COALESCE($5, plan_type)
        WHERE id = $6
        RETURNING {USER_COLS}
        """,
        clean_name,
        age,
        clean_email,
        clean_country,
        clean_plan,
        user_id,
    )
    if not row:
        raise NotFoundError(f"User {user_id} not found")
    return dict(row)


async def delete_user(user_id: int) -> bool:
    result = await get_pool().execute("DELETE FROM users WHERE id = $1", user_id)
    return result.endswith("1")


# -------------------- SONGS (7 atributos) --------------------

async def list_songs() -> List[Dict[str, Any]]:
    rows = await get_pool().fetch(f"SELECT {SONG_COLS} FROM songs ORDER BY id")
    return [dict(r) for r in rows]


async def get_song(song_id: int) -> Dict[str, Any]:
    row = await get_pool().fetchrow(f"SELECT {SONG_COLS} FROM songs WHERE id = $1", song_id)
    if not row:
        raise NotFoundError(f"Song {song_id} not found")
    return dict(row)


async def create_song(
    name: str,
    artist: str,
    album: Optional[str] = None,
    genre: Optional[str] = None,
    duration_sec: Optional[int] = None,
    release_year: Optional[int] = None,
) -> Dict[str, Any]:
    if not name or not name.strip():
        raise ValidationError("Song name is required")
    if not artist or not artist.strip():
        raise ValidationError("Song artist is required")
    dur = duration_sec if (duration_sec is not None and duration_sec > 0) else 180
    yr = release_year if (release_year is not None and release_year >= 1900) else 2024
    if duration_sec is not None and duration_sec <= 0:
        raise ValidationError("Song duration_sec must be positive")
    if release_year is not None and release_year < 1900:
        raise ValidationError("Song release_year must be >= 1900")
    row = await get_pool().fetchrow(
        f"""
        INSERT INTO songs (name, artist, album, genre, duration_sec, release_year)
        VALUES ($1, $2, $3, $4, $5, $6)
        RETURNING {SONG_COLS}
        """,
        name.strip(),
        artist.strip(),
        (album or "").strip() or "Single",
        (genre or "").strip() or "Pop",
        dur,
        yr,
    )
    return dict(row)


async def update_song(
    song_id: int,
    name: str,
    artist: str,
    album: Optional[str] = None,
    genre: Optional[str] = None,
    duration_sec: Optional[int] = None,
    release_year: Optional[int] = None,
) -> Dict[str, Any]:
    if not name or not name.strip():
        raise ValidationError("Song name is required")
    if not artist or not artist.strip():
        raise ValidationError("Song artist is required")
    if duration_sec is not None and duration_sec <= 0:
        raise ValidationError("Song duration_sec must be positive")
    if release_year is not None and release_year < 1900:
        raise ValidationError("Song release_year must be >= 1900")
    row = await get_pool().fetchrow(
        f"""
        UPDATE songs
        SET name = $1,
            artist = $2,
            album = COALESCE($3, album),
            genre = COALESCE($4, genre),
            duration_sec = COALESCE($5, duration_sec),
            release_year = COALESCE($6, release_year)
        WHERE id = $7
        RETURNING {SONG_COLS}
        """,
        name.strip(),
        artist.strip(),
        (album or "").strip() or None,
        (genre or "").strip() or None,
        duration_sec,
        release_year,
        song_id,
    )
    if not row:
        raise NotFoundError(f"Song {song_id} not found")
    return dict(row)


async def delete_song(song_id: int) -> bool:
    async with get_pool().acquire() as conn:
        async with conn.transaction():
            solo_playlists = await conn.fetch(
                """
                SELECT ps.playlist_id
                FROM playlist_songs ps
                WHERE ps.playlist_id IN (
                    SELECT playlist_id FROM playlist_songs WHERE song_id = $1
                )
                GROUP BY ps.playlist_id
                HAVING COUNT(*) = 1
                ORDER BY ps.playlist_id
                """,
                song_id,
            )
            if solo_playlists:
                ids = [r["playlist_id"] for r in solo_playlists]
                raise ValidationError(
                    f"Cannot delete song {song_id}: it is the only song in playlist(s) {ids} (1..*)"
                )
            result = await conn.execute("DELETE FROM songs WHERE id = $1", song_id)
            return result.endswith("1")


# -------------------- PLAYLISTS (6 atributos) & CONSULTAS RELACIONAIS --------------------

async def list_playlist_songs(playlist_id: int) -> List[Dict[str, Any]]:
    exists = await get_pool().fetchval("SELECT 1 FROM playlists WHERE id = $1", playlist_id)
    if not exists:
        raise NotFoundError(f"Playlist {playlist_id} not found")
    rows = await get_pool().fetch(
        """
        SELECT s.id, s.name, s.artist, s.album, s.genre, s.duration_sec, s.release_year
        FROM songs s
        INNER JOIN playlist_songs ps ON ps.song_id = s.id
        WHERE ps.playlist_id = $1
        ORDER BY s.id
        """,
        playlist_id,
    )
    return [dict(r) for r in rows]


async def get_playlist(playlist_id: int, include_songs: bool = True) -> Dict[str, Any]:
    row = await get_pool().fetchrow(
        f"SELECT {PLAYLIST_COLS} FROM playlists WHERE id = $1",
        playlist_id,
    )
    if not row:
        raise NotFoundError(f"Playlist {playlist_id} not found")
    playlist = dict(row)
    playlist["songs"] = await list_playlist_songs(playlist_id) if include_songs else []
    return playlist


async def list_user_playlists(user_id: int, include_songs: bool = False) -> List[Dict[str, Any]]:
    exists = await get_pool().fetchval("SELECT 1 FROM users WHERE id = $1", user_id)
    if not exists:
        raise NotFoundError(f"User {user_id} not found")
    rows = await get_pool().fetch(
        f"SELECT {PLAYLIST_COLS} FROM playlists WHERE user_id = $1 ORDER BY id",
        user_id,
    )
    playlists = [dict(r) for r in rows]
    if include_songs and playlists:
        pl_ids = [p["id"] for p in playlists]
        song_rows = await get_pool().fetch(
            """
            SELECT ps.playlist_id, s.id, s.name, s.artist, s.album, s.genre, s.duration_sec, s.release_year
            FROM playlist_songs ps
            INNER JOIN songs s ON s.id = ps.song_id
            WHERE ps.playlist_id = ANY($1::int[])
            ORDER BY s.id
            """,
            pl_ids,
        )
        by_pl: Dict[int, List[Dict[str, Any]]] = {pid: [] for pid in pl_ids}
        for sr in song_rows:
            by_pl[sr["playlist_id"]].append(
                {
                    "id": sr["id"],
                    "name": sr["name"],
                    "artist": sr["artist"],
                    "album": sr["album"],
                    "genre": sr["genre"],
                    "duration_sec": sr["duration_sec"],
                    "release_year": sr["release_year"],
                }
            )
        for p in playlists:
            p["songs"] = by_pl[p["id"]]
    else:
        for p in playlists:
            p["songs"] = []
    return playlists


async def list_playlists_by_song(song_id: int) -> List[Dict[str, Any]]:
    exists = await get_pool().fetchval("SELECT 1 FROM songs WHERE id = $1", song_id)
    if not exists:
        raise NotFoundError(f"Song {song_id} not found")
    rows = await get_pool().fetch(
        """
        SELECT p.id, p.name, p.user_id, p.description, p.is_public,
               TO_CHAR(p.created_at, 'YYYY-MM-DD') AS created_at
        FROM playlists p
        INNER JOIN playlist_songs ps ON ps.playlist_id = p.id
        WHERE ps.song_id = $1
        ORDER BY p.id
        """,
        song_id,
    )
    return [{**dict(r), "songs": []} for r in rows]


async def create_playlist(
    user_id: int,
    name: str,
    song_ids: List[int],
    description: Optional[str] = None,
    is_public: Optional[bool] = None,
) -> Dict[str, Any]:
    if not name or not name.strip():
        raise ValidationError("Playlist name is required")
    unique_songs = list(dict.fromkeys(song_ids))
    if not unique_songs:
        raise ValidationError("A playlist must contain at least one song (1..*)")

    async with get_pool().acquire() as conn:
        async with conn.transaction():
            user_exists = await conn.fetchval("SELECT 1 FROM users WHERE id = $1", user_id)
            if not user_exists:
                raise NotFoundError(f"User {user_id} not found")
            existing_rows = await conn.fetch(
                "SELECT id FROM songs WHERE id = ANY($1::int[])",
                unique_songs,
            )
            existing_ids = {r["id"] for r in existing_rows}
            missing = [sid for sid in unique_songs if sid not in existing_ids]
            if missing:
                raise NotFoundError(f"Song(s) not found: {missing}")
            row = await conn.fetchrow(
                "INSERT INTO playlists (name, user_id, description, is_public) VALUES ($1, $2, $3, $4) RETURNING id",
                name.strip(),
                user_id,
                (description or "").strip(),
                True if is_public is None else bool(is_public),
            )
            playlist_id = row["id"]
            await conn.executemany(
                "INSERT INTO playlist_songs (playlist_id, song_id) VALUES ($1, $2) ON CONFLICT DO NOTHING",
                [(playlist_id, sid) for sid in unique_songs],
            )
    return await get_playlist(playlist_id, include_songs=True)


async def update_playlist(
    playlist_id: int,
    name: str,
    song_ids: Optional[List[int]] = None,
    description: Optional[str] = None,
    is_public: Optional[bool] = None,
) -> Dict[str, Any]:
    if not name or not name.strip():
        raise ValidationError("Playlist name is required")

    async with get_pool().acquire() as conn:
        async with conn.transaction():
            row = await conn.fetchrow(
                """
                UPDATE playlists
                SET name = $1,
                    description = COALESCE($2, description),
                    is_public = COALESCE($3, is_public)
                WHERE id = $4
                RETURNING id
                """,
                name.strip(),
                description.strip() if description is not None else None,
                is_public,
                playlist_id,
            )
            if not row:
                raise NotFoundError(f"Playlist {playlist_id} not found")
            if song_ids is not None:
                unique_songs = list(dict.fromkeys(song_ids))
                if not unique_songs:
                    raise ValidationError("A playlist must contain at least one song (1..*)")
                existing_rows = await conn.fetch(
                    "SELECT id FROM songs WHERE id = ANY($1::int[])",
                    unique_songs,
                )
                existing_ids = {r["id"] for r in existing_rows}
                missing = [sid for sid in unique_songs if sid not in existing_ids]
                if missing:
                    raise NotFoundError(f"Song(s) not found: {missing}")
                await conn.execute("DELETE FROM playlist_songs WHERE playlist_id = $1", playlist_id)
                await conn.executemany(
                    "INSERT INTO playlist_songs (playlist_id, song_id) VALUES ($1, $2) ON CONFLICT DO NOTHING",
                    [(playlist_id, sid) for sid in unique_songs],
                )
    return await get_playlist(playlist_id, include_songs=True)


async def delete_playlist(playlist_id: int) -> bool:
    result = await get_pool().execute("DELETE FROM playlists WHERE id = $1", playlist_id)
    return result.endswith("1")


async def add_song_to_playlist(playlist_id: int, song_id: int) -> Dict[str, Any]:
    async with get_pool().acquire() as conn:
        pl_exists = await conn.fetchval("SELECT 1 FROM playlists WHERE id = $1", playlist_id)
        if not pl_exists:
            raise NotFoundError(f"Playlist {playlist_id} not found")
        song_exists = await conn.fetchval("SELECT 1 FROM songs WHERE id = $1", song_id)
        if not song_exists:
            raise NotFoundError(f"Song {song_id} not found")
        await conn.execute(
            "INSERT INTO playlist_songs (playlist_id, song_id) VALUES ($1, $2) ON CONFLICT DO NOTHING",
            playlist_id,
            song_id,
        )
    return await get_playlist(playlist_id, include_songs=True)


async def remove_song_from_playlist(playlist_id: int, song_id: int) -> Dict[str, Any]:
    async with get_pool().acquire() as conn:
        async with conn.transaction():
            pl_exists = await conn.fetchval(
                "SELECT 1 FROM playlists WHERE id = $1 FOR UPDATE", playlist_id
            )
            if not pl_exists:
                raise NotFoundError(f"Playlist {playlist_id} not found")
            in_playlist = await conn.fetchval(
                "SELECT 1 FROM playlist_songs WHERE playlist_id = $1 AND song_id = $2",
                playlist_id,
                song_id,
            )
            if not in_playlist:
                raise NotFoundError(f"Song {song_id} not found in playlist {playlist_id}")
            count = await conn.fetchval(
                "SELECT COUNT(*) FROM playlist_songs WHERE playlist_id = $1", playlist_id
            )
            if count <= 1:
                raise ValidationError("Cannot remove the last song of a playlist (1..*)")
            await conn.execute(
                "DELETE FROM playlist_songs WHERE playlist_id = $1 AND song_id = $2",
                playlist_id,
                song_id,
            )
    return await get_playlist(playlist_id, include_songs=True)
