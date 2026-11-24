import Fastify, { FastifyReply } from "fastify";
import * as db from "../common/db";

const app = Fastify({ logger: false });

function handleError(reply: FastifyReply, err: unknown) {
  if (err instanceof db.NotFoundError) {
    return reply.code(404).send({ detail: err.message });
  }
  if (err instanceof db.ValidationError) {
    return reply.code(400).send({ detail: err.message });
  }
  return reply.code(500).send({ detail: (err as Error).message });
}

function parseIntField(val: unknown, field: string): number {
  if (val === undefined || val === null || val === "") {
    throw new db.ValidationError(`Missing integer field: ${field}`);
  }
  const n = typeof val === "number" ? val : Number(String(val).trim());
  if (!Number.isInteger(n)) {
    throw new db.ValidationError(`Invalid integer for field '${field}': ${val}`);
  }
  return n;
}

function requireBody<T extends Record<string, unknown>>(body: unknown): T {
  if (!body || typeof body !== "object" || Array.isArray(body)) {
    throw new db.ValidationError("Request body must be a JSON object");
  }
  return body as T;
}

function parseIntArray(val: unknown, field: string): number[] {
  if (!Array.isArray(val)) {
    throw new db.ValidationError(`Field '${field}' must be an array of integers`);
  }
  return val.map((item) => parseIntField(item, field));
}

app.get("/health", async () => ({ status: "ok", service: "node-rest" }));

// -------------------- USUÁRIOS --------------------

app.get("/users", async () => db.listUsers());

app.get<{ Params: { id: string } }>("/users/:id", async (req, reply) => {
  try {
    return await db.getUser(parseIntField(req.params.id, "id"));
  } catch (err) {
    return handleError(reply, err);
  }
});

app.post("/users", async (req, reply) => {
  try {
    const body = requireBody<{ name: unknown; age: unknown }>(req.body);
    const user = await db.createUser(
      String(body.name ?? ""),
      parseIntField(body.age, "age")
    );
    return reply.code(201).send(user);
  } catch (err) {
    return handleError(reply, err);
  }
});

app.put<{ Params: { id: string } }>("/users/:id", async (req, reply) => {
  try {
    const body = requireBody<{ name: unknown; age: unknown }>(req.body);
    return await db.updateUser(
      parseIntField(req.params.id, "id"),
      String(body.name ?? ""),
      parseIntField(body.age, "age")
    );
  } catch (err) {
    return handleError(reply, err);
  }
});

app.delete<{ Params: { id: string } }>("/users/:id", async (req, reply) => {
  try {
    const id = parseIntField(req.params.id, "id");
    const deleted = await db.deleteUser(id);
    if (!deleted) return reply.code(404).send({ detail: `User ${id} not found` });
    return { deleted: true };
  } catch (err) {
    return handleError(reply, err);
  }
});

// Consulta #3: Listar todas as playlists de um usuário
app.get<{ Params: { id: string } }>(
  "/users/:id/playlists",
  async (req, reply) => {
    try {
      return await db.listUserPlaylists(parseIntField(req.params.id, "id"), false);
    } catch (err) {
      return handleError(reply, err);
    }
  }
);

// -------------------- MÚSICAS --------------------

app.get("/songs", async () => db.listSongs());

app.get<{ Params: { id: string } }>("/songs/:id", async (req, reply) => {
  try {
    return await db.getSong(parseIntField(req.params.id, "id"));
  } catch (err) {
    return handleError(reply, err);
  }
});

app.post("/songs", async (req, reply) => {
  try {
    const body = requireBody<{ name: unknown; artist: unknown }>(req.body);
    const song = await db.createSong(
      String(body.name ?? ""),
      String(body.artist ?? "")
    );
    return reply.code(201).send(song);
  } catch (err) {
    return handleError(reply, err);
  }
});

