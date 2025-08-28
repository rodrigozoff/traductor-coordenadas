"""Interfaz de línea de comandos para el traductor de coordenadas."""

import argparse
import logging
import os
import sys
from pathlib import Path
from typing import List, Dict, Any, Tuple

from .converter import CoordinateConverter, parse_google_coords, parse_gk_coords
from .file_handler import CSVHandler

def setup_logging(level=logging.INFO):
    """Configura el sistema de logging.
    
    Args:
        level: Nivel de logging (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )

logger = logging.getLogger(__name__)

class CoordinateTranslator:
    """Clase principal para la traducción de coordenadas."""
    
    def __init__(self, utm_zone: str = '20S'):
        """Inicializa el traductor de coordenadas.
        
        Args:
            utm_zone: Zona UTM a utilizar (por defecto '20S' para el oeste de Argentina)
        """
        self.converter = CoordinateConverter(utm_zone=utm_zone)
        self.csv_handler = CSVHandler()
    
    def process_csv(self, input_path: str, output_path: str = None, to_gk: bool = True) -> None:
        """Procesa un archivo CSV con coordenadas.
        
        Args:
            input_path: Ruta al archivo de entrada
            output_path: Ruta al archivo de salida (opcional)
            to_gk: Si es True, convierte a Gauss-Krüger; si es False, a Google Maps
        """
        try:
            logger.info(f"Procesando archivo: {input_path}")
            
            # Leer el archivo CSV
            valid_rows, error_rows = self.csv_handler.read_csv(input_path)
            
            if not valid_rows and not error_rows:
                logger.warning("El archivo está vacío o no contiene filas válidas")
                return
            
            # Determinar el formato de las coordenadas
            first_row = valid_rows[0] if valid_rows else {}
            has_single_column = 'coordenadas' in first_row
            has_separate_columns = all(col in first_row for col in ['lat', 'lng'])
            
            # Procesar cada fila
            processed_rows = []
            for row in valid_rows:
                try:
                    # Create a new row with just the basic info
                    processed_row = {'nombre': row['nombre']}
                    
                    if to_gk:
                        # Convertir de Google Maps a Gauss-Krüger
                        if 'lat' in row and 'lng' in row and row['lat'] is not None and row['lng'] is not None:
                            # Formato: columnas separadas 'lat' y 'lng'
                            try:
                                lat = float(row['lat'])
                                lng = float(row['lng'])
                                easting, northing = self.converter.google_to_gk(lat, lng)
                                processed_row['coordenadas_gauss_kruger_easting'] = easting
                                processed_row['coordenadas_gauss_kruger_northing'] = northing
                                processed_rows.append(processed_row)
                            except (ValueError, TypeError) as e:
                                error_rows.append({
                                    'linea': row.get('linea', '?'),
                                    'contenido': str(row),
                                    'error': f'Error al convertir coordenadas: {e}'
                                })
                    elif not to_gk:
                        # Convertir de Gauss-Krüger a Google Maps
                        if all(f'coordenadas_gauss_kruger_{i}' in row for i in ['easting', 'northing']):
                            try:
                                easting = float(row['coordenadas_gauss_kruger_easting'])
                                northing = float(row['coordenadas_gauss_kruger_northing'])
                                lat, lng = self.converter.gk_to_google(easting, northing)
                                processed_row['coordenadas_google_maps'] = f"{lat:.6f},{lng:.6f}"
                                processed_rows.append(processed_row)
                            except (ValueError, TypeError) as e:
                                error_rows.append({
                                    'linea': row.get('linea', '?'),
                                    'contenido': str(row),
                                    'error': f'Error al convertir coordenadas: {e}'
                                })
                    
                except Exception as e:
                    error_rows.append({
                        'row': row,
                        'error': f"Error al procesar la fila: {str(e)}"
                    })
            
            # Definir las columnas de salida
            fieldnames = ['nombre']
            if to_gk:
                fieldnames.extend(['coordenadas_gauss_kruger_easting', 'coordenadas_gauss_kruger_northing'])
            else:
                fieldnames.append('coordenadas_google_maps')
                
            # Escribir el archivo de salida
            if not output_path:
                prefix = 'gauss_kruger_' if to_gk else 'google_maps_'
                output_path = self.csv_handler.get_output_path(input_path, prefix)
            
            logger.debug(f"Ruta de salida: {output_path}")
            logger.debug(f"Columnas de salida: {fieldnames}")
            
            # Preparar las filas para la salida
            output_rows = []
            for row in processed_rows:
                try:
                    output_row = {'nombre': row['nombre']}
                    if to_gk and 'coordenadas_gauss_kruger_easting' in row:
                        output_row['coordenadas_gauss_kruger_easting'] = row['coordenadas_gauss_kruger_easting']
                        output_row['coordenadas_gauss_kruger_northing'] = row['coordenadas_gauss_kruger_northing']
                        logger.debug(f"Procesando fila para GK: {output_row}")
                    elif not to_gk and 'coordenadas_google_maps' in row:
                        output_row['coordenadas_google_maps'] = row['coordenadas_google_maps']
                        logger.debug(f"Procesando fila para GM: {output_row}")
                    output_rows.append(output_row)
                except Exception as e:
                    logger.error(f"Error al procesar fila {row}: {e}")
                    
            logger.debug(f"Total de filas a escribir: {len(output_rows)}")
            logger.debug(f"Primeras 2 filas: {output_rows[:2] if len(output_rows) > 0 else 'No hay filas'}")
            
            # Escribir el archivo
            try:
                self.csv_handler.write_csv(output_path, fieldnames, output_rows, error_rows)
                logger.debug(f"Archivo escrito en: {os.path.abspath(output_path)}")
                logger.debug(f"Tamaño del archivo: {os.path.getsize(output_path) if os.path.exists(output_path) else 'No existe'}")
            except Exception as e:
                logger.error(f"Error al escribir el archivo: {e}")
                raise
            
            logger.info(f"Archivo procesado correctamente: {output_path}")
            if error_rows:
                logger.warning(f"Se encontraron {len(error_rows)} errores. Ver el archivo de log para más detalles.")
            
        except Exception as e:
            logger.error(f"Error al procesar el archivo: {e}")
            raise

def parse_args():
    """Parsear los argumentos de línea de comandos."""
    # Configurar logging básico inicial
    setup_logging(level=logging.INFO)
    
    # Crear el parser principal
    parser = argparse.ArgumentParser(
        description='Traductor de coordenadas entre Google Maps y Gauss-Krüger para Argentina.'
    )
    
    # Subparsers para los comandos
    subparsers = parser.add_subparsers(dest='command', help='Comandos disponibles')
    
    # Comando: to_gk
    parser_gk = subparsers.add_parser(
        'to_gk',
        help='Convertir de Google Maps a Gauss-Krüger',
        add_help=False  # Vamos a manejar la ayuda manualmente
    )
    parser_gk.add_argument(
        '--input',
        required=True,
        help='Ruta al archivo CSV de entrada con coordenadas de Google Maps'
    )
    parser_gk.add_argument(
        '--output',
        help='Ruta al archivo de salida (opcional)'
    )
    parser_gk.add_argument(
        '--utm-zone',
        default='20S',
        choices=['18S', '19S', '20S'],
        help='Zona UTM a utilizar (por defecto: 20S)'
    )
    parser_gk.add_argument(
        '--log-level',
        default='INFO',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
        help='Nivel de logging (por defecto: INFO)'
    )
    
    # Comando: to_gmaps
    parser_gmaps = subparsers.add_parser(
        'to_gmaps',
        help='Convertir de Gauss-Krüger a Google Maps',
        add_help=False  # Vamos a manejar la ayuda manualmente
    )
    parser_gmaps.add_argument(
        '--input',
        required=True,
        help='Ruta al archivo CSV de entrada con coordenadas Gauss-Krüger'
    )
    parser_gmaps.add_argument(
        '--output',
        help='Ruta al archivo de salida (opcional)'
    )
    parser_gmaps.add_argument(
        '--utm-zone',
        default='20S',
        choices=['18S', '19S', '20S'],
        help='Zona UTM a utilizar (por defecto: 20S)'
    )
    parser_gmaps.add_argument(
        '--log-level',
        default='INFO',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
        help='Nivel de logging (por defecto: INFO)'
    )
    
    # Manejar la ayuda para el comando raíz
    if len(sys.argv) == 1 or sys.argv[1] in ['-h', '--help']:
        parser.print_help()
        sys.exit(0)
        
    # Si no se proporciona un comando, mostrar ayuda
    if len(sys.argv) == 1 or sys.argv[1] not in ['to_gk', 'to_gmaps']:
        parser.print_help()
        sys.exit(1)
    
    return parser.parse_args()

def main():
    """Función principal para la interfaz de línea de comandos."""
    # Parsear argumentos
    args = parse_args()
    
    # Configurar logging con el nivel especificado
    log_level = getattr(logging, args.log_level.upper(), logging.INFO)
    setup_logging(level=log_level)
    
    logger.debug(f"Argumentos de línea de comandos: {args}")
    
    if not hasattr(args, 'input'):
        logger.error("Se requiere especificar un comando. Use -h para ayuda.")
        sys.exit(1)
    
    try:
        # Inicializar el traductor
        translator = CoordinateTranslator(utm_zone=args.utm_zone)
        
        # Procesar según el comando
        if args.command == 'to_gk':
            translator.process_csv(
                input_path=args.input,
                output_path=args.output,
                to_gk=True
            )
        elif args.command == 'to_gmaps':
            translator.process_csv(
                input_path=args.input,
                output_path=args.output,
                to_gk=False
            )
    
    except Exception as e:
        logger.error(f"Error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
