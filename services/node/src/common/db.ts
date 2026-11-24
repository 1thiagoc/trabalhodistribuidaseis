import { Pool } from "pg";

export interface User {
  id: number;
  name: string;
  age: number;
}

export interface Song {
  id: number;
  name: string;
  artist: string;
}

export interface Playlist {
  id: number;
  name: string;
  user_id: number;
  songs: Song[];
}

export class NotFoundError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "NotFoundError";
  }
}

export class ValidationError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "ValidationError";
  }
}

const connectionString =
  process.env.DATABASE_URL ||
  "postgresql://streaming:streaming@postgres:5432/music_streaming";

export const pool = new Pool({
  connectionString,
  max: 20,
});

// -------------------- USERS --------------------

export async function listUsers(): Promise<User[]> {
  const { rows } = await pool.query<User>(
    "SELECT id, name, age FROM users ORDER BY id"
  );
  return rows;
}

export async function getUser(userId: number): Promise<User> {
  const { rows } = await pool.query<User>(
    "SELECT id, name, age FROM users WHERE id = $1",
    [userId]
  );
  if (rows.length === 0) throw new NotFoundError(`User ${userId} not found`);
  return rows[0];
}

export async function createUser(name: string, age: number): Promise<User> {
  if (typeof name !== "string" || !name.trim())
    throw new ValidationError("User name is required");
  if (!Number.isInteger(age) || age < 0)
    throw new ValidationError("User age must be a non-negative integer");
  const { rows } = await pool.query<User>(
    "INSERT INTO users (name, age) VALUES ($1, $2) RETURNING id, name, age",
    [name.trim(), age]
  );
  return rows[0];
}

export async function updateUser(
  userId: number,
  name: string,
  age: number
): Promise<User> {
  if (typeof name !== "string" || !name.trim())
    throw new ValidationError("User name is required");
  if (!Number.isInteger(age) || age < 0)
    throw new ValidationError("User age must be a non-negative integer");
  const { rows } = await pool.query<User>(
    "UPDATE users SET name = $1, age = $2 WHERE id = $3 RETURNING id, name, age",
    [name.trim(), age, userId]
  );
  if (rows.length === 0) throw new NotFoundError(`User ${userId} not found`);
  return rows[0];
}

export async function deleteUser(userId: number): Promise<boolean> {
  const res = await pool.query("DELETE FROM users WHERE id = $1", [userId]);
  return (res.rowCount ?? 0) > 0;
}

// -------------------- SONGS --------------------

export async function listSongs(): Promise<Song[]> {
  const { rows } = await pool.query<Song>(
    "SELECT id, name, artist FROM songs ORDER BY id"
  );
  return rows;
}

export async function getSong(songId: number): Promise<Song> {
  const { rows } = await pool.query<Song>(
    "SELECT id, name, artist FROM songs WHERE id = $1",
    [songId]
  );
  if (rows.length === 0) throw new NotFoundError(`Song ${songId} not found`);
  return rows[0];
}

export async function createSong(name: string, artist: string): Promise<Song> {
  if (!name || !name.trim()) throw new ValidationError("Song name is required");
  if (!artist || !artist.trim())
    throw new ValidationError("Song artist is required");
  const { rows } = await pool.query<Song>(
    "INSERT INTO songs (name, artist) VALUES ($1, $2) RETURNING id, name, artist",
    [name.trim(), artist.trim()]
  );
  return rows[0];
}

export async function updateSong(
  songId: number,
  name: string,
  artist: string
): Promise<Song> {
  if (!name || !name.trim()) throw new ValidationError("Song name is required");
  if (!artist || !artist.trim())
    throw new ValidationError("Song artist is required");
  const { rows } = await pool.query<Song>(
    "UPDATE songs SET name = $1, artist = $2 WHERE id = $3 RETURNING id, name, artist",
    [name.trim(), artist.trim(), songId]
  );
  if (rows.length === 0) throw new NotFoundError(`Song ${songId} not found`);
  return rows[0];
}

export async function deleteSong(songId: number): Promise<boolean> {
  const client = await pool.connect();
  try {
    await client.query("BEGIN");
    const solo = await client.query<{ playlist_id: number }>(
      `SELECT ps.playlist_id
       FROM playlist_songs ps
       WHERE ps.playlist_id IN (
         SELECT playlist_id FROM playlist_songs WHERE song_id = $1
       )
       GROUP BY ps.playlist_id
       HAVING COUNT(*) = 1
       ORDER BY ps.playlist_id`,
      [songId]
    );
    if (solo.rows.length > 0) {
      const ids = solo.rows.map((r) => r.playlist_id);
      throw new ValidationError(
        `Cannot delete song ${songId}: it is the only song in playlist(s) [${ids.join(", ")}] (1..*)`
      );
    }
    const res = await client.query("DELETE FROM songs WHERE id = $1", [songId]);
    await client.query("COMMIT");
    return (res.rowCount ?? 0) > 0;
  } catch (err) {
    await client.query("ROLLBACK");
    throw err;
  } finally {
    client.release();
  }
}

