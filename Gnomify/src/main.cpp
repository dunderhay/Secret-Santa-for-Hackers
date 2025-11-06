#include <Arduino.h>
#include <WiFi.h>
#include <WebServer.h>
#include <ESPmDNS.h>
#include <WiFiManager.h>
#include <ArduinoJson.h>
#include <Preferences.h>

// ----------------- CONFIG -----------------
static const char* DEFAULT_TOKEN = "verysecrettoken";
static const char* MDNS_NAME     = "gnomify";

#define PIN_R 0   // Red
#define PIN_G 1   // Green
#define PIN_B 2   // Blue
#define COMMON_ANODE false

#define FACTORY_RESET_PIN 9
#define FACTORY_RESET_HOLD_MS 5000

#define LEDC_FREQ_HZ  1000
#define LEDC_RES_BITS 10
const unsigned long BREATH_PERIOD_MS = 4000;

// ----------------- GLOBALS ----------------
WebServer     server(80);
WiFiManager   wm;
Preferences   prefs;

char API_TOKEN[64];
volatile bool inPortal = false;

enum LedState : uint8_t {
  LED_OFF = 0,
  LED_BUSY,
  LED_SUCCESS,
  LED_ERROR,
  LED_ATTENTION,
  LED_ONLINE,
  LED_OFFLINE,
  LED_PORTAL
};
volatile LedState currentState = LED_OFF;

// ---------- COLOR TABLE (single source of truth) ----------
struct RGB { uint8_t r, g, b; };
static const RGB STATE_COLOR[] = {
  /* LED_OFF       */ {  0,   0,   0},
  /* LED_BUSY      */ {128,   0, 128}, // purple
  /* LED_SUCCESS   */ {  0, 255,   0}, // green
  /* LED_ERROR     */ {255,   0,   0}, // red
  /* LED_ATTENTION */ {  0,   0, 255}, // blue
  /* LED_ONLINE    */ {  0, 255, 255}, // cyan
  /* LED_OFFLINE   */ {255, 128,   0}, // orange
  /* LED_PORTAL    */ {255, 255, 255}  // white
};

// -------------- LED / RENDER --------------
static inline int dutyFrom8(uint8_t v) {
  return map(v, 0, 255, 0, (1 << LEDC_RES_BITS) - 1);
}

void ledWrite(uint8_t r, uint8_t g, uint8_t b) {
  if (COMMON_ANODE) { r = 255 - r; g = 255 - g; b = 255 - b; }
  ledcWrite(0, dutyFrom8(r));
  ledcWrite(1, dutyFrom8(g));
  ledcWrite(2, dutyFrom8(b));
}

void render(float brightness) {
  RGB c = STATE_COLOR[currentState];
  if (currentState == LED_OFF) {
    ledWrite(0,0,0);
    return;
  }
  uint8_t r = (uint8_t)(c.r * brightness);
  uint8_t g = (uint8_t)(c.g * brightness);
  uint8_t b = (uint8_t)(c.b * brightness);
  ledWrite(r,g,b);
}

float breathe() {
  unsigned long now = millis();
  float t = (now % BREATH_PERIOD_MS) / (float)BREATH_PERIOD_MS;  // 0..1
  float raw = 0.5f - 0.5f * cosf(2.0f * PI * t);                 // 0..1
  return 0.1f + 0.9f * raw;                                      // 0.1..1.0
}

void setState(LedState s, bool renderNow = true) {
  currentState = s;
  if (renderNow) render(1.0f);  // instant visual change; breathing will take over next loop
}

// -------------- WIFI ----------------------
void startWiFi() {
  // load saved token
  prefs.begin("gnomify", false);
  String saved = prefs.getString("apitoken", DEFAULT_TOKEN);
  prefs.end();
  saved.toCharArray(API_TOKEN, sizeof(API_TOKEN));

  // token field in captive portal
  WiFiManagerParameter tokenParam("api_token", "API Token", API_TOKEN, 64);
  wm.addParameter(&tokenParam);

  wm.setAPCallback([](WiFiManager*) {
    inPortal = true;
    setState(LED_PORTAL);
  });

  wm.setConnectRetries(2);
  wm.setConnectTimeout(15);
  wm.setConfigPortalTimeout(180);

  Serial.println("[WiFi] autoConnect (AP if needed)...");
  bool ok = wm.autoConnect("Gnomify-Setup", "gnomify123");
  inPortal = false;

  // persist (possibly) updated token
  strncpy(API_TOKEN, tokenParam.getValue(), sizeof(API_TOKEN) - 1);
  API_TOKEN[sizeof(API_TOKEN) - 1] = '\0';
  prefs.begin("gnomify", false);
  prefs.putString("apitoken", API_TOKEN);
  prefs.end();
  Serial.printf("[Config] API token set to: %s\n", API_TOKEN);

  if (!ok) {
    Serial.println("[WiFi] Failed to connect, restarting...");
    ESP.restart();
  }

  Serial.println("[WiFi] Connected!");
  if (MDNS.begin(MDNS_NAME)) {
    Serial.printf("[mDNS] http://%s.local\n", MDNS_NAME);
  } else {
    Serial.println("[mDNS] failed");
  }
  setState(LED_ONLINE);
}

