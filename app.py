from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory, session
import rasterio
from rasterio.plot import show
import os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import io
import base64
from werkzeug.utils import secure_filename
import uuid
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'una_clave_secreta_predeterminada_muy_insegura') # ¡Cambia esto en producción!
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 32 * 1024 * 1024  # Aumentado para permitir múltiples archivos

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

ALLOWED_EXTENSIONS = {'tif', 'tiff', 'csv', 'txt'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'files[]' not in request.files:
        flash('No se seleccionaron archivos')
        return redirect(url_for('index'))
    
    files = request.files.getlist('files[]')
    if len(files) == 0 or all(file.filename == '' for file in files):
        flash('No se seleccionaron archivos')
        return redirect(url_for('index'))
    
    # Verificar que todos los archivos tengan formatos permitidos
    if not all(allowed_file(file.filename) for file in files):
        flash('Formato de archivo no permitido. Use archivos .tif, .tiff, .csv o .txt')
        return redirect(request.url)
    
    # Crear un ID único para esta sesión de análisis
    session_id = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # Guardar los archivos y procesar cada uno
    filepaths = []
    filenames = []
    
    for file in files:
        filename = secure_filename(file.filename)
        filenames.append(filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        filepaths.append(filepath)
    
    try:
        # Crear un DataFrame para almacenar todos los valores
        combined_df = pd.DataFrame()
        thumbnails = []
        plot_urls = []
        
        # Procesar cada archivo
        for i, filepath in enumerate(filepaths):
            filename = filenames[i]
            
            # Generar miniatura del raster
            plt.figure(figsize=(8, 8))
            with rasterio.open(filepath) as src:
                data = src.read(1)
                # Normalize data for better visualization
                data = np.ma.masked_where(data <= 0, data)
                plt.imshow(data, cmap='terrain')
                plt.colorbar(label='Elevación (m)')
                plt.title(f'Vista del Raster: {filename}')
                
                # Si es el primer archivo, extraer coordenadas X e Y de cada píxel
                if i == 0:
                    # Obtener la transformación afín del raster
                    transform = src.transform
                    
                    # Crear arrays para almacenar coordenadas X e Y
                    height, width = data.shape
                    rows, cols = np.where(~data.mask)
                    
                    # Calcular coordenadas del centro de cada píxel
                    x_coords = []
                    y_coords = []
                    
                    for row, col in zip(rows, cols):
                        # Transformar índices de píxel a coordenadas geográficas (centro del píxel)
                        x, y = transform * (col + 0.5, row + 0.5)
                        x_coords.append(x)
                        y_coords.append(y)
            
            thumbnail = io.BytesIO()
            plt.savefig(thumbnail, format='png', bbox_inches='tight', dpi=300)
            plt.close()
            thumbnail_url = base64.b64encode(thumbnail.getvalue()).decode()
            thumbnails.append(thumbnail_url)
            
            # Procesar datos del raster
            elevations = data.compressed()  # Get only valid data
            
            # Añadir al DataFrame combinado
            # Usar el nombre completo del archivo como nombre de columna
            column_name = filename
            combined_df[column_name] = pd.Series(elevations)
            
            # Si es el primer archivo, añadir las coordenadas X e Y al DataFrame
            if i == 0:
                combined_df['X'] = pd.Series(x_coords)
                combined_df['Y'] = pd.Series(y_coords)
            
            # Crear histograma individual
            plt.figure(figsize=(10, 6))
            plt.hist(elevations, bins=100)
            plt.title(f'Histograma de valores: {filename}')
            plt.xlabel('Elevación (m)')
            plt.ylabel('Frecuencia')
            
            img = io.BytesIO()
            plt.savefig(img, format='png')
            img.seek(0)
            plot_url = base64.b64encode(img.getvalue()).decode('utf8')
            plt.close()
            plot_urls.append(plot_url)
        
        # Añadir identificador por fila al DataFrame
        combined_df.insert(0, 'ID', range(1, len(combined_df) + 1))

        # Reordenar las columnas para que X e Y estén después de ID
        if 'X' in combined_df.columns and 'Y' in combined_df.columns:
            elevation_cols = [col for col in combined_df.columns if col not in ['ID', 'X', 'Y']]
            new_order = ['ID', 'X', 'Y'] + elevation_cols
            combined_df = combined_df[new_order]
        
        # Ya no generamos el gráfico comparativo
        comparison_url = None
        
        # Guardar CSV con todos los datos incluyendo el identificador y el orden correcto
        csv_path = os.path.join(app.config['UPLOAD_FOLDER'], f'elevaciones_{session_id}.csv')
        combined_df.to_csv(csv_path, index=False)
        
        return render_template('result.html', 
                            thumbnails=thumbnails,
                            plot_urls=plot_urls,
                            comparison_url=comparison_url,
                            filenames=filenames,
                            csv_filename=f'elevaciones_{session_id}.csv')
            
    except Exception as e:
        flash(f'Error al procesar los archivos: {str(e)}')
        return redirect(url_for('index'))

@app.route('/downloads/<filename>')
def download_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# El bloque if __name__ == '__main__': se elimina para producción.
# Usa un servidor WSGI como Waitress o Gunicorn para ejecutar la aplicación.
