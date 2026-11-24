import http from "http";
import fs from "fs";
import * as soap from "soap";
import * as db from "../common/db";

const port = Number(process.env.PORT || 8102);
const wsdlPath = "/app/contracts/music_streaming.wsdl";
const wsdlXml = fs
  .readFileSync(wsdlPath, "utf-8")
  .replace("http://localhost:8002/soap", `http://localhost:${port}/soap`);

function parseIntArg(val: unknown, field: string): number {
  if (val === undefined || val === null || val === "") {
    throw new db.ValidationError(`Missing integer field: ${field}`);
  }
  const n = Number(String(val).trim());
  if (!Number.isInteger(n)) {
    throw new db.ValidationError(`Invalid integer for field '${field}': ${val}`);
  }
  return n;
}

function toIntArray(val: unknown, field = "songIds"): number[] {
  if (val === undefined || val === null) return [];
  const arr = Array.isArray(val) ? val : [val];
  return arr.map((x) => parseIntArg(x, field));
}

function mapPlaylist(p: db.Playlist) {
  return {
    id: p.id,
    name: p.name,
    userId: p.user_id,
    songs: p.songs,
  };
}

function wrapError(err: unknown) {
  const msg = err instanceof Error ? err.message : String(err);
  const code =
    err instanceof db.NotFoundError || err instanceof db.ValidationError
      ? "soap:Client"
      : "soap:Server";
  return {
    Fault: {
      faultcode: code,
      faultstring: msg,
    },
  };
}

const soapService = {
  MusicStreamingService: {
    MusicStreamingPort: {
      async ListUsers() {
        try {
          const users = await db.listUsers();
          return { users };
        } catch (err) {
          throw wrapError(err);
        }
      },
      async GetUser(args: { id: string | number }) {
        try {
          const user = await db.getUser(parseIntArg(args?.id, "id"));
          return { user };
        } catch (err) {
          throw wrapError(err);
        }
      },
      async CreateUser(args: { name: string; age: string | number }) {
        try {
          const user = await db.createUser(args?.name, parseIntArg(args?.age, "age"));
          return { user };
        } catch (err) {
          throw wrapError(err);
        }
      },
      async UpdateUser(args: {
        id: string | number;
        name: string;
        age: string | number;
      }) {
        try {
          const user = await db.updateUser(
            parseIntArg(args?.id, "id"),
            args?.name,
            parseIntArg(args?.age, "age")
          );
          return { user };
        } catch (err) {
          throw wrapError(err);
        }
      },
      async DeleteUser(args: { id: string | number }) {
        try {
          const deleted = await db.deleteUser(parseIntArg(args?.id, "id"));
          return { deleted };
        } catch (err) {
          throw wrapError(err);
        }
      },

      async ListSongs() {
        try {
          const songs = await db.listSongs();
          return { songs };
        } catch (err) {
          throw wrapError(err);
        }
      },
      async GetSong(args: { id: string | number }) {
        try {
          const song = await db.getSong(parseIntArg(args?.id, "id"));
          return { song };
        } catch (err) {
          throw wrapError(err);
        }
      },
      async CreateSong(args: { name: string; artist: string }) {
        try {
          const song = await db.createSong(args?.name, args?.artist);
          return { song };
        } catch (err) {
          throw wrapError(err);
        }
      },
      async UpdateSong(args: {
        id: string | number;
        name: string;
        artist: string;
      }) {
        try {
          const song = await db.updateSong(
            parseIntArg(args?.id, "id"),
            args?.name,
            args?.artist
          );
          return { song };
        } catch (err) {
          throw wrapError(err);
        }
      },
      async DeleteSong(args: { id: string | number }) {
        try {
          const deleted = await db.deleteSong(parseIntArg(args?.id, "id"));
          return { deleted };
        } catch (err) {
          throw wrapError(err);
        }
      },

      async GetPlaylist(args: { id: string | number }) {
        try {
          const pl = await db.getPlaylist(parseIntArg(args?.id, "id"), true);
          return { playlist: mapPlaylist(pl) };
        } catch (err) {
          throw wrapError(err);
        }
      },
      async CreatePlaylist(args: {
        name: string;
        userId: string | number;
        songIds: unknown;
      }) {
        try {
          const pl = await db.createPlaylist(
            parseIntArg(args?.userId, "userId"),
            args?.name,
            toIntArray(args?.songIds, "songIds")
          );
          return { playlist: mapPlaylist(pl) };
        } catch (err) {
          throw wrapError(err);
        }
      },
      async UpdatePlaylist(args: {
        id: string | number;
        name: string;
        songIds?: unknown;
      }) {
        try {
          const sids = toIntArray(args?.songIds, "songIds");
          const pl = await db.updatePlaylist(
            parseIntArg(args?.id, "id"),
            args?.name,
            sids.length > 0 ? sids : undefined
          );
          return { playlist: mapPlaylist(pl) };
        } catch (err) {
          throw wrapError(err);
        }
      },
      async DeletePlaylist(args: { id: string | number }) {
        try {
          const deleted = await db.deletePlaylist(parseIntArg(args?.id, "id"));
          return { deleted };
        } catch (err) {
          throw wrapError(err);
        }
      },
      async AddSongToPlaylist(args: {
        playlistId: string | number;
        songId: string | number;
      }) {
        try {
          const pl = await db.addSongToPlaylist(
            parseIntArg(args?.playlistId, "playlistId"),
            parseIntArg(args?.songId, "songId")
          );
          return { playlist: mapPlaylist(pl) };
        } catch (err) {
          throw wrapError(err);
        }
      },
      async RemoveSongFromPlaylist(args: {
        playlistId: string | number;
        songId: string | number;
      }) {
        try {
          const pl = await db.removeSongFromPlaylist(
            parseIntArg(args?.playlistId, "playlistId"),
            parseIntArg(args?.songId, "songId")
          );
          return { playlist: mapPlaylist(pl) };
        } catch (err) {
          throw wrapError(err);
        }
      },

      async ListUserPlaylists(args: { userId: string | number }) {
        try {
          const pls = await db.listUserPlaylists(parseIntArg(args?.userId, "userId"), false);
          return { playlists: pls.map(mapPlaylist) };
        } catch (err) {
          throw wrapError(err);
        }
      },
      async ListPlaylistSongs(args: { playlistId: string | number }) {
        try {
          const songs = await db.listPlaylistSongs(parseIntArg(args?.playlistId, "playlistId"));
          return { songs };
        } catch (err) {
          throw wrapError(err);
        }
      },
      async ListPlaylistsBySong(args: { songId: string | number }) {
        try {
          const pls = await db.listPlaylistsBySong(parseIntArg(args?.songId, "songId"));
          return { playlists: pls.map(mapPlaylist) };
        } catch (err) {
          throw wrapError(err);
        }
      },
    },
  },
};

const server = http.createServer((req, res) => {
  if (req.url === "/health") {
    res.writeHead(200, { "Content-Type": "application/json" });
    res.end(JSON.stringify({ status: "ok", service: "node-soap" }));
    return;
  }
  if (!req.url?.startsWith("/soap")) {
    res.statusCode = 404;
    res.end("Not Found");
  }
});

server.listen(port, "0.0.0.0", () => {
  soap.listen(server, "/soap", soapService, wsdlXml);
  console.log(`Node SOAP server listening on 0.0.0.0:${port}/soap`);
});
