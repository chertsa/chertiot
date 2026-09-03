-- Runs once on first postgres start (docker-entrypoint-initdb.d). Owner = POSTGRES_USER.
CREATE DATABASE thingsboard;
CREATE DATABASE keycloak;
CREATE DATABASE portal;
CREATE DATABASE chirpstack;
