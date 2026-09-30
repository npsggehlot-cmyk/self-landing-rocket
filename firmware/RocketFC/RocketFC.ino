// RocketFC v2.1 flight software  -  Arduino Nano (ATmega328P, 5 V, 16 MHz)
// Libraries: Wire, SPI, SD, Servo (all built into the Arduino IDE).
#include <Wire.h>
#include <SPI.h>
#include <SD.h>
#include <Servo.h>

const float G = 9.80665;
// ======================= CONFIG: edit these =======================
#define MODE_CHUTE_TEST 0            // TVC ascent, chute at apogee (fly this first)
#define MODE_LANDING    1            // TVC ascent, landing burn with the 2nd F15
const uint8_t FLIGHT_MODE = MODE_CHUTE_TEST;

// TVC mount (set with the 'sweep' and 'tvc' bench commands)
const int   X_CENTER_US = 1500, Y_CENTER_US = 1500;
const float US_PER_DEG  = 30.0;      // servo microseconds per 1 deg of motor tilt
const float GIMBAL_MAX  = 5.0;       // deg
const int8_t SIGN_X = 1, SIGN_Y = 1; // flip to -1 if a nozzle moves the wrong way
const bool  SWAP_XY = false;         // true if servo X actually tilts about the IMU Y axis
const float KP = 0.30, KI = 0.05, KD = 0.08;   // gimbal deg per: deg, deg*s, deg/s

// chute servo (Servo.write degrees)
const uint8_t CHUTE_LOCK = 90, CHUTE_OPEN = 0;

// flight events
const float    LAUNCH_G      = 1.5;   // F15 peaks ~2.3 g on a 1.1 kg rocket; 1.5 g catches it
const uint16_t LAUNCH_MS     = 50;
const float    CONFIRM_ALT   = 3.0;   // must climb this high within CONFIRM_MS or it was a bump
const uint32_t CONFIRM_MS    = 2500;
const uint32_t BURN_MAX_MS   = 4000;  // F15 burns ~3.5 s
const uint32_t APOGEE_MAX_MS = 9000;  // backup: chute no later than this after liftoff
const float    LEGS_ALT      = 20.0;  // chute mode: release legs below this (m AGL)
const uint16_t EMATCH_MS = 1000, BURNWIRE_MS = 2500;

// landing mode: the F15 can't throttle, so the burn must END at the ground.
// It only works when apogee matches the landing mass (0.95 kg needs ~46 m, 1.0 kg ~37 m);
// otherwise the computer uses the chute instead.
const float LAND_MASS_KG = 0.95;     // WEIGH IT: total mass at landing ignition (kg)
const float IGN_DELAY_S  = 0.35;     // command -> thrust; measure with a static test ('fire2')
const float LAND_MARGIN  = -0.5;     // burn ends just "below" ground: touch down while still braking
const float CDA          = 0.0027;   // drag area Cd*A (m^2); 3in tube falling tail-first ~0.6 x 0.0046
const float MAX_TOUCHDOWN = 3.0;     // predicted touchdown faster than this -> chute instead
const float MAX_TILT     = 25.0;     // tilted more than this at apogee/ignition -> chute
const float F15_I = 49.6, F15_J = 88.6, F15_TB = 3.45;   // Estes F15: impulse, 1st moment, burn time
const float DV_BURN = F15_I / LAND_MASS_KG - G * F15_TB;                 // speed the burn removes
const float S_BURN  = F15_J / LAND_MASS_KG - 0.5f * G * F15_TB * F15_TB; // climb the burn adds from rest
// ==================================================================

// Pins (RocketFC v2.1)
const uint8_t PYRO_PIN[4] = {2, 4, 6, 8};       // P1 ascent, P2 landing, P3 legs, P4 spare
const uint8_t CONT_PIN[4] = {A0, A1, A2, A3};
enum { P_ASCENT, P_LANDING, P_LEGS, P_SPARE };
const uint8_t PIN_SX = 3, PIN_SY = 5, PIN_CHUTE = 7, PIN_BUZZ = 9, PIN_SD = 10;
const uint8_t IMU = 0x6A, BARO = 0x77;

