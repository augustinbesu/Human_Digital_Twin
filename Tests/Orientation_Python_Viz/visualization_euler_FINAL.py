import pygame
from pygame.locals import *
from OpenGL.GL import *
from OpenGL.GLU import *
import numpy as np
import serial
import time

class EulerVisualizer:
    def __init__(self, port='COM6', baudrate=115200):
        # Inicializar PyGame y OpenGL
        pygame.init()
        
        # Obtener resolución de la pantalla para pantalla completa
        info = pygame.display.Info()
        display = (info.current_w, info.current_h)
        
        # Configurar pantalla completa
        pygame.display.set_mode(display, DOUBLEBUF | OPENGL | FULLSCREEN)
        pygame.display.set_caption("Visualizador de Orientación Euler - Presiona ESC para salir")
        
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

    def apply_euler_rotations(self, yaw, pitch, roll):
        """Aplica las rotaciones de Euler con mapeo corregido"""
        # CORRECCIÓN DEL MAPEO:
        # - El pitch del sensor es el roll del modelo
        # - El roll del sensor es el pitch del modelo  
        # - El yaw está en dirección opuesta
        
        glRotatef(yaw, 0, 0, 1)      # Yaw corregido (sin invertir)
        glRotatef(roll, 0, 1, 0)     # Roll del sensor = Pitch del modelo
        glRotatef(pitch, 1, 0, 0)    # Pitch del sensor = Roll del modelo

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
                    
                    if "Yaw:" in line:
                        # Parsear formato: "Yaw: X Pitch: Y Roll: Z"
                        parts = line.split()
                        yaw = float(parts[1])
                        pitch = float(parts[3])
                        roll = float(parts[5])
                    else:
                        # Parsear formato simple: "yaw,pitch,roll"
                        yaw, pitch, roll = map(float, line.split(','))
                
                # Limpiar pantalla
                glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
                
                # Resetear la matriz de modelado
                glLoadIdentity()
                glTranslatef(0.0, 0.0, -5)
                glRotatef(90, 1, 0, 0)  # Mantener alineación inicial
                
                # Aplicar rotaciones de Euler CORREGIDAS
                self.apply_euler_rotations(yaw, pitch, roll)
                
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
        visualizer = EulerVisualizer(port='COM6')
        visualizer.run()
    except Exception as e:
        print(f"Error al iniciar: {e}")