// Host simulation harness: runs the real RocketFC.ino against simulated sensors + physics.
#include <random>
#include "Arduino.h"
#include "Wire.h"
#include "SD.h"
#include "Servo.h"
uint64_t simUs = 0; std::string simLog;
volatile uint8_t PINB, PORTB, TIMSK2, TCCR2A, TCCR2B, OCR2A, TCNT2;
SerialC Serial; TwoWire Wire; SDC SD;
int SerialC::available(){ return 0; } int SerialC::read(){ return -1; }
#include "../../firmware/RocketFC/RocketFC.ino"

// ---------------- scenario ----------------
std::mt19937 rng(1); std::normal_distribution<double> N01(0, 1);
int scen = 0;                        // 0 chute flight, 1 pad bump, 2 landing flight
double IGN_T = 6.0, massAsc = 1.10, massLand = 0.95, trueIgnDelay = 0.35;
double h = 0, v = 0, sf = 1.0;       // altitude, velocity, specific force (g) along body z
bool flying = false, landed = false, chuteDeployed = false; double chuteT = -1, landIgnCmd = -1, legsT = -1;
double impactV = 0, apogeeTrue = 0; int pyroHigh[16];
double CT[][2]={{0,0},{0.063,2.13},{0.118,4.41},{0.158,8.36},{0.228,13.68},{0.34,20.82},{0.386,25.3},{0.425,24.9},{0.481,22.19},
 {0.583,17.93},{0.883,16.01},{1.191,14.50},{1.364,15.26},{1.569,15.56},{1.727,14.65},{2.066,14.19},{2.347,13.90},{2.662,13.75},
 {2.906,13.44},{3.08,13.29},{3.223,13.59},{3.316,13.44},{3.358,10.87},{3.4,7.85},{3.427,3.47},{3.45,0}};
double thrustF15(double tb){
  if (tb <= 0 || tb >= 3.45) return 0;
  for (int i = 1; i < 26; i++) if (tb < CT[i][0]) return CT[i-1][1] + (CT[i][1]-CT[i-1][1])*(tb-CT[i-1][0])/(CT[i][0]-CT[i-1][0]);
  return 0; }
void digitalWrite(uint8_t p, uint8_t val){
  double t = simUs * 1e-6;
  if (val && !pyroHigh[p]) { if (p == 4) landIgnCmd = t; if (p == 6 && legsT < 0) legsT = t; }
  pyroHigh[p] = val; }