app.put<{ Params: { id: string } }>("/songs/:id", async (req, reply) => {
  try {
    const body = requireBody<{ name: unknown; artist: unknown }>(req.body);
    return await db.updateSong(
      parseIntField(req.params.id, "id"),
      String(body.name ?? ""),
      String(body.artist ?? "")
    );
  } catch (err) {
    return handleError(reply, err);
  }
});

app.delete<{ Params: { id: string } }>("/songs/:id", async (req, reply) => {
  try {
    const id = parseIntField(req.params.id, "id");
    const deleted = await db.deleteSong(id);
    if (!deleted) return reply.code(404).send({ detail: `Song ${id} not found` });
    return { deleted: true };
  } catch (err) {
    return handleError(reply, err);
  }
});

// Consulta #5: Listar todas as playlists que contêm uma música
app.get<{ Params: { id: string } }>(
  "/songs/:id/playlists",
  async (req, reply) => {
    try {
      return await db.listPlaylistsBySong(parseIntField(req.params.id, "id"));
    } catch (err) {
      return handleError(reply, err);
    }
  }
);

// -------------------- PLAYLISTS --------------------

app.get<{ Params: { id: string } }>("/playlists/:id", async (req, reply) => {
  try {
    return await db.getPlaylist(parseIntField(req.params.id, "id"), true);
  } catch (err) {
    return handleError(reply, err);
  }
});

app.post("/playlists", async (req, reply) => {
  try {
    const body = requireBody<{
      name: unknown;
      user_id: unknown;
      song_ids: unknown;
    }>(req.body);
    const pl = await db.createPlaylist(
      parseIntField(body.user_id, "user_id"),
      String(body.name ?? ""),
      parseIntArray(body.song_ids, "song_ids")
    );
    return reply.code(201).send(pl);
  } catch (err) {
    return handleError(reply, err);
  }
});

app.put<{ Params: { id: string } }>("/playlists/:id", async (req, reply) => {
  try {
    const body = requireBody<{ name: unknown; song_ids?: unknown }>(req.body);
    const songIds =
      body.song_ids !== undefined && body.song_ids !== null
        ? parseIntArray(body.song_ids, "song_ids")
        : undefined;
    return await db.updatePlaylist(
      parseIntField(req.params.id, "id"),
      String(body.name ?? ""),
      songIds
    );
  } catch (err) {
    return handleError(reply, err);
  }
});

app.delete<{ Params: { id: string } }>("/playlists/:id", async (req, reply) => {
  try {
    const id = parseIntField(req.params.id, "id");
    const deleted = await db.deletePlaylist(id);
    if (!deleted)
      return reply.code(404).send({ detail: `Playlist ${id} not found` });
    return { deleted: true };
  } catch (err) {
    return handleError(reply, err);
  }
});

// Consulta #4: Listar todas as músicas de uma playlist
app.get<{ Params: { id: string } }>(
  "/playlists/:id/songs",
  async (req, reply) => {
    try {
      return await db.listPlaylistSongs(parseIntField(req.params.id, "id"));
    } catch (err) {
      return handleError(reply, err);
    }
  }
);

app.post<{ Params: { id: string; songId: string } }>(
  "/playlists/:id/songs/:songId",
  async (req, reply) => {
    try {
      return await db.addSongToPlaylist(
        parseIntField(req.params.id, "id"),
        parseIntField(req.params.songId, "songId")
      );
    } catch (err) {
      return handleError(reply, err);
    }
  }
);

app.delete<{ Params: { id: string; songId: string } }>(
  "/playlists/:id/songs/:songId",
  async (req, reply) => {
    try {
      return await db.removeSongFromPlaylist(
        parseIntField(req.params.id, "id"),
        parseIntField(req.params.songId, "songId")
      );
    } catch (err) {
      return handleError(reply, err);
    }
  }
);

const port = Number(process.env.PORT || 8101);
app.listen({ host: "0.0.0.0", port }).then(() => {
  console.log(`Node REST server listening on 0.0.0.0:${port}`);
});
