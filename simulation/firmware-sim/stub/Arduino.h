#pragma once
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <cmath>
#include <string>
using std::sqrt; using std::atan2; using std::log; using std::fabs;
extern uint64_t simUs;
inline uint32_t micros(){ return (uint32_t)simUs; }
inline uint32_t millis(){ return (uint32_t)(simUs/1000); }
void simStep(uint32_t us);
inline void delay(uint32_t ms){ simStep(ms*1000); }
#define F(s) (s)
#define _BV(b) (1u<<(b))
#define ISR(v) void v()
extern volatile uint8_t PINB, PORTB, TIMSK2, TCCR2A, TCCR2B, OCR2A, TCNT2;
#define WGM21 1
#define CS22 2
#define OCIE2A 1
enum { A0=14, A1, A2, A3, A4, A5, A6, A7 };
#define HIGH 1
#define LOW 0
#define OUTPUT 1
void digitalWrite(uint8_t p, uint8_t v); inline void pinMode(uint8_t, uint8_t){}
int analogRead(uint8_t p);
template<class T, class L, class H> T constrain(T x, L lo, H hi){ return x<lo?(T)lo:(x>hi?(T)hi:x); }
extern std::string simLog;
struct SerialC {
  void begin(long){}
  int available(); int read();
  void print(const char* s){ simLog += s; fputs(s, stdout);} void print(char c){ char b[2]={c,0}; print(b);}
  void print(long v){ char b[24]; snprintf(b,24,"%ld",v); print(b);} void print(int v){print((long)v);} void print(unsigned v){print((long)v);}
  void print(uint8_t v){print((long)v);} void print(unsigned long v){print((long)v);} void print(float v){ char b[24]; snprintf(b,24,"%.2f",v); print(b);}
  template<class T> void println(T v){ print(v); print("\n"); }
  void println(){ print("\n"); }
};
extern SerialC Serial;
