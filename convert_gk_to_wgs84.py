#!/usr/bin/env python3
"""
Script para convertir coordenadas entre Gauss-Krüger y WGS84 (Google Maps) de forma bidireccional.

Uso:
    # Convertir de Gauss-Krüger a WGS84:
    python convert_gk_to_wgs84.py gk_to_wgs84 input.csv output_base_name
    
    # Convertir de WGS84 a Gauss-Krüger:
    python convert_gk_to_wgs84.py wgs84_to_gk input.csv output_base_name
    
    Esto generará archivos:
    - output_base_name.csv: Coordenadas en formato CSV
    - output_base_name.kml: Polígono en formato KML (solo para conversiones a WGS84)
    - output_base_name.geojson: Polígono en formato GeoJSON (solo para conversiones a WGS84)
"""

import csv
import json
import sys
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
from datetime import datetime
from typing import List, Tuple, Dict, Any
import pyproj
from pyproj import Transformer

def parse_kml_polygon(kml_path: str) -> List[Tuple[float, float, str]]:
    """Extrae vértices de polígonos de un archivo KML.
    
    Args:
        kml_path: Ruta al archivo KML
        
    Returns:
        Lista de tuplas (nombre, lat, lng) con los vértices del polígono
    """
    coordinates = []
    
    try:
        # Parsear el archivo KML
        tree = ET.parse(kml_path)
        root = tree.getroot()
        
        # Namespace de KML
        ns = {'kml': 'http://www.opengis.net/kml/2.2'}
        
        # Buscar todos los polígonos
        polygons = root.findall('.//kml:Polygon', ns)
        
        for i, polygon in enumerate(polygons):
            # Buscar el anillo exterior (outerBoundaryIs)
            outer_boundary = polygon.find('.//kml:outerBoundaryIs/kml:LinearRing/kml:coordinates', ns)
            
            if outer_boundary is not None and outer_boundary.text:
                # Parsear las coordenadas (formato: lng,lat,alt lng,lat,alt ...)
                coords_text = outer_boundary.text.strip()
                coord_pairs = coords_text.split()
                
                for j, coord_pair in enumerate(coord_pairs):
                    try:
                        parts = coord_pair.split(',')
                        if len(parts) >= 2:
                            lng = float(parts[0])
                            lat = float(parts[1])
                            
                            # Nombre del vértice
                            vertex_name = f"Polígono_{i+1}_Vértice_{j+1}"
                            
                            coordinates.append((vertex_name, lat, lng))
                    except (ValueError, IndexError) as e:
                        print(f"Error parseando coordenada '{coord_pair}': {e}")
                        continue
        
        # También buscar puntos individuales (Placemark con Point)
        placemarks = root.findall('.//kml:Placemark', ns)
        
        for placemark in placemarks:
            name_elem = placemark.find('kml:name', ns)
            point_elem = placemark.find('.//kml:Point/kml:coordinates', ns)
            
            if point_elem is not None and point_elem.text:
                try:
                    coords_text = point_elem.text.strip()
                    parts = coords_text.split(',')
                    if len(parts) >= 2:
                        lng = float(parts[0])
                        lat = float(parts[1])
                        
                        # Usar el nombre del placemark o generar uno
                        point_name = name_elem.text if name_elem is not None and name_elem.text else f"Punto_{len(coordinates)+1}"
                        
                        coordinates.append((point_name, lat, lng))
                except (ValueError, IndexError) as e:
                    print(f"Error parseando punto: {e}")
                    continue
    
    except ET.ParseError as e:
        raise ValueError(f"Error parseando archivo KML: {e}")
    except FileNotFoundError:
        raise ValueError(f"Archivo KML no encontrado: {kml_path}")
    
    if not coordinates:
        raise ValueError("No se encontraron coordenadas válidas en el archivo KML")
    
    return coordinates

def convert_kml_to_csv(input_path: str, output_base: str, target_system: str = "gk") -> None:
    """Convierte un archivo KML con polígonos a CSV con coordenadas convertidas.
    
    Args:
        input_path: Ruta al archivo KML de entrada
        output_base: Nombre base para los archivos de salida
        target_system: Sistema de destino ('gk' para Gauss-Krüger, 'wgs84' para WGS84)
    """
    # Extraer coordenadas del KML
    coordinates = parse_kml_polygon(input_path)
    
    print(f"Extraídos {len(coordinates)} vértices del archivo KML")
    
    # Crear archivo CSV temporal con las coordenadas extraídas
    temp_csv = f"{output_base}_temp.csv"
    
    with open(temp_csv, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['nombre', 'lat', 'lng'])
        
        for name, lat, lng in coordinates:
            writer.writerow([name, lat, lng])
    
    try:
        # Convertir usando las funciones existentes
        if target_system.lower() == "gk":
            convert_wgs84_to_gk(temp_csv, output_base)
            print(f"\nConversión de KML a Gauss-Krüger completada.")
        else:
            # Si ya está en WGS84, solo generar los archivos de salida
            final_csv = f"{output_base}.csv"
            
            # Copiar el archivo temporal al final
            with open(temp_csv, 'r', encoding='utf-8') as src, \
                 open(final_csv, 'w', newline='', encoding='utf-8') as dst:
                dst.write(src.read())
            
            # Crear archivos KML y GeoJSON
            create_kml(f"{output_base}.kml", coordinates, name=Path(input_path).stem)
            create_geojson(f"{output_base}.geojson", coordinates, name=Path(input_path).stem)
            
            print(f"\nExtracción de vértices de KML completada.")
    
    finally:
        # Limpiar archivo temporal
        if Path(temp_csv).exists():
            Path(temp_csv).unlink()

