#!/usr/bin/env python3
"""
Script independiente para probar la descarga de archivos GOES desde CITIC
Este script nos ayudará a debuggear la conexión WebDAV antes de usar en el DAG
"""

import os
import requests
from urllib.parse import quote, unquote

def test_webdav_connection():
    """Probar conexión WebDAV con CITIC"""
    try:
        from webdav3.client import Client as WebDAVClient
        print("✓ webdavclient3 está disponible")
        
        # Configuración WebDAV para CITIC Nextcloud
        webdav_options = {
            'webdav_hostname': 'https://nube.citic.ucr.ac.cr/public.php/webdav',
            'webdav_login': '3CcdjpMxsiYtagr',  # Share token como usuario
            'webdav_password': ''  # Sin contraseña para share público
        }
        
        client = WebDAVClient(webdav_options)
        
        # Probar conexión básica
        print("Probando conexión WebDAV...")
        
        # Diferentes rutas que podemos probar
        test_paths = [
            "/",
            "/1. GOES",
            "/1.%20GOES",
            "/1. GOES/Repositorio01",
            "/1. GOES/Repositorio01/EXIS",
            "/1. GOES/Repositorio01/EXIS/SFXR",
            "/1. GOES/Repositorio01/EXIS/SFXR/20230426"
        ]
        
        for path in test_paths:
            try:
                print(f"\n--- Probando ruta: {path} ---")
                files = client.list(path)
                print(f"✓ Éxito! Encontrados {len(files)} elementos:")
                
                # Mostrar algunos archivos
                for i, file in enumerate(files[:5]):  # Solo los primeros 5
                    print(f"  - {file}")
                
                if len(files) > 5:
                    print(f"  ... y {len(files) - 5} más")
                
                # Si encontramos archivos .nc, intentar descargar uno
                nc_files = [f for f in files if f.endswith('.nc')]
                if nc_files:
                    print(f"\n✓ Encontrados {len(nc_files)} archivos .nc")
                    return path, nc_files[0]  # Retornar ruta exitosa y primer archivo
                    
            except Exception as e:
                print(f"✗ Error en ruta {path}: {e}")
                continue
        
        return None, None
        
    except ImportError:
        print("✗ webdavclient3 no está instalado")
        return None, None

def test_direct_download(file_path, file_name, local_dir="./test_downloads"):
    """Probar descarga directa de un archivo específico"""
    print(f"\n=== Probando descarga directa ===")
    print(f"Archivo: {file_name}")
    print(f"Ruta: {file_path}")
    
    # Crear directorio local
    os.makedirs(local_dir, exist_ok=True)
    
    try:
        from webdav3.client import Client as WebDAVClient
        
        webdav_options = {
            'webdav_hostname': 'https://nube.citic.ucr.ac.cr/public.php/webdav',
            'webdav_login': '3CcdjpMxsiYtagr',
            'webdav_password': ''
        }
        
        client = WebDAVClient(webdav_options)
        
        # Ruta completa del archivo remoto
        remote_file = f"{file_path}/{file_name}"
        local_file = os.path.join(local_dir, file_name)
        
        print(f"Descargando desde: {remote_file}")
        print(f"Guardando en: {local_file}")
        
        # Intentar descarga
        client.download_file(remote_file, local_file)
        
        # Verificar si se descargó correctamente
        if os.path.exists(local_file):
            file_size = os.path.getsize(local_file)
            print(f"✓ ¡Descarga exitosa! Tamaño: {file_size / (1024*1024):.2f} MB")
            return True, local_file
        else:
            print("✗ El archivo no se descargó correctamente")
            return False, None
            
    except Exception as e:
        print(f"✗ Error en descarga: {e}")
        return False, None

