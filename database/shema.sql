DROP TABLE IF EXISTS fact_aqi CASCADE;
DROP TABLE IF EXISTS dim_city CASCADE;
DROP TABLE IF EXISTS dim_time CASCADE;

CREATE TABLE dim_city (
    id_city    SERIAL PRIMARY KEY,
    city_name  VARCHAR(100) NOT NULL,
    country    VARCHAR(100) NOT NULL,
    latitude   NUMERIC(9,6) NOT NULL,
    longitude  NUMERIC(9,6) NOT NULL,
    UNIQUE (city_name)
);

CREATE TABLE dim_time (
    id_time       SERIAL PRIMARY KEY,
    full_datetime TIMESTAMP NOT NULL,
    date          DATE NOT NULL,
    hour          SMALLINT NOT NULL CHECK (hour BETWEEN 0 AND 23),
    day           SMALLINT NOT NULL,
    month         SMALLINT NOT NULL,
    year          SMALLINT NOT NULL,
    day_of_week   VARCHAR(10) NOT NULL,   -- ex: 'Monday'
    is_weekend    BOOLEAN NOT NULL,
    UNIQUE (full_datetime)
);

CREATE TABLE fact_aqi (
    id_fact           SERIAL PRIMARY KEY,
    id_city           INTEGER NOT NULL REFERENCES dim_city(id_city),
    id_time           INTEGER NOT NULL REFERENCES dim_time(id_time),
    pm10              NUMERIC(8,3),
    pm2_5             NUMERIC(8,3),
    carbon_monoxide   NUMERIC(8,3),
    nitrogen_dioxide  NUMERIC(8,3),
    sulphur_dioxide   NUMERIC(8,3),
    ozone             NUMERIC(8,3),
    us_aqi            INTEGER,
    UNIQUE (id_city, id_time)
);

CREATE INDEX idx_fact_aqi_city ON fact_aqi(id_city);
CREATE INDEX idx_fact_aqi_time ON fact_aqi(id_time);