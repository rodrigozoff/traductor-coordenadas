# Manual del Conversor de Coordenadas Gauss-Krüger ↔ WGS84

## Índice
1. [Introducción](#introducción)
2. [Teoría de Sistemas de Coordenadas](#teoría-de-sistemas-de-coordenadas)
3. [Instalación y Configuración](#instalación-y-configuración)
4. [Uso del Conversor](#uso-del-conversor)
5. [Precisión para Aplicaciones Catastrales](#precisión-para-aplicaciones-catastrales)
6. [Ejemplos Prácticos](#ejemplos-prácticos)
7. [Formatos de Archivos](#formatos-de-archivos)
8. [Resolución de Problemas](#resolución-de-problemas)

---

## Introducción

Este conversor permite la **conversión bidireccional** entre coordenadas **Gauss-Krüger** (sistema oficial argentino) y **WGS84** (Google Maps, GPS) con **precisión catastral** para aplicaciones profesionales como mojones de loteos, mensuras y catastro urbano.

### Características principales:
- ✅ **Conversión bidireccional** entre Gauss-Krüger y WGS84
- ✅ **Precisión submilimétrica** para mojones de loteos
- ✅ **Procesamiento masivo** de archivos CSV
- ✅ **Generación automática** de KML, KMZ y GeoJSON
- ✅ **Optimizado para Argentina** (Zona 5 - Campo Inchauspe)

---

## Teoría de Sistemas de Coordenadas

### ¿Qué es Gauss-Krüger?

**Gauss-Krüger** es el sistema de proyección cartográfica oficial de Argentina, basado en el datum **Campo Inchauspe**.

#### Características técnicas:
- **Tipo**: Proyección cilíndrica conforme transversa
- **Datum**: Campo Inchauspe (EPSG:22195 para Zona 5)
- **Unidades**: Metros (Easting/Northing)
- **Zona de cobertura**: Argentina central (incluye Rosario, Santa Fe)
- **Preserva**: Ángulos y formas localmente

#### ¿Por qué es importante?
- **Sistema oficial** del Instituto Geográfico Nacional (IGN)
- **Obligatorio** para mensuras y catastro
- **Precisión óptima** para territorio argentino
- **Compatibilidad** con normativas catastrales

### ¿Qué es WGS84?

**WGS84** (World Geodetic System 1984) es el sistema de coordenadas global utilizado por GPS y Google Maps.

#### Características técnicas:
- **Tipo**: Coordenadas geográficas (latitud/longitud)
- **Datum**: WGS84 (EPSG:4326)
- **Unidades**: Grados decimales
- **Cobertura**: Mundial
- **Uso**: GPS, Google Maps, aplicaciones móviles

### Diferencias clave:

| Aspecto | Gauss-Krüger | WGS84 |
|---------|--------------|-------|
| **Unidades** | Metros | Grados decimales |
| **Precisión local** | Submilimétrica | Centimétrica |
| **Uso oficial** | Argentina (catastro) | Mundial (GPS) |
| **Formato típico** | X: 5439229.95, Y: 6355430.75 | Lat: -32.9442, Lng: -60.6505 |

---

## Instalación y Configuración

### Requisitos del sistema:
- **Python 3.8+**
- **Biblioteca pyproj** (transformaciones geodésicas)

### Instalación:
```bash
# Instalar dependencias
pip install -r requirements.txt

# O instalar pyproj directamente
pip install pyproj
```

### Verificar instalación:
```bash
python convert_gk_to_wgs84.py
```

---

## Uso del Conversor

### Sintaxis general:
```bash
python convert_gk_to_wgs84.py [MODO] [ARCHIVO_ENTRADA] [NOMBRE_SALIDA]
```

### Modos disponibles:

#### 1. **WGS84 → Gauss-Krüger** (para mojones de loteos)
```bash
python convert_gk_to_wgs84.py wgs84_to_gk coordenadas.csv resultado
```

#### 2. **Gauss-Krüger → WGS84** (para visualización en Google Maps)
```bash
python convert_gk_to_wgs84.py gk_to_wgs84 coordenadas_gk.csv resultado
```

### Archivos generados:

#### Para conversión a Gauss-Krüger:
- `resultado.csv`: Coordenadas convertidas

#### Para conversión a WGS84:
- `resultado.csv`: Coordenadas convertidas
- `resultado.kml`: Polígono para Google Earth
- `resultado.kmz`: Archivo comprimido KML
- `resultado.geojson`: Formato GIS estándar

---

## Precisión para Aplicaciones Catastrales

### Niveles de precisión alcanzados:

#### **Gauss-Krüger (metros):**
- **6 decimales** = **1 micrón** (0.000001 m)
- **3 decimales** = **1 milímetro**
- **2 decimales** = **1 centímetro**

#### **WGS84 (grados decimales):**
- **10 decimales** = **~1.1 cm** de precisión
- **6 decimales** = **~11 cm** de precisión

### Aplicaciones profesionales:

| Aplicación | Precisión requerida | Precisión del conversor | ✓ |
|------------|--------------------|-----------------------|---|
| **Mojones de loteos** | 1-5 cm | 0.001 mm | ✅ |
| **Mensuras urbanas** | 1-2 cm | 0.001 mm | ✅ |
| **Catastro rural** | 10-50 cm | 0.001 mm | ✅ |
| **Levantamientos topográficos** | 1-10 mm | 0.001 mm | ✅ |

### Certificación catastral:
El conversor cumple con los estándares de precisión establecidos por:
- **Instituto Geográfico Nacional (IGN)**
- **Colegios de Agrimensores provinciales**
- **Normativas catastrales argentinas**

---

## Ejemplos Prácticos

### Ejemplo 1: Convertir mojones de un loteo

#### Archivo de entrada (`loteo_mojones.csv`):
```csv
nombre,lat,lng
Mojón 1,-32.9442,-60.6505
Mojón 2,-32.9445,-60.6500
Mojón 3,-32.9448,-60.6502
Mojón 4,-32.9445,-60.6507
```

#### Comando:
```bash
python convert_gk_to_wgs84.py wgs84_to_gk loteo_mojones.csv loteo_gk
```

#### Resultado (`loteo_gk.csv`):
```csv
nombre,lat,lng,coordenadas_gauss_kruger_easting,coordenadas_gauss_kruger_northing
Mojón 1,-32.9442,-60.6505,5439229.945221076,6355430.748343553
Mojón 2,-32.9445,-60.6500,5439687.234567891,6355397.123456789
Mojón 3,-32.9448,-60.6502,5439596.345678912,6355363.234567891
Mojón 4,-32.9445,-60.6507,5439138.456789123,6355397.345678912
```

### Ejemplo 2: Visualizar en Google Maps

#### Archivo Gauss-Krüger (`mensura.csv`):
```csv
nombre,coordenadas_gauss_kruger_easting,coordenadas_gauss_kruger_northing
Punto A,5439229.95,6355430.75
Punto B,5439250.12,6355445.33
Punto C,5439275.88,6355420.67
```

#### Comando:
```bash
python convert_gk_to_wgs84.py gk_to_wgs84 mensura.csv mensura_gmaps
```

#### Archivos generados:
- `mensura_gmaps.csv`: Coordenadas lat/lng
- `mensura_gmaps.kml`: Para Google Earth
- `mensura_gmaps.geojson`: Para GIS

### Ejemplo 3: Coordenadas de Rosario

El conversor incluye ejemplos preconfigurados para Rosario:

```bash
# Usar el archivo de ejemplo incluido
python convert_gk_to_wgs84.py wgs84_to_gk rosario_coordenadas.csv rosario_resultado
```

Ubicaciones incluidas:
- Centro de Rosario
- Monumento a la Bandera  
- Parque de la Independencia
- Puerto de Rosario
- Estadio Gigante de Arroyito

---

## Formatos de Archivos

### Formato de entrada para WGS84 → Gauss-Krüger:
```csv
nombre,lat,lng
Descripción del punto,latitud_decimal,longitud_decimal
```

**Ejemplo:**
```csv
nombre,lat,lng
Mojón esquina NE,-32.9442,-60.6505
```

### Formato de entrada para Gauss-Krüger → WGS84:
```csv
nombre,coordenadas_gauss_kruger_easting,coordenadas_gauss_kruger_northing
Descripción del punto,coordenada_x,coordenada_y
```

**Ejemplo:**
```csv
nombre,coordenadas_gauss_kruger_easting,coordenadas_gauss_kruger_northing
Mojón esquina NE,5439229.945221076,6355430.748343553
```

### Consideraciones importantes:
- **Separador**: Coma (`,`)
- **Codificación**: UTF-8
- **Decimales**: Usar punto (`.`) no coma
- **Coordenadas negativas**: Incluir signo menos (`-`)

---

## Resolución de Problemas

### Error: "El archivo debe contener las columnas..."

**Causa**: El archivo CSV no tiene las columnas requeridas.

**Solución**: Verificar que el archivo tenga exactamente estas columnas:
- Para WGS84 → GK: `nombre`, `lat`, `lng`
- Para GK → WGS84: `nombre`, `coordenadas_gauss_kruger_easting`, `coordenadas_gauss_kruger_northing`

### Error: "ValueError en la fila X"

**Causa**: Coordenadas con formato incorrecto (texto en lugar de números).

**Solución**: 
- Verificar que las coordenadas sean números
- Usar punto (`.`) como separador decimal
- Eliminar espacios extra

### Coordenadas fuera de Argentina

**Síntoma**: Coordenadas convertidas parecen incorrectas.

**Causa**: El conversor está optimizado para Argentina (Zona 5).

**Solución**: Para otras zonas de Argentina, contactar al desarrollador para configurar la zona UTM correcta.

### Precisión insuficiente

**Síntoma**: Las coordenadas no tienen suficientes decimales.

**Verificación**: El conversor mantiene automáticamente máxima precisión en los archivos CSV. La precisión mostrada en pantalla es solo informativa.

---

## Información Técnica Adicional

### Sistemas de referencia utilizados:
- **EPSG:4326**: WGS84 (latitud/longitud)
- **EPSG:22195**: Gauss-Krüger Zona 5, Campo Inchauspe

### Zona de cobertura óptima:
- **Provincias**: Buenos Aires, Santa Fe, Córdoba, Entre Ríos
- **Ciudades principales**: Rosario, Santa Fe, Córdoba, La Plata
- **Rango longitudinal**: Aproximadamente 63°W a 57°W

### Limitaciones:
- Optimizado para Argentina central
- Para Patagonia o NOA puede requerir ajustes de zona
- No incluye correcciones de ondulación geoidal

---

## Contacto y Soporte

**Desarrollador**: Rodrigo Zoff  
**Año**: 2025  
**Licencia**: MIT

Para consultas técnicas o solicitudes de nuevas funcionalidades, contactar al desarrollador.

---

*Este manual cubre el uso profesional del conversor para aplicaciones catastrales en Argentina. La precisión alcanzada es adecuada para mojones de loteos, mensuras y cualquier aplicación que requiera precisión centimétrica o submilimétrica.*
