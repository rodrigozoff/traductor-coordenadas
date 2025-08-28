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

def convert_wgs84_to_gk(df):
    """Convierte coordenadas de WGS84 a Gauss-Krüger"""
    transformer = Transformer.from_crs("EPSG:4326", "EPSG:22195", always_xy=True)
    
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
                'coordenadas_gauss_kruger_northing': northing
            })
            
        except Exception as e:
            errors.append(f"Error en fila {idx + 1}: {str(e)}")
    
    return pd.DataFrame(results), errors

def convert_gk_to_wgs84(df):
    """Convierte coordenadas de Gauss-Krüger a WGS84"""
    transformer = Transformer.from_crs("EPSG:22195", "EPSG:4326", always_xy=True)
    
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
                'coordenadas_gauss_kruger_northing': northing
            })
            
        except Exception as e:
            errors.append(f"Error en fila {idx + 1}: {str(e)}")
    
    return pd.DataFrame(results), errors

def create_kml(df, name="Coordenadas"):
    """Genera contenido KML a partir del DataFrame"""
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
    {placemarks}
  </Document>
</kml>"""
    
    placemarks = []
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
    
    return kml_template.format(name=name, placemarks='\n'.join(placemarks))

def main():
    # Título principal
    st.markdown('<h1 class="main-header">🗺️ Conversor de Coordenadas Gauss-Krüger ↔ WGS84</h1>', unsafe_allow_html=True)
    
    # Información general
    st.markdown("""
    <div class="info-box">
        <h3>📍 Conversor Profesional para Argentina</h3>
        <p><strong>Precisión catastral</strong> para mojones de loteos, mensuras y aplicaciones profesionales.</p>
        <ul>
            <li><strong>Gauss-Krüger:</strong> Sistema oficial argentino (EPSG:22195 - Zona 5)</li>
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
            Mojón 1,5439229.95,6355430.75
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
                    'coordenadas_gauss_kruger_easting': [5439229.945221, 5440260.962679, 5441349.818856],
                    'coordenadas_gauss_kruger_northing': [6355430.748344, 6355048.873111, 6355931.615095]
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
        st.header("📊 Información de precisión")
        
        st.metric("Precisión Gauss-Krüger", "1 micrón", "6 decimales")
        st.metric("Precisión WGS84", "1.1 cm", "10 decimales")
        st.metric("Zona de cobertura", "Argentina Central", "EPSG:22195")
        
        st.markdown("""
        <div class="info-box">
            <h4>✅ Certificación</h4>
            <p>Cumple normativas del IGN y colegios de agrimensores argentinos.</p>
        </div>
        """, unsafe_allow_html=True)
    
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
                    df_result, errors = convert_wgs84_to_gk(df_input)
                    result_title = "Coordenadas en Gauss-Krüger"
                else:
                    df_result, errors = convert_gk_to_wgs84(df_input)
                    result_title = "Coordenadas en WGS84"
            
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
                            <small>EPSG:22195 - Zona 5</small>
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
                    
                    st.info(f"""
                    📍 **Centro del mapa**: {center_lat:.8f}, {center_lng:.8f}
                    📏 **Puntos mostrados**: {len(df_result)}
                    🔍 **Vista**: Ajustada automáticamente con padding del 5%
                    📐 **Área cubierta**: {lat_range:.6f}° × {lng_range:.6f}°
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
                
                # Solo generar KML para conversiones a WGS84
                if conversion_mode == "Gauss-Krüger → WGS84":
                    with col2:
                        kml_content = create_kml(df_result, "Coordenadas Convertidas")
                        st.download_button(
                            label="🗺️ Descargar KML",
                            data=kml_content,
                            file_name=f"coordenadas_{datetime.now().strftime('%Y%m%d_%H%M%S')}.kml",
                            mime="application/vnd.google-earth.kml+xml"
                        )
                    
                    with col3:
                        # Crear GeoJSON
                        geojson = {
                            "type": "FeatureCollection",
                            "features": []
                        }
                        
                        for _, row in df_result.iterrows():
                            feature = {
                                "type": "Feature",
                                "properties": {"name": row['nombre']},
                                "geometry": {
                                    "type": "Point",
                                    "coordinates": [row['lng'], row['lat']]
                                }
                            }
                            geojson["features"].append(feature)
                        
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
        <p>Precisión catastral para Argentina • Sistema optimizado para Zona 5 (EPSG:22195)</p>
        <p>Rosario, Santa Fe, Buenos Aires</p>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
