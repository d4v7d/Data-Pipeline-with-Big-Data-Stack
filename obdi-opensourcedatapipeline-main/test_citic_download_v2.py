#!/usr/bin/env python3
"""
Script mejorado para probar descarga usando la URL directa de CITIC
"""

import os
import requests
from urllib.parse import quote

def test_direct_citic_download():
    """Probar descarga usando la URL directa de CITIC"""
    print("🚀 PROBANDO DESCARGA DIRECTA DE CITIC")
    print("=" * 50)
    
    # Crear directorio de descarga
    download_dir = "./test_downloads"
    os.makedirs(download_dir, exist_ok=True)
    
    # URL base del DAV que mencionaste
    base_url = "https://nube.citic.ucr.ac.cr/public.php/dav/files/3CcdjpMxsiYtagr"
    
    # Diferentes rutas a probar
    file_paths = [
        "/1. GOES/Repositorio01/EXIS/SFXR/20230426/OR_EXIS-L1b-SFXR_G18_s20231160000599_e20231160001294_c20231160001297.nc",
        "/1.%20GOES/Repositorio01/EXIS/SFXR/20230426/OR_EXIS-L1b-SFXR_G18_s20231160000599_e20231160001294_c20231160001297.nc",
        "1. GOES/Repositorio01/EXIS/SFXR/20230426/OR_EXIS-L1b-SFXR_G18_s20231160000599_e20231160001294_c20231160001297.nc",
        "1.%20GOES/Repositorio01/EXIS/SFXR/20230426/OR_EXIS-L1b-SFXR_G18_s20231160000599_e20231160001294_c20231160001297.nc",
    ]
    
    for i, file_path in enumerate(file_paths):
        print(f"\n--- Intento {i+1} ---")
        
        # Construir URL completa
        if file_path.startswith('/'):
            full_url = base_url + file_path
        else:
            full_url = base_url + "/" + file_path
            
        print(f"URL: {full_url}")
        
        try:
            # Realizar petición
            response = requests.get(full_url, stream=True, timeout=30)
            
            print(f"Status: {response.status_code}")
            print(f"Content-Length: {response.headers.get('content-length', 'No especificado')}")
            print(f"Content-Type: {response.headers.get('content-type', 'No especificado')}")
            
            if response.status_code == 200:
                # Nombre del archivo local
                filename = "OR_EXIS-L1b-SFXR_G18_s20231160000599_e20231160001294_c20231160001297.nc"
                local_file = os.path.join(download_dir, filename)
                
                # Descargar archivo
                with open(local_file, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                
                # Verificar descarga
                if os.path.exists(local_file):
                    file_size = os.path.getsize(local_file)
                    print(f"✓ Archivo descargado: {file_size / (1024*1024):.2f} MB")
                    
                    if file_size > 0:
                        print(f"🎉 ¡ÉXITO! Archivo real descargado en: {local_file}")
                        
                        # Intentar leer el archivo para verificar que es NetCDF
                        try:
                            with open(local_file, 'rb') as f:
                                header = f.read(8)
                                if header.startswith(b'CDF') or header.startswith(b'\x89HDF'):
                                    print("✓ Archivo parece ser NetCDF válido")
                                else:
                                    print(f"⚠️ Archivo no parece ser NetCDF. Header: {header}")
                        except Exception as e:
                            print(f"⚠️ Error leyendo archivo: {e}")
                        
                        return True, local_file
                    else:
                        print("❌ Archivo descargado pero está vacío")
                        
            else:
                print(f"❌ Error HTTP: {response.status_code}")
                
        except Exception as e:
            print(f"❌ Error en descarga: {e}")
            continue
    
    return False, None

def test_list_directory():
    """Probar listado de directorio usando DAV y extraer nombres de archivos"""
    print("\n🗂️ PROBANDO LISTADO DE DIRECTORIO")
    print("=" * 50)
    
    base_url = "https://nube.citic.ucr.ac.cr/public.php/dav/files/3CcdjpMxsiYtagr"
    
    # Diferentes rutas de directorio a probar
    dir_paths = [
        "/1. GOES/Repositorio01/EXIS/SFXR/20230426",
        "/1.%20GOES/Repositorio01/EXIS/SFXR/20230426",
        "1. GOES/Repositorio01/EXIS/SFXR/20230426",
        "1.%20GOES/Repositorio01/EXIS/SFXR/20230426",
    ]
    
    for i, dir_path in enumerate(dir_paths):
        print(f"\n--- Listando directorio {i+1} ---")
        
        if dir_path.startswith('/'):
            full_url = base_url + dir_path
        else:
            full_url = base_url + "/" + dir_path
            
        print(f"URL: {full_url}")
        
        try:
            # Usar método PROPFIND para listar archivos
            response = requests.request('PROPFIND', full_url, timeout=30)
            
            print(f"Status: {response.status_code}")
            
            if response.status_code == 207:  # Multi-Status para WebDAV
                print("✓ Directorio accesible!")
                
                # Parsear XML para extraer nombres de archivos
                nc_files = extract_nc_files_from_webdav_response(response.text)
                
                if nc_files:
                    print(f"✓ ¡Encontrados {len(nc_files)} archivos .nc!")
                    for j, nc_file in enumerate(nc_files):
                        print(f"  {j+1}. {nc_file}")
                    
                    return True, dir_path, nc_files
                else:
                    print("❌ No se encontraron archivos .nc en la respuesta")
                    print("Contenido XML (muestra):")
                    print(response.text[:1000])
                
        except Exception as e:
            print(f"❌ Error: {e}")
            continue
    
    return False, None, []

def extract_nc_files_from_webdav_response(xml_content):
    """Extraer nombres de archivos .nc del XML de respuesta WebDAV"""
    import re
    
    # Buscar patrones de archivos .nc en el XML
    # Los archivos aparecen en tags como <d:href> o similares
    nc_pattern = r'OR_EXIS-L1b-SFXR_G18_[^<>\s]+\.nc'
    nc_files = re.findall(nc_pattern, xml_content)
    
    # Eliminar duplicados y ordenar
    nc_files = sorted(list(set(nc_files)))
    
    return nc_files

def download_multiple_files(base_url, dir_path, nc_files, max_files=5):
    """Descargar múltiples archivos .nc de un directorio"""
    print(f"\n📥 DESCARGANDO MÚLTIPLES ARCHIVOS")
    print("=" * 50)
    
    # Crear directorio de descarga
    download_dir = "./test_downloads"
    os.makedirs(download_dir, exist_ok=True)
    
    downloaded_files = []
    total_size = 0
    
    # Limitar número de archivos para pruebas
    files_to_download = nc_files[:max_files]
    
    print(f"Descargando {len(files_to_download)} archivos de {len(nc_files)} disponibles...")
    
    for i, filename in enumerate(files_to_download):
        print(f"\n--- Descargando archivo {i+1}/{len(files_to_download)} ---")
        print(f"Archivo: {filename}")
        
        # Construir URL completa del archivo usando el formato que sabemos que funciona
        # Limpiar dir_path
        clean_path = dir_path.replace('%20', ' ')
        if clean_path.startswith('/'):
            clean_path = clean_path[1:]
        
        file_url = f"{base_url}/{clean_path}/{filename}"
        
        print(f"URL: {file_url}")
        
        try:
            # Descargar archivo
            response = requests.get(file_url, stream=True, timeout=60)
            
            print(f"Status: {response.status_code}")
            
            if response.status_code == 200:
                local_file = os.path.join(download_dir, filename)
                
                # Escribir archivo
                with open(local_file, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                
                # Verificar descarga
                if os.path.exists(local_file):
                    file_size = os.path.getsize(local_file)
                    
                    if file_size > 0:
                        size_mb = file_size / (1024 * 1024)
                        total_size += file_size
                        print(f"✓ Descargado: {filename} ({size_mb:.2f} MB)")
                        downloaded_files.append({
                            'filename': filename,
                            'local_path': local_file,
                            'size_bytes': file_size,
                            'size_mb': size_mb
                        })
                        
                        # Verificar que es NetCDF
                        try:
                            with open(local_file, 'rb') as f:
                                header = f.read(8)
                                if header.startswith(b'CDF') or header.startswith(b'\x89HDF'):
                                    print(f"  ✓ NetCDF válido")
                                else:
                                    print(f"  ⚠️ Posible problema con formato NetCDF")
                        except Exception as e:
                            print(f"  ⚠️ Error verificando NetCDF: {e}")
                    else:
                        print(f"✗ Archivo vacío: {filename}")
                else:
                    print(f"✗ No se pudo crear archivo: {filename}")
            else:
                print(f"✗ Error HTTP {response.status_code} para {filename}")
                # Para archivos que no existen, continuar con el siguiente
                if response.status_code == 404:
                    print(f"  (El archivo {filename} no existe en el servidor)")
                
        except Exception as e:
            print(f"✗ Error descargando {filename}: {e}")
            continue
    
    # Resumen
    print(f"\n📊 RESUMEN DE DESCARGA")
    print("=" * 50)
    print(f"Archivos descargados: {len(downloaded_files)}")
    print(f"Tamaño total: {total_size / (1024 * 1024):.2f} MB")
    
    if downloaded_files:
        print("\nArchivos descargados exitosamente:")
        for file_info in downloaded_files:
            print(f"  • {file_info['filename']} ({file_info['size_mb']:.2f} MB)")
    
    return downloaded_files

def get_directory_nc_files(base_url, dir_path):
    """Obtener lista de archivos .nc de un directorio CITIC usando formato de URL simplificado"""
    print(f"\n📁 Obteniendo lista de archivos .nc")
    print(f"Base URL: {base_url}")
    print(f"Directorio: {dir_path}")
    
    # Construir URL usando el formato que sabemos que funciona
    if "?dir=" in base_url:
        # Ya tiene formato query parameter
        full_url = f"{base_url}{dir_path}"
    else:
        # Agregar formato query parameter
        full_url = f"{base_url}?dir={dir_path}"
    
    print(f"URL completa: {full_url}")
    
    try:
        # Intentar obtener el contenido del directorio
        response = requests.get(full_url, timeout=30)
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            # Buscar archivos .nc en el HTML/contenido de respuesta
            content = response.text
            
            # Mostrar una muestra del contenido para debugging
            print(f"Contenido de respuesta (muestra): {content[:500]}")
            
            # Buscar patrones de archivos GOES .nc en el contenido
            import re
            
            # Varios patrones para buscar archivos .nc
            patterns = [
                r'OR_EXIS-L1b-SFXR_G18_s\d{13}_e\d{13}_c\d{13}\.nc',  # Patrón específico GOES
                r'OR_EXIS[^"<>\s]*\.nc',  # Patrón más amplio para GOES
                r'[\w\-_]+\.nc',  # Patrón genérico para archivos .nc
                r'href="([^"]*\.nc)"',  # Archivos .nc en enlaces href
                r'>([^<]*\.nc)<',  # Archivos .nc entre tags
            ]
            
            nc_files = []
            for pattern in patterns:
                matches = re.findall(pattern, content, re.IGNORECASE)
                if matches:
                    print(f"✓ Patrón '{pattern}' encontró {len(matches)} archivos")
                    nc_files.extend(matches)
                    break  # Usar el primer patrón que encuentre archivos
            
            # Limpiar nombres de archivos (remover rutas si las hay)
            cleaned_files = []
            for f in nc_files:
                # Extraer solo el nombre del archivo si viene con ruta
                if '/' in f:
                    filename = f.split('/')[-1]
                else:
                    filename = f
                
                # Verificar que termine en .nc
                if filename.lower().endswith('.nc'):
                    cleaned_files.append(filename)
            
            # Eliminar duplicados y ordenar
            nc_files = sorted(list(set(cleaned_files)))
            
            print(f"✓ Encontrados {len(nc_files)} archivos .nc únicos")
            
            # Mostrar algunos archivos encontrados
            if nc_files:
                print("Archivos encontrados:")
                for i, f in enumerate(nc_files[:3]):
                    print(f"  {i+1}. {f}")
                if len(nc_files) > 3:
                    print(f"  ... y {len(nc_files) - 3} más")
            
            return nc_files
        else:
            print(f"❌ Error HTTP {response.status_code}")
            print(f"Contenido de respuesta (muestra): {response.text[:500]}")
            
    except Exception as e:
        print(f"❌ Error obteniendo directorio: {e}")
        import traceback
        traceback.print_exc()
    
    return []

def get_directory_nc_files_webdav(base_url, dir_path):
    """Obtener lista de archivos .nc usando WebDAV PROPFIND"""
    print(f"\n📁 Obteniendo lista de archivos .nc vía WebDAV")
    
    # Convertir a URL de WebDAV
    webdav_base = "https://nube.citic.ucr.ac.cr/public.php/dav/files/3CcdjpMxsiYtagr"
    
    # Limpiar el dir_path para WebDAV
    clean_path = dir_path
    if clean_path.startswith('/'):
        clean_path = clean_path[1:]
    
    # Decodificar URL encoding si es necesario
    clean_path = clean_path.replace('%20', ' ')
    
    webdav_url = f"{webdav_base}/{clean_path}"
    
    print(f"WebDAV URL: {webdav_url}")
    
    try:
        # Usar PROPFIND para listar contenido del directorio
        headers = {
            'Depth': '1',
            'Content-Type': 'application/xml; charset=utf-8'
        }
        
        # XML body para PROPFIND
        propfind_body = '''<?xml version="1.0"?>
        <d:propfind xmlns:d="DAV:">
            <d:prop>
                <d:displayname/>
                <d:getcontentlength/>
                <d:getcontenttype/>
                <d:resourcetype/>
            </d:prop>
        </d:propfind>'''
        
        response = requests.request('PROPFIND', webdav_url, 
                                  headers=headers, 
                                  data=propfind_body, 
                                  timeout=30)
        
        print(f"Status: {response.status_code}")
        
        if response.status_code == 207:  # Multi-Status
            print("✓ WebDAV PROPFIND exitoso")
            
            # Parsear XML para encontrar archivos .nc
            import xml.etree.ElementTree as ET
            
            try:
                root = ET.fromstring(response.text)
                nc_files = []
                
                # Buscar elementos de respuesta
                for response_elem in root.findall('.//{DAV:}response'):
                    href_elem = response_elem.find('.//{DAV:}href')
                    if href_elem is not None:
                        href = href_elem.text
                        
                        # Extraer nombre de archivo de la URL
                        if href and href.endswith('.nc'):
                            filename = href.split('/')[-1]
                            # Decodificar URL si es necesario
                            from urllib.parse import unquote
                            filename = unquote(filename)
                            nc_files.append(filename)
                
                # Eliminar duplicados y ordenar
                nc_files = sorted(list(set(nc_files)))
                
                print(f"✓ Encontrados {len(nc_files)} archivos .nc vía WebDAV")
                
                if nc_files:
                    print("Archivos encontrados:")
                    for i, f in enumerate(nc_files[:5]):
                        print(f"  {i+1}. {f}")
                    if len(nc_files) > 5:
                        print(f"  ... y {len(nc_files) - 5} más")
                
                return nc_files
                
            except ET.ParseError as e:
                print(f"❌ Error parseando XML: {e}")
                print(f"XML Response (muestra): {response.text[:1000]}")
        else:
            print(f"❌ Error WebDAV: {response.status_code}")
            print(f"Response: {response.text[:500]}")
            
    except Exception as e:
        print(f"❌ Error en WebDAV PROPFIND: {e}")
        import traceback
        traceback.print_exc()
    
    return []

def test_directory_download():
    """Probar descarga de múltiples archivos de un directorio CITIC"""
    print(f"\n🗂️ PROBANDO DESCARGA DE DIRECTORIO COMPLETO")
    print("=" * 50)
    
    # Usar el formato de URL que sabemos que funciona
    base_url = "https://nube.citic.ucr.ac.cr/index.php/s/3CcdjpMxsiYtagr"
    dir_path = "/1.%20GOES/Repositorio01/EXIS/SFXR/20230426"
    
    print(f"Directorio objetivo: {dir_path}")
    
    # Intentar primero con WebDAV
    print("\n--- Intentando con WebDAV ---")
    nc_files = get_directory_nc_files_webdav(base_url, dir_path)
    
    # Si WebDAV no funciona, intentar con HTML parsing
    if not nc_files:
        print("\n--- Intentando con HTML parsing ---")
        nc_files = get_directory_nc_files(base_url, dir_path)
    
    # Si aún no tenemos archivos, crear una lista manual basada en patrones conocidos
    if not nc_files:
        print("\n--- Generando lista manual basada en patrones conocidos ---")
        # Basándonos en el archivo que sabemos que existe
        base_filename = "OR_EXIS-L1b-SFXR_G18_s20231160000599_e20231160001294_c20231160001297.nc"
        
        # Generar algunos nombres de archivos probables para el mismo día
        nc_files = [
            "OR_EXIS-L1b-SFXR_G18_s20231160000599_e20231160001294_c20231160001297.nc",
            "OR_EXIS-L1b-SFXR_G18_s20231160001299_e20231160001994_c20231160001997.nc",
            "OR_EXIS-L1b-SFXR_G18_s20231160001999_e20231160002694_c20231160002697.nc",
            "OR_EXIS-L1b-SFXR_G18_s20231160002699_e20231160003394_c20231160003397.nc",
            "OR_EXIS-L1b-SFXR_G18_s20231160003399_e20231160004094_c20231160004097.nc",
        ]
        print(f"⚠️ Usando lista manual de {len(nc_files)} archivos probables")
    
    if nc_files:
        print(f"\n✓ Trabajando con {len(nc_files)} archivos .nc:")
        
        # Mostrar primeros archivos
        for i, filename in enumerate(nc_files[:3]):
            print(f"  {i+1}. {filename}")
        
        if len(nc_files) > 3:
            print(f"  ... y {len(nc_files) - 3} archivos más")
        
        # Preguntar cuántos descargar
        print(f"\n¿Cuántos archivos desea descargar?")
        print("1 - Descargar 1 archivo (prueba rápida)")
        print("2 - Descargar 2 archivos")  
        print("3 - Descargar 3 archivos")
        print("0 - Solo mostrar lista, no descargar")
        
        try:
            choice = input("\nSeleccione una opción (0-3): ").strip()
            
            download_count = 0
            if choice == "1":
                download_count = 1
            elif choice == "2":
                download_count = 2
            elif choice == "3":
                download_count = 3
            
            if download_count > 0:
                print(f"\n🚀 Iniciando descarga de {download_count} archivo(s)...")
                
                # Usar el formato de descarga directa que sabemos que funciona
                download_base_url = "https://nube.citic.ucr.ac.cr/public.php/dav/files/3CcdjpMxsiYtagr"
                
                downloaded_files = download_multiple_files(download_base_url, dir_path, nc_files, download_count)
                
                if downloaded_files:
                    print(f"\n🎉 ¡Descarga completada exitosamente!")
                    print(f"Descargados {len(downloaded_files)} archivos en ./test_downloads/")
                    
                    # Mostrar estadísticas
                    total_size = sum(f['size_bytes'] for f in downloaded_files)
                    print(f"Tamaño total: {total_size / (1024 * 1024):.2f} MB")
                    
                    return True, downloaded_files
                else:
                    print(f"\n❌ No se pudo descargar ningún archivo")
            else:
                print(f"\n📝 Solo se listaron los archivos")
                return True, []
                
        except KeyboardInterrupt:
            print(f"\n\n⚠️ Operación cancelada por el usuario")
        except Exception as e:
            print(f"\n❌ Error: {e}")
    else:
        print(f"\n❌ No se encontraron archivos .nc en el directorio")
    
    return False, []

def main():
    """Función principal"""
    print("🔍 DIAGNÓSTICO COMPLETO DE DESCARGA CITIC")
    print("=" * 60)
    
    # Probar descarga directa
    print("\n1️⃣ PROBANDO DESCARGA DIRECTA DE ARCHIVO INDIVIDUAL")
    success, file_path = test_direct_citic_download()
    
    if success:
        print(f"\n🎉 ¡PERFECTO! Archivo individual descargado: {file_path}")
    
    # Probar descarga de directorio completo
    print("\n2️⃣ PROBANDO DESCARGA DE DIRECTORIO COMPLETO")
    dir_success, downloaded_files = test_directory_download()
    
    if dir_success and downloaded_files:
        print(f"\n🎉 ¡EXCELENTE! Descarga de directorio exitosa:")
        for file_info in downloaded_files:
            print(f"  ✓ {file_info['filename']} ({file_info['size_mb']:.2f} MB)")
        return True
    elif dir_success:
        print(f"\n✓ Directorio accesible, pero no se descargaron archivos")
    
    # Si llegamos aquí, algo no funcionó completamente
    if success:
        print(f"\n✅ RESULTADO: Descarga individual funciona")
        print("📝 Sugerencia: Usar descarga individual para el DAG")
    else:
        print("\n❌ RESULTADO: Problemas con la descarga")
        print("\nPosibles soluciones:")
        print("1. Verificar conectividad a CITIC")
        print("2. Revisar estructura de directorios")
        print("3. Probar URLs alternativas")
    
    return success

if __name__ == "__main__":
    main()
