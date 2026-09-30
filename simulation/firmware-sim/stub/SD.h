#pragma once
#include "Arduino.h"
#define FILE_WRITE 1
struct File {
  FILE* f=nullptr; explicit operator bool() const { return f!=nullptr; }
  void print(long v){ fprintf(f,"%ld",v);} void print(char c){ fputc(c,f);} void print(const char* s){ fputs(s,f);}
  void print(int v){print((long)v);} void print(uint8_t v){print((long)v);} void print(bool v){print((long)v);}
  template<class T> void println(T v){ print(v); fputc('\n',f);} void flush(){ fflush(f);} void close(){ fclose(f); f=nullptr;}
};
struct SDC { bool begin(int){return true;} bool exists(const char*){return false;} File open(const char* n,int){ File x; x.f=fopen(("/tmp/claude-0/-home-claude/18c35358-e614-5f2c-b9f0-0f191b74fbf5/scratchpad/"+std::string(n)).c_str(),"w"); return x;} };
extern SDC SD;
