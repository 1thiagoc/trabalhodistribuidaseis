-- Schema do Serviço de Streaming de Músicas (≥ 6 atributos por entidade + volume realista)
-- Computação Distribuída — Comparação de Tecnologias de Invocação Remota

DROP TABLE IF EXISTS playlist_songs CASCADE;
DROP TABLE IF EXISTS playlists CASCADE;
DROP TABLE IF EXISTS songs CASCADE;
DROP TABLE IF EXISTS users CASCADE;

-- Usuário: 7 atributos (id, name, age, email, country, plan_type, created_at)
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    name VARCHAR(150) NOT NULL,
    age INTEGER NOT NULL CHECK (age >= 0),
    email VARCHAR(200) NOT NULL,
    country VARCHAR(60) NOT NULL DEFAULT 'BR',
    plan_type VARCHAR(30) NOT NULL DEFAULT 'free',
    created_at DATE NOT NULL DEFAULT CURRENT_DATE
);

-- Música: 7 atributos (id, name, artist, album, genre, duration_sec, release_year)
CREATE TABLE songs (
    id SERIAL PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    artist VARCHAR(150) NOT NULL,
    album VARCHAR(200) NOT NULL DEFAULT 'Single',
    genre VARCHAR(80) NOT NULL DEFAULT 'Pop',
    duration_sec INTEGER NOT NULL DEFAULT 180 CHECK (duration_sec > 0),
    release_year INTEGER NOT NULL DEFAULT 2024 CHECK (release_year >= 1900)
);

-- Playlist: 6 atributos (id, name, user_id, description, is_public, created_at)
CREATE TABLE playlists (
    id SERIAL PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    description VARCHAR(300) NOT NULL DEFAULT '',
    is_public BOOLEAN NOT NULL DEFAULT TRUE,
    created_at DATE NOT NULL DEFAULT CURRENT_DATE
);

CREATE TABLE playlist_songs (
    playlist_id INTEGER NOT NULL REFERENCES playlists(id) ON DELETE CASCADE,
    song_id INTEGER NOT NULL REFERENCES songs(id) ON DELETE CASCADE,
    PRIMARY KEY (playlist_id, song_id)
);

-- Índices para garantir que o banco não seja o gargalo nas consultas relacionais
CREATE INDEX idx_playlists_user_id ON playlists(user_id);
CREATE INDEX idx_playlist_songs_playlist_id ON playlist_songs(playlist_id);
CREATE INDEX idx_playlist_songs_song_id ON playlist_songs(song_id);

