import fs from "fs";
import { ApolloServer } from "@apollo/server";
import { unwrapResolverError } from "@apollo/server/errors";
import { startStandaloneServer } from "@apollo/server/standalone";
import * as db from "../common/db";

const typeDefs = fs.readFileSync("/app/contracts/schema.graphql", "utf-8");

const resolvers = {
  User: {
    planType: (parent: db.User) => parent.plan_type,
    createdAt: (parent: db.User) => parent.created_at,
    playlists: (parent: db.User) => db.listUserPlaylists(parent.id, false),
  },
  Song: {
    durationSec: (parent: db.Song) => parent.duration_sec,
    releaseYear: (parent: db.Song) => parent.release_year,
    playlists: (parent: db.Song) => db.listPlaylistsBySong(parent.id),
  },
  Playlist: {
    userId: (parent: db.Playlist) => parent.user_id,
    isPublic: (parent: db.Playlist) => parent.is_public,
    createdAt: (parent: db.Playlist) => parent.created_at,
    user: (parent: db.Playlist) => db.getUser(parent.user_id),
    songs: (parent: db.Playlist) => db.listPlaylistSongs(parent.id),
  },
  Query: {
    users: () => db.listUsers(),
    user: async (_: unknown, args: { id: number }) => {
      try {
        return await db.getUser(args.id);
      } catch (err) {
        if (err instanceof db.NotFoundError) return null;
        throw err;
      }
    },
    songs: () => db.listSongs(),
    song: async (_: unknown, args: { id: number }) => {
      try {
        return await db.getSong(args.id);
      } catch (err) {
        if (err instanceof db.NotFoundError) return null;
        throw err;
      }
    },
    playlist: async (_: unknown, args: { id: number }) => {
      try {
        return await db.getPlaylist(args.id, false);
      } catch (err) {
        if (err instanceof db.NotFoundError) return null;
        throw err;
      }
    },
    userPlaylists: (_: unknown, args: { userId: number }) =>
      db.listUserPlaylists(args.userId, false),
    playlistSongs: (_: unknown, args: { playlistId: number }) =>
      db.listPlaylistSongs(args.playlistId),
    playlistsBySong: (_: unknown, args: { songId: number }) =>
      db.listPlaylistsBySong(args.songId),
  },
  Mutation: {
    createUser: (
      _: unknown,
      args: { name: string; age: number; email?: string; country?: string; planType?: string }
    ) => db.createUser(args.name, args.age, args.email, args.country, args.planType),
    updateUser: (
      _: unknown,
      args: { id: number; name: string; age: number; email?: string; country?: string; planType?: string }
    ) => db.updateUser(args.id, args.name, args.age, args.email, args.country, args.planType),
    deleteUser: (_: unknown, args: { id: number }) => db.deleteUser(args.id),

    createSong: (
      _: unknown,
      args: {
        name: string;
        artist: string;
        album?: string;
        genre?: string;
        durationSec?: number;
        releaseYear?: number;
      }
    ) =>
      db.createSong(
        args.name,
        args.artist,
        args.album,
        args.genre,
        args.durationSec,
        args.releaseYear
      ),
    updateSong: (
      _: unknown,
      args: {
        id: number;
        name: string;
        artist: string;
        album?: string;
        genre?: string;
        durationSec?: number;
        releaseYear?: number;
      }
    ) =>
      db.updateSong(
        args.id,
        args.name,
        args.artist,
        args.album,
        args.genre,
        args.durationSec,
        args.releaseYear
      ),
    deleteSong: (_: unknown, args: { id: number }) => db.deleteSong(args.id),

    createPlaylist: (
      _: unknown,
      args: { userId: number; name: string; songIds: number[]; description?: string; isPublic?: boolean }
    ) => db.createPlaylist(args.userId, args.name, args.songIds, args.description, args.isPublic),
    updatePlaylist: (
      _: unknown,
      args: { id: number; name: string; songIds?: number[]; description?: string; isPublic?: boolean }
    ) => db.updatePlaylist(args.id, args.name, args.songIds, args.description, args.isPublic),
    deletePlaylist: (_: unknown, args: { id: number }) =>
      db.deletePlaylist(args.id),
    addSongToPlaylist: (
      _: unknown,
      args: { playlistId: number; songId: number }
    ) => db.addSongToPlaylist(args.playlistId, args.songId),
    removeSongFromPlaylist: (
      _: unknown,
      args: { playlistId: number; songId: number }
    ) => db.removeSongFromPlaylist(args.playlistId, args.songId),
  },
};

async function main() {
  const port = Number(process.env.PORT || 8103);
  const server = new ApolloServer({
    typeDefs,
    resolvers,
    formatError: (formattedError, error) => {
      const original = unwrapResolverError(error);
      if (original instanceof db.NotFoundError) {
        return {
          ...formattedError,
          extensions: { ...formattedError.extensions, code: "NOT_FOUND" },
        };
      }
      if (original instanceof db.ValidationError) {
        return {
          ...formattedError,
          extensions: { ...formattedError.extensions, code: "BAD_USER_INPUT" },
        };
      }
      return formattedError;
    },
  });
  const { url } = await startStandaloneServer(server, {
    listen: { host: "0.0.0.0", port },
  });
  console.log(`Node GraphQL (Apollo) server listening at ${url}`);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