// -------------- HTTP ----------------------
bool validToken() {
  return server.hasArg("token") && server.arg("token") == API_TOKEN;
}

void handleRoot() {
  String msg =
    "POST /event?token=TOKEN\n"
    "Body: {\"state\":\"busy|success|error|attention|off\"}\n\n"
    "GET /state?token=TOKEN\n"
    "Returns current state and Wi-Fi status in JSON.\n";
  server.send(200, "text/plain", msg);
}

void handleEvent() {
  if (!validToken()) { server.send(403, "text/plain", "forbidden\n"); return; }

  String body = server.arg("plain");
  if (body.length()==0 && server.args()>0) body = server.arg(0);

  StaticJsonDocument<128> doc;
  if (deserializeJson(doc, body))         { server.send(400, "text/plain", "bad json\n"); return; }
  if (!doc.containsKey("state"))          { server.send(400, "text/plain", "missing state\n"); return; }

  String s = doc["state"]; s.trim();
  if      (s == "busy")      setState(LED_BUSY);
  else if (s == "success")   setState(LED_SUCCESS);
  else if (s == "error")     setState(LED_ERROR);
  else if (s == "attention") setState(LED_ATTENTION);
  else if (s == "off")       setState(LED_OFF);
  else                       setState(LED_ONLINE);

  server.send(200, "application/json", "{\"ok\":true}\n");
}

void handleState() {
  if (!validToken()) { server.send(403, "text/plain", "forbidden\n"); return; }

  StaticJsonDocument<192> doc;
  doc["wifi_connected"] = (WiFi.status() == WL_CONNECTED);
  doc["state"]          = (int)currentState;
  doc["in_portal"]      = inPortal;
  doc["token"]          = API_TOKEN;

  String json; serializeJson(doc, json);
  server.send(200, "application/json", json);
}

// ---------- Factory Reset -----------------
void checkFactoryReset() {
  pinMode(FACTORY_RESET_PIN, INPUT_PULLUP);
  unsigned long pressStart = 0;

  if (digitalRead(FACTORY_RESET_PIN) == LOW) {
    pressStart = millis();
    Serial.println("[Reset] Button pressed... hold to confirm");
    while (digitalRead(FACTORY_RESET_PIN) == LOW) {
      delay(100);
      if (millis() - pressStart >= FACTORY_RESET_HOLD_MS) {
        Serial.println("[Reset] Factory reset confirmed");
        WiFi.disconnect(true, true); // erase Wi-Fi creds
        prefs.begin("gnomify", false);
        prefs.clear();               // clear API token
        prefs.end();
        delay(200);
        ESP.restart();
      }
    }
    Serial.println("[Reset] Button released before timeout (cancelled)");
  }
}

// -------------- SETUP/LOOP ----------------
void setup() {
  Serial.begin(115200);
  delay(100);

  ledcSetup(0, LEDC_FREQ_HZ, LEDC_RES_BITS);
  ledcSetup(1, LEDC_FREQ_HZ, LEDC_RES_BITS);
  ledcSetup(2, LEDC_FREQ_HZ, LEDC_RES_BITS);
  ledcAttachPin(PIN_R, 0);
  ledcAttachPin(PIN_G, 1);
  ledcAttachPin(PIN_B, 2);

  

  Serial.println("[Init] Gnomify starting...");
  startWiFi();

  server.on("/",      handleRoot);
  server.on("/event", HTTP_POST, handleEvent);
  server.on("/state", HTTP_GET,  handleState);
  server.begin();
  Serial.println("[HTTP] Ready.");
}

void loop() {
  server.handleClient();

  if (!inPortal) {
    if (WiFi.status() == WL_CONNECTED) {
      if (currentState == LED_OFFLINE) setState(LED_ONLINE, false);
    } else {
      if (currentState != LED_PORTAL && currentState != LED_OFF)
        setState(LED_OFFLINE, false);
    }
  }

  render(breathe());
  checkFactoryReset();
}
