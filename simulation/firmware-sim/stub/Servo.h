#pragma once
#include "Arduino.h"
struct Servo { int us=1500; void attach(int){} void write(int deg){ us = 544 + deg*(2400-544)/180; } void writeMicroseconds(int u){ us=u; } };
