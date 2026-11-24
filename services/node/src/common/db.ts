import { Pool } from "pg";

export interface User {
  id: number;
  name: string;
  age: number;
  email: string;
  country: string;
  plan_type: string;
  created_at: string;
}

export interface Song {
  id: number;
  name: string;
  artist: string;
  album: string;
  genre: string;
  duration_sec: number;
  release_year: number;
}

export interface Playlist {
  id: number;
  name: string;
  user_id: number;
  description: string;
  is_public: boolean;
  created_at: string;
  songs: Song[];
}

const USER_COLS =
  "id, name, age, email, country, plan_type, TO_CHAR(created_at, 'YYYY-MM-DD') AS created_at";
const SONG_COLS =
  "id, name, artist, album, genre, duration_sec, release_year";
const PLAYLIST_COLS =
  "id, name, user_id, description, is_public, TO_CHAR(created_at, 'YYYY-MM-DD') AS created_at";

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

function defaultEmail(name: string): string {
  const slug =
    name
      .trim()
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, ".")
      .replace(/^\.+|\.+$/g, "") || "user";
  return `${slug}@musicstream.io`;
}

const connectionString =
  process.env.DATABASE_URL ||
  "postgresql://streaming:streaming@postgres:5432/music_streaming";

export const pool = new Pool({
  connectionString,
  max: 20,
});

// -------------------- USERS (7 atributos) --------------------

export async function listUsers(): Promise<User[]> {
  const { rows } = await pool.query<User>(
    `SELECT ${USER_COLS} FROM users ORDER BY id`
  );
  return rows;
}

export async function getUser(userId: number): Promise<User> {
  const { rows } = await pool.query<User>(
    `SELECT ${USER_COLS} FROM users WHERE id = $1`,
    [userId]
  );
  if (rows.length === 0) throw new NotFoundError(`User ${userId} not found`);
  return rows[0];
}

export async function createUser(
  name: string,
  age: number,
  email?: string,
  country?: string,
  planType?: string
): Promise<User> {
  if (typeof name !== "string" || !name.trim())
    throw new ValidationError("User name is required");
  if (!Number.isInteger(age) || age < 0)
    throw new ValidationError("User age must be a non-negative integer");
  const cleanName = name.trim();
  const cleanEmail = (email || "").trim() || defaultEmail(cleanName);
  const cleanCountry = (country || "").trim() || "BR";
  const cleanPlan = (planType || "").trim() || "free";
  const { rows } = await pool.query<User>(
    `INSERT INTO users (name, age, email, country, plan_type)
     VALUES ($1, $2, $3, $4, $5)
     RETURNING ${USER_COLS}`,
    [cleanName, age, cleanEmail, cleanCountry, cleanPlan]
  );
  return rows[0];
}

export async function updateUser(
  userId: number,
  name: string,
  age: number,
  email?: string,
  country?: string,
  planType?: string
): Promise<User> {
  if (typeof name !== "string" || !name.trim())
    throw new ValidationError("User name is required");
  if (!Number.isInteger(age) || age < 0)
    throw new ValidationError("User age must be a non-negative integer");
  const cleanEmail = (email || "").trim() || null;
  const cleanCountry = (country || "").trim() || null;
  const cleanPlan = (planType || "").trim() || null;
  const { rows } = await pool.query<User>(
    `UPDATE users
     SET name = $1,
         age = $2,
         email = COALESCE($3, email),
         country = COALESCE($4, country),
         plan_type = COALESCE($5, plan_type)
     WHERE id = $6
     RETURNING ${USER_COLS}`,
    [name.trim(), age, cleanEmail, cleanCountry, cleanPlan, userId]
  );
  if (rows.length === 0) throw new NotFoundError(`User ${userId} not found`);
  return rows[0];
}

export async function deleteUser(userId: number): Promise<boolean> {
  const res = await pool.query("DELETE FROM users WHERE id = $1", [userId]);
  return (res.rowCount ?? 0) > 0;
}

// -------------------- SONGS (7 atributos) --------------------

export async function listSongs(): Promise<Song[]> {
  const { rows } = await pool.query<Song>(
    `SELECT ${SONG_COLS} FROM songs ORDER BY id`
  );
  return rows;
}

export async function getSong(songId: number): Promise<Song> {
  const { rows } = await pool.query<Song>(
    `SELECT ${SONG_COLS} FROM songs WHERE id = $1`,
    [songId]
  );
  if (rows.length === 0) throw new NotFoundError(`Song ${songId} not found`);
  return rows[0];
}

