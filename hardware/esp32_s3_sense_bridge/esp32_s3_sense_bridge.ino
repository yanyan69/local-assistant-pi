#include <WiFi.h>
#include <WebServer.h>

// ------------------------------------------------------------
// Xiao ESP32-S3 Sense bridge sketch
// ------------------------------------------------------------
// Purpose:
//   1. Join the local Wi-Fi you own.
//   2. Expose a tiny serial + HTTP command surface for the Pi.
//   3. Return a typed debug event stream visible from Arduino IDE.
//
// Notes:
//   - Keep the Pi as the authority for safety and routing.
//   - Only allow a small set of commands through this bridge.
//   - Compile in Arduino IDE using an ESP32-S3 board definition.
// ------------------------------------------------------------

const char* WIFI_SSID = "yanyan-laptop";
const char* WIFI_PASSWORD = "12345678";
const char* DEVICE_ID = "esp32s3sense";

WebServer server(8080);

String safeJsonString(const String& text) {
  String out = text;
  out.replace("\\", "\\\\");
  out.replace("\"", "\\\"");
  out.replace("\n", "\\n");
  out.replace("\r", "");
  return out;
}

String jsonField(const String& body, const char* key) {
  String needle = String("\"") + key + String("\"");
  int keyIndex = body.indexOf(needle);
  if (keyIndex < 0) return "";

  int colonIndex = body.indexOf(':', keyIndex);
  if (colonIndex < 0) return "";

  int valueStart = body.indexOf('"', colonIndex + 1);
  int valueEnd = body.indexOf('"', valueStart + 1);
  if (valueStart < 0 || valueEnd < 0 || valueEnd <= valueStart) return "";

  return body.substring(valueStart + 1, valueEnd);
}

String jsonType(const String& body) {
  return jsonField(body, "type");
}

String jsonDevice(const String& body) {
  return jsonField(body, "device");
}

String jsonId(const String& body) {
  return jsonField(body, "id");
}

String jsonPayload(const String& body) {
  int p = body.indexOf("\"payload\"");
  if (p < 0) return "{}";

  int firstBrace = body.indexOf('{', p);
  int lastBrace = body.lastIndexOf('}');
  if (firstBrace < 0 || lastBrace < 0 || firstBrace >= lastBrace) return "{}";

  return body.substring(firstBrace, lastBrace + 1);
}

void sendJson(int code, String payload) {
  server.send(code, "application/json", payload);
}

void logEvent(String event, String detail = "") {
  Serial.print("[ESP32_S3_EVENT] ");
  Serial.print(event);
  if (detail.length() > 0) {
    Serial.print(" :: ");
    Serial.print(detail);
  }
  Serial.println();
}

void handleStatus() {
  String reply = "{\"device\":\"" + String(DEVICE_ID) +
                 "\",\"status\":\"online\",\"queue\":\"idle\"}";
  sendJson(200, reply);
}

String processCommand(String body) {
  String type = jsonType(body);
  String device = jsonDevice(body);
  String id = jsonId(body);
  String payload = jsonPayload(body);

  if (type.length() == 0) {
    return "{\"device\":\"" + String(DEVICE_ID) +
           "\",\"status\":\"error\",\"message\":\"missing type\"}";
  }

  logEvent("command_received", type + " device=" + device + " id=" + id);

  if (device.length() > 0 && device != DEVICE_ID) {
    return "{\"device\":\"" + String(DEVICE_ID) +
           "\",\"status\":\"error\",\"message\":\"device mismatch\"}";
  }

  if (type == "CAPTURE_IMAGE") {
    logEvent("capture_requested", payload);
    return "{\"device\":\"" + String(DEVICE_ID) +
           "\",\"type\":\"CAPTURE_IMAGE\",\"status\":\"accepted\",\"id\":\"" + id +
           "\",\"payload\":\"image_staged\"}";
  }

  if (type == "DISPLAY_TEXT") {
    logEvent("display_text", safeJsonString(payload));
    return "{\"device\":\"" + String(DEVICE_ID) +
           "\",\"type\":\"DISPLAY_TEXT\",\"status\":\"accepted\",\"id\":\"" + id +
           "\"}";
  }

  if (type == "LED_ON") {
    digitalWrite(LED_BUILTIN, HIGH);
    logEvent("led_on", "");
    return "{\"device\":\"" + String(DEVICE_ID) +
           "\",\"type\":\"LED_ON\",\"status\":\"accepted\",\"id\":\"" + id +
           "\"}";
  }

  if (type == "LED_OFF") {
    digitalWrite(LED_BUILTIN, LOW);
    logEvent("led_off", "");
    return "{\"device\":\"" + String(DEVICE_ID) +
           "\",\"type\":\"LED_OFF\",\"status\":\"accepted\",\"id\":\"" + id +
           "\"}";
  }

  if (type == "DEVICE_STATUS") {
    return "{\"device\":\"" + String(DEVICE_ID) +
           "\",\"type\":\"DEVICE_STATUS\",\"status\":\"online\",\"id\":\"" + id +
           "\"}";
  }

  return "{\"device\":\"" + String(DEVICE_ID) +
         "\",\"status\":\"error\",\"message\":\"unsupported type\",\"id\":\"" + id +
         "\"}";
}

void handleCommand() {
  String body = server.arg("plain");
  String reply = processCommand(body);
  sendJson(200, reply);
}

void setup() {
  Serial.begin(115200);
  delay(1000);

  pinMode(LED_BUILTIN, OUTPUT);
  digitalWrite(LED_BUILTIN, LOW);

  Serial.println("[ESP32_S3] booting bridge...");
  Serial.println("[ESP32_S3] waiting for WiFi...");

  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  int tries = 0;
  while (WiFi.status() != WL_CONNECTED && tries < 30) {
    delay(500);
    Serial.print(".");
    tries++;
  }

  if (WiFi.status() == WL_CONNECTED) {
    Serial.println();
    Serial.print("[ESP32_S3] WiFi connected: ");
    Serial.println(WiFi.localIP());
  } else {
    Serial.println();
    Serial.println("[ESP32_S3] WiFi not connected - check SSID/password");
  }

  server.on("/status", HTTP_GET, handleStatus);
  server.on("/command", HTTP_POST, handleCommand);
  server.on("/ping", HTTP_GET, []() {
    sendJson(200, "{\"device\":\"" + String(DEVICE_ID) + "\",\"status\":\"ok\"}");
  });

  server.begin();
  Serial.println("[ESP32_S3] HTTP bridge ready on port 8080");
}

void processSerialLine(String line) {
  line.trim();
  if (line.length() == 0) return;

  logEvent("serial_command", line);
  String reply = processCommand(line);
  Serial.println("[ESP32_S3_ACK] " + reply);
}

void loop() {
  server.handleClient();

  if (Serial.available()) {
    String line = Serial.readStringUntil('\n');
    processSerialLine(line);
  }
}
