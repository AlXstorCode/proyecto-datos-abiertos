IF DB_ID('DatosAbiertosDB') IS NULL
    CREATE DATABASE DatosAbiertosDB;
GO
USE DatosAbiertosDB;
GO

CREATE TABLE RegistrosAPI (
    id INT IDENTITY(1, 1) PRIMARY KEY,
    anno SMALLINT NOT NULL,
    trimestre TINYINT NOT NULL,
    proveedor NVARCHAR(150) NOT NULL,
    proveedor_destino NVARCHAR(500) NOT NULL,
    trafico_prepago BIGINT NOT NULL,
    trafico_pospago BIGINT NOT NULL,
    fecha_captura DATETIME2 NOT NULL DEFAULT SYSDATETIME(),
    CONSTRAINT UQ_RegistrosAPI_clave UNIQUE (anno, trimestre, proveedor, proveedor_destino)
);
GO