enum State : uint8_t { PAD, BOOST, COAST, CHUTE_DESCENT, WAIT_IGNITE, LAND_BURN, LANDED };
State state = PAD;

Servo sx, sy, chute;
File logFile;
bool imuOK, baroOK, sdOK, tvcTest;

// sensors
float ax, ay, az, gx, gy, gz;          // g and deg/s (bias removed)
float gbx, gby, gbz;                   // gyro bias
float lax, lay, laz = 1;               // low-passed accel (pad levelling)
uint16_t C[7];                         // baro PROM
float pressure, p0, baroAlt;
bool baroNew;

// state estimate
float q0 = 1, q1, q2, q3;              // attitude, body -> world
float tiltX, tiltY, tilt;              // deg
float alt, vel, maxAlt;                // m, m/s (fused baro + accel)
float ix, iy;                          // PID integrators
int   usX = X_CENTER_US, usY = Y_CENTER_US;

// timing / events
uint32_t tLaunch, tEvent, tCond, lastCtl, lastLog, lastFlush, lastBeep, lastAdc;
uint32_t pyroEnd[4];
uint8_t  pyroFired, contMask;
bool     armed, chuteOpen, legsDone, confirmed, thrustSeen;
float    vbat;

// ------------------------------------------------------------------ I2C helpers
bool i2cCmd(uint8_t addr, uint8_t c) {
  Wire.beginTransmission(addr); Wire.write(c);
  return Wire.endTransmission() == 0;
}
bool i2cWrite(uint8_t addr, uint8_t reg, uint8_t val) {
  Wire.beginTransmission(addr); Wire.write(reg); Wire.write(val);
  return Wire.endTransmission() == 0;
}
bool i2cRead(uint8_t addr, uint8_t reg, uint8_t* buf, uint8_t n) {
  Wire.beginTransmission(addr); Wire.write(reg);
  if (Wire.endTransmission(false)) return false;
  if (Wire.requestFrom(addr, n) != n) return false;
  for (uint8_t i = 0; i < n; i++) buf[i] = Wire.read();
  return true;
}

// ------------------------------------------------------------------ LSM6DSO32
bool imuInit() {
  uint8_t id = 0;
  if (!i2cRead(IMU, 0x0F, &id, 1) || id != 0x6C) return false;
  i2cWrite(IMU, 0x12, 0x01); delay(20);   // CTRL3_C: software reset
  i2cWrite(IMU, 0x12, 0x44);              // block data update + auto-increment
  i2cWrite(IMU, 0x10, 0x74);              // CTRL1_XL: 833 Hz, +/-32 g
  i2cWrite(IMU, 0x11, 0x7C);              // CTRL2_G : 833 Hz, +/-2000 dps
  return true;
}
float rgx, rgy, rgz;                      // raw gyro (deg/s) for bias tracking
bool imuRead() {
  uint8_t b[12];
  if (!i2cRead(IMU, 0x22, b, 12)) return false;
  int16_t r[6];
  for (uint8_t i = 0; i < 6; i++) r[i] = (int16_t)((uint16_t)b[2 * i + 1] << 8 | b[2 * i]);
  rgx = r[0] * 0.070f; rgy = r[1] * 0.070f; rgz = r[2] * 0.070f;
  gx = rgx - gbx; gy = rgy - gby; gz = rgz - gbz;
  ax = r[3] * 0.000976f; ay = r[4] * 0.000976f; az = r[5] * 0.000976f;
  return true;
}

