import cv2
import mediapipe as mp
import numpy as np

class PoseDetector:
    def __init__(self):
        self.mp_pose = mp.solutions.pose
        self.pose = self.mp_pose.Pose(
            static_image_mode=True,
            model_complexity=2,
            min_detection_confidence=0.5
        )
        self.mp_draw = mp.solutions.drawing_utils
        
        # Puntos de interés (los mismos que en el código original)
        self.keypoints_indices = [
            0,   # nariz
            11,  # hombro izquierdo
            13,  # codo izquierdo
            15,  # muñeca izquierda
            23,  # cadera izquierda
            12,  # hombro derecho
            14,  # codo derecho
            16,  # muñeca derecha
            24,  # cadera derecha
            25,  # rodilla izquierda
            26,  # rodilla derecha
        ]

    def detect_pose(self, image):
        # Convertir BGR a RGB
        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        results = self.pose.process(image_rgb)
        
        points = []
        if results.pose_landmarks:
            # Obtener coordenadas de los puntos de interés
            for idx in self.keypoints_indices:
                landmark = results.pose_landmarks.landmark[idx]
                # Convertir coordenadas normalizadas a píxeles
                x = int(landmark.x * image.shape[1])
                y = int(landmark.y * image.shape[0])
                points.append([x, y])
                
            # Dibujar el esqueleto
            self.mp_draw.draw_landmarks(
                image, 
                results.pose_landmarks, 
                self.mp_pose.POSE_CONNECTIONS
            )
            
        return image, points

def process_images(img1_path, img2_path):
    # Inicializar detector
    detector = PoseDetector()
    
    # Leer imágenes
    img1 = cv2.imread(img1_path)
    img2 = cv2.imread(img2_path)
    
    if img1 is None or img2 is None:
        raise ValueError("Error al cargar las imágenes")
    
    # Detectar poses
    img1_annotated, points1 = detector.detect_pose(img1.copy())
    img2_annotated, points2 = detector.detect_pose(img2.copy())
    
    # Mostrar imágenes
    cv2.imshow("Cámara 1", img1_annotated)
    cv2.imshow("Cámara 2", img2_annotated)
    
    # Guardar puntos en archivo de texto
    if points1 and points2:
        with open('puntos_uv.txt', 'w') as f:
            f.write("# Puntos UV para triangulación\n")
            f.write("# Formato: [puntos_camara1, puntos_camara2]\n\n")
            
            f.write("uvs1 = [\n")
            for point in points1:
                f.write(f"    [{point[0]}, {point[1]}],\n")
            f.write("]\n\n")
            
            f.write("uvs2 = [\n")
            for point in points2:
                f.write(f"    [{point[0]}, {point[1]}],\n")
            f.write("]\n")
            
        print("Puntos guardados en 'puntos_uv.txt'")
    else:
        print("No se detectaron todos los puntos en ambas imágenes")
    
    # Esperar tecla y cerrar ventanas
    cv2.waitKey(0)
    cv2.destroyAllWindows()

if __name__ == "__main__":
    try:
        # Reemplaza estas rutas con las de tus imágenes
        process_images('testing/T1.jpg', 'testing/T2.jpg')
    except Exception as e:
        print(f"Error: {str(e)}") 