int analogRead(uint8_t p){ bool armed = true; if (p >= A0 && p <= A3) return armed ? 430 : 244; if (p == A6) return 406; if (p == A7) return armed ? 426 : 120; return 0; }
void simStep(uint32_t us){
  double dt = us * 1e-6; simUs += us; double t = simUs * 1e-6;
  double m = (scen == 2 && t > IGN_T + 4) ? massLand : massAsc;
  double T = thrustF15(t - IGN_T);
  static double thrScale = getenv("THR") ? atof(getenv("THR")) : 1.0;
  if (scen == 2 && landIgnCmd > 0) T += thrScale * thrustF15(t - landIgnCmd - trueIgnDelay);
  if (scen == 1 && t > 6.0 && t < 6.08) { sf = 2.0; return; }
  if (scen == 1) { sf = 1.0; return; }          // someone bumps the rocket: 2 g for 80 ms
  if (!chuteDeployed && sx.us && chute.us < 800) { chuteDeployed = true; chuteT = t; }
  double k = getenv("NODRAG") ? 0 : 0.00168; if (chuteDeployed && t > chuteT + 0.5) k = m * 9.80665 / 25.0;   // chute: 5 m/s
  double D = k * v * fabs(v);
  double a = (T - D) / m - 9.80665;
  if (!flying && !landed) { if (T > m * 9.80665) flying = true; else { sf = 1.0; return; } }
  if (landed) { sf = 1.0; return; }
  v += a * dt; h += v * dt; sf = (T - D) / (m * 9.80665);
  if (h > apogeeTrue) apogeeTrue = h;
  if (h <= 0 && flying && t > IGN_T + 1) { impactV = v; h = 0; v = 0; landed = true; sf = 1.0; }
}
// ---------------- device models ----------------
uint8_t baroLast = 0;
void TwoWire::write(uint8_t v){ if (!hasReg) { reg = v; hasReg = true; if (addr == 0x77 && (v == 0x44 || v == 0x54)) baroLast = v; } }
uint8_t TwoWire::endTransmission(bool){ return 0; }
uint8_t TwoWire::requestFrom(uint8_t a, uint8_t cnt){
  n = cnt; idx = 0;
  if (a == 0x6A) {
    if (reg == 0x0F) { buf[0] = 0x6C; return cnt; }
    auto put = [&](int i, double val){ int16_t r = (int16_t)lround(val); buf[2*i] = r & 0xFF; buf[2*i+1] = (r >> 8) & 0xFF; };
    put(0, (1.0 + 0.2 * N01(rng)) / 0.070); put(1, (-0.8 + 0.2 * N01(rng)) / 0.070); put(2, (0.5 + 0.2 * N01(rng)) / 0.070);
    put(3, 0.02 * N01(rng) / 0.000976); put(4, 0.02 * N01(rng) / 0.000976); put(5, (sf + 0.02 * N01(rng)) / 0.000976);
    return cnt;
  }
  static const uint16_t Cc[7] = {0, 46372, 43981, 29059, 27842, 31553, 28165};
  if (reg >= 0xA2 && reg <= 0xAC) { uint16_t c = Cc[(reg - 0xA0) / 2]; buf[0] = c >> 8; buf[1] = c & 0xFF; return cnt; }
  if (reg == 0x00) {
    uint32_t D2v = 8077636, val = D2v;
    if (baroLast == 0x44) {
      double hb = h + 0.25 * N01(rng);
      double P = 101325.0 * pow(1 - 2.25577e-5 * hb, 5.25588);
      double dT = D2v - Cc[5] * 256.0, OFF = Cc[2] * 131072.0 + Cc[4] * dT / 64, SENS = Cc[1] * 65536.0 + Cc[3] * dT / 128;
      val = (uint32_t)((P * 32768 + OFF) * 2097152.0 / SENS);
    }
    buf[0] = val >> 16; buf[1] = val >> 8; buf[2] = val; return cnt;
  }
  return cnt;
}
int main(int argc, char** argv){
  scen = argc > 1 ? atoi(argv[1]) : 0; if (scen == 1) IGN_T = 1e9; if (argc > 2) trueIgnDelay = atof(argv[2]); if (argc > 3) massAsc = atof(argv[3]); if (argc > 4) massLand = atof(argv[4]);
  setup();
  uint32_t lastPrint = 0; State lastState = state;
  while (simUs < 60e6) {
    loop(); simStep(250);
    if (state != lastState) { printf("  [t=%.2fs] state %d -> %d | sim h=%.1f v=%.1f | fw alt=%.1f vel=%.1f\n", simUs*1e-6, lastState, state, h, v, alt, vel); lastState = state; }
    if (getenv("TRACE") && landIgnCmd > 0 && simUs % 250000 == 0) printf("   t=%.2f h=%.2f v=%.2f sf=%.2f | fw alt=%.2f vel=%.2f\n", simUs*1e-6, h, v, sf, alt, vel);
    if (state == LANDED && millis() - lastPrint > 100000) break;
  }
  printf("SUMMARY scen=%d trueApogee=%.1f fwMaxAlt=%.1f chuteT=%.2f legsT=%.2f landIgnCmd=%.2f impactV=%.2f final_state=%d pressure@pad=%.1fPa\n",
         scen, apogeeTrue, maxAlt, chuteT, legsT, landIgnCmd, impactV, state, p0);
}
