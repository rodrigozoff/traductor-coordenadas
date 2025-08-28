"""Módulo para conversión entre coordenadas Google Maps y Gauss-Krüger."""

from typing import Tuple, Optional
import pyproj
import logging

# Configuración para Argentina - Zonas UTM más comunes en Argentina
ZONAS_UTM_ARGENTINA = {
    '18S': {'zone': 18, 'south': True, 'ellps': 'WGS84'},  # Este (Bs. As., Córdoba, etc.)
    '19S': {'zone': 19, 'south': True, 'ellps': 'WGS84'},  # Centro (Mendoza, San Juan)
    '20S': {'zone': 20, 'south': True, 'ellps': 'WGS84'},  # Oeste (Bariloche, Neuquén)
}

# Configuración de proyección Gauss-Krüger para Argentina
GK_PARAMS = {
    'proj': 'tmerc',
    'lat_0': -90,
    'lon_0': -60,
    'k': 1,
    'x_0': 5500000,
    'y_0': 0,
    'ellps': 'intl',
    'units': 'm',
    'no_defs': True
}

class CoordinateConverter:
    """Clase para manejar la conversión entre sistemas de coordenadas."""

    def __init__(self, utm_zone: str = '20S'):
        """Inicializa el convertidor con una zona UTM específica.
        
        Args:
            utm_zone: Zona UTM a utilizar (por defecto '20S' para el oeste de Argentina)
        """
        if utm_zone not in ZONAS_UTM_ARGENTINA:
            raise ValueError(f"Zona UTM no válida. Debe ser una de: {', '.join(ZONAS_UTM_ARGENTINA.keys())}")
        
        self.utm_zone = utm_zone
        self.utm_params = ZONAS_UTM_ARGENTINA[utm_zone]
        
        # Inicializar transformadores
        self.wgs84_to_gk = pyproj.Transformer.from_crs(
            'EPSG:4326',  # WGS84 (Google Maps)
            GK_PARAMS,    # Gauss-Krüger
            always_xy=True
        )
        
        self.gk_to_wgs84 = pyproj.Transformer.from_crs(
            GK_PARAMS,    # Gauss-Krüger
            'EPSG:4326',  # WGS84 (Google Maps)
            always_xy=True
        )

    def google_to_gk(self, lat: float, lng: float) -> Tuple[float, float]:
        """Convierte coordenadas de Google Maps (WGS84) a Gauss-Krüger.
        
        Args:
            lat: Latitud en grados decimales
            lng: Longitud en grados decimales
            
        Returns:
            Tupla con coordenadas (Easting, Northing) en Gauss-Krüger
        """
        try:
            # Convertir a Gauss-Krüger
            x, y = self.wgs84_to_gk.transform(lng, lat)
            return round(x, 3), round(y, 3)  # Redondear a 3 decimales (milímetros)
        except Exception as e:
            logging.error(f"Error al convertir de Google Maps a Gauss-Krüger: {e}")
            raise ValueError(f"No se pudo convertir las coordenadas: {e}")

    def gk_to_google(self, easting: float, northing: float) -> Tuple[float, float]:
        """Convierte coordenadas de Gauss-Krüger a Google Maps (WGS84).
        
        Args:
            easting: Coordenada Este (X) en metros
            northing: Coordenada Norte (Y) en metros
            
        Returns:
            Tupla con coordenadas (lat, lng) en grados decimales
        """
        try:
            # Convertir a WGS84 (Google Maps)
            lng, lat = self.gk_to_wgs84.transform(easting, northing)
            return round(lat, 6), round(lng, 6)  # Redondear a 6 decimales (~10cm de precisión)
        except Exception as e:
            logging.error(f"Error al convertir de Gauss-Krüger a Google Maps: {e}")
            raise ValueError(f"No se pudo convertir las coordenadas: {e}")

def parse_google_coords(coord_str: str) -> Tuple[float, float]:
    """Parsea un string de coordenadas de Google Maps.
    
    Args:
        coord_str: String en formato "lat,lng" o "lat, lng"
        
    Returns:
        Tupla con (lat, lng) como floats
    """
    try:
        lat, lng = map(float, coord_str.replace(" ", "").split(","))
        return lat, lng
    except (ValueError, AttributeError) as e:
        raise ValueError(f"Formato de coordenadas de Google Maps inválido: {coord_str}")

def parse_gk_coords(coord_str: str) -> Tuple[float, float]:
    """Parsea un string de coordenadas Gauss-Krüger.
    
    Args:
        coord_str: String en formato "easting,northing" o "easting, northing"
        
    Returns:
        Tupla con (easting, northing) como floats
    """
    try:
        easting, northing = map(float, coord_str.replace(" ", "").split(","))
        return easting, northing
    except (ValueError, AttributeError) as e:
        raise ValueError(f"Formato de coordenadas Gauss-Krüger inválido: {coord_str}")