// -------------------- PLAYLISTS & RELATIONAL QUERIES --------------------

export async function listPlaylistSongs(playlistId: number): Promise<Song[]> {
  const check = await pool.query("SELECT 1 FROM playlists WHERE id = $1", [
    playlistId,
  ]);
  if (check.rowCount === 0)
    throw new NotFoundError(`Playlist ${playlistId} not found`);

  const { rows } = await pool.query<Song>(
    `SELECT s.id, s.name, s.artist
     FROM songs s
     INNER JOIN playlist_songs ps ON ps.song_id = s.id
     WHERE ps.playlist_id = $1
     ORDER BY s.id`,
    [playlistId]
  );
  return rows;
}

export async function getPlaylist(
  playlistId: number,
  includeSongs = true
): Promise<Playlist> {
  const { rows } = await pool.query<{ id: number; name: string; user_id: number }>(
    "SELECT id, name, user_id FROM playlists WHERE id = $1",
    [playlistId]
  );
  if (rows.length === 0)
    throw new NotFoundError(`Playlist ${playlistId} not found`);
  const songs = includeSongs ? await listPlaylistSongs(playlistId) : [];
  return { ...rows[0], songs };
}

export async function listUserPlaylists(
  userId: number,
  includeSongs = false
): Promise<Playlist[]> {
  const uCheck = await pool.query("SELECT 1 FROM users WHERE id = $1", [
    userId,
  ]);
  if (uCheck.rowCount === 0)
    throw new NotFoundError(`User ${userId} not found`);
  const { rows } = await pool.query<{ id: number; name: string; user_id: number }>(
    "SELECT id, name, user_id FROM playlists WHERE user_id = $1 ORDER BY id",
    [userId]
  );
  const playlists: Playlist[] = rows.map((r) => ({ ...r, songs: [] }));

  if (includeSongs && playlists.length > 0) {
    const ids = playlists.map((p) => p.id);
    const { rows: songRows } = await pool.query<{
      playlist_id: number;
      id: number;
      name: string;
      artist: string;
    }>(
      `SELECT ps.playlist_id, s.id, s.name, s.artist
       FROM playlist_songs ps
       INNER JOIN songs s ON s.id = ps.song_id
       WHERE ps.playlist_id = ANY($1::int[])
       ORDER BY s.id`,
      [ids]
    );
    const map = new Map<number, Song[]>();
    for (const id of ids) map.set(id, []);
    for (const sr of songRows) {
      map.get(sr.playlist_id)?.push({
        id: sr.id,
        name: sr.name,
        artist: sr.artist,
      });
    }
    for (const pl of playlists) {
      pl.songs = map.get(pl.id) || [];
    }
  }
  return playlists;
}

export async function listPlaylistsBySong(songId: number): Promise<Playlist[]> {
  const sCheck = await pool.query("SELECT 1 FROM songs WHERE id = $1", [
    songId,
  ]);
  if (sCheck.rowCount === 0)
    throw new NotFoundError(`Song ${songId} not found`);
  const { rows } = await pool.query<{ id: number; name: string; user_id: number }>(
    `SELECT p.id, p.name, p.user_id
     FROM playlists p
     INNER JOIN playlist_songs ps ON ps.playlist_id = p.id
     WHERE ps.song_id = $1
     ORDER BY p.id`,
    [songId]
  );
  return rows.map((r) => ({ ...r, songs: [] }));
}

export async function createPlaylist(
  userId: number,
  name: string,
  songIds: number[]
): Promise<Playlist> {
  if (typeof name !== "string" || !name.trim())
    throw new ValidationError("Playlist name is required");
  const uniqueSongs = Array.from(new Set(songIds));
  if (uniqueSongs.length === 0)
    throw new ValidationError("A playlist must contain at least one song (1..*)");

  const client = await pool.connect();
  try {
    await client.query("BEGIN");
    const uCheck = await client.query("SELECT 1 FROM users WHERE id = $1", [
      userId,
    ]);
    if (uCheck.rowCount === 0)
      throw new NotFoundError(`User ${userId} not found`);

    const sCheck = await client.query<{ id: number }>(
      "SELECT id FROM songs WHERE id = ANY($1::int[])",
      [uniqueSongs]
    );
    const existingIds = new Set(sCheck.rows.map((r) => r.id));
    const missing = uniqueSongs.filter((sid) => !existingIds.has(sid));
    if (missing.length > 0)
      throw new NotFoundError(`Song(s) not found: [${missing.join(", ")}]`);

    const { rows } = await client.query<{ id: number }>(
      "INSERT INTO playlists (name, user_id) VALUES ($1, $2) RETURNING id",
      [name.trim(), userId]
    );
    const playlistId = rows[0].id;
    for (const sid of uniqueSongs) {
      await client.query(
        "INSERT INTO playlist_songs (playlist_id, song_id) VALUES ($1, $2) ON CONFLICT DO NOTHING",
        [playlistId, sid]
      );
    }
    await client.query("COMMIT");
    return await getPlaylist(playlistId, true);
  } catch (err) {
    await client.query("ROLLBACK");
    throw err;
  } finally {
    client.release();
  }
}