def create_kml(output_path: str, coordinates: list, name: str = "Polígono") -> None:
    """Crea un archivo KML con un polígono a partir de las coordenadas.
    
    Args:
        output_path: Ruta donde se guardará el archivo KML
        coordinates: Lista de tuplas (lat, lng, nombre)
        name: Nombre del polígono en el KML
    """
    # Crear el contenido KML
    kml_template = """<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <name>{name}</name>
    <Style id="polygonStyle">
      <LineStyle>
        <color>ff0000ff</color>
        <width>2</width>
      </LineStyle>
      <PolyStyle>
        <color>7f00ff00</color>
        <fill>1</fill>
        <outline>1</outline>
      </PolyStyle>
    </Style>
    <Placemark>
      <name>{name}</name>
      <styleUrl>#polygonStyle</styleUrl>
      <Polygon>
        <extrude>1</extrude>
        <altitudeMode>clampToGround</altitudeMode>
        <outerBoundaryIs>
          <LinearRing>
            <coordinates>
              {coordinates}
            </coordinates>
          </LinearRing>
        </outerBoundaryIs>
      </Polygon>
    </Placemark>
  </Document>
</kml>"""
    
    # Preparar las coordenadas en el formato correcto para KML (lng,lat,altitud)
    coords_list = []
    for lat, lng, _ in coordinates:
        # Formato: longitud,latitud,altura (0 por defecto)
        coords_list.append(f"{lng:.15f},{lat:.15f},0")
    
    # Cerrar el polígono repitiendo el primer punto al final
    if coordinates:
        first_lat, first_lng, _ = coordinates[0]
        coords_list.append(f"{first_lng:.15f},{first_lat:.15f},0")
    
    coords_str = '\n              '.join(coords_list)
    
    # Escribir el archivo KML
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(kml_template.format(name=name, coordinates=coords_str))
    
    print(f"\nArchivo KML generado: {output_path}")

def create_kmz(kml_path: str, kmz_path: str) -> None:
    """Crea un archivo KMZ a partir de un archivo KML.
    
    Args:
        kml_path: Ruta al archivo KML de entrada
        kmz_path: Ruta donde se guardará el archivo KMZ
    """
    try:
        # Crear un archivo ZIP con extensión .kmz
        with zipfile.ZipFile(kmz_path, 'w', zipfile.ZIP_DEFLATED) as kmz:
            # Añadir el archivo KML al KMZ
            kmz.write(kml_path, 'doc.kml')
            
        print(f"\nArchivo KMZ generado: {kmz_path}")
    except Exception as e:
        print(f"Error al crear el archivo KMZ: {e}")

