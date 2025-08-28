#!/bin/bash
# Convert from Gauss-Krüger to WGS84 (Google Maps)
source venv/bin/activate && python -m traductor_coordenadas to_gk --input fede-kml.csv --output resultadoFede