export async function updatePlaylist(
  playlistId: number,
  name: string,
  songIds?: number[]
): Promise<Playlist> {
  if (typeof name !== "string" || !name.trim())
    throw new ValidationError("Playlist name is required");

  const client = await pool.connect();
  try {
    await client.query("BEGIN");
    const { rowCount } = await client.query(
      "UPDATE playlists SET name = $1 WHERE id = $2",
      [name.trim(), playlistId]
    );
    if (rowCount === 0)
      throw new NotFoundError(`Playlist ${playlistId} not found`);

    if (songIds !== undefined) {
      const uniqueSongs = Array.from(new Set(songIds));
      if (uniqueSongs.length === 0)
        throw new ValidationError(
          "A playlist must contain at least one song (1..*)"
        );
      const sCheck = await client.query<{ id: number }>(
        "SELECT id FROM songs WHERE id = ANY($1::int[])",
        [uniqueSongs]
      );
      const existingIds = new Set(sCheck.rows.map((r) => r.id));
      const missing = uniqueSongs.filter((sid) => !existingIds.has(sid));
      if (missing.length > 0)
        throw new NotFoundError(`Song(s) not found: [${missing.join(", ")}]`);
      await client.query("DELETE FROM playlist_songs WHERE playlist_id = $1", [
        playlistId,
      ]);
      for (const sid of uniqueSongs) {
        await client.query(
          "INSERT INTO playlist_songs (playlist_id, song_id) VALUES ($1, $2) ON CONFLICT DO NOTHING",
          [playlistId, sid]
        );
      }
    }
    await client.query("COMMIT");
    return await getPlaylist(playlistId, true);
  } catch (err) {
    await client.query("ROLLBACK");
    throw err;
  } finally {
    client.release();
  }
}

export async function deletePlaylist(playlistId: number): Promise<boolean> {
  const res = await pool.query("DELETE FROM playlists WHERE id = $1", [
    playlistId,
  ]);
  return (res.rowCount ?? 0) > 0;
}

export async function addSongToPlaylist(
  playlistId: number,
  songId: number
): Promise<Playlist> {
  const plCheck = await pool.query("SELECT 1 FROM playlists WHERE id = $1", [
    playlistId,
  ]);
  if (plCheck.rowCount === 0)
    throw new NotFoundError(`Playlist ${playlistId} not found`);
  const sCheck = await pool.query("SELECT 1 FROM songs WHERE id = $1", [songId]);
  if (sCheck.rowCount === 0) throw new NotFoundError(`Song ${songId} not found`);

  await pool.query(
    "INSERT INTO playlist_songs (playlist_id, song_id) VALUES ($1, $2) ON CONFLICT DO NOTHING",
    [playlistId, songId]
  );
  return await getPlaylist(playlistId, true);
}

export async function removeSongFromPlaylist(
  playlistId: number,
  songId: number
): Promise<Playlist> {
  const client = await pool.connect();
  try {
    await client.query("BEGIN");
    const plCheck = await client.query(
      "SELECT 1 FROM playlists WHERE id = $1 FOR UPDATE",
      [playlistId]
    );
    if (plCheck.rowCount === 0)
      throw new NotFoundError(`Playlist ${playlistId} not found`);

    const inPl = await client.query(
      "SELECT 1 FROM playlist_songs WHERE playlist_id = $1 AND song_id = $2",
      [playlistId, songId]
    );
    if (inPl.rowCount === 0)
      throw new NotFoundError(
        `Song ${songId} not found in playlist ${playlistId}`
      );

    const countRes = await client.query<{ count: string }>(
      "SELECT COUNT(*)::text AS count FROM playlist_songs WHERE playlist_id = $1",
      [playlistId]
    );
    if (parseInt(countRes.rows[0].count, 10) <= 1) {
      throw new ValidationError(
        "Cannot remove the last song of a playlist (1..*)"
      );
    }

    await client.query(
      "DELETE FROM playlist_songs WHERE playlist_id = $1 AND song_id = $2",
      [playlistId, songId]
    );
    await client.query("COMMIT");
    return await getPlaylist(playlistId, true);
  } catch (err) {
    await client.query("ROLLBACK");
    throw err;
  } finally {
    client.release();
  }
}
