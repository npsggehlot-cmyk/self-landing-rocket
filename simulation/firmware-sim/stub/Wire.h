#pragma once
#include "Arduino.h"
#define WIRE_HAS_TIMEOUT 1
struct TwoWire {
  uint8_t addr, reg, buf[16], n, idx; bool hasReg;
  void begin(){} void setClock(long){} void setWireTimeout(int, bool){}
  void beginTransmission(uint8_t a){ addr=a; hasReg=false; }
  void write(uint8_t v);
  uint8_t endTransmission(bool stop=true);
  uint8_t requestFrom(uint8_t a, uint8_t cnt);
  int read(){ return idx<n ? buf[idx++] : -1; }
};
extern TwoWire Wire;
