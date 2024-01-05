#include <Arduino.h>
#include <ESP8266WiFi.h>
#include "Custom.h"

#if MINOTA_HTTPSERVER
  #include <ESP8266WebServer.h>
  #include <ESP8266HTTPUpdateServer.h>
#endif
#if MINOTA_OTASERVER
  #include <ArduinoOTA.h>
#endif
#if MINOTA_AUTO_UPDATE
  #include <ESP8266httpUpdate.h>
#endif

//helper macro for debug printing
#if MINOTA_DEBUG_SERIAL
  #define DEBUGPRINT(...) Serial.printf(__VA_ARGS__)
#else
  #define DEBUGPRINT(...)
#endif

#if MINOTA_HTTPSERVER
  ESP8266WebServer server(80);
  ESP8266HTTPUpdateServer httpUpdater;
#endif

#if MINOTA_AUTO_UPDATE
  bool autoUpdateLocalUrl = false;
#endif

bool waitForWifi(int maxAttempts = 100) {
  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < maxAttempts) {
    delay(100);
    attempts++;
  }

  return WiFi.status() == WL_CONNECTED;
}


void setup() {
  #ifdef MINOTA_DEBUG_SERIAL
    Serial.begin(115200);
  #endif
  DEBUGPRINT("Booting..\n");

  bool connected = false;
#if MINOTA_WIFI_CONNECT_TO_AP
  DEBUGPRINT("STA mode, try using stored creds\n");
  WiFi.begin();
  connected = waitForWifi();
  #if MINOTA_WIFI_USE_CUSTOM_DEPLOYMENT 
    if (!connected) {
      DEBUGPRINT("STA mode, try using custom_deployment creds\n");
      WiFi.begin(CUSTOM_DEPLOYMENT_SSID, CUSTOM_DEPLOYMENT_KEY);
      connected = waitForWifi();
    }
  #endif
  if (!connected) { // prepare for AP mode
    DEBUGPRINT("AP mode\n");
    WiFi.mode(WIFI_OFF);
    delay(100);
    WiFi.mode(WIFI_AP);
    delay(2000);
  }
#endif
  if (!connected) {
    WiFi.softAP(MINOTA_WIFI_AP_SSID, MINOTA_WIFI_AP_KEY);
    #if MINOTA_AUTO_UPDATE
      autoUpdateLocalUrl = true; //start with local mode
    #endif
  }
  DEBUGPRINT("IP address: %s\n", WiFi.localIP().toString().c_str());


 #if MINOTA_HTTPSERVER
  server.onNotFound([]() {
    server.sendHeader("Location", "/update", true); // Nastaví hlavičku pro přesměrování
    server.send(302); // Odešle HTTP status 302 pro přesměrování
  });
  httpUpdater.setup(&server);
  server.begin();
  DEBUGPRINT("HTTPUpdateServer ready\n");
 #endif
 #if MINOTA_OTASERVER
  ArduinoOTA.setPort(ARDUINO_OTA_PORT);
  ArduinoOTA.setPassword(MINOTA_OTA_PASSWORD);
  ArduinoOTA.begin();
  DEBUGPRINT("OTA ready\n");
 #endif
}

void loop() {
  #if MINOTA_OTASERVER
    ArduinoOTA.handle();
  #endif
  #if MINOTA_HTTPSERVER
    server.handleClient();
  #endif
  #if MINOTA_AUTO_UPDATE
  //autoUpdateLocalUrl
    const char *update_url = autoUpdateLocalUrl ? MINOTA_AUTO_UPDATE_URL_APMODE : MINOTA_AUTO_UPDATE_URL;
    DEBUGPRINT("Auto update from %s\n", update_url);
    t_httpUpdate_return ret = ESPhttpUpdate.update(update_url);
    DEBUGPRINT("Auto update result: %d\n", ret);
    autoUpdateLocalUrl = !autoUpdateLocalUrl;
  #endif
}