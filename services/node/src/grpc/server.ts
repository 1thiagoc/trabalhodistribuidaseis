import * as grpc from "@grpc/grpc-js";
import * as protoLoader from "@grpc/proto-loader";
import * as db from "../common/db";

const PROTO_PATH = "/app/contracts/music_streaming.proto";

const packageDefinition = protoLoader.loadSync(PROTO_PATH, {
  keepCase: true,
  longs: String,
  enums: String,
  defaults: true,
  oneofs: true,
});

const proto = grpc.loadPackageDefinition(packageDefinition) as any;

function toGrpcError(err: unknown): grpc.ServiceError {
  const msg = err instanceof Error ? err.message : String(err);
  let code = grpc.status.INTERNAL;
  if (err instanceof db.NotFoundError) code = grpc.status.NOT_FOUND;
  else if (err instanceof db.ValidationError) code = grpc.status.INVALID_ARGUMENT;
  return { name: "GrpcError", message: msg, code } as grpc.ServiceError;
}

const handlers = {
  async ListUsers(_call: any, cb: any) {
    try {
      const users = await db.listUsers();
      cb(null, { users });
    } catch (err) {
      cb(toGrpcError(err));
    }
  },
  async GetUser(call: any, cb: any) {
    try {
      cb(null, await db.getUser(call.request.id));
    } catch (err) {
      cb(toGrpcError(err));
    }
  },
  async CreateUser(call: any, cb: any) {
    try {
      cb(
        null,
        await db.createUser(
          call.request.name,
          call.request.age,
          call.request.email || undefined,
          call.request.country || undefined,
          call.request.plan_type || undefined
        )
      );
    } catch (err) {
      cb(toGrpcError(err));
    }
  },
  async UpdateUser(call: any, cb: any) {
    try {
      cb(
        null,
        await db.updateUser(
          call.request.id,
          call.request.name,
          call.request.age,
          call.request.email || undefined,
          call.request.country || undefined,
          call.request.plan_type || undefined
        )
      );
    } catch (err) {
      cb(toGrpcError(err));
    }
  },
  async DeleteUser(call: any, cb: any) {
    try {
      const deleted = await db.deleteUser(call.request.id);
      cb(null, { deleted });
    } catch (err) {
      cb(toGrpcError(err));
    }
  },

  async ListSongs(_call: any, cb: any) {
    try {
      const songs = await db.listSongs();
      cb(null, { songs });
    } catch (err) {
      cb(toGrpcError(err));
    }
  },
  async GetSong(call: any, cb: any) {
    try {
      cb(null, await db.getSong(call.request.id));
    } catch (err) {
      cb(toGrpcError(err));
    }
  },
  async CreateSong(call: any, cb: any) {
    try {
      cb(
        null,
        await db.createSong(
          call.request.name,
          call.request.artist,
          call.request.album || undefined,
          call.request.genre || undefined,
          call.request.duration_sec || undefined,
          call.request.release_year || undefined
        )
      );
    } catch (err) {
      cb(toGrpcError(err));
    }
  },
  async UpdateSong(call: any, cb: any) {
    try {
      cb(
        null,
        await db.updateSong(
          call.request.id,
          call.request.name,
          call.request.artist,
          call.request.album || undefined,
          call.request.genre || undefined,
          call.request.duration_sec || undefined,
          call.request.release_year || undefined
        )
      );
    } catch (err) {
      cb(toGrpcError(err));
    }
  },
  async DeleteSong(call: any, cb: any) {
    try {
      const deleted = await db.deleteSong(call.request.id);
      cb(null, { deleted });
    } catch (err) {
      cb(toGrpcError(err));
    }
  },

  async GetPlaylist(call: any, cb: any) {
    try {
      cb(null, await db.getPlaylist(call.request.id, true));
    } catch (err) {
      cb(toGrpcError(err));
    }
  },
  async CreatePlaylist(call: any, cb: any) {
    try {
      cb(
        null,
        await db.createPlaylist(
          call.request.user_id,
          call.request.name,
          call.request.song_ids || [],
          call.request.description || "",
          call.request.is_public
        )
      );
    } catch (err) {
      cb(toGrpcError(err));
    }
  },
  async UpdatePlaylist(call: any, cb: any) {
    try {
      const sids =
        call.request.song_ids && call.request.song_ids.length > 0
          ? call.request.song_ids
          : undefined;
      cb(
        null,
        await db.updatePlaylist(
          call.request.id,
          call.request.name,
          sids,
          call.request.description || undefined,
          call.request.is_public
        )
      );
    } catch (err) {
      cb(toGrpcError(err));
    }
  },
  async DeletePlaylist(call: any, cb: any) {
    try {
      const deleted = await db.deletePlaylist(call.request.id);
      cb(null, { deleted });
    } catch (err) {
      cb(toGrpcError(err));
    }
  },
  async AddSongToPlaylist(call: any, cb: any) {
    try {
      cb(
        null,
        await db.addSongToPlaylist(
          call.request.playlist_id,
          call.request.song_id
        )
      );
    } catch (err) {
      cb(toGrpcError(err));
    }
  },
  async RemoveSongFromPlaylist(call: any, cb: any) {
    try {
      cb(
        null,
        await db.removeSongFromPlaylist(
          call.request.playlist_id,
          call.request.song_id
        )
      );
    } catch (err) {
      cb(toGrpcError(err));
    }
  },

  async ListUserPlaylists(call: any, cb: any) {
    try {
      const playlists = await db.listUserPlaylists(call.request.id, false);
      cb(null, { playlists });
    } catch (err) {
      cb(toGrpcError(err));
    }
  },
  async ListPlaylistSongs(call: any, cb: any) {
    try {
      const songs = await db.listPlaylistSongs(call.request.id);
      cb(null, { songs });
    } catch (err) {
      cb(toGrpcError(err));
    }
  },
  async ListPlaylistsBySong(call: any, cb: any) {
    try {
      const playlists = await db.listPlaylistsBySong(call.request.id);
      cb(null, { playlists });
    } catch (err) {
      cb(toGrpcError(err));
    }
  },
};

const port = process.env.PORT || "50052";
const server = new grpc.Server();
server.addService(proto.musicstreaming.MusicStreamingService.service, handlers);
server.bindAsync(
  `0.0.0.0:${port}`,
  grpc.ServerCredentials.createInsecure(),
  (err) => {
    if (err) {
      console.error(err);
      process.exit(1);
    }
    console.log(`Node gRPC server listening on 0.0.0.0:${port}`);
  }
);
