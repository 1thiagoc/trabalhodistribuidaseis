-- Schema do Serviço de Streaming de Músicas
-- Computação Distribuída — Comparação de Tecnologias de Invocação Remota

DROP TABLE IF EXISTS playlist_songs CASCADE;
DROP TABLE IF EXISTS playlists CASCADE;
DROP TABLE IF EXISTS songs CASCADE;
DROP TABLE IF EXISTS users CASCADE;

CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    name VARCHAR(150) NOT NULL,
    age INTEGER NOT NULL CHECK (age >= 0)
);

CREATE TABLE songs (
    id SERIAL PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    artist VARCHAR(150) NOT NULL
);

CREATE TABLE playlists (
    id SERIAL PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE
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

-- Seed determinístico: 50 usuários, 100 músicas, 120 playlists e ~960 associações
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
    artists TEXT[] := ARRAY[
        'Daft Punk', 'Queen', 'Pink Floyd', 'Radiohead', 'Coldplay',
        'The Beatles', 'Arctic Monkeys', 'Tame Impala', 'Fleetwood Mac', 'Nirvana',
        'Legiao Urbana', 'Chico Buarque', 'Tim Maia', 'Jorge Ben Jor', 'Milton Nascimento',
        'Miles Davis', 'Kendrick Lamar', 'Frank Ocean', 'Billie Eilish', 'The Weeknd'
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
BEGIN
    -- 50 Usuários
    FOR i IN 1..50 LOOP
        INSERT INTO users (name, age)
        VALUES (
            first_names[i] || ' ' || last_names[((i - 1) % 20) + 1],
            18 + ((i * 7) % 35)
        );
    END LOOP;

    -- 100 Músicas
    FOR i IN 1..100 LOOP
        INSERT INTO songs (name, artist)
        VALUES (
            song_prefixes[((i - 1) % 10) + 1] || ' ' || song_suffixes[(((i - 1) / 10) % 10) + 1] || ' #' || i,
            artists[((i - 1) % 20) + 1]
        );
    END LOOP;

    -- 120 Playlists (distribuídas entre os 50 usuários; cada usuário 1..20 tem 3 playlists, 21..50 tem 2 playlists)
    FOR i IN 1..120 LOOP
        u_id := ((i - 1) % 50) + 1;
        INSERT INTO playlists (name, user_id)
        VALUES (
            playlist_themes[((i - 1) % 8) + 1] || ' Vol. ' || ((i - 1) / 8 + 1),
            u_id
        )
        RETURNING id INTO p_id;

        -- Cada playlist recebe entre 6 e 10 músicas (garantindo relação 1..*)
        songs_per_pl := 6 + (i % 5);
        FOR j IN 1..songs_per_pl LOOP
            s_id := (((i * 7) + (j * 11) - 1) % 100) + 1;
            INSERT INTO playlist_songs (playlist_id, song_id)
            VALUES (p_id, s_id)
            ON CONFLICT DO NOTHING;
        END LOOP;
    END LOOP;
END $$;
