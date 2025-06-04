import cv2 as cv
import glob
import numpy as np
import matplotlib.pyplot as plt
import os

def save_camera_parameters(camera_id, mtx, dist):
    """Guarda los parámetros intrínsecos de la cámara en un archivo .dat"""
    # Crear directorio si no existe
    os.makedirs("camera_parameters", exist_ok=True)
    
    # Guardar matriz de cámara y coeficientes de distorsión
    filename = f"camera_parameters/c{camera_id}.dat"
    with open(filename, 'w') as f:
        f.write(f"{mtx.shape[0]} {mtx.shape[1]}\n")
        for row in mtx:
            f.write(" ".join(map(str, row)) + "\n")
        f.write(f"{len(dist[0])}\n")
        f.write(" ".join(map(str, dist[0])) + "\n")
    
    print(f"Parámetros de cámara {camera_id} guardados en {filename}")
    return filename

def save_rotation_translation(camera_id, R, T):
    """Guarda la matriz de rotación y el vector de traslación en un archivo .dat"""
    # Crear directorio si no existe
    os.makedirs("camera_parameters", exist_ok=True)
    
    filename = f"camera_parameters/rot_trans_c{camera_id}.dat"
    with open(filename, 'w') as f:
        f.write(f"{R.shape[0]} {R.shape[1]}\n")
        for row in R:
            f.write(" ".join(map(str, row)) + "\n")
        f.write(f"{T.shape[0]} {T.shape[1]}\n")
        for i in range(T.shape[0]):
            f.write(str(T[i][0]) + "\n")
    
    print(f"Rotación y traslación para cámara {camera_id} guardadas en {filename}")
    return filename

