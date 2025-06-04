#include <Wire.h>
#include <Adafruit_Sensor.h>
#include <Adafruit_BNO055.h>
#include <utility/imumaths.h>

Adafruit_BNO055 bno = Adafruit_BNO055(55, 0x29);

void setup(void) {
    Serial.begin(115200);
    
    // Inicializar el BNO055
    if (!bno.begin()) {
        Serial.println("Error al inicializar BNO055!");
        while (1);
    }
    
    bno.setExtCrystalUse(true);
    delay(1000);
    
    Serial.println("Enviando ángulos de Euler por Serial...");
}

void loop(void) {
    // Obtener evento de orientación (ángulos de Euler)
    sensors_event_t event;
    bno.getEvent(&event);
    
    // Enviar datos en formato "yaw,pitch,roll"
    Serial.print(event.orientation.x, 4);  // Yaw
    Serial.print(",");
    Serial.print(event.orientation.z, 4);  // Pitch
    Serial.print(",");
    Serial.println(event.orientation.y, 4);  // Roll
    
    delay(50);  // 20Hz de actualización
}