def convert_wgs84_to_gk(input_path: str, output_base: str) -> None:
    """Convierte un archivo CSV con coordenadas WGS84 (lat/long) a Gauss-Krüger.
    
    Args:
        input_path: Ruta al archivo de entrada con columnas:
                   - nombre: Nombre del punto
                   - lat: Latitud en grados decimales
                   - lng: Longitud en grados decimales
        output_base: Nombre base para los archivos de salida (sin extensión)
    """
    # Definir la transformación de WGS84 a Gauss-Krüger (Campo Inchauspe)
    # Usando el EPSG:4326 (WGS84) a EPSG:22195 (Gauss-Krüger Zona 5 - Argentina)
    transformer = Transformer.from_crs("EPSG:4326", "EPSG:22195", always_xy=True)
    
    # Asegurarse de que el directorio de salida exista
    output_dir = Path(output_base).parent
    if output_dir and not output_dir.exists():
        output_dir.mkdir(parents=True)
    
    # Nombres de archivos de salida
    csv_path = f"{output_base}.csv"
    
    with open(input_path, 'r', encoding='utf-8') as infile, \
         open(csv_path, 'w', newline='', encoding='utf-8') as outfile:
        
        reader = csv.DictReader(infile)
        
        # Verificar que el archivo tenga las columnas necesarias
        required_columns = ['nombre', 'lat', 'lng']
        if not all(col in reader.fieldnames for col in required_columns):
            raise ValueError(f"El archivo debe contener las columnas: {', '.join(required_columns)}")
        
        # Configurar el writer de salida
        fieldnames = ['nombre', 'lat', 'lng', 'coordenadas_gauss_kruger_easting', 'coordenadas_gauss_kruger_northing']
        writer = csv.DictWriter(outfile, fieldnames=fieldnames)
        writer.writeheader()
        
        # Procesar cada fila
        for row_num, row in enumerate(reader, 1):
            try:
                # Obtener las coordenadas
                lat = float(row['lat'])
                lng = float(row['lng'])
                nombre = row['nombre']
                
                # Realizar la transformación de WGS84 a Gauss-Krüger
                easting, northing = transformer.transform(lng, lat)
                
                # Escribir la fila de salida
                writer.writerow({
                    'nombre': nombre,
                    'lat': lat,
                    'lng': lng,
                    'coordenadas_gauss_kruger_easting': easting,
                    'coordenadas_gauss_kruger_northing': northing
                })
                
                print(f"Convertido: {nombre} -> Easting: {easting:.6f}, Northing: {northing:.6f}")
                
            except (ValueError, KeyError) as e:
                print(f"Error en la fila {row_num}: {e}")
    
    print(f"\nArchivo CSV generado: {csv_path}")

def convert_gk_to_wgs84(input_path: str, output_base: str) -> None:
    """Convierte un archivo CSV con coordenadas Gauss-Krüger a WGS84.
    
    Args:
        input_path: Ruta al archivo de entrada con columnas:
                   - nombre: Nombre del punto
                   - coordenadas_gauss_kruger_easting: Coordenada X (Easting)
                   - coordenadas_gauss_kruger_northing: Coordenada Y (Northing)
        output_base: Nombre base para los archivos de salida (sin extensión)
    """
    # Definir la transformación de Gauss-Krüger (Campo Inchauspe) a WGS84
    # Usando el EPSG:22195 (Gauss-Krüger Zona 5 - Argentina)
    transformer = Transformer.from_crs("EPSG:22195", "EPSG:4326", always_xy=True)
    
    # Asegurarse de que el directorio de salida exista
    output_dir = Path(output_base).parent
    if output_dir and not output_dir.exists():
        output_dir.mkdir(parents=True)
    
    # Nombres de archivos de salida
    csv_path = f"{output_base}.csv"
    kml_path = f"{output_base}.kml"
    kmz_path = f"{output_base}.kmz"
    geojson_path = f"{output_base}.geojson"
    
    # Lista para almacenar todas las coordenadas para el KML
    all_coordinates = []
    
    with open(input_path, 'r', encoding='utf-8') as infile, \
         open(csv_path, 'w', newline='', encoding='utf-8') as outfile:
        
        reader = csv.DictReader(infile)
        
        # Verificar que el archivo tenga las columnas necesarias
        required_columns = ['nombre', 'coordenadas_gauss_kruger_easting', 'coordenadas_gauss_kruger_northing']
        if not all(col in reader.fieldnames for col in required_columns):
            raise ValueError(f"El archivo debe contener las columnas: {', '.join(required_columns)}")
        
        # Configurar el writer de salida
        fieldnames = ['nombre', 'lat', 'lng']
        writer = csv.DictWriter(outfile, fieldnames=fieldnames)
        writer.writeheader()
        
        # Procesar cada fila
        for row_num, row in enumerate(reader, 1):
            try:
                # Obtener las coordenadas
                easting = float(row['coordenadas_gauss_kruger_easting'])
                northing = float(row['coordenadas_gauss_kruger_northing'])
                nombre = row['nombre']
                
                # Realizar la transformación de Gauss-Krüger a WGS84
                # Usando el transformador definido al inicio
                lng, lat = transformer.transform(easting, northing)
                
                # Guardar para el KML
                all_coordinates.append((lat, lng, nombre))
                
                # Escribir la fila de salida
                writer.writerow({
                    'nombre': nombre,
                    'lat': lat,
                    'lng': lng
                })
                
                print(f"Convertido: {nombre} -> {lat:.10f}, {lng:.10f}")
                
            except (ValueError, KeyError) as e:
                print(f"Error en la fila {row_num}: {e}")
    
    # Generar los archivos de salida si hay coordenadas
    if all_coordinates:
        create_kml(kml_path, all_coordinates, name=Path(input_path).stem)
        create_kmz(kml_path, kmz_path)
        create_geojson(geojson_path, all_coordinates, name=Path(input_path).stem)

