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

function parseOptIntArg(val: unknown, field: string): number | undefined {
  if (val === undefined || val === null || val === "") return undefined;
  return parseIntArg(val, field);
}

function parseOptBoolArg(val: unknown): boolean | undefined {
  if (val === undefined || val === null || val === "") return undefined;
  if (typeof val === "boolean") return val;
  const s = String(val).trim().toLowerCase();
  if (s === "true" || s === "1") return true;
  if (s === "false" || s === "0") return false;
  throw new db.ValidationError(`Invalid boolean value: ${val}`);
}

function toIntArray(val: unknown, field = "songIds"): number[] {
  if (val === undefined || val === null) return [];
  const arr = Array.isArray(val) ? val : [val];
  return arr.map((x) => parseIntArg(x, field));
}

function mapUser(u: db.User) {
  return {
    id: u.id,
    name: u.name,
    age: u.age,
    email: u.email,
    country: u.country,
    planType: u.plan_type,
    createdAt: u.created_at,
  };
}

function mapSong(s: db.Song) {
  return {
    id: s.id,
    name: s.name,
    artist: s.artist,
    album: s.album,
    genre: s.genre,
    durationSec: s.duration_sec,
    releaseYear: s.release_year,
  };
}

function mapPlaylist(p: db.Playlist) {
  return {
    id: p.id,
    name: p.name,
    userId: p.user_id,
    description: p.description,
    isPublic: p.is_public,
    createdAt: p.created_at,
    songs: p.songs.map(mapSong),
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
          return { users: users.map(mapUser) };
        } catch (err) {
          throw wrapError(err);
        }
      },
      async GetUser(args: any) {
        try {
          const user = await db.getUser(parseIntArg(args?.id, "id"));
          return { user: mapUser(user) };
        } catch (err) {
          throw wrapError(err);
        }
      },
      async CreateUser(args: any) {
        try {
          const user = await db.createUser(
            args?.name,
            parseIntArg(args?.age, "age"),
            args?.email,
            args?.country,
            args?.planType
          );
          return { user: mapUser(user) };
        } catch (err) {
          throw wrapError(err);
        }
      },
      async UpdateUser(args: any) {
        try {
          const user = await db.updateUser(
            parseIntArg(args?.id, "id"),
            args?.name,
            parseIntArg(args?.age, "age"),
            args?.email,
            args?.country,
            args?.planType
          );
          return { user: mapUser(user) };
        } catch (err) {
          throw wrapError(err);
        }
      },
      async DeleteUser(args: any) {
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
          return { songs: songs.map(mapSong) };
        } catch (err) {
          throw wrapError(err);
        }
      },
      async GetSong(args: any) {
        try {
          const song = await db.getSong(parseIntArg(args?.id, "id"));
          return { song: mapSong(song) };
        } catch (err) {
          throw wrapError(err);
        }
      },
      async CreateSong(args: any) {
        try {
          const song = await db.createSong(
            args?.name,
            args?.artist,
            args?.album,
            args?.genre,
            parseOptIntArg(args?.durationSec, "durationSec"),
            parseOptIntArg(args?.releaseYear, "releaseYear")
          );
          return { song: mapSong(song) };
        } catch (err) {
          throw wrapError(err);
        }
      },
      async UpdateSong(args: any) {
        try {
          const song = await db.updateSong(
            parseIntArg(args?.id, "id"),
            args?.name,
            args?.artist,
            args?.album,
            args?.genre,
            parseOptIntArg(args?.durationSec, "durationSec"),
            parseOptIntArg(args?.releaseYear, "releaseYear")
          );
          return { song: mapSong(song) };
        } catch (err) {
          throw wrapError(err);
        }
      },
      async DeleteSong(args: any) {
        try {
          const deleted = await db.deleteSong(parseIntArg(args?.id, "id"));
          return { deleted };
        } catch (err) {
          throw wrapError(err);
        }
      },

      async GetPlaylist(args: any) {
        try {
          const pl = await db.getPlaylist(parseIntArg(args?.id, "id"), true);
          return { playlist: mapPlaylist(pl) };
        } catch (err) {
          throw wrapError(err);
        }
      },
      async CreatePlaylist(args: any) {
        try {
          const pl = await db.createPlaylist(
            parseIntArg(args?.userId, "userId"),
            args?.name,
            toIntArray(args?.songIds, "songIds"),
            args?.description,
            parseOptBoolArg(args?.isPublic)
          );
          return { playlist: mapPlaylist(pl) };
        } catch (err) {
          throw wrapError(err);
        }
      },
      async UpdatePlaylist(args: any) {
        try {
          const sids = toIntArray(args?.songIds, "songIds");
          const pl = await db.updatePlaylist(
            parseIntArg(args?.id, "id"),
            args?.name,
            sids.length > 0 ? sids : undefined,
            args?.description,
            parseOptBoolArg(args?.isPublic)
          );
          return { playlist: mapPlaylist(pl) };
        } catch (err) {
          throw wrapError(err);
        }
      },
      async DeletePlaylist(args: any) {
        try {
          const deleted = await db.deletePlaylist(parseIntArg(args?.id, "id"));
          return { deleted };
        } catch (err) {
          throw wrapError(err);
        }
      },
      async AddSongToPlaylist(args: any) {
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
      async RemoveSongFromPlaylist(args: any) {
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

      async ListUserPlaylists(args: any) {
        try {
          const pls = await db.listUserPlaylists(parseIntArg(args?.userId, "userId"), false);
          return { playlists: pls.map(mapPlaylist) };
        } catch (err) {
          throw wrapError(err);
        }
      },
      async ListPlaylistSongs(args: any) {
        try {
          const songs = await db.listPlaylistSongs(parseIntArg(args?.playlistId, "playlistId"));
          return { songs: songs.map(mapSong) };
        } catch (err) {
          throw wrapError(err);
        }
      },
      async ListPlaylistsBySong(args: any) {
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
