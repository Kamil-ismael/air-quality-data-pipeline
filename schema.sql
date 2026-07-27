-- Dimension Ville
CREATE TABLE DimCity (
    id_city SERIAL PRIMARY KEY,
    city_name VARCHAR(100) NOT NULL,
    latitude FLOAT,
    longitude FLOAT
);

-- Dimension Date
CREATE TABLE DimDate (
    id_date SERIAL PRIMARY KEY,
    full_date TIMESTAMP NOT NULL,
    year INT,
    month INT,
    day INT
);

-- Table de Faits Qualité de l'air
CREATE TABLE FactAirQuality (
    id_fact SERIAL PRIMARY KEY,
    id_city INT REFERENCES DimCity(id_city),
    id_date INT REFERENCES DimDate(id_date),
    pm10 FLOAT,
    pm2_5 FLOAT,
    carbon_monoxide FLOAT,
    nitrogen_dioxide FLOAT,
    sulphur_dioxide FLOAT,
    ozone FLOAT,
    us_aqi INT
);
