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
    
    Serial.println("Enviando cuaterniones por Serial...");
}

void loop(void) {
    // Obtener cuaternión
    imu::Quaternion quat = bno.getQuat();
    
    // Enviar datos en formato "w,x,y,z"
    Serial.print(quat.w(), 4);
    Serial.print(",");
    Serial.print(quat.x(), 4);
    Serial.print(",");
    Serial.print(quat.y(), 4);
    Serial.print(",");
    Serial.println(quat.z(), 4);
    
    delay(50);  // 20Hz de actualización
} 