-- Seed determinístico em escala: 500 usuários, 1.000 músicas, 1.000 playlists e ~10.000 associações
DO $$
DECLARE
    first_names TEXT[] := ARRAY[
        'Ana', 'Bruno', 'Carla', 'Diego', 'Eduarda', 'Felipe', 'Gabriela', 'Henrique', 'Isabela', 'Jean',
        'Karen', 'Lucas', 'Mariana', 'Nathan', 'Olivia', 'Pedro', 'Rafaela', 'Samuel', 'Tatiana', 'Vinicius',
        'Amanda', 'Caio', 'Daniela', 'Enzo', 'Fernanda', 'Gustavo', 'Helena', 'Igor', 'Julia', 'Leonardo',
        'Leticia', 'Mateus', 'Natalia', 'Otavio', 'Paula', 'Renan', 'Sofia', 'Thiago', 'Vitoria', 'Yuri',
        'Beatriz', 'Davi', 'Elisa', 'Fabio', 'Giovanna', 'Heitor', 'Ingrid', 'Joao', 'Larissa', 'Murilo'
    ];
    last_names TEXT[] := ARRAY[
        'Silva', 'Santos', 'Oliveira', 'Souza', 'Pereira', 'Costa', 'Rodrigues', 'Almeida', 'Nascimento', 'Lima',
        'Araujo', 'Fernandes', 'Carvalho', 'Gomes', 'Martins', 'Rocha', 'Ribeiro', 'Alves', 'Monteiro', 'Mendes'
    ];
    countries TEXT[] := ARRAY['BR', 'US', 'PT', 'GB', 'DE', 'JP', 'CA', 'AR', 'ES', 'FR'];
    plans TEXT[] := ARRAY['free', 'premium', 'family', 'student'];
    artists TEXT[] := ARRAY[
        'Daft Punk', 'Queen', 'Pink Floyd', 'Radiohead', 'Coldplay',
        'The Beatles', 'Arctic Monkeys', 'Tame Impala', 'Fleetwood Mac', 'Nirvana',
        'Legiao Urbana', 'Chico Buarque', 'Tim Maia', 'Jorge Ben Jor', 'Milton Nascimento',
        'Miles Davis', 'Kendrick Lamar', 'Frank Ocean', 'Billie Eilish', 'The Weeknd'
    ];
    genres TEXT[] := ARRAY[
        'Rock', 'Pop', 'Electronic', 'MPB', 'Jazz', 'Hip-Hop', 'Indie', 'Soul', 'Alternative', 'Synthwave'
    ];
    albums TEXT[] := ARRAY[
        'Discovery', 'Dark Side', 'OK Computer', 'Currents', 'Rumours',
        'Abbey Road', 'AM', 'Nevermind', 'Blonde', 'After Hours'
    ];
    song_prefixes TEXT[] := ARRAY[
        'Midnight', 'Electric', 'Golden', 'Silent', 'Velvet',
        'Neon', 'Solar', 'Crimson', 'Silver', 'Endless'
    ];
    song_suffixes TEXT[] := ARRAY[
        'Echoes', 'Horizon', 'Rhythm', 'Dreams', 'Pulse',
        'Memories', 'Journey', 'Lights', 'Waves', 'Symphony'
    ];
    playlist_themes TEXT[] := ARRAY[
        'Foco no Estudo', 'Treino Pesado', 'Chill da Noite', 'Classicos Eternos',
        'Estrada e Viagem', 'Descobertas da Semana', 'Favoritas de Sempre', 'Acustico Relax'
    ];
    i INT;
    j INT;
    u_id INT;
    p_id INT;
    s_id INT;
    songs_per_pl INT;
    fn TEXT;
    ln TEXT;
BEGIN
    -- 500 Usuários (7 atributos cada)
    FOR i IN 1..500 LOOP
        fn := first_names[((i - 1) % 50) + 1];
        ln := last_names[(((i - 1) / 5 + i) % 20) + 1];
        INSERT INTO users (name, age, email, country, plan_type, created_at)
        VALUES (
            fn || ' ' || ln || ' ' || i,
            18 + ((i * 7) % 45),
            lower(fn) || '.' || lower(ln) || i || '@musicstream.io',
            countries[((i - 1) % 10) + 1],
            plans[((i - 1) % 4) + 1],
            DATE '2023-01-01' + ((i * 3) % 700)
        );
    END LOOP;

    -- 1.000 Músicas (7 atributos cada)
    FOR i IN 1..1000 LOOP
        INSERT INTO songs (name, artist, album, genre, duration_sec, release_year)
        VALUES (
            song_prefixes[((i - 1) % 10) + 1] || ' ' || song_suffixes[(((i - 1) / 10) % 10) + 1] || ' #' || i,
            artists[((i - 1) % 20) + 1],
            albums[((i - 1) % 10) + 1] || ' Vol. ' || (((i - 1) / 100) + 1),
            genres[((i - 1) % 10) + 1],
            140 + ((i * 17) % 220),
            1970 + ((i * 3) % 55)
        );
    END LOOP;

    -- 1.000 Playlists (2 por usuário, 6 atributos cada, 8 a 12 músicas por playlist = ~10.000 associações)
    FOR i IN 1..1000 LOOP
        u_id := ((i - 1) % 500) + 1;
        INSERT INTO playlists (name, user_id, description, is_public, created_at)
        VALUES (
            playlist_themes[((i - 1) % 8) + 1] || ' #' || i,
            u_id,
            'Selecao curada de faixas para ' || lower(playlist_themes[((i - 1) % 8) + 1]) || ' (edicao ' || i || ')',
            (i % 5 <> 0),
            DATE '2024-01-01' + ((i * 2) % 360)
        )
        RETURNING id INTO p_id;

        songs_per_pl := 8 + (i % 5);
        FOR j IN 1..songs_per_pl LOOP
            s_id := (((i * 13) + (j * 29) - 1) % 1000) + 1;
            INSERT INTO playlist_songs (playlist_id, song_id)
            VALUES (p_id, s_id)
            ON CONFLICT DO NOTHING;
        END LOOP;
    END LOOP;
END $$;