def evaluate_calibration_quality(mtx, dist, objpoints, imgpoints, rvecs, tvecs, camera_id):
    """Evalúa la calidad de la calibración calculando varias métricas."""
    
    print(f"\n=== EVALUACIÓN DE CALIDAD - CÁMARA {camera_id} ===")
    
    # Error de reproyección por imagen
    reprojection_errors = []
    for i in range(len(objpoints)):
        imgpoints2, _ = cv.projectPoints(objpoints[i], rvecs[i], tvecs[i], mtx, dist)
        error = cv.norm(imgpoints[i], imgpoints2, cv.NORM_L2)/len(imgpoints2)
        reprojection_errors.append(error)
        print(f"Imagen {i+1}: Error = {error:.4f} píxeles")
    
    mean_error = np.mean(reprojection_errors)
    std_error = np.std(reprojection_errors)
    max_error = np.max(reprojection_errors)
    min_error = np.min(reprojection_errors)
    
    print(f"\nEstadísticas de error:")
    print(f"Error promedio: {mean_error:.4f} ± {std_error:.4f} píxeles")
    print(f"Error mínimo: {min_error:.4f} píxeles")
    print(f"Error máximo: {max_error:.4f} píxeles")
    
    # Clasificación de calidad
    if mean_error < 0.5:
        quality = "EXCELENTE"
        color = 'green'
    elif mean_error < 1.0:
        quality = "BUENA"
        color = 'blue'
    elif mean_error < 2.0:
        quality = "ACEPTABLE"
        color = 'orange'
    else:
        quality = "POBRE"
        color = 'red'
    
    print(f"Calidad de calibración: {quality}")
    
    # Visualización de errores
    plt.figure(f'Errores de Reproyección - Cámara {camera_id}', figsize=(12, 8))
    
    # Subplot 1: Histograma de errores
    plt.subplot(2, 2, 1)
    plt.hist(reprojection_errors, bins=10, alpha=0.7, color=color, edgecolor='black')
    plt.axvline(mean_error, color='red', linestyle='--', label=f'Media: {mean_error:.3f}')
    plt.xlabel('Error de reproyección (píxeles)')
    plt.ylabel('Frecuencia')
    plt.title(f'Distribución de Errores - Cámara {camera_id}')
    plt.legend()
    plt.grid(True, alpha=0.3)
    
    # Subplot 2: Errores por imagen
    plt.subplot(2, 2, 2)
    plt.plot(range(1, len(reprojection_errors)+1), reprojection_errors, 'o-', color=color, linewidth=2, markersize=6)
    plt.axhline(mean_error, color='red', linestyle='--', label=f'Media: {mean_error:.3f}')
    plt.axhline(mean_error + std_error, color='orange', linestyle=':', label=f'Media + σ')
    plt.axhline(mean_error - std_error, color='orange', linestyle=':', label=f'Media - σ')
    plt.xlabel('Número de imagen')
    plt.ylabel('Error de reproyección (píxeles)')
    plt.title(f'Error por Imagen - Cámara {camera_id}')
    plt.legend()
    plt.grid(True, alpha=0.3)
    
    # Subplot 3: Box plot
    plt.subplot(2, 2, 3)
    plt.boxplot(reprojection_errors, patch_artist=True, 
                boxprops=dict(facecolor=color, alpha=0.7))
    plt.ylabel('Error de reproyección (píxeles)')
    plt.title(f'Distribución de Errores - Cámara {camera_id}')
    plt.grid(True, alpha=0.3)
    
    # Subplot 4: Métricas de resumen
    plt.subplot(2, 2, 4)
    plt.axis('off')
    metrics_text = f"""
    RESUMEN DE CALIBRACIÓN - CÁMARA {camera_id}
    
    Calidad: {quality}
    
    Error promedio: {mean_error:.4f} px
    Desviación estándar: {std_error:.4f} px
    Error mínimo: {min_error:.4f} px
    Error máximo: {max_error:.4f} px
    
    Número de imágenes: {len(reprojection_errors)}
    
    Parámetros focales:
    fx = {mtx[0,0]:.2f}
    fy = {mtx[1,1]:.2f}
    
    Centro óptico:
    cx = {mtx[0,2]:.2f}
    cy = {mtx[1,2]:.2f}
    """
    plt.text(0.1, 0.9, metrics_text, transform=plt.gca().transAxes, 
             fontsize=10, verticalalignment='top', fontfamily='monospace',
             bbox=dict(boxstyle="round,pad=0.3", facecolor=color, alpha=0.3))
    
    plt.tight_layout()
    plt.show()
    
    return {
        'mean_error': mean_error,
        'std_error': std_error,
        'max_error': max_error,
        'min_error': min_error,
        'quality': quality,
        'errors': reprojection_errors
    }

