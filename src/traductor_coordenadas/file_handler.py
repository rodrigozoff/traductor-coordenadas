"""Módulo para manejo de archivos CSV."""

import csv
import os
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional
import logging

# Configurar logger
logger = logging.getLogger(__name__)

class CSVHandler:
    """Clase para manejar la lectura y escritura de archivos CSV."""

    @staticmethod
    def read_csv(file_path: str) -> Tuple[List[Dict[str, Any]], List[Dict]]:
        """Lee un archivo CSV y devuelve sus filas.
        
        Args:
            file_path: Ruta al archivo CSV
            
        Returns:
            Tupla con (filas_válidas, filas_con_errores)
        """
        valid_rows = []
        error_rows = []
        
        try:
            logger.debug(f"Leyendo archivo: {file_path}")
            with open(file_path, 'r', encoding='utf-8') as f:
                # Leer el archivo CSV
                reader = csv.DictReader(f)
                
                # Verificar que el archivo tenga las columnas requeridas
                required_columns = ['nombre']
                if not reader.fieldnames:
                    raise ValueError("El archivo CSV está vacío o no tiene encabezados válidos")
                    
                missing_columns = [col for col in required_columns if col not in reader.fieldnames]
                if missing_columns:
                    raise ValueError(f"El archivo CSV debe contener las columnas: {', '.join(required_columns)}")
                
                # Verificar si tenemos columnas de coordenadas
                has_separate_columns = all(col in reader.fieldnames for col in ['lat', 'lng'])
                has_single_column = 'coordenadas' in reader.fieldnames
                
                if not has_separate_columns and not has_single_column:
                    raise ValueError("El archivo CSV debe contener columnas 'lat' y 'lng' o una columna 'coordenadas'")
                
                # Procesar cada fila
                for line_num, row in enumerate(reader, 2):  # Empezar desde la línea 2 (1-based + header)
                    try:
                        # Validar que la fila tenga todos los campos requeridos
                        if not all(row.get(col) for col in required_columns):
                            raise ValueError("Faltan campos requeridos")
                        
                        # Obtener el nombre
                        nombre = row['nombre'].strip()
                        if not nombre:
                            raise ValueError("El campo 'nombre' no puede estar vacío")
                            
                        # Verificar el formato de las coordenadas
                        if has_separate_columns:
                            # Formato: nombre,lat,lng (pero con encabezado 'coordenadas_google_maps')
                            lat = row.get(reader.fieldnames[1], '').strip()
                            lng = row.get(reader.fieldnames[2], '').strip()
                            
                            if not lat or not lng:
                                raise ValueError("Las columnas de latitud y longitud no pueden estar vacías")
                                
                            try:
                                lat_float = float(lat)
                                lng_float = float(lng)
                                if not (-90 <= lat_float <= 90) or not (-180 <= lng_float <= 180):
                                    raise ValueError("Coordenadas fuera de rango")
                            except ValueError:
                                raise ValueError(f"Formato de coordenadas inválido: lat={lat}, lng={lng}")
                                
                            # Si llegamos aquí, la fila es válida
                            valid_rows.append({
                                'nombre': nombre,
                                'coordenadas': f"{lat_float},{lng_float}",
                                'linea': line_num
                            })
                            
                        elif 'coordenadas_google_maps' in reader.fieldnames:
                            # Formato: nombre,coordenadas_google_maps (lat,lng en una sola celda)
                            coords = row.get('coordenadas_google_maps', '').strip()
                            if not coords:
                                raise ValueError("El campo 'coordenadas_google_maps' está vacío")
                            
                            # Validar que las coordenadas tengan el formato correcto
                            try:
                                lat, lng = map(float, coords.split(','))
                                if not (-90 <= lat <= 90) or not (-180 <= lng <= 180):
                                    raise ValueError("Coordenadas fuera de rango")
                            except (ValueError, AttributeError):
                                raise ValueError(f"Formato de coordenadas inválido: {coords}")
                                
                            # Si llegamos aquí, la fila es válida
                            valid_rows.append({
                                'nombre': nombre,
                                'coordenadas': coords,
                                'linea': line_num
                            })
                            
                        if has_separate_columns:
                            # Formato: nombre,lat,lng
                            lat = row.get('lat', '').strip()
                            lng = row.get('lng', '').strip()
                            
                            if not lat or not lng:
                                raise ValueError("Los campos 'lat' y 'lng' no pueden estar vacíos")
                                
                            try:
                                lat_float = float(lat)
                                lng_float = float(lng)
                                if not (-90 <= lat_float <= 90) or not (-180 <= lng_float <= 180):
                                    raise ValueError("Coordenadas fuera de rango")
                                    
                                # Si llegamos aquí, la fila es válida
                                valid_rows.append({
                                    'nombre': nombre,
                                    'lat': lat_float,
                                    'lng': lng_float,
                                    'linea': line_num
                                })
                                
                            except ValueError as e:
                                raise ValueError(f"Formato de coordenadas inválido: lat={lat}, lng={lng}")
                                
                        elif has_single_column:
                            # Formato: nombre,coordenadas (lat,lng en una sola celda)
                            coords = row.get('coordenadas', '').strip()
                            if not coords:
                                raise ValueError("El campo 'coordenadas' está vacío")
                            
                            try:
                                lat, lng = map(float, coords.split(','))
                                if not (-90 <= lat <= 90) or not (-180 <= lng <= 180):
                                    raise ValueError("Coordenadas fuera de rango")
                                    
                                # Si llegamos aquí, la fila es válida
                                valid_rows.append({
                                    'nombre': nombre,
                                    'lat': lat,
                                    'lng': lng,
                                    'linea': line_num
                                })
                                
                            except (ValueError, AttributeError) as e:
                                raise ValueError(f"Formato de coordenadas inválido: {coords}")
                        else:
                            raise ValueError("No se encontraron columnas de coordenadas válidas. Se requiere 'coordenadas_google_maps' o 'lat' y 'lng'")
                        
                    except Exception as e:
                        error_rows.append({
                            'linea': line_num,
                            'contenido': str(row),
                            'error': str(e)
                        })
                        logger.warning(f"Error en la línea {line_num}: {e}")
                        
            return valid_rows, error_rows
            
        except Exception as e:
            logging.error(f"Error al leer el archivo {file_path}: {e}")
            raise
    
    @staticmethod
    def write_csv(
        output_path: str,
        fieldnames: List[str],
        rows: List[Dict[str, Any]],
        errors: List[Dict] = None
    ) -> None:
        """Escribe un archivo CSV con los datos proporcionados.
        
        Args:
            output_path: Ruta donde se guardará el archivo
            fieldnames: Lista de nombres de columnas
            rows: Lista de diccionarios con los datos
            errors: Lista opcional de errores para incluir en un archivo de log
        """
        try:
            # Crear directorio si no existe
            output_dir = os.path.dirname(output_path) or '.'
            os.makedirs(output_dir, exist_ok=True)
            
            logger.debug(f"Escribiendo archivo de salida en: {os.path.abspath(output_path)}")
            logger.debug(f"Columnas: {fieldnames}")
            logger.debug(f"Filas a escribir: {len(rows)}")
            logger.debug(f"Primera fila: {rows[0] if rows else 'No hay filas'}")
            
            with open(output_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                for row in rows:
                    logger.debug(f"Escribiendo fila: {row}")
                    writer.writerow(row)
            
            logger.debug(f"Archivo escrito exitosamente en: {os.path.abspath(output_path)}")
                
            # Si hay errores, guardarlos en un archivo de log
            if errors:
                log_path = f"{os.path.splitext(output_path)[0]}_errores.log"
                with open(log_path, 'w', encoding='utf-8') as f:
                    for error in errors:
                        line_num = error.get('linea', '?')
                        f.write(f"Línea {line_num}: {error.get('error', 'Error desconocido')}\n")
                logger.debug(f"Archivo de errores escrito en: {os.path.abspath(log_path)}")
                        
        except Exception as e:
            logging.error(f"Error al escribir el archivo {output_path}: {e}")
            raise

    @staticmethod
    def get_output_path(input_path: str, prefix: str) -> str:
        """Genera la ruta de salida con el prefijo especificado.
        
        Args:
            input_path: Ruta del archivo de entrada
            prefix: Prefijo para el nombre del archivo de salida
            
        Returns:
            Ruta del archivo de salida
        """
        input_path = Path(input_path)
        output_filename = f"{prefix}{input_path.name}"
        return str(input_path.parent / output_filename)
