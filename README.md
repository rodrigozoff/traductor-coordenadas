# Traductor de Coordenadas

Herramienta para convertir entre coordenadas de Google Maps (WGS84) y coordenadas Gauss-Krüger, específicamente adaptada para Argentina.

## Características

- Conversión bidireccional entre Google Maps y Gauss-Krüger
- Procesamiento de archivos CSV con miles de registros
- Manejo de errores robusto con registro detallado
- Soporte para múltiples zonas UTM de Argentina
- Interfaz de línea de comandos fácil de usar

## Requisitos

- Python 3.8 o superior
- pip (gestor de paquetes de Python)

## Instalación

1. Clona este repositorio o descarga los archivos
2. Instala las dependencias:

```bash
pip install -r requirements.txt
```

O instala el paquete en modo desarrollo:

```bash
pip install -e .
```

## Uso

### Desde la línea de comandos

#### Convertir de Google Maps a Gauss-Krüger

```bash
python -m traductor_coordenadas to_gk --input ejemplo_coordenadas.csv
```

Esto generará un archivo llamado `gauss_kruger_ejemplo_coordenadas.csv` con las coordenadas convertidas.

#### Convertir de Gauss-Krüger a Google Maps

```bash
python -m traductor_coordenadas to_gmaps --input gauss_kruger_coordenadas.csv
```

Esto generará un archivo llamado `google_maps_coordenadas.csv` con las coordenadas convertidas.

### Opciones avanzadas

- `--output`: Especifica la ruta del archivo de salida
- `--utm-zone`: Especifica la zona UTM a utilizar (18S, 19S, 20S). Por defecto es 20S.

Ejemplo:

```bash
python -m traductor_coordenadas to_gk --input ejemplo.csv --output salida.csv --utm-zone 19S
```

## Formato de archivos

### Entrada (Google Maps a Gauss-Krüger)

```csv
nombre,coordenadas_google_maps
Ubicación 1,-34.6083,-58.3712
Ubicación 2,-34.6037,-58.3816
```

### Salida (Google Maps a Gauss-Krüger)

```csv
nombre,coordenadas_google_maps,coordenadas_gauss_kruger_easting,coordenadas_gauss_kruger_northing
Ubicación 1,-34.6083,-58.3712,500000.0,4000000.0
Ubicación 2,-34.6037,-58.3816,500100.0,4000100.0
```

### Entrada (Gauss-Krüger a Google Maps)

```csv
nombre,coordenadas_gauss_kruger_easting,coordenadas_gauss_kruger_northing
Ubicación 1,500000.0,4000000.0
Ubicación 2,500100.0,4000100.0
```

### Salida (Gauss-Krüger a Google Maps)

```csv
nombre,coordenadas_gauss_kruger_easting,coordenadas_gauss_kruger_northing,coordenadas_google_maps
Ubicación 1,500000.0,4000000.0,-34.608300,-58.371200
Ubicación 2,500100.0,4000100.0,-34.603700,-58.381600
```

## Zonas UTM soportadas

El traductor soporta las siguientes zonas UTM para Argentina:

- **18S**: Este (Buenos Aires, Córdoba, etc.)
- **19S**: Centro (Mendoza, San Juan)
- **20S**: Oeste (Bariloche, Neuquén) - **Predeterminado**

## Ejemplo práctico

1. Crea un archivo `coordenadas.csv` con el siguiente contenido:

```csv
nombre,coordenadas_google_maps
Plaza de Mayo,-34.6083,-58.3712
Obelisco,-34.6037,-58.3816
```

2. Convierte a Gauss-Krüger:

```bash
python -m traductor_coordenadas to_gk --input coordenadas.csv
```

3. Verifica el archivo de salida `gauss_kruger_coordenadas.csv` con las coordenadas convertidas.

## Licencia

Este proyecto está bajo la Licencia MIT. Consulta el archivo [LICENSE](LICENSE) para más información.

---

Desarrollado por Rodrigo Zoff - 2025