// ------------------------------------------------------------------ MS5607 (non-blocking)
bool baroInit() {
  if (!i2cCmd(BARO, 0x1E)) return false;
  delay(5);
  for (uint8_t i = 1; i <= 6; i++) {
    uint8_t b[2];
    if (!i2cRead(BARO, 0xA0 + 2 * i, b, 2)) return false;
    C[i] = (uint16_t)b[0] << 8 | b[1];
  }
  return C[1] != 0 && C[1] != 0xFFFF;
}
uint32_t D1, D2;
uint8_t baroStep, baroCount;
uint32_t baroT;
void baroService() {                      // OSR1024 (2.3 ms); temperature every 20th sample
  if (!baroOK || micros() - baroT < 2600) return;
  uint8_t b[3];
  if (baroStep) {
    if (!i2cRead(BARO, 0x00, b, 3)) { baroStep = 0; return; }
    uint32_t v = (uint32_t)b[0] << 16 | (uint16_t)b[1] << 8 | b[2];
    if (baroStep == 2) D2 = v;
    else if (D2) {
      D1 = v;
      float dT   = (float)D2 - C[5] * 256.0f;              // MS5607 datasheet, in float
      float T    = 2000 + dT * C[6] / 8388608.0f;
      float off  = C[2] * 131072.0f + C[4] * dT / 64.0f;
      float sens = C[1] * 65536.0f + C[3] * dT / 128.0f;
      if (T < 2000) { float t = T - 2000; off -= 61 * t * t / 16; sens -= 2 * t * t; }   // cold day
      pressure = ((float)D1 * sens / 2097152.0f - off) / 32768.0f;                        // Pa
      if (p0 > 0) {                        // hypsometric 8434*ln(p0/P), series form (<1 cm error below 300 m)
        float x = (p0 - pressure) / p0;
        baroAlt = 8434.0f * x * (1 + x * (0.5f + x * 0.3333f));
      }
      baroNew = true;
    }
  }
  bool temp = (baroCount++ % 20 == 0);
  i2cCmd(BARO, temp ? 0x54 : 0x44);
  baroStep = temp ? 2 : 1;
  baroT = micros();
}

// ------------------------------------------------------------------ attitude
void levelFromAccel() {                   // quaternion that rotates measured "up" onto world +Z
  float n = sqrt(lax * lax + lay * lay + laz * laz);
  if (n < 0.5f) return;
  float vx = lax / n, vy = lay / n, vz = laz / n;
  float w = 1 + vz, x = vy, y = -vx;
  float m = sqrt(w * w + x * x + y * y);
  if (m < 1e-3f) return;                  // upside down: keep last
  q0 = w / m; q1 = x / m; q2 = y / m; q3 = 0;
}
void integrateGyro(float dt) {
  const float k = 0.5f * dt * 0.0174533f;
  float wx = gx * k, wy = gy * k, wz = gz * k;
  float n0 = q0 - q1 * wx - q2 * wy - q3 * wz;
  float n1 = q1 + q0 * wx + q2 * wz - q3 * wy;
  float n2 = q2 + q0 * wy + q3 * wx - q1 * wz;
  float n3 = q3 + q0 * wz + q1 * wy - q2 * wx;
  float n = 1.0f / sqrt(n0 * n0 + n1 * n1 + n2 * n2 + n3 * n3);
  q0 = n0 * n; q1 = n1 * n; q2 = n2 * n; q3 = n3 * n;
}
float fatan2(float y, float x) {          // compact atan2, error < 0.3 deg
  float ay = fabs(y), ax = fabs(x), a;
  if (ax + ay < 1e-9f) return 0;
  if (ax >= ay) { float r = ay / ax; a = r * (0.9724f - 0.1919f * r * r); }
  else          { float r = ax / ay; a = 1.5708f - r * (0.9724f - 0.1919f * r * r); }
  if (x < 0) a = 3.14159f - a;
  return y < 0 ? -a : a;
}
float ux, uy, uz = 1;                     // world "up" seen in the body frame
void updateTilt() {
  ux = 2 * (q1 * q3 - q0 * q2); uy = 2 * (q2 * q3 + q0 * q1); uz = 1 - 2 * (q1 * q1 + q2 * q2);
  tiltX = fatan2(uy, uz) * 57.2958f;
  tiltY = fatan2(-ux, uz) * 57.2958f;
  tilt  = fatan2(sqrt(ux * ux + uy * uy), uz) * 57.2958f;
}
float verticalAccel() {                   // m/s^2, world frame, gravity removed (call after updateTilt)
  return (ux * ax + uy * ay + uz * az - 1.0f) * G;
}
void fuseAltitude(float dt, bool useAccel) {
  if (useAccel) { vel += verticalAccel() * dt; alt += vel * dt; }
  if (baroNew) {
    baroNew = false;
    float e = baroAlt - alt;
    alt += (useAccel ? 0.10f : 0.30f) * e;
    vel += (useAccel ? 0.05f : 0.10f) * e;
  }
  if (alt > maxAlt) maxAlt = alt;
}