def calibrate_camera(images_folder, camera_id=0):
    print(f"\nCalibrando cámara {camera_id} con imágenes de: {images_folder}")
    images_names = glob.glob(images_folder)
    print(f"Imágenes encontradas: {len(images_names)}")
    
    images = []
    for imname in images_names:
        im = cv.imread(imname, 1)
        if im is None:
            print(f"Error al cargar imagen: {imname}")
            continue
        images.append(im)
    
    print(f"Imágenes cargadas exitosamente: {len(images)}")

    criteria = (cv.TERM_CRITERIA_EPS + cv.TERM_CRITERIA_MAX_ITER, 30, 0.001)

    rows = 7
    columns = 7
    world_scaling = 1.

    objp = np.zeros((rows*columns,3), np.float32)
    objp[:,:2] = np.mgrid[0:rows,0:columns].T.reshape(-1,2)
    objp = world_scaling* objp

    width = images[0].shape[1]
    height = images[0].shape[0]
    
    print(f"Dimensiones de imagen: {width}x{height}")

    imgpoints = []
    objpoints = []

    for i, frame in enumerate(images):
        gray = cv.cvtColor(frame, cv.COLOR_BGR2GRAY)
        ret, corners = cv.findChessboardCorners(gray, (rows, columns), None)

        if ret == True:
            print(f"Esquinas encontradas en imagen {i+1}")
            conv_size = (11, 11)
            corners = cv.cornerSubPix(gray, corners, conv_size, (-1, -1), criteria)
            
            # Dibujar y mostrar las esquinas
            cv.drawChessboardCorners(frame, (rows, columns), corners, ret)
            cv.imshow(f'Calibracion Camara {camera_id} - Imagen {i+1}', frame)
            cv.waitKey(500)

            objpoints.append(objp)
            imgpoints.append(corners)

    cv.destroyAllWindows()
    
    print(f"Total de imágenes usadas para calibración: {len(objpoints)}")

    if len(objpoints) == 0:
        raise ValueError("No se encontraron esquinas del tablero en ninguna imagen")

    ret, mtx, dist, rvecs, tvecs = cv.calibrateCamera(objpoints, imgpoints, (width, height), None, None)
    
    print(f'\nResultados de calibración - Cámara {camera_id}:')
    print('Error RMS:', ret)
    print('Matriz de cámara:\n', mtx)
    print('Coeficientes de distorsión:', dist)
    
    # Evaluar calidad de calibración con visualización, no se usa el return, pero si se quiere acceder a la variable,
    # se puede
    quality_metrics = evaluate_calibration_quality(mtx, dist, objpoints, imgpoints, rvecs, tvecs, camera_id)
    
    # Guardar parámetros en archivo
    saved_file = save_camera_parameters(camera_id, mtx, dist)
    print(f"Parámetros guardados en: {saved_file}")

    return mtx, dist

