import pygame
from pygame.locals import *
from OpenGL.GL import *
from OpenGL.GLU import *
import numpy as np
import serial
import time

class QuaternionVisualizer:
    def __init__(self, port='COM6', baudrate=115200):
        # Inicializar PyGame y OpenGL
        pygame.init()
        
        # Obtener resolución de la pantalla para pantalla completa
        info = pygame.display.Info()
        display = (info.current_w, info.current_h)
        
        # Configurar pantalla completa
        pygame.display.set_mode(display, DOUBLEBUF | OPENGL | FULLSCREEN)
        pygame.display.set_caption("Visualizador de Orientación - Presiona ESC para salir")
        
        # Configurar la vista
        glEnable(GL_DEPTH_TEST)
        glMatrixMode(GL_PROJECTION)
        gluPerspective(45, (display[0]/display[1]), 0.1, 50.0)
        glMatrixMode(GL_MODELVIEW)
        glTranslatef(0.0, 0.0, -5)
        
        # Añadir rotación inicial para alinear los ejes correctamente
        glRotatef(90, 1, 0, 0)  # Rotar 90 grados en X para alinear Z hacia arriba
        
        # Configurar color de fondo negro
        glClearColor(0.0, 0.0, 0.0, 1.0)
        
        # Inicializar conexión serial
        try:
            self.serial = serial.Serial(port, baudrate)
            print(f"Conectado al puerto {port}")
            time.sleep(1)  # Esperar a que se establezca la conexión
        except Exception as e:
            print(f"Error al conectar al puerto {port}: {e}")
            raise

    def quaternion_to_matrix(self, w, x, y, z):
        """Convierte un cuaternión a matriz de rotación con ejes corregidos"""
        # Normalizar cuaternión
        norm = np.sqrt(w*w + x*x + y*y + z*z)
        w /= norm
        x /= norm
        y /= norm
        z /= norm

        # Matriz corregida para que:
        # X sea el eje de roll (rotación frontal)
        # Y sea el eje de pitch (rotación lateral)
        # Z sea el eje de yaw (rotación horizontal)
        return [
            [1 - 2*y*y - 2*z*z,     2*x*y + 2*w*z,     2*x*z - 2*w*y,     0],
            [    2*x*y - 2*w*z, 1 - 2*x*x - 2*z*z,     2*y*z + 2*w*x,     0],
            [    2*x*z + 2*w*y,     2*y*z - 2*w*x, 1 - 2*x*x - 2*y*y,     0],
            [                0,                 0,                 0,     1]
        ]

    def draw_rectangle(self):
        """Dibuja un rectángulo 3D en color blanco con bordes de color"""
        # Dibujar las caras rellenas en blanco
        glBegin(GL_QUADS)
        glColor3f(1.0, 1.0, 1.0)  # Blanco para las caras
        
        # Cara frontal
        glVertex3f(-1.0, -2.0, 0.1)
        glVertex3f( 1.0, -2.0, 0.1)
        glVertex3f( 1.0,  2.0, 0.1)
        glVertex3f(-1.0,  2.0, 0.1)
        
        # Cara trasera
        glVertex3f(-1.0, -2.0, -0.1)
        glVertex3f(-1.0,  2.0, -0.1)
        glVertex3f( 1.0,  2.0, -0.1)
        glVertex3f( 1.0, -2.0, -0.1)
        
        # Caras laterales
        glVertex3f(-1.0,  2.0,  0.1)
        glVertex3f(-1.0, -2.0,  0.1)
        glVertex3f(-1.0, -2.0, -0.1)
        glVertex3f(-1.0,  2.0, -0.1)
        
        glVertex3f( 1.0,  2.0,  0.1)
        glVertex3f( 1.0,  2.0, -0.1)
        glVertex3f( 1.0, -2.0, -0.1)
        glVertex3f( 1.0, -2.0,  0.1)
        
        # Cara superior
        glVertex3f(-1.0,  2.0,  0.1)
        glVertex3f( 1.0,  2.0,  0.1)
        glVertex3f( 1.0,  2.0, -0.1)
        glVertex3f(-1.0,  2.0, -0.1)
        
        # Cara inferior
        glVertex3f(-1.0, -2.0,  0.1)
        glVertex3f(-1.0, -2.0, -0.1)
        glVertex3f( 1.0, -2.0, -0.1)
        glVertex3f( 1.0, -2.0,  0.1)
        
        glEnd()
        
        # Dibujar los bordes en color azul
        glColor3f(0.0, 0.5, 1.0)  # Azul claro para los bordes
        glLineWidth(2.0)  # Grosor de línea
        
        glBegin(GL_LINES)
        
        # Bordes de la cara frontal
        glVertex3f(-1.0, -2.0, 0.1)
        glVertex3f( 1.0, -2.0, 0.1)
        
        glVertex3f( 1.0, -2.0, 0.1)
        glVertex3f( 1.0,  2.0, 0.1)
        
        glVertex3f( 1.0,  2.0, 0.1)
        glVertex3f(-1.0,  2.0, 0.1)
        
        glVertex3f(-1.0,  2.0, 0.1)
        glVertex3f(-1.0, -2.0, 0.1)
        
        # Bordes de la cara trasera
        glVertex3f(-1.0, -2.0, -0.1)
        glVertex3f( 1.0, -2.0, -0.1)
        
        glVertex3f( 1.0, -2.0, -0.1)
        glVertex3f( 1.0,  2.0, -0.1)
        
        glVertex3f( 1.0,  2.0, -0.1)
        glVertex3f(-1.0,  2.0, -0.1)
        
        glVertex3f(-1.0,  2.0, -0.1)
        glVertex3f(-1.0, -2.0, -0.1)
        
        # Líneas que conectan cara frontal y trasera
        glVertex3f(-1.0, -2.0,  0.1)
        glVertex3f(-1.0, -2.0, -0.1)
        
        glVertex3f( 1.0, -2.0,  0.1)
        glVertex3f( 1.0, -2.0, -0.1)
        
        glVertex3f( 1.0,  2.0,  0.1)
        glVertex3f( 1.0,  2.0, -0.1)
        
        glVertex3f(-1.0,  2.0,  0.1)
        glVertex3f(-1.0,  2.0, -0.1)
        
        glEnd()
        
        # Restaurar grosor de línea por defecto
        glLineWidth(1.0)

    def run(self):
        """Bucle principal de visualización"""
        while True:
            # Manejar eventos de PyGame
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    self.serial.close()
                    return
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:  # Salir con ESC
                        pygame.quit()
                        self.serial.close()
                        return

            try:
                # Leer datos seriales si están disponibles
                if self.serial.in_waiting:
                    line = self.serial.readline().decode().strip()
                    w, x, y, z = map(float, line.split(','))
                    
                    # Limpiar pantalla
                    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
                    
                    # Resetear la matriz de modelado
                    glLoadIdentity()
                    glTranslatef(0.0, 0.0, -5)
                    glRotatef(90, 1, 0, 0)  # Mantener alineación inicial
                    
                    # Aplicar rotación usando matriz de cuaternión
                    rotation_matrix = self.quaternion_to_matrix(-w, -x, y, z)
                    glMultMatrixf(rotation_matrix)
                    
                    # Dibujar solo el rectángulo (sin ejes)
                    self.draw_rectangle()
                    
                    # Actualizar pantalla
                    pygame.display.flip()
                
            except Exception as e:
                print(f"Error: {e}")
                continue

if __name__ == "__main__":
    try:
        # Ajusta el puerto COM según tu sistema
        visualizer = QuaternionVisualizer(port='COM6')
        visualizer.run()
    except Exception as e:
        print(f"Error al iniciar: {e}")