// ------------------------------------------------------------------ landing burn prediction
float burnoutAlt(float h, float v) {      // altitude at landing-motor burnout if we fire right now
  float v1 = v - G * IGN_DELAY_S;
  float h1 = h + v * IGN_DELAY_S - 0.5f * G * IGN_DELAY_S * IGN_DELAY_S;
  // drag during the burn stops us higher than the vacuum answer (factor fitted in simulation)
  return h1 + v1 * F15_TB + S_BURN + (0.6125f * CDA / LAND_MASS_KG) * v1 * v1 * (F15_TB * F15_TB * 0.28f);
}
float predictTouchdown(float H) {         // falling from apogee H and firing on time: speed at burnout
  // fall speed u at motor start solves  u^2/2g + u*TB = H + S - margin  (burn ends at the ground)
  float u = G * (sqrt(F15_TB * F15_TB + 2 * (H + S_BURN - LAND_MARGIN) / G) - F15_TB);
  return DV_BURN - u;                     // m/s, + = up
}

// ------------------------------------------------------------------ TVC
void tvcCenter() {
  ix = iy = 0; usX = X_CENTER_US; usY = Y_CENTER_US;
  sx.writeMicroseconds(usX); sy.writeMicroseconds(usY);
}
void tvcControl(float dt) {
  ix = constrain(ix + tiltX * dt, -20.0f, 20.0f);
  iy = constrain(iy + tiltY * dt, -20.0f, 20.0f);
  float cx = -(KP * tiltX + KI * ix + KD * gx);          // correction about body X
  float cy = -(KP * tiltY + KI * iy + KD * gy);          // correction about body Y
  cx = constrain(cx, -GIMBAL_MAX, GIMBAL_MAX);
  cy = constrain(cy, -GIMBAL_MAX, GIMBAL_MAX);
  if (SWAP_XY) { float t = cx; cx = cy; cy = t; }
  usX = X_CENTER_US + (int)(SIGN_X * cx * US_PER_DEG);
  usY = Y_CENTER_US + (int)(SIGN_Y * cy * US_PER_DEG);
  sx.writeMicroseconds(usX); sy.writeMicroseconds(usY);
}