def stereo_calibrate(mtx1, dist1, mtx2, dist2, frames_folder):
    print(f"\nIniciando calibración estéreo con imágenes de: {frames_folder}")
    
    images_names = glob.glob(frames_folder)
    images_names = sorted(images_names)
    
    if len(images_names) == 0:
        raise ValueError(f"No se encontraron imágenes en {frames_folder}")
    
    c1_images_names = images_names[:len(images_names)//2]
    c2_images_names = images_names[len(images_names)//2:]
    
    print(f"Pares de imágenes encontrados: {len(c1_images_names)}")

    c1_images = []
    c2_images = []
    for im1, im2 in zip(c1_images_names, c2_images_names):
        _im1 = cv.imread(im1, 1)
        _im2 = cv.imread(im2, 1)
        
        if _im1 is None:
            print(f"Error al cargar imagen de cámara 0: {im1}")
            continue
        if _im2 is None:
            print(f"Error al cargar imagen de cámara 1: {im2}")
            continue
            
        c1_images.append(_im1)
        c2_images.append(_im2)

    print(f"Pares de imágenes cargados exitosamente: {len(c1_images)}")

    criteria = (cv.TERM_CRITERIA_EPS + cv.TERM_CRITERIA_MAX_ITER, 100, 0.0001)

    rows = 7
    columns = 7
    world_scaling = 1.

    objp = np.zeros((rows*columns,3), np.float32)
    objp[:,:2] = np.mgrid[0:rows,0:columns].T.reshape(-1,2)
    objp = world_scaling* objp

    width = c1_images[0].shape[1]
    height = c1_images[0].shape[0]
    
    print(f"Dimensiones de imagen: {width}x{height}")
    print(f"Dimensiones del tablero: {rows}x{columns}")
    print(f"Puntos 3D del tablero: {objp.shape}")

    imgpoints_left = []
    imgpoints_right = []
    objpoints = []

    for i, (frame1, frame2) in enumerate(zip(c1_images, c2_images)):
        print(f"\nProcesando par de imágenes {i+1}")
        
        gray1 = cv.cvtColor(frame1, cv.COLOR_BGR2GRAY)
        gray2 = cv.cvtColor(frame2, cv.COLOR_BGR2GRAY)
        
        # Guardar imágenes en escala de grises para debug
        cv.imwrite(f'debug_gray1_{i}.png', gray1)
        cv.imwrite(f'debug_gray2_{i}.png', gray2)
        
        c_ret1, corners1 = cv.findChessboardCorners(gray1, (rows, columns), None)
        c_ret2, corners2 = cv.findChessboardCorners(gray2, (rows, columns), None)

        if c_ret1 == True and c_ret2 == True:
            print(f"Esquinas encontradas en par de imágenes {i+1}")
            
            corners1 = cv.cornerSubPix(gray1, corners1, (11, 11), (-1, -1), criteria)
            corners2 = cv.cornerSubPix(gray2, corners2, (11, 11), (-1, -1), criteria)

            # Dibujar y mostrar las esquinas
            cv.drawChessboardCorners(frame1, (rows, columns), corners1, c_ret1)
            cv.drawChessboardCorners(frame2, (rows, columns), corners2, c_ret2)
            
            cv.imshow('Camara 1', frame1)
            cv.imshow('Camara 2', frame2)
            cv.waitKey(500)

            objpoints.append(objp)
            imgpoints_left.append(corners1)
            imgpoints_right.append(corners2)
        else:
            print(f"No se encontraron esquinas en par de imágenes {i+1}")

    cv.destroyAllWindows()

    if len(objpoints) == 0:
        raise ValueError("No se encontraron esquinas del tablero en ningún par de imágenes")

    print(f"\nNúmero de pares de imágenes usadas para calibración: {len(objpoints)}")

    stereocalibration_flags = cv.CALIB_FIX_INTRINSIC
    ret, CM1, dist1, CM2, dist2, R, T, E, F = cv.stereoCalibrate(objpoints, imgpoints_left, imgpoints_right, mtx1, dist1,
                                                                 mtx2, dist2, (width, height), criteria = criteria, flags = stereocalibration_flags)

    print("\n=== RESULTADOS CALIBRACIÓN ESTÉREO ===")
    print("Error de reproyección:", ret)
    print("Matriz de rotación:\n", R)
    print("Vector de traslación:\n", T)
    print(f"Matriz esencial:\n{E}")
    print(f"Matriz fundamental:\n{F}")
    
    # Calcular información geométrica adicional
    baseline = np.linalg.norm(T)
    print(f"Línea base (distancia entre cámaras): {baseline:.2f} unidades")
    
    # Ángulo de rotación
    angle = np.arccos((np.trace(R) - 1) / 2) * 180 / np.pi
    print(f"Ángulo de rotación entre cámaras: {angle:.2f} grados")
    
    # Guardar parámetros de rotación y traslación para ambas cámaras
    # Para cámara 0, usamos R=I (identidad) y T=0
    R_identity = np.eye(3, dtype=np.float32)
    T_zero = np.zeros((3, 1), dtype=np.float32)
    
    # Guardar parámetros para cámara 0
    saved_file0 = save_rotation_translation(0, R_identity, T_zero)
    print(f"Parámetros R,T para cámara 0 guardados en: {saved_file0}")
    
    # Guardar parámetros para cámara 1
    saved_file1 = save_rotation_translation(1, R, T)
    print(f"Parámetros R,T para cámara 1 guardados en: {saved_file1}")

    return R, T

def triangulate(mtx1, mtx2, R, T):
    print("\nIniciando triangulación")
    
    # Leer puntos del archivo puntos_uv.txt
    try:
        with open('puntos_uv.txt', 'r') as f:
            # Saltar las líneas de comentarios
            for _ in range(3):
                next(f)
                
            # Leer uvs1
            exec_vars = {}
            exec(''.join(f.readlines()), exec_vars)
            uvs1 = exec_vars['uvs1']
            uvs2 = exec_vars['uvs2']
            
        print("Puntos UV cargados exitosamente del archivo")
        print(f"Número de puntos encontrados: {len(uvs1)}")
        
    except FileNotFoundError:
        print("No se encontró el archivo puntos_uv.txt. Saltando triangulación.")
        return

    uvs1 = np.array(uvs1)
    uvs2 = np.array(uvs2)

    # Cargar imágenes para visualización
    frame1 = cv.imread('testing/T1.jpg')
    frame2 = cv.imread('testing/T2.jpg')
    
    if frame1 is None or frame2 is None:
        print("No se pudieron cargar las imágenes de prueba. Saltando visualización.")
        return

    # Mostrar puntos sobre las imágenes
    plt.figure("Puntos en Cámara 0", figsize=(12, 8))
    plt.imshow(frame1[:,:,[2,1,0]])
    plt.scatter(uvs1[:,0], uvs1[:,1], c='red', s=100, edgecolors='white', linewidths=2)
    for i, (x, y) in enumerate(uvs1):
        plt.annotate(str(i), (x, y), xytext=(5, 5), textcoords='offset points',
                    fontsize=12, color='yellow', weight='bold')
    plt.title('Puntos detectados en Cámara 0', fontsize=14)
    plt.axis('off')
    plt.show()

    plt.figure("Puntos en Cámara 1", figsize=(12, 8))
    plt.imshow(frame2[:,:,[2,1,0]])
    plt.scatter(uvs2[:,0], uvs2[:,1], c='red', s=100, edgecolors='white', linewidths=2)
    for i, (x, y) in enumerate(uvs2):
        plt.annotate(str(i), (x, y), xytext=(5, 5), textcoords='offset points',
                    fontsize=12, color='yellow', weight='bold')
    plt.title('Puntos detectados en Cámara 1', fontsize=14)
    plt.axis('off')
    plt.show()

    RT1 = np.concatenate([np.eye(3), [[0],[0],[0]]], axis = -1)
    P1 = mtx1 @ RT1

    RT2 = np.concatenate([R, T], axis = -1)
    P2 = mtx2 @ RT2

    def DLT(P1, P2, point1, point2):
        """Direct Linear Transform."""
        # Construir la matriz A usando las ecuaciones de proyección
        A = np.zeros((4, 4))
        
        # Ecuaciones para la primera cámara
        A[0] = point1[1] * P1[2] - P1[1]
        A[1] = P1[0] - point1[0] * P1[2]
        
        # Ecuaciones para la segunda cámara
        A[2] = point2[1] * P2[2] - P2[1]
        A[3] = P2[0] - point2[0] * P2[2]
        
        # Resolver el sistema usando SVD
        _, _, Vh = np.linalg.svd(A)
        point_3d = Vh[-1, :3] / Vh[-1, 3]
        
        # Verificar que el punto está delante de ambas cámaras
        if point_3d[2] < 0:
            point_3d = -point_3d
            
        return point_3d

    def verify_triangulation(P1, P2, point_3d, point1, point2, threshold=15):
        """Verifica la calidad de la triangulación usando el error de reproyección con múltiples escalas."""
        # Proyectar punto 3D en ambas cámaras
        point_3d_homog = np.append(point_3d, 1)
        
        # Proyectar en cámara 0
        proj1 = P1 @ point_3d_homog
        proj1 = proj1[:2] / proj1[2]
        
        # Proyectar en cámara 1
        proj2 = P2 @ point_3d_homog
        proj2 = proj2[:2] / proj2[2]
        
        # Calcular errores de reproyección
        error1 = np.linalg.norm(proj1 - point1)
        error2 = np.linalg.norm(proj2 - point2)
        max_error = max(error1, error2)
        
        # Clasificación por escalas múltiples
        if max_error < 1:
            quality = "EXCELENTE (sub-píxel)"
            quality_color = 'green'
            is_valid = True
        elif max_error < 5:
            quality = "MUY BUENA"
            quality_color = 'blue'
            is_valid = True
        elif max_error < 15:
            quality = "ACEPTABLE"
            quality_color = 'orange'
            is_valid = True
        else:
            quality = "POBRE"
            quality_color = 'red'
            is_valid = False
        
        print(f"Errores de reproyección: {error1:.2f}, {error2:.2f} → {quality}")
        return is_valid, quality, quality_color, max_error

    # Triangular todos los puntos
    p3ds = []
    valid_points = []
    triangulation_errors = []
    point_qualities = []
    point_colors = []
    
    for i, (uv1, uv2) in enumerate(zip(uvs1, uvs2)):
        try:
            print(f"\nTriangulando punto {i}...")
            _p3d = DLT(P1, P2, uv1, uv2)
            print(f'Punto triangulado: {_p3d}')
            
            # Verificar calidad con nuevo sistema de escalas
            is_valid, quality, quality_color, max_error = verify_triangulation(P1, P2, _p3d, uv1, uv2)
            
            triangulation_errors.append(max_error)
            point_qualities.append(quality)
            point_colors.append(quality_color)
            
            if is_valid:
                print(f"Punto {i}: {quality}")
                valid_points.append(True)
            else:
                print(f"Punto {i}: {quality} - Rechazado")
                valid_points.append(False)
                
            p3ds.append(_p3d)
            
        except Exception as e:
            print(f"Error triangulando punto {i}: {str(e)}")
            p3ds.append(np.zeros(3))
            valid_points.append(False)
            triangulation_errors.append(np.inf)
            point_qualities.append("ERROR")
            point_colors.append('black')
    
    p3ds = np.array(p3ds)
    valid_points = np.array(valid_points)
    triangulation_errors = np.array(triangulation_errors)

    # Mostrar estadísticas de triangulación mejoradas
    valid_errors = triangulation_errors[triangulation_errors != np.inf]
    if len(valid_errors) > 0:
        print(f"\n=== ESTADÍSTICAS DE TRIANGULACIÓN DETALLADAS ===")
        print(f"Total de puntos: {len(p3ds)}")
        
        # Contar por categorías
        excelente = sum(1 for q in point_qualities if "EXCELENTE" in q)
        muy_buena = sum(1 for q in point_qualities if "MUY BUENA" in q)
        aceptable = sum(1 for q in point_qualities if "ACEPTABLE" in q)
        pobre = sum(1 for q in point_qualities if "POBRE" in q)
        
        print(f"🟢 EXCELENTE (< 1px): {excelente} puntos")
        print(f"🔵 MUY BUENA (1-5px): {muy_buena} puntos")
        print(f"🟠 ACEPTABLE (5-15px): {aceptable} puntos")
        print(f"🔴 POBRE (> 15px): {pobre} puntos")
        print(f"📊 Puntos válidos totales: {excelente + muy_buena + aceptable}/{len(p3ds)}")
        
        print(f"\nError promedio de triangulación: {np.mean(valid_errors):.3f} píxeles")
        print(f"Error máximo: {np.max(valid_errors):.3f} píxeles")
        print(f"Error mínimo: {np.min(valid_errors):.3f} píxeles")

    # =============== ESCALADO Y NORMALIZACIÓN DE PUNTOS 3D ===============
    print(f"\n=== ESCALADO DE PUNTOS 3D ===")
    print(f"Rango original de coordenadas:")
    print(f"X: {p3ds[:,0].min():.2f} - {p3ds[:,0].max():.2f}")
    print(f"Y: {p3ds[:,1].min():.2f} - {p3ds[:,1].max():.2f}")
    print(f"Z: {p3ds[:,2].min():.2f} - {p3ds[:,2].max():.2f}")
    
    # Filtrar puntos válidos para el escalado
    valid_p3ds = p3ds[valid_points] if np.any(valid_points) else p3ds
    
    # Calcular centroide de los puntos válidos
    centroid = np.mean(valid_p3ds, axis=0)
    p3ds_centered = p3ds - centroid
    
    # Calcular el rango máximo para normalizar
    max_range = np.max([
        np.max(valid_p3ds[:,0]) - np.min(valid_p3ds[:,0]),
        np.max(valid_p3ds[:,1]) - np.min(valid_p3ds[:,1]),
        np.max(valid_p3ds[:,2]) - np.min(valid_p3ds[:,2])
    ])
    
    # Factor de escalado para que el objeto tenga un tamaño razonable (2 unidades)
    target_size = 2.0
    scale_factor = target_size / max_range if max_range > 0 else 1.0
    
    # Aplicar escalado
    p3ds_scaled = p3ds_centered * scale_factor
    
    print(f"Centroide original: {centroid}")
    print(f"Factor de escalado aplicado: {scale_factor:.6f}")
    print(f"Rango escalado de coordenadas:")
    print(f"X: {p3ds_scaled[:,0].min():.2f} - {p3ds_scaled[:,0].max():.2f}")
    print(f"Y: {p3ds_scaled[:,1].min():.2f} - {p3ds_scaled[:,1].max():.2f}")
    print(f"Z: {p3ds_scaled[:,2].min():.2f} - {p3ds_scaled[:,2].max():.2f}")

    # Calcular posiciones de cámaras escaladas
    cam1_pos_scaled = -centroid * scale_factor
    R_t = R.T
    cam2_pos_original = -R_t @ T
    cam2_pos_scaled = (cam2_pos_original.flatten() - centroid) * scale_factor

    from mpl_toolkits.mplot3d import Axes3D

    # =============== VISUALIZACIÓN 3D ESCALADA ===============
    fig = plt.figure("Reconstrucción 3D - Escalada", figsize=(15, 10))
    ax = fig.add_subplot(111, projection='3d')
    
    # Configurar límites escalados (alejar la cámara)
    limit = target_size * 1  # Cambiar este valor para alejar más o menos
    ax.set_xlim3d(-limit, limit)
    ax.set_ylim3d(-limit, limit)
    ax.set_zlim3d(-limit, limit)

    # Dibujar puntos escalados con colores según su calidad
    # Separar puntos por categoría de calidad
    excellent_mask = np.array([("EXCELENTE" in q) for q in point_qualities])
    very_good_mask = np.array([("MUY BUENA" in q) for q in point_qualities])
    acceptable_mask = np.array([("ACEPTABLE" in q) for q in point_qualities])
    poor_mask = np.array([("POBRE" in q) for q in point_qualities])
    
    # Dibujar cada categoría con su color
    if np.any(excellent_mask):
        ax.scatter(p3ds_scaled[excellent_mask,0], 
                  p3ds_scaled[excellent_mask,1], 
                  p3ds_scaled[excellent_mask,2],
                  c='green', s=120, marker='o', label='EXCELENTE (<1px)', alpha=0.9)
    
    if np.any(very_good_mask):
        ax.scatter(p3ds_scaled[very_good_mask,0], 
                  p3ds_scaled[very_good_mask,1], 
                  p3ds_scaled[very_good_mask,2],
                  c='blue', s=100, marker='o', label='MUY BUENA (1-5px)', alpha=0.8)
    
    if np.any(acceptable_mask):
        ax.scatter(p3ds_scaled[acceptable_mask,0], 
                  p3ds_scaled[acceptable_mask,1], 
                  p3ds_scaled[acceptable_mask,2],
                  c='orange', s=80, marker='s', label='ACEPTABLE (5-15px)', alpha=0.7)
    
    if np.any(poor_mask):
        ax.scatter(p3ds_scaled[poor_mask,0], 
                  p3ds_scaled[poor_mask,1], 
                  p3ds_scaled[poor_mask,2],
                  c='red', s=100, marker='x', label='POBRE (>15px)', alpha=0.8)

    # Añadir etiquetas a los puntos con colores correspondientes
    for i, (x, y, z) in enumerate(p3ds_scaled):
        if i < len(point_colors):
            color = point_colors[i]
        else:
            color = 'black'
        ax.text(x, y, z, f' {i}', fontsize=10, color=color, weight='bold')

    # Nuevas conexiones del esqueleto escaladas
    connections = [[7,6], [6,5], [5,1], [1,2], [2,3], [5,8], [1,4], [8,4], [4,9], [8,10]]
    for _c in connections:
        try:
            ax.plot([p3ds_scaled[_c[0],0], p3ds_scaled[_c[1],0]], 
                    [p3ds_scaled[_c[0],1], p3ds_scaled[_c[1],1]], 
                    [p3ds_scaled[_c[0],2], p3ds_scaled[_c[1],2]], 
                    c='darkred', alpha=0.6, linewidth=3)
        except IndexError:
            print(f"Advertencia: No se puede conectar puntos {_c[0]} y {_c[1]}")
    
    # Añadir posición de las cámaras escaladas
    ax.scatter([cam1_pos_scaled[0]], [cam1_pos_scaled[1]], [cam1_pos_scaled[2]], 
               c='red', marker='^', s=200, label='Cámara 0', alpha=1.0)
    ax.scatter([cam2_pos_scaled[0]], [cam2_pos_scaled[1]], [cam2_pos_scaled[2]], 
               c='green', marker='^', s=200, label='Cámara 1', alpha=1.0)
    
    # Configuración de la visualización
    ax.grid(True, alpha=0.3)
    ax.set_xlabel('X (escalado)', fontsize=12)
    ax.set_ylabel('Y (escalado)', fontsize=12)
    ax.set_zlabel('Z (escalado)', fontsize=12)
    ax.set_title('Reconstrucción 3D - Sistema Estéreo (Escalado)', fontsize=14, weight='bold')
    
    # Rotar la vista para que coincida con la perspectiva de las cámaras
    ax.view_init(elev=-70, azim=-90)
    
    # Hacer que los ejes tengan la misma escala
    ax.set_box_aspect([1, 1, 1])
    
    ax.legend(loc='upper right', fontsize=10)
    
    # Añadir información del escalado en el gráfico
    info_text = f"""Escalado aplicado:
Factor: {scale_factor:.6f}
Centroide original: ({centroid[0]:.1f}, {centroid[1]:.1f}, {centroid[2]:.1f})
Rango escalado: ±{target_size/2:.1f} unidades"""
    
    ax.text2D(0.02, 0.98, info_text, transform=ax.transAxes, fontsize=9,
              verticalalignment='top', bbox=dict(boxstyle="round,pad=0.3", 
              facecolor='lightblue', alpha=0.7))
    
    plt.tight_layout()
    plt.show()
    
if __name__ == "__main__":
    try:
        print("=== INICIANDO CALIBRACIÓN DE SISTEMA ESTÉREO ===")
        
        # Calibración de la primera cámara (ID=0)
        print("\n" + "="*50)
        mtx1, dist1 = calibrate_camera("CAM1/*.jpg", camera_id=0)
        
        # Calibración de la segunda cámara (ID=1)
        print("\n" + "="*50)
        mtx2, dist2 = calibrate_camera("CAM2/*.jpg", camera_id=1)
        
        # Calibración estéreo
        print("\n" + "="*50)
        R, T = stereo_calibrate(mtx1, dist1, mtx2, dist2, "SYNCHED/*.jpg")
        
        # Triangulación (opcional)
        print("\n" + "="*50)
        triangulate(mtx1, mtx2, R, T)
        
        print("\n" + "="*50)
        print("PROCESO DE CALIBRACIÓN COMPLETO")
        print("Los parámetros se han guardado en la carpeta 'camera_parameters/'")
        print("="*50)
        
    except Exception as e:
        print(f"\nError durante la ejecución: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        cv.destroyAllWindows()