def create_geojson(output_path: str, coordinates: List[Tuple[float, float, str]], name: str = "Polígono") -> None:
    """Crea un archivo GeoJSON con un polígono a partir de las coordenadas.
    
    Args:
        output_path: Ruta donde se guardará el archivo GeoJSON
        coordinates: Lista de tuplas (lat, lng, nombre)
        name: Nombre del polígono en el GeoJSON
    """
    # Crear la estructura GeoJSON
    geojson = {
        "type": "FeatureCollection",
        "name": name,
        "crs": {
            "type": "name",
            "properties": {
                "name": "urn:ogc:def:crs:OGC:1.3:CRS84"
            }
        },
        "features": [
            {
                "type": "Feature",
                "properties": {
                    "name": name,
                    "description": "Polígono generado automáticamente"
                },
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [
                        # Formato GeoJSON: [lng, lat] para cada punto con 15 decimales
                        [[round(lng, 15), round(lat, 15)] for lat, lng, _ in coordinates] + 
                        # Cerrar el polígono solo si hay suficientes puntos
                        ([[round(coordinates[0][1], 15), round(coordinates[0][0], 15)]] if len(coordinates) > 2 else [])
                    ]
                }
            }
        ]
    }
    
    # Escribir el archivo GeoJSON
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(geojson, f, indent=2, ensure_ascii=False)
    
    print(f"\nArchivo GeoJSON generado: {output_path}")

def main():
    if len(sys.argv) != 4:
        print("Uso:")
        print("  python convert_gk_to_wgs84.py gk_to_wgs84 input.csv output_base_name")
        print("  python convert_gk_to_wgs84.py wgs84_to_gk input.csv output_base_name")
        print("  python convert_gk_to_wgs84.py kml_to_gk input.kml output_base_name")
        print("  python convert_gk_to_wgs84.py kml_to_wgs84 input.kml output_base_name")
        print("\nModos disponibles:")
        print("  gk_to_wgs84: Convierte de Gauss-Krüger a WGS84 (lat/lng)")
        print("  wgs84_to_gk: Convierte de WGS84 (lat/lng) a Gauss-Krüger")
        print("  kml_to_gk: Extrae vértices de KML y convierte a Gauss-Krüger")
        print("  kml_to_wgs84: Extrae vértices de KML y mantiene en WGS84")
        print("\nFormatos de entrada:")
        print("  Para gk_to_wgs84: nombre,coordenadas_gauss_kruger_easting,coordenadas_gauss_kruger_northing")
        print("  Para wgs84_to_gk: nombre,lat,lng")
        print("  Para kml_to_*: Archivo KML con polígonos o puntos")
        sys.exit(1)
        
    mode = sys.argv[1]
    input_path = sys.argv[2]
    output_base = sys.argv[3]
    
    # Validar modo
    valid_modes = ['gk_to_wgs84', 'wgs84_to_gk', 'kml_to_gk', 'kml_to_wgs84']
    if mode not in valid_modes:
        print(f"Error: Modo '{mode}' no válido. Use uno de: {', '.join(valid_modes)}")
        sys.exit(1)
    
    # Eliminar la extensión si se proporcionó
    output_base = Path(output_base).with_suffix('')
    
    if not Path(input_path).exists():
        print(f"Error: El archivo de entrada '{input_path}' no existe.")
        sys.exit(1)
    
    try:
        if mode == 'gk_to_wgs84':
            convert_gk_to_wgs84(input_path, str(output_base))
            print(f"\nConversión de Gauss-Krüger a WGS84 completada. Archivos generados:")
            print(f"- {output_base}.csv: Coordenadas en formato CSV")
            print(f"- {output_base}.kml: Polígono en formato KML")
            print(f"- {output_base}.kmz: Polígono en formato KMZ")
            print(f"- {output_base}.geojson: Polígono en formato GeoJSON")
        elif mode == 'wgs84_to_gk':
            convert_wgs84_to_gk(input_path, str(output_base))
            print(f"\nConversión de WGS84 a Gauss-Krüger completada. Archivo generado:")
            print(f"- {output_base}.csv: Coordenadas en formato CSV")
        elif mode == 'kml_to_gk':
            convert_kml_to_csv(input_path, str(output_base), "gk")
            print(f"\nArchivos generados:")
            print(f"- {output_base}.csv: Vértices convertidos a Gauss-Krüger")
        elif mode == 'kml_to_wgs84':
            convert_kml_to_csv(input_path, str(output_base), "wgs84")
            print(f"\nArchivos generados:")
            print(f"- {output_base}.csv: Vértices extraídos en WGS84")
            print(f"- {output_base}.kml: Polígono en formato KML")
            print(f"- {output_base}.geojson: Polígono en formato GeoJSON")
    except Exception as e:
        print(f"\nError durante la conversión: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
