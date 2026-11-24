import fs from "fs";
import { ApolloServer } from "@apollo/server";
import { unwrapResolverError } from "@apollo/server/errors";
import { startStandaloneServer } from "@apollo/server/standalone";
import * as db from "../common/db";

const typeDefs = fs.readFileSync("/app/contracts/schema.graphql", "utf-8");

const resolvers = {
  User: {
    playlists: (parent: db.User) => db.listUserPlaylists(parent.id, false),
  },
  Song: {
    playlists: (parent: db.Song) => db.listPlaylistsBySong(parent.id),
  },
  Playlist: {
    userId: (parent: db.Playlist) => parent.user_id,
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
    createUser: (_: unknown, args: { name: string; age: number }) =>
      db.createUser(args.name, args.age),
    updateUser: (_: unknown, args: { id: number; name: string; age: number }) =>
      db.updateUser(args.id, args.name, args.age),
    deleteUser: (_: unknown, args: { id: number }) => db.deleteUser(args.id),

    createSong: (_: unknown, args: { name: string; artist: string }) =>
      db.createSong(args.name, args.artist),
    updateSong: (
      _: unknown,
      args: { id: number; name: string; artist: string }
    ) => db.updateSong(args.id, args.name, args.artist),
    deleteSong: (_: unknown, args: { id: number }) => db.deleteSong(args.id),

    createPlaylist: (
      _: unknown,
      args: { userId: number; name: string; songIds: number[] }
    ) => db.createPlaylist(args.userId, args.name, args.songIds),
    updatePlaylist: (
      _: unknown,
      args: { id: number; name: string; songIds?: number[] }
    ) => db.updatePlaylist(args.id, args.name, args.songIds),
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
