-- Data warehouse AQI — schéma en étoile
-- Une table de faits (mesures) + deux dimensions (temps, ville).
-- Aucune mesure dans les dimensions, aucune colonne descriptive dans les faits.

CREATE TABLE IF NOT EXISTS dim_city (
    city_id     SERIAL PRIMARY KEY,
    name        VARCHAR(100) NOT NULL,
    country     VARCHAR(10)  NOT NULL,
    latitude    DOUBLE PRECISION NOT NULL,
    longitude   DOUBLE PRECISION NOT NULL,
    UNIQUE (name, country)
);

CREATE TABLE IF NOT EXISTS dim_time (
    time_id       SERIAL PRIMARY KEY,
    timestamp_utc TIMESTAMPTZ NOT NULL UNIQUE,
    date          DATE       NOT NULL,
    hour          SMALLINT   NOT NULL,
    day_of_week   SMALLINT   NOT NULL,  -- 0 = lundi ... 6 = dimanche
    is_weekend    BOOLEAN    NOT NULL,
    month         SMALLINT   NOT NULL,
    year          SMALLINT   NOT NULL
);

CREATE TABLE IF NOT EXISTS fact_aqi (
    fact_id   BIGSERIAL PRIMARY KEY,
    city_id   INTEGER NOT NULL REFERENCES dim_city(city_id),
    time_id   INTEGER NOT NULL REFERENCES dim_time(time_id),
    aqi       SMALLINT,          -- indice global OpenWeatherMap (1 à 5)
    co        DOUBLE PRECISION,  -- µg/m3
    no        DOUBLE PRECISION,
    no2       DOUBLE PRECISION,
    o3        DOUBLE PRECISION,
    so2       DOUBLE PRECISION,
    pm2_5     DOUBLE PRECISION,
    pm10      DOUBLE PRECISION,
    nh3       DOUBLE PRECISION,
    UNIQUE (city_id, time_id)
);

CREATE INDEX IF NOT EXISTS idx_fact_aqi_city ON fact_aqi(city_id);
CREATE INDEX IF NOT EXISTS idx_fact_aqi_time ON fact_aqi(time_id);
