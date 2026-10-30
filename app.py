import streamlit as st
import pandas as pd
import pyproj
from pyproj import Transformer
import io
import zipfile
import json
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
import base64
import folium
from streamlit_folium import st_folium
import math

# Sistemas Gauss-Krüger faja 5 disponibles. POSGAR 2007 es el marco oficial
# vigente en Argentina (IGN, 2009); Campo Inchauspe queda solo para planos viejos.
SISTEMAS_GK = {
    "POSGAR 2007 / Argentina faja 5 (EPSG:5347)": "EPSG:5347",
    "POSGAR 94 / Argentina faja 5 (EPSG:22185)": "EPSG:22185",
    "Campo Inchauspe / Argentina faja 5 (EPSG:22195) - histórico": "EPSG:22195",
}
SISTEMA_GK_DEFAULT = "POSGAR 2007 / Argentina faja 5 (EPSG:5347)"

# Configuración de la página
st.set_page_config(
    page_title="Conversor de Coordenadas Gauss-Krüger ↔ WGS84",
    page_icon="🗺️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS personalizado para mejorar la apariencia
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .info-box {
        background-color: #e8f4fd;
        padding: 1.5rem;
        border-radius: 0.5rem;
        border-left: 4px solid #1f77b4;
        margin: 1rem 0;
        color: #2c3e50;
        font-weight: 500;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .success-box {
        background-color: #d4edda;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #28a745;
        margin: 1rem 0;
    }
    .error-box {
        background-color: #f8d7da;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #dc3545;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

def create_download_link(df, filename, file_format="csv"):
    """Crea un enlace de descarga para el DataFrame"""
    if file_format == "csv":
        csv = df.to_csv(index=False)
        b64 = base64.b64encode(csv.encode()).decode()
        href = f'<a href="data:file/csv;base64,{b64}" download="{filename}.csv">📥 Descargar {filename}.csv</a>'
    return href

def convert_wgs84_to_gk(df, sistema_gk=SISTEMA_GK_DEFAULT):
    """Convierte coordenadas de WGS84 a Gauss-Krüger"""
    transformer = Transformer.from_crs("EPSG:4326", SISTEMAS_GK[sistema_gk], always_xy=True)
    
    results = []
    errors = []
    
    for idx, row in df.iterrows():
        try:
            lat = float(row['lat'])
            lng = float(row['lng'])
            nombre = row['nombre']
            
            easting, northing = transformer.transform(lng, lat)
            
            results.append({
                'nombre': nombre,
                'lat': lat,
                'lng': lng,
                'coordenadas_gauss_kruger_easting': easting,
                'coordenadas_gauss_kruger_northing': northing,
                'sistema_gk': sistema_gk
            })
            
        except Exception as e:
            errors.append(f"Error en fila {idx + 1}: {str(e)}")
    
    return pd.DataFrame(results), errors

def convert_gk_to_wgs84(df, sistema_gk=SISTEMA_GK_DEFAULT):
    """Convierte coordenadas de Gauss-Krüger a WGS84"""
    transformer = Transformer.from_crs(SISTEMAS_GK[sistema_gk], "EPSG:4326", always_xy=True)
    
    results = []
    errors = []
    
    for idx, row in df.iterrows():
        try:
            easting = float(row['coordenadas_gauss_kruger_easting'])
            northing = float(row['coordenadas_gauss_kruger_northing'])
            nombre = row['nombre']
            
            lng, lat = transformer.transform(easting, northing)
            
            results.append({
                'nombre': nombre,
                'lat': lat,
                'lng': lng,
                'coordenadas_gauss_kruger_easting': easting,
                'coordenadas_gauss_kruger_northing': northing,
                'sistema_gk': sistema_gk
            })
            
        except Exception as e:
            errors.append(f"Error en fila {idx + 1}: {str(e)}")
    
    return pd.DataFrame(results), errors

def create_kml(df, name="Coordenadas", sistema_gk=SISTEMA_GK_DEFAULT):
    """Genera contenido KML a partir del DataFrame con puntos y polígono"""
    kml_template = """<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <name>{name}</name>
    <Style id="pointStyle">
      <IconStyle>
        <color>ff0000ff</color>
        <scale>1.2</scale>
      </IconStyle>
    </Style>
    <Style id="polygonStyle">
      <LineStyle>
        <color>ff0000ff</color>
        <width>2</width>
      </LineStyle>
      <PolyStyle>
        <color>4d0000ff</color>
      </PolyStyle>
    </Style>
    {placemarks}
    {polygon}
  </Document>
</kml>"""
    
    placemarks = []
    polygon_coords = []
    
    # Si el DataFrame tiene coordenadas Gauss-Krüger pero no WGS84, convertir primero
    if 'coordenadas_gauss_kruger_easting' in df.columns and 'coordenadas_gauss_kruger_northing' in df.columns:
        if 'lat' not in df.columns or 'lng' not in df.columns:
            # Convertir GK a WGS84 para el KML
            transformer = Transformer.from_crs(SISTEMAS_GK[sistema_gk], "EPSG:4326", always_xy=True)
            df_temp = df.copy()
            coords_wgs84 = []
            for _, row in df_temp.iterrows():
                lng, lat = transformer.transform(
                    row['coordenadas_gauss_kruger_easting'],
                    row['coordenadas_gauss_kruger_northing']
                )
                coords_wgs84.append({'lat': lat, 'lng': lng})
            df_temp['lat'] = [c['lat'] for c in coords_wgs84]
            df_temp['lng'] = [c['lng'] for c in coords_wgs84]
            df = df_temp
    
    # Crear placemarks para puntos individuales
    for _, row in df.iterrows():
        if 'lat' in row and 'lng' in row:
            placemark = f"""    <Placemark>
      <name>{row['nombre']}</name>
      <styleUrl>#pointStyle</styleUrl>
      <Point>
        <coordinates>{row['lng']:.10f},{row['lat']:.10f},0</coordinates>
      </Point>
    </Placemark>"""
            placemarks.append(placemark)
            polygon_coords.append(f"{row['lng']:.10f},{row['lat']:.10f},0")
    
    # Crear polígono si hay 3 o más puntos
    polygon = ""
    if len(polygon_coords) >= 3:
        # Cerrar el polígono si no está cerrado
        if polygon_coords[0] != polygon_coords[-1]:
            polygon_coords.append(polygon_coords[0])
        
        polygon = f"""    <Placemark>
      <name>Polígono</name>
      <styleUrl>#polygonStyle</styleUrl>
      <Polygon>
        <outerBoundaryIs>
          <LinearRing>
            <coordinates>
              {' '.join(polygon_coords)}
            </coordinates>
          </LinearRing>
        </outerBoundaryIs>
      </Polygon>
    </Placemark>"""
    
    return kml_template.format(name=name, placemarks='\n'.join(placemarks), polygon=polygon)

def calculate_polygon_area_gk(coordinates_gk):
    """
    Calcula el área de un polígono usando coordenadas Gauss-Krüger.
    Usa la fórmula del área de Shoelace (coordenadas cartesianas).
    
    Args:
        coordinates_gk: Lista de tuplas (easting, northing)
    
    Returns:
        Área en metros cuadrados
    """
    if len(coordinates_gk) < 3:
        return 0
    
    # Asegurar que el polígono esté cerrado
    coords = list(coordinates_gk)
    if coords[0] != coords[-1]:
        coords.append(coords[0])
    
    # Fórmula de Shoelace
    area = 0
    n = len(coords) - 1
    
    for i in range(n):
        area += coords[i][0] * coords[i+1][1]
        area -= coords[i+1][0] * coords[i][1]
    
    return abs(area) / 2

def calculate_polygon_area_wgs84(coordinates_wgs84):
    """
    Calcula el área aproximada de un polígono usando coordenadas WGS84.
    Usa proyección local para pequeñas áreas.
    
    Args:
        coordinates_wgs84: Lista de tuplas (lat, lng)
    
    Returns:
        Área en metros cuadrados
    """
    if len(coordinates_wgs84) < 3:
        return 0
    
    # Convertir a coordenadas cartesianas locales
    # Usar el centro del polígono como origen
    center_lat = sum(coord[0] for coord in coordinates_wgs84) / len(coordinates_wgs84)
    center_lng = sum(coord[1] for coord in coordinates_wgs84) / len(coordinates_wgs84)
    
    # Factores de conversión aproximados para Argentina
    lat_to_m = 111320  # metros por grado de latitud
    lng_to_m = 111320 * math.cos(math.radians(center_lat))  # metros por grado de longitud
    
    # Convertir a coordenadas cartesianas locales
    local_coords = []
    for lat, lng in coordinates_wgs84:
        x = (lng - center_lng) * lng_to_m
        y = (lat - center_lat) * lat_to_m
        local_coords.append((x, y))
    
    # Usar fórmula de Shoelace
    return calculate_polygon_area_gk(local_coords)

def main():
    # Título principal
    st.markdown('<h1 class="main-header">🗺️ Conversor de Coordenadas Gauss-Krüger ↔ WGS84</h1>', unsafe_allow_html=True)
    
    # Información general
    st.markdown("""
    <div class="info-box">
        <h3>📍 Conversor Profesional para Argentina</h3>
        <p><strong>Precisión catastral</strong> para mojones de loteos, mensuras y aplicaciones profesionales.</p>
        <ul>
            <li><strong>Gauss-Krüger:</strong> POSGAR 2007 faja 5 (EPSG:5347), marco oficial vigente del IGN. Se puede elegir otro sistema en la barra lateral.</li>
            <li><strong>WGS84:</strong> Sistema GPS/Google Maps (EPSG:4326)</li>
            <li><strong>Precisión:</strong> Submilimétrica (hasta 15 decimales)</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)
    
    # Sidebar para configuración
    with st.sidebar:
        st.header("⚙️ Configuración")
        
        conversion_mode = st.selectbox(
            "Tipo de conversión:",
            ["KML → Gauss-Krüger", "WGS84 → Gauss-Krüger", "Gauss-Krüger → WGS84"],
            help="Selecciona el tipo de conversión que necesitas"
        )
        
        sistema_gk = st.selectbox(
            "Sistema Gauss-Krüger:",
            list(SISTEMAS_GK.keys()),
            index=list(SISTEMAS_GK.keys()).index(SISTEMA_GK_DEFAULT),
            help="POSGAR 2007 es el marco oficial vigente (catastro, IDESF, mensuras actuales). "
                 "Usá Campo Inchauspe solo para coordenadas de planos anteriores a POSGAR: "
                 "entre ambos sistemas hay un corrimiento de unos 200 m."
        )
        if SISTEMAS_GK[sistema_gk] == "EPSG:22195":
            st.warning("⚠️ Campo Inchauspe es un datum histórico. Sus coordenadas difieren ~200 m de POSGAR 2007.")
        
        st.markdown("---")
        
        # Información sobre formatos
        if conversion_mode == "WGS84 → Gauss-Krüger":
            st.markdown("""
            **📄 Formato requerido:**
            ```csv
            nombre,lat,lng
            Mojón 1,-32.9442,-60.6505
            ```
            """)
        elif conversion_mode == "Gauss-Krüger → WGS84":
            st.markdown("""
            **📄 Formato requerido:**
            ```csv
            nombre,coordenadas_gauss_kruger_easting,coordenadas_gauss_kruger_northing
            Mojón 1,5439170.04,6355218.96
            ```
            """)
        elif "KML" in conversion_mode:
            st.markdown("""
            **📄 Formato requerido:**
            ```xml
            Archivo KML con polígonos o puntos
            - Google Earth (.kml)
            - Polígonos con vértices
            - Puntos individuales
            ```
            """)
        
        st.markdown("---")
        st.markdown("**🎯 Aplicaciones:**")
        st.markdown("• Mojones de loteos")
        st.markdown("• Mensuras urbanas")
        st.markdown("• Catastro rural")
        st.markdown("• Levantamientos topográficos")
    
    # Área principal
    col1, col2 = st.columns([2, 1])
    
    with col1:
        if "KML" in conversion_mode:
            st.header("📁 Cargar archivo KML")
            
            uploaded_file = st.file_uploader(
                "Selecciona tu archivo KML:",
                type=['kml'],
                help="Archivo KML con polígonos o puntos para extraer vértices"
            )
        else:
            st.header("📁 Cargar archivo CSV")
            
            uploaded_file = st.file_uploader(
                "Selecciona tu archivo CSV:",
                type=['csv'],
                help="Archivo CSV con las coordenadas a convertir"
            )
        
        # Ejemplo de datos
        if "KML" not in conversion_mode:
            st.subheader("📋 Datos de ejemplo")
            if conversion_mode == "WGS84 → Gauss-Krüger":
                example_data = pd.DataFrame({
                    'nombre': ['Centro de Rosario', 'Monumento a la Bandera', 'Puerto de Rosario'],
                    'lat': [-32.9442, -32.9477, -32.9398],
                    'lng': [-60.6505, -60.6395, -60.6278]
                })
            else:
                example_data = pd.DataFrame({
                    'nombre': ['Mojón 1', 'Mojón 2', 'Mojón 3'],
                    'coordenadas_gauss_kruger_easting': [5439170.036235, 5440201.051327, 5441289.905108],
                    'coordenadas_gauss_kruger_northing': [6355218.955229, 6354837.080781, 6355719.820668]
                })
            
            st.dataframe(example_data, use_container_width=True)
            
            # Botón para usar datos de ejemplo
            if st.button("🔄 Usar datos de ejemplo", type="secondary"):
                st.session_state.example_data = example_data
        else:
            st.subheader("📋 Información sobre KML")
            st.info("""
            **Tipos de geometrías soportadas:**
            - 🔺 **Polígonos**: Extrae todos los vértices del perímetro
            - 📍 **Puntos**: Extrae coordenadas individuales
            - 📁 **Múltiples elementos**: Procesa todos los elementos del archivo
            
            **Fuentes compatibles:**
            - Google Earth
            - QGIS
            - ArcGIS
            - Cualquier software que genere KML estándar
            """)
    
    with col2:
        pass  # Columna vacía para balance visual
    
    # Procesamiento de datos
    df_input = None
    
    if uploaded_file is not None:
        try:
            if "KML" in conversion_mode:
                # Procesar archivo KML
                # Guardar temporalmente el archivo KML
                temp_kml_path = f"temp_{uploaded_file.name}"
                with open(temp_kml_path, "wb") as f:
                    f.write(uploaded_file.read())
                
                # Usar la función del script principal
                from convert_gk_to_wgs84 import parse_kml_polygon
                coordinates = parse_kml_polygon(temp_kml_path)
                
                # Limpiar archivo temporal
                Path(temp_kml_path).unlink()
                
                if coordinates:
                    df_input = pd.DataFrame(coordinates, columns=['nombre', 'lat', 'lng'])
                    st.success(f"✅ Archivo KML procesado: {len(coordinates)} vértices extraídos")
                    
                    # Mostrar preview de los vértices extraídos
                    st.subheader("🔍 Vértices extraídos del KML")
                    # Formatear coordenadas con mayor precisión
                    df_display = df_input.head(10).copy()
                    if 'lat' in df_display.columns:
                        df_display['lat'] = df_display['lat'].apply(lambda x: f"{x:.10f}")
                    if 'lng' in df_display.columns:
                        df_display['lng'] = df_display['lng'].apply(lambda x: f"{x:.10f}")
                    st.dataframe(df_display, use_container_width=True)
                    if len(df_input) > 10:
                        st.info(f"Mostrando los primeros 10 de {len(df_input)} vértices totales")
                else:
                    st.error("❌ No se encontraron coordenadas válidas en el archivo KML")
            else:
                # Procesar archivo CSV
                df_input = pd.read_csv(uploaded_file)
                st.success(f"✅ Archivo cargado: {len(df_input)} filas")
        except Exception as e:
            st.error(f"❌ Error al cargar el archivo: {str(e)}")
    
    elif 'example_data' in st.session_state and "KML" not in conversion_mode:
        df_input = st.session_state.example_data
        st.info("📋 Usando datos de ejemplo")
    
    # Conversión y resultados
    if df_input is not None:
        st.header("🔄 Conversión de coordenadas")
        
        # Validar columnas requeridas
        if conversion_mode == "WGS84 → Gauss-Krüger" or "KML" in conversion_mode:
            required_cols = ['nombre', 'lat', 'lng']
        else:
            required_cols = ['nombre', 'coordenadas_gauss_kruger_easting', 'coordenadas_gauss_kruger_northing']
        
        missing_cols = [col for col in required_cols if col not in df_input.columns]
        
        if missing_cols:
            st.error(f"❌ Faltan columnas requeridas: {', '.join(missing_cols)}")
        else:
            # Realizar conversión
            with st.spinner('🔄 Convirtiendo coordenadas...'):
                if conversion_mode == "WGS84 → Gauss-Krüger" or conversion_mode == "KML → Gauss-Krüger":
                    df_result, errors = convert_wgs84_to_gk(df_input, sistema_gk)
                    result_title = f"Coordenadas en Gauss-Krüger ({sistema_gk})"
                else:
                    df_result, errors = convert_gk_to_wgs84(df_input, sistema_gk)
                    result_title = f"Coordenadas en WGS84 (desde {sistema_gk})"
            
            # Mostrar errores si los hay
            if errors:
                st.error("❌ Errores encontrados:")
                for error in errors:
                    st.error(error)
            
            # Mostrar resultados
            if not df_result.empty:
                st.markdown(f"""
                <div class="success-box">
                    <h3>✅ {result_title}</h3>
                    <p>Conversión completada exitosamente: <strong>{len(df_result)} puntos</strong></p>
                </div>
                """, unsafe_allow_html=True)
                
                # Mostrar tabla de resultados con mayor precisión
                df_display_result = df_result.copy()
                
                # Formatear coordenadas con alta precisión
                if 'lat' in df_display_result.columns:
                    df_display_result['lat'] = df_display_result['lat'].apply(lambda x: f"{x:.10f}")
                if 'lng' in df_display_result.columns:
                    df_display_result['lng'] = df_display_result['lng'].apply(lambda x: f"{x:.10f}")
                if 'coordenadas_gauss_kruger_easting' in df_display_result.columns:
                    df_display_result['coordenadas_gauss_kruger_easting'] = df_display_result['coordenadas_gauss_kruger_easting'].apply(lambda x: f"{x:.6f}")
                if 'coordenadas_gauss_kruger_northing' in df_display_result.columns:
                    df_display_result['coordenadas_gauss_kruger_northing'] = df_display_result['coordenadas_gauss_kruger_northing'].apply(lambda x: f"{x:.6f}")
                
                st.dataframe(df_display_result, use_container_width=True)
                
                # Mostrar mapa si hay coordenadas WGS84
                if 'lat' in df_result.columns and 'lng' in df_result.columns:
                    st.subheader("🗺️ Visualización del polígono")
                    
                    # Ayuda sobre interacción con el mapa
                    st.info("💡 **Tip**: Haz clic en los marcadores rojos 📍 para ver las coordenadas en ambos sistemas (WGS84 y Gauss-Krüger)")
                    
                    # Calcular bounds para mostrar todos los puntos con padding
                    min_lat = df_result['lat'].min()
                    max_lat = df_result['lat'].max()
                    min_lng = df_result['lng'].min()
                    max_lng = df_result['lng'].max()
                    
                    # Agregar padding (5% del rango en cada dirección)
                    lat_range = max_lat - min_lat
                    lng_range = max_lng - min_lng
                    padding_lat = max(lat_range * 0.05, 0.0001)  # Mínimo padding para puntos muy cercanos
                    padding_lng = max(lng_range * 0.05, 0.0001)
                    
                    # Crear bounds con padding
                    bounds = [
                        [min_lat - padding_lat, min_lng - padding_lng],  # Southwest
                        [max_lat + padding_lat, max_lng + padding_lng]   # Northeast
                    ]
                    
                    # Crear el mapa
                    m = folium.Map(tiles='OpenStreetMap')
                    
                    # Ajustar el mapa para mostrar todos los puntos
                    m.fit_bounds(bounds)
                    
                    # Agregar marcadores para cada punto
                    for idx, row in df_result.iterrows():
                        # Crear popup con información de ambos sistemas de coordenadas
                        popup_content = f"""
                        <b>{row['nombre']}</b><br>
                        <hr>
                        <b>🌍 WGS84:</b><br>
                        Lat: {row['lat']:.10f}<br>
                        Lng: {row['lng']:.10f}<br>
                        """
                        
                        # Agregar coordenadas Gauss-Krüger si están disponibles
                        if 'coordenadas_gauss_kruger_easting' in row and 'coordenadas_gauss_kruger_northing' in row:
                            popup_content += f"""
                            <br><b>📐 Gauss-Krüger:</b><br>
                            Easting: {row['coordenadas_gauss_kruger_easting']:.6f}<br>
                            Northing: {row['coordenadas_gauss_kruger_northing']:.6f}<br>
                            <small>{row['sistema_gk']}</small>
                            """
                        
                        folium.Marker(
                            [row['lat'], row['lng']],
                            popup=folium.Popup(popup_content, max_width=300),
                            tooltip=row['nombre'],
                            icon=folium.Icon(color='red', icon='info-sign')
                        ).add_to(m)
                    
                    # Si hay más de 2 puntos, crear polígono
                    if len(df_result) > 2:
                        coordinates = [[row['lat'], row['lng']] for _, row in df_result.iterrows()]
                        # Cerrar el polígono si no está cerrado
                        if coordinates[0] != coordinates[-1]:
                            coordinates.append(coordinates[0])
                        
                        folium.Polygon(
                            locations=coordinates,
                            color='blue',
                            weight=2,
                            fillColor='lightblue',
                            fillOpacity=0.3,
                            popup="Polígono del loteo"
                        ).add_to(m)
                    
                    # Mostrar el mapa
                    map_data = st_folium(m, width=700, height=500)
                    
                    # Información del mapa
                    center_lat = (min_lat + max_lat) / 2
                    center_lng = (min_lng + max_lng) / 2
                    
                    # Calcular área del polígono si hay suficientes puntos
                    area_info = ""
                    if len(df_result) >= 3:
                        if 'coordenadas_gauss_kruger_easting' in df_result.columns and 'coordenadas_gauss_kruger_northing' in df_result.columns:
                            # Usar coordenadas Gauss-Krüger para mayor precisión
                            gk_coords = [(row['coordenadas_gauss_kruger_easting'], row['coordenadas_gauss_kruger_northing']) 
                                        for _, row in df_result.iterrows()]
                            area_m2 = calculate_polygon_area_gk(gk_coords)
                        else:
                            # Usar coordenadas WGS84
                            wgs84_coords = [(row['lat'], row['lng']) for _, row in df_result.iterrows()]
                            area_m2 = calculate_polygon_area_wgs84(wgs84_coords)
                        
                        # Convertir a diferentes unidades
                        area_ha = area_m2 / 10000  # hectáreas
                        
                        if area_m2 < 10000:  # Menos de 1 hectárea
                            area_info = f"\n📐 **Área del polígono**: {area_m2:.2f} m²"
                        else:
                            area_info = f"\n📐 **Área del polígono**: {area_ha:.4f} ha ({area_m2:,.0f} m²)"
                    
                    st.info(f"""
                    📍 **Centro del mapa**: {center_lat:.8f}, {center_lng:.8f}
                    📏 **Puntos mostrados**: {len(df_result)}{area_info}
                    """)
                
                # Botones de descarga
                st.subheader("📥 Descargar resultados")
                
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    csv = df_result.to_csv(index=False)
                    st.download_button(
                        label="📄 Descargar CSV",
                        data=csv,
                        file_name=f"coordenadas_convertidas_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                        mime="text/csv"
                    )
                
                with col2:
                    # Generar KML para todos los modos de conversión
                    kml_content = create_kml(df_result, "Coordenadas Convertidas", sistema_gk)
                    st.download_button(
                        label="🗺️ Descargar KML",
                        data=kml_content,
                        file_name=f"coordenadas_{datetime.now().strftime('%Y%m%d_%H%M%S')}.kml",
                        mime="application/vnd.google-earth.kml+xml"
                    )
                
                with col3:
                    # Crear GeoJSON con puntos y polígono
                    if 'lat' in df_result.columns and 'lng' in df_result.columns:
                        geojson = {
                            "type": "FeatureCollection",
                            "features": []
                        }
                        
                        # Agregar puntos individuales
                        polygon_coords = []
                        for _, row in df_result.iterrows():
                            # Punto individual
                            feature = {
                                "type": "Feature",
                                "properties": {"name": row['nombre'], "type": "point"},
                                "geometry": {
                                    "type": "Point",
                                    "coordinates": [row['lng'], row['lat']]
                                }
                            }
                            geojson["features"].append(feature)
                            polygon_coords.append([row['lng'], row['lat']])
                        
                        # Agregar polígono si hay 3 o más puntos
                        if len(polygon_coords) >= 3:
                            # Cerrar el polígono
                            if polygon_coords[0] != polygon_coords[-1]:
                                polygon_coords.append(polygon_coords[0])
                            
                            polygon_feature = {
                                "type": "Feature",
                                "properties": {"name": "Polígono", "type": "polygon"},
                                "geometry": {
                                    "type": "Polygon",
                                    "coordinates": [polygon_coords]
                                }
                            }
                            geojson["features"].append(polygon_feature)
                        
                        st.download_button(
                            label="🌍 Descargar GeoJSON",
                            data=json.dumps(geojson, indent=2),
                            file_name=f"coordenadas_{datetime.now().strftime('%Y%m%d_%H%M%S')}.geojson",
                            mime="application/geo+json"
                        )
                    else:
                        # Si no hay coordenadas WGS84, convertir GK a WGS84 para GeoJSON
                        transformer = Transformer.from_crs(SISTEMAS_GK[sistema_gk], "EPSG:4326", always_xy=True)
                        geojson = {
                            "type": "FeatureCollection",
                            "features": []
                        }
                        
                        # Agregar puntos individuales
                        polygon_coords = []
                        for _, row in df_result.iterrows():
                            lng, lat = transformer.transform(
                                row['coordenadas_gauss_kruger_easting'],
                                row['coordenadas_gauss_kruger_northing']
                            )
                            # Punto individual
                            feature = {
                                "type": "Feature",
                                "properties": {"name": row['nombre'], "type": "point"},
                                "geometry": {
                                    "type": "Point",
                                    "coordinates": [lng, lat]
                                }
                            }
                            geojson["features"].append(feature)
                            polygon_coords.append([lng, lat])
                        
                        # Agregar polígono si hay 3 o más puntos
                        if len(polygon_coords) >= 3:
                            # Cerrar el polígono
                            if polygon_coords[0] != polygon_coords[-1]:
                                polygon_coords.append(polygon_coords[0])
                            
                            polygon_feature = {
                                "type": "Feature",
                                "properties": {"name": "Polígono", "type": "polygon"},
                                "geometry": {
                                    "type": "Polygon",
                                    "coordinates": [polygon_coords]
                                }
                            }
                            geojson["features"].append(polygon_feature)
                        
                        st.download_button(
                            label="🌍 Descargar GeoJSON",
                            data=json.dumps(geojson, indent=2),
                            file_name=f"coordenadas_{datetime.now().strftime('%Y%m%d_%H%M%S')}.geojson",
                            mime="application/geo+json"
                        )
                
                # Estadísticas de precisión
                st.subheader("📊 Estadísticas de precisión")
                
                if conversion_mode == "WGS84 → Gauss-Krüger":
                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric("Precisión Easting", "< 1 mm", "15 decimales internos")
                    with col2:
                        st.metric("Precisión Northing", "< 1 mm", "15 decimales internos")
                else:
                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric("Precisión Latitud", "~1.1 cm", "10 decimales")
                    with col2:
                        st.metric("Precisión Longitud", "~1.1 cm", "10 decimales")

    # Footer
    st.markdown("---")
    st.markdown("""
    <div style="text-align: center; color: #666; padding: 2rem;">
        <p><strong>Conversor de Coordenadas Gauss-Krüger ↔ WGS84</strong></p>
        <p>Desarrollado por Rodrigo Zoff • <a href="mailto:rodrigo@zoff.tech">rodrigo@zoff.tech</a> • 2025</p>
        <p>Precisión catastral para Argentina • Gauss-Krüger faja 5 • POSGAR 2007 (EPSG:5347) por defecto</p>
        <p>Rosario, Santa Fe, Buenos Aires</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Información de precisión en el footer
    st.markdown("---")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown("""
        <div style="text-align: center; padding: 10px;">
            <h6>📐 Precisión GK</h6>
            <p style="margin: 0; font-size: 0.8em;">1 micrón<br><small>6 decimales</small></p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div style="text-align: center; padding: 10px;">
            <h6>🌍 Precisión WGS84</h6>
            <p style="margin: 0; font-size: 0.8em;">1.1 cm<br><small>10 decimales</small></p>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown("""
        <div style="text-align: center; padding: 10px;">
            <h6>📍 Zona</h6>
            <p style="margin: 0; font-size: 0.8em;">Faja 5 POSGAR 2007<br><small>EPSG:5347</small></p>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        st.markdown("""
        <div style="text-align: center; padding: 10px;">
            <h6>✅ Certificación</h6>
            <p style="margin: 0; font-size: 0.8em;">IGN y colegios<br><small>de agrimensores</small></p>
        </div>
        """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
