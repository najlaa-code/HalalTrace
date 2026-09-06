// HalalTrace hardware test rig — ESP32 + DS18B20 + analog turbidity sensor.
//
// This sketch does NOT use WiFi. The ESP32 stays cabled to the laptop over
// USB (needed for power anyway) and just prints readings over serial, one
// per second. A bridge script on the laptop
// (hardware/bridge/serial_to_backend.py) reads this serial output and does
// the actual cycle/start -> reading -> cycle/end calls to the local backend.
// No wireless dependency at all.

#include <OneWire.h>
#include <DallasTemperature.h>

#define ONE_WIRE_BUS   4    // DS18B20 DATA
#define TURBIDITY_PIN  32   // turbidity AOUT

OneWire oneWire(ONE_WIRE_BUS);
DallasTemperature tempSensor(&oneWire);

void setup() {
  Serial.begin(115200);
  analogReadResolution(12);
  analogSetPinAttenuation(TURBIDITY_PIN, ADC_11db); // extend ADC range to 0-3.3 V
  tempSensor.begin();
  Serial.printf("# DS18B20 sensors found: %d\n", tempSensor.getDeviceCount());
}

void loop() {
  tempSensor.requestTemperatures();
  float tempC = tempSensor.getTempCByIndex(0);
  int turbidityRaw = analogRead(TURBIDITY_PIN);

  // Machine-readable line for serial_to_backend.py. Anything not starting
  // with "DATA," is ignored by the bridge script, so free-form debug prints
  // (like the sensor-count line above) are safe to keep.
  Serial.printf("DATA,%.2f,%d\n", tempC, turbidityRaw);
  delay(1000);
}