// ------------------------------------------------------------------ pyro, chute, ADC, buzzer
void fire(uint8_t ch, uint16_t ms) {
  digitalWrite(PYRO_PIN[ch], HIGH);
  pyroEnd[ch] = millis() + ms; if (!pyroEnd[ch]) pyroEnd[ch] = 1;
  pyroFired |= 1 << ch;
  Serial.print(F("FIRE P")); Serial.println(ch + 1);
}
void pyroService() {
  for (uint8_t i = 0; i < 4; i++)
    if (pyroEnd[i] && (int32_t)(millis() - pyroEnd[i]) >= 0) { digitalWrite(PYRO_PIN[i], LOW); pyroEnd[i] = 0; }
}
void deployChute() {
  if (chuteOpen) return;
  chute.write(CHUTE_OPEN); chuteOpen = true;
  Serial.println(F("CHUTE"));
}
void readAdc() {
  contMask = 0;
  for (uint8_t i = 0; i < 4; i++) if (analogRead(CONT_PIN[i]) > 80) contMask |= 1 << i;
  armed = analogRead(A7) > 300;                       // ~2.1 V when the ARM plug is in
  vbat  = analogRead(A6) * (5.0f / 1023.0f) * (133.0f / 33.0f);
}
// buzzer: Timer2 toggles D9 (PB1); much smaller than tone()
volatile uint16_t buzzLeft;
ISR(TIMER2_COMPA_vect) {
  if (buzzLeft) { PINB = _BV(1); buzzLeft--; }
  else { TIMSK2 = 0; PORTB &= ~_BV(1); }
}
void beep(uint16_t f, uint16_t ms) {
  TIMSK2 = 0;
  TCCR2A = _BV(WGM21); TCCR2B = _BV(CS22);              // CTC, 16 MHz / 64 = 250 kHz
  OCR2A = (uint8_t)(125000UL / f - 1);                   // valid for 490 Hz .. 60 kHz
  TCNT2 = 0;
  buzzLeft = (uint32_t)f * ms / 500;                     // two toggles per cycle
  TIMSK2 = _BV(OCIE2A);
}
void noBeep() { buzzLeft = 0; }

// ------------------------------------------------------------------ logging (CSV)
void openLog() {
  char name[] = "FLT00.CSV";
  for (uint8_t i = 0; i < 100; i++) {
    name[3] = '0' + i / 10; name[4] = '0' + i % 10;
    if (!SD.exists(name)) break;
  }
  logFile = SD.open(name, FILE_WRITE);
  if (!logFile) { sdOK = false; return; }
  logFile.println(F("ms,st,alt_cm,vel_cms,ax_mg,ay_mg,az_mg,gx_ddps,gy_ddps,gz_ddps,tx_cdeg,ty_cdeg,sx_us,sy_us,vb_mV,cont,fired,chute"));
  logFile.flush();
  Serial.print(F("log: ")); Serial.println(name);
}
void logLine() {
  if (!sdOK || !logFile) return;
  long v[17] = { (long)millis(), state, (long)(alt * 100), (long)(vel * 100),
                 (long)(ax * 1000), (long)(ay * 1000), (long)(az * 1000),
                 (long)(gx * 10), (long)(gy * 10), (long)(gz * 10),
                 (long)(tiltX * 100), (long)(tiltY * 100), usX, usY,
                 (long)(vbat * 1000), contMask, pyroFired };
  for (uint8_t i = 0; i < 17; i++) { logFile.print(v[i]); logFile.print(','); }
  logFile.println(chuteOpen);
}