def test_http_download():
    """Probar descarga usando HTTP directo (método alternativo)"""
    print(f"\n=== Probando descarga HTTP directa ===")
    
    # Archivo específico que sabemos que existe
    file_name = "OR_EXIS-L1b-SFXR_G18_s20231160000599_e20231160001294_c20231160001297.nc"
    
    # Construir URL según el patrón de Nextcloud
    base_url = "https://nube.citic.ucr.ac.cr/index.php/s/3CcdjpMxsiYtagr/download"
    
    # Diferentes variaciones de la ruta
    path_variations = [
        "/1. GOES/Repositorio01/EXIS/SFXR/20230426",
        "/1.%20GOES/Repositorio01/EXIS/SFXR/20230426",
        "1. GOES/Repositorio01/EXIS/SFXR/20230426",
        "1.%20GOES/Repositorio01/EXIS/SFXR/20230426"
    ]
    
    for path in path_variations:
        try:
            # URL encode del path
            encoded_path = quote(path, safe='/')
            url = f"{base_url}?path={encoded_path}&files={file_name}"
            
            print(f"\nProbando URL: {url}")
            
            response = requests.get(url, stream=True, timeout=30)
            
            print(f"Status code: {response.status_code}")
            print(f"Headers: {dict(response.headers)}")
            
            if response.status_code == 200:
                # Crear directorio de descarga
                os.makedirs("./test_downloads", exist_ok=True)
                local_file = f"./test_downloads/{file_name}"
                
                # Descargar archivo
                with open(local_file, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                
                # Verificar descarga
                if os.path.exists(local_file):
                    file_size = os.path.getsize(local_file)
                    print(f"✓ ¡Descarga HTTP exitosa! Tamaño: {file_size / (1024*1024):.2f} MB")
                    return True, local_file
                    
            else:
                print(f"✗ Falló con status {response.status_code}")
                
        except Exception as e:
            print(f"✗ Error HTTP: {e}")
            continue
    
    return False, None

def test_browse_directory():
    """Probar navegación por directorios para encontrar la estructura correcta"""
    print(f"\n=== Explorando estructura de directorios ===")
    
    try:
        from webdav3.client import Client as WebDAVClient
        
        webdav_options = {
            'webdav_hostname': 'https://nube.citic.ucr.ac.cr/public.php/webdav',
            'webdav_login': '3CcdjpMxsiYtagr',
            'webdav_password': ''
        }
        
        client = WebDAVClient(webdav_options)
        
        def explore_path(path, max_depth=3, current_depth=0):
            if current_depth >= max_depth:
                return
                
            try:
                print(f"{'  ' * current_depth}📁 {path}")
                files = client.list(path)
                
                for file in files[:10]:  # Limitar a 10 para no saturar
                    full_path = f"{path}/{file}".replace("//", "/")
                    
                    if file.endswith('/'):  # Es un directorio
                        if current_depth < max_depth - 1:
                            explore_path(full_path.rstrip('/'), max_depth, current_depth + 1)
                    else:
                        print(f"{'  ' * (current_depth + 1)}📄 {file}")
                        
                        # Si encontramos archivos .nc, mostrar detalles
                        if file.endswith('.nc'):
                            print(f"{'  ' * (current_depth + 2)}🎯 ARCHIVO GOES ENCONTRADO!")
                            return full_path  # Retornar ruta del archivo encontrado
                        
            except Exception as e:
                print(f"{'  ' * current_depth}❌ Error explorando {path}: {e}")
                
        # Empezar exploración desde la raíz
        found_file = explore_path("/", max_depth=4)
        return found_file
        
    except Exception as e:
        print(f"❌ Error en exploración: {e}")
        return None

def main():
    """Función principal para ejecutar todas las pruebas"""
    print("🚀 INICIANDO PRUEBAS DE DESCARGA CITIC")
    print("=" * 50)
    
    # Paso 1: Probar conexión WebDAV
    print("\n1. Probando conexión WebDAV...")
    successful_path, nc_file = test_webdav_connection()
    
    if successful_path and nc_file:
        print(f"\n✓ Conexión exitosa! Encontrado archivo: {nc_file}")
        
        # Paso 2: Probar descarga del archivo encontrado
        print("\n2. Probando descarga del archivo encontrado...")
        success, local_file = test_direct_download(successful_path, nc_file)
        
        if success:
            print(f"✓ ¡Perfecto! Archivo descargado en: {local_file}")
            print("\n🎉 ¡ÉXITO! Podemos descargar archivos de CITIC")
            return True
    
    # Paso 3: Si WebDAV falla, probar HTTP directo
    print("\n3. Probando método HTTP alternativo...")
    success, local_file = test_http_download()
    
    if success:
        print(f"✓ ¡HTTP funcionó! Archivo descargado en: {local_file}")
        print("\n🎉 ¡ÉXITO! Podemos descargar archivos vía HTTP")
        return True
    
    # Paso 4: Explorar estructura de directorios
    print("\n4. Explorando estructura de directorios...")
    found_file = test_browse_directory()
    
    if found_file:
        print(f"✓ Encontrado archivo en: {found_file}")
        return True
    
    print("\n❌ No se pudo establecer conexión con CITIC")
    print("Posibles problemas:")
    print("- Token de acceso incorrecto")
    print("- Estructura de directorios diferente")
    print("- Problema de red o permisos")
    
    return False

if __name__ == "__main__":
    main()