export async function createSong(
  name: string,
  artist: string,
  album?: string,
  genre?: string,
  durationSec?: number,
  releaseYear?: number
): Promise<Song> {
  if (typeof name !== "string" || !name.trim())
    throw new ValidationError("Song name is required");
  if (typeof artist !== "string" || !artist.trim())
    throw new ValidationError("Song artist is required");
  if (durationSec !== undefined && (!Number.isInteger(durationSec) || durationSec <= 0))
    throw new ValidationError("Song duration_sec must be a positive integer");
  if (releaseYear !== undefined && (!Number.isInteger(releaseYear) || releaseYear < 1900))
    throw new ValidationError("Song release_year must be >= 1900");
  const { rows } = await pool.query<Song>(
    `INSERT INTO songs (name, artist, album, genre, duration_sec, release_year)
     VALUES ($1, $2, $3, $4, $5, $6)
     RETURNING ${SONG_COLS}`,
    [
      name.trim(),
      artist.trim(),
      (album || "").trim() || "Single",
      (genre || "").trim() || "Pop",
      durationSec ?? 180,
      releaseYear ?? 2024,
    ]
  );
  return rows[0];
}

export async function updateSong(
  songId: number,
  name: string,
  artist: string,
  album?: string,
  genre?: string,
  durationSec?: number,
  releaseYear?: number
): Promise<Song> {
  if (typeof name !== "string" || !name.trim())
    throw new ValidationError("Song name is required");
  if (typeof artist !== "string" || !artist.trim())
    throw new ValidationError("Song artist is required");
  if (durationSec !== undefined && (!Number.isInteger(durationSec) || durationSec <= 0))
    throw new ValidationError("Song duration_sec must be a positive integer");
  if (releaseYear !== undefined && (!Number.isInteger(releaseYear) || releaseYear < 1900))
    throw new ValidationError("Song release_year must be >= 1900");
  const { rows } = await pool.query<Song>(
    `UPDATE songs
     SET name = $1,
         artist = $2,
         album = COALESCE($3, album),
         genre = COALESCE($4, genre),
         duration_sec = COALESCE($5, duration_sec),
         release_year = COALESCE($6, release_year)
     WHERE id = $7
     RETURNING ${SONG_COLS}`,
    [
      name.trim(),
      artist.trim(),
      (album || "").trim() || null,
      (genre || "").trim() || null,
      durationSec ?? null,
      releaseYear ?? null,
      songId,
    ]
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

// -------------------- PLAYLISTS (6 atributos) & RELATIONAL QUERIES --------------------

export async function listPlaylistSongs(playlistId: number): Promise<Song[]> {
  const check = await pool.query("SELECT 1 FROM playlists WHERE id = $1", [
    playlistId,
  ]);
  if (check.rowCount === 0)
    throw new NotFoundError(`Playlist ${playlistId} not found`);

  const { rows } = await pool.query<Song>(
    `SELECT s.id, s.name, s.artist, s.album, s.genre, s.duration_sec, s.release_year
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
  const { rows } = await pool.query<Omit<Playlist, "songs">>(
    `SELECT ${PLAYLIST_COLS} FROM playlists WHERE id = $1`,
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
  const { rows } = await pool.query<Omit<Playlist, "songs">>(
    `SELECT ${PLAYLIST_COLS} FROM playlists WHERE user_id = $1 ORDER BY id`,
    [userId]
  );
  const playlists: Playlist[] = rows.map((r) => ({ ...r, songs: [] }));

  if (includeSongs && playlists.length > 0) {
    const ids = playlists.map((p) => p.id);
    const { rows: songRows } = await pool.query<Song & { playlist_id: number }>(
      `SELECT ps.playlist_id, s.id, s.name, s.artist, s.album, s.genre, s.duration_sec, s.release_year
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
        album: sr.album,
        genre: sr.genre,
        duration_sec: sr.duration_sec,
        release_year: sr.release_year,
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
  const { rows } = await pool.query<Omit<Playlist, "songs">>(
    `SELECT p.id, p.name, p.user_id, p.description, p.is_public,
            TO_CHAR(p.created_at, 'YYYY-MM-DD') AS created_at
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
  songIds: number[],
  description?: string,
  isPublic?: boolean
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
      "INSERT INTO playlists (name, user_id, description, is_public) VALUES ($1, $2, $3, $4) RETURNING id",
      [name.trim(), userId, (description || "").trim(), isPublic ?? true]
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
  songIds?: number[],
  description?: string,
  isPublic?: boolean
): Promise<Playlist> {
  if (typeof name !== "string" || !name.trim())
    throw new ValidationError("Playlist name is required");

  const client = await pool.connect();
  try {
    await client.query("BEGIN");
    const { rowCount } = await client.query(
      `UPDATE playlists
       SET name = $1,
           description = COALESCE($2, description),
           is_public = COALESCE($3, is_public)
       WHERE id = $4`,
      [
        name.trim(),
        description !== undefined ? description.trim() : null,
        isPublic !== undefined ? isPublic : null,
        playlistId,
      ]
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