// ------------------------------------------------------------------ bench commands (USB serial, PAD only)
char cmd[12]; uint8_t cmdLen;
void printStatus() {
  Serial.print(F("state ")); Serial.print(state);   // 0 PAD 1 BOOST 2 COAST 3 CHUTE 4 WAIT_IGN 5 LAND_BURN 6 LANDED
  Serial.print(F(" | IMU/BARO/SD (1=ok) ")); Serial.print(imuOK); Serial.print(baroOK); Serial.println(sdOK);
  Serial.print(F("batt mV ")); Serial.print((int)(vbat * 1000)); Serial.print(F(" | ARM plug ")); Serial.println(armed ? F("IN") : F("out"));
  Serial.print(F("continuity P1..P4: "));
  for (uint8_t i = 0; i < 4; i++) Serial.print(contMask & (1 << i) ? F("Y ") : F("- "));
  Serial.println();
  Serial.print(F("accel mg ")); Serial.print((int)(ax * 1000)); Serial.print(' '); Serial.print((int)(ay * 1000)); Serial.print(' '); Serial.print((int)(az * 1000));
  Serial.print(F(" | tilt X/Y deg ")); Serial.print((int)tiltX); Serial.print(' '); Serial.print((int)tiltY);
  Serial.print(F(" | alt cm ")); Serial.print((long)(alt * 100)); Serial.print(F(" | P Pa ")); Serial.println((long)pressure);
}
void servoSweep() {
  Serial.println(F("sweep: X then Y, +/- max"));
  const int d = (int)(GIMBAL_MAX * US_PER_DEG);
  int seq[] = {0, d, -d, 0};
  for (uint8_t i = 0; i < 4; i++) { sx.writeMicroseconds(X_CENTER_US + seq[i]); delay(600); }
  for (uint8_t i = 0; i < 4; i++) { sy.writeMicroseconds(Y_CENTER_US + seq[i]); delay(600); }
}
void handleCommand() {
  if (!strcmp(cmd, "s") || !strcmp(cmd, "status")) printStatus();
  else if (!strcmp(cmd, "sweep")) servoSweep();
  else if (!strcmp(cmd, "tvc"))  { tvcTest = !tvcTest; if (!tvcTest) tvcCenter(); Serial.println(tvcTest ? F("TVC test ON: lean the rocket") : F("TVC test off")); }
  else if (!strcmp(cmd, "open")) { chute.write(CHUTE_OPEN); Serial.println(F("chute OPEN")); }
  else if (!strcmp(cmd, "lock")) { chute.write(CHUTE_LOCK); chuteOpen = false; Serial.println(F("chute LOCK")); }
  else if (!strcmp(cmd, "beep")) beep(4000, 300);
  else if (!strncmp(cmd, "fire", 4) && cmd[4] >= '1' && cmd[4] <= '4' && !cmd[5]) {
    if (!armed) Serial.println(F("ARM plug is out - nothing will fire"));
    fire(cmd[4] - '1', cmd[4] == '3' ? BURNWIRE_MS : EMATCH_MS);
  }
  else Serial.println(F("cmds: s | sweep | tvc | open | lock | beep | fire1..fire4"));
}
void serialService() {
  while (Serial.available()) {
    char c = Serial.read();
    if (c == '\n' || c == '\r') { if (cmdLen) { cmd[cmdLen] = 0; handleCommand(); cmdLen = 0; } }
    else if (cmdLen < sizeof(cmd) - 1) cmd[cmdLen++] = c;
  }
}

// ------------------------------------------------------------------ setup
void setup() {
  for (uint8_t i = 0; i < 4; i++) { digitalWrite(PYRO_PIN[i], LOW); pinMode(PYRO_PIN[i], OUTPUT); }
  chute.write(CHUTE_LOCK); chute.attach(PIN_CHUTE);   // hold the latch closed first
  sx.writeMicroseconds(X_CENTER_US); sx.attach(PIN_SX);
  sy.writeMicroseconds(Y_CENTER_US); sy.attach(PIN_SY);
  Serial.begin(115200);
  Wire.begin(); Wire.setClock(400000);
#if defined(WIRE_HAS_TIMEOUT)
  Wire.setWireTimeout(3000, true);        // never hang the flight loop on a stuck I2C bus
#endif
  imuOK  = imuInit();
  baroOK = baroInit();
  sdOK   = SD.begin(PIN_SD);
  if (sdOK) openLog();
  // gyro bias + level + ground pressure (keep the rocket still for 2 s)
  float sgx = 0, sgy = 0, sgz = 0; float sax = 0, say = 0, saz = 0; uint16_t n = 0;
  uint32_t t0 = millis();
  while (millis() - t0 < 2000) {
    baroService();
    if (imuOK && imuRead()) { sgx += rgx; sgy += rgy; sgz += rgz; sax += ax; say += ay; saz += az; n++; }
    if (baroNew) { baroNew = false; p0 = p0 > 0 ? p0 * 0.9f + pressure * 0.1f : pressure; }
    delay(4);
  }
  if (n) { gbx = sgx / n; gby = sgy / n; gbz = sgz / n; lax = sax / n; lay = say / n; laz = saz / n; }
  levelFromAccel(); updateTilt();
  readAdc();
  printStatus();
  beep(imuOK && baroOK && sdOK ? 2500 : 600, imuOK && baroOK && sdOK ? 150 : 1000);
  lastCtl = micros();
}

// ------------------------------------------------------------------ main loop (200 Hz)
uint16_t launchCount, stillCount;
void loop() {
  baroService();
  pyroService();
  uint32_t now = micros();
  if (now - lastCtl < 5000) return;
  float dt = (now - lastCtl) * 1e-6f;
  lastCtl = now;
  if (dt > 0.1f) dt = 0.1f;                // after an SD stall, don't over-integrate
  uint32_t ms = millis();
  bool ok = imuOK && imuRead();

  switch (state) {
    case PAD: {
      if (ok) {                              // track gyro bias + level while sitting still
        float gmag = fabs(gx) + fabs(gy) + fabs(gz);
        if (az < 1.3f && gmag < 6) {
          gbx += 0.002f * (rgx - gbx); gby += 0.002f * (rgy - gby); gbz += 0.002f * (rgz - gbz);
          lax += 0.02f * (ax - lax); lay += 0.02f * (ay - lay); laz += 0.02f * (az - laz);
          levelFromAccel();
        } else integrateGyro(dt);
        updateTilt();
      }
      if (baroNew && fabs(vel) < 1 && launchCount == 0) {   // slow ground-pressure tracking
        p0 = p0 * 0.999f + pressure * 0.001f; baroAlt = 0;
      }
      fuseAltitude(dt, false); vel = 0;
      serialService();
      if (tvcTest) tvcControl(dt);
      if (ms - lastAdc > 200) { lastAdc = ms; readAdc(); }
      bool ready = imuOK && baroOK && sdOK && tilt < 30 && vbat > 7.0f;   // beeps only
      if (ms - lastBeep > 3000) {            // pad beeps: high chirp = ready, low buzz = not ready
        lastBeep = ms;
        beep(ready ? 3000 : 700, ready ? (armed ? 300 : 80) : 400);
      }
      if (ok && tilt < 30 && !tvcTest && az > LAUNCH_G) {   // never blocked by battery/SD
        if (++launchCount * 5 >= LAUNCH_MS) {
          state = BOOST; tLaunch = ms - LAUNCH_MS; alt = 0; vel = 0; maxAlt = 0; ix = iy = 0; confirmed = false;
          noBeep();
          Serial.println(F("LIFTOFF"));
        }
      } else launchCount = 0;
      break;
    }
    case BOOST:
      if (ok) { integrateGyro(dt); updateTilt(); tvcControl(dt); }
      fuseAltitude(dt, ok);
      if ((ms - tLaunch > 500 && az < 0.3f) || ms - tLaunch > BURN_MAX_MS) {
        state = COAST; tvcCenter(); Serial.println(F("BURNOUT"));
      }
      break;
    case COAST:
      if (ok) { integrateGyro(dt); updateTilt(); }
      fuseAltitude(dt, ok);
      if (vel < 0) { if (!tCond) tCond = ms; } else tCond = 0;
      if (confirmed && ((tCond && ms - tCond > 200 && ms - tLaunch > 2000) || ms - tLaunch > APOGEE_MAX_MS)) {
        tEvent = ms; tCond = 0;
        Serial.print(F("APOGEE cm ")); Serial.println((long)(maxAlt * 100));
        float vtd = predictTouchdown(maxAlt);
        if (FLIGHT_MODE == MODE_LANDING) { Serial.print(F("predicted touchdown cm/s ")); Serial.println((long)(vtd * 100)); }
        if (FLIGHT_MODE == MODE_LANDING && vtd > -MAX_TOUCHDOWN && vtd < 0.5f && tilt <= MAX_TILT && ms - tLaunch <= APOGEE_MAX_MS)
          state = WAIT_IGNITE;
        else { deployChute(); state = CHUTE_DESCENT; }
      }
      break;
    case CHUTE_DESCENT:
      if (ok) { integrateGyro(dt); updateTilt(); }
      fuseAltitude(dt, ok);
      if (!legsDone && alt < LEGS_ALT && ms - tEvent > 1000) { fire(P_LEGS, BURNWIRE_MS); legsDone = true; }
      break;
    case WAIT_IGNITE: {
      if (ok) { integrateGyro(dt); updateTilt(); }
      fuseAltitude(dt, ok);
      // fire when a burn started now (after the igniter delay) would end right at the ground
      if (vel < 0 && burnoutAlt(alt, vel) <= LAND_MARGIN) {
        if (tilt > MAX_TILT) { deployChute(); state = CHUTE_DESCENT; Serial.println(F("ABORT: tilt")); break; }
        fire(P_LANDING, EMATCH_MS); fire(P_LEGS, BURNWIRE_MS); legsDone = true;
        state = LAND_BURN; tEvent = ms; ix = iy = 0;
      } else if (alt < 8) { deployChute(); state = CHUTE_DESCENT; Serial.println(F("ABORT: never triggered")); }
      break;
    }
    case LAND_BURN:
      if (ok) { integrateGyro(dt); updateTilt(); tvcControl(dt); }
      fuseAltitude(dt, ok);
      if (az > 1.3f) thrustSeen = true;
      if (!thrustSeen && ms - tEvent > (uint32_t)(IGN_DELAY_S * 1000) + 800) {           // no light -> chute
        deployChute(); tvcCenter(); state = CHUTE_DESCENT; Serial.println(F("ABORT: no ignition"));
      }
      if (thrustSeen && ms - tEvent > 4500 && alt > 8 && vel < -6) {                     // burnt out too high
        deployChute(); tvcCenter(); state = CHUTE_DESCENT; Serial.println(F("ABORT: high burnout"));
      }
      break;
    case LANDED:
      if (ms - lastBeep > 2000) { lastBeep = ms; beep(3500, 500); }   // locator beeps
      serialService();
      break;
  }

  // liftoff confirmation: a bump on the pad never gets past here
  if ((state == BOOST || state == COAST) && !confirmed) {
    if (alt > CONFIRM_ALT) { confirmed = true; Serial.println(F("CLIMB CONFIRMED")); }
    else if (ms - tLaunch > CONFIRM_MS) {
      state = PAD; tvcCenter(); launchCount = 0; alt = vel = 0; Serial.println(F("false liftoff - back to PAD"));
    }
  }

  // touchdown: low, slow, still for 1.5 s
  if (state == CHUTE_DESCENT || state == LAND_BURN) {
    float a2 = ax * ax + ay * ay + az * az;
    bool still = ok && a2 > 0.64f && a2 < 1.44f && fabs(gx) + fabs(gy) + fabs(gz) < 20 && alt < 3 && fabs(vel) < 0.7f;
    stillCount = still ? stillCount + 1 : 0;
    if (stillCount > 300) {
      state = LANDED; tvcCenter();
      if (sdOK && logFile) { logLine(); logFile.close(); sdOK = false; }
      Serial.println(F("LANDED"));
    }
  }

  // logging: 10 Hz on the pad, 40 Hz in flight; no flush during burns (SD stalls)
  uint16_t period = state == PAD ? 100 : 25;
  if (state != LANDED && ms - lastLog >= period) {
    lastLog = ms; logLine();
    bool burning = state == BOOST || state == LAND_BURN;
    if (!burning && ms - lastFlush > 1000) { lastFlush = ms; if (sdOK && logFile) logFile.flush(); }
  }
}
