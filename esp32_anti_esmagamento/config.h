#pragma once

// ============================================================
// SafeAlert / anti-esmagamento — ESP32
// Sensores no TOPO do cesto, apontando para CIMA
// ============================================================

#include <math.h>

#ifndef PI
#define PI 3.14159265f
#endif

// --- Faixas de severidade (metros), aplicadas APÓS filtro geométrico ---
static const float DIST_AMARELO_M          = 6.0f;
static const float DIST_VERMELHO_M         = 3.5f;
static const float DIST_BLOQUEIO_M         = 1.5f;
static const float DIST_LIBERA_BLOQUEIO_M  = 1.7f;

static const float DIST_MAX_VALIDA_M = 8.0f;
static const float DIST_MIN_VALIDA_M = 0.03f;

static const int NUM_SENSORES = 3;

enum SensorId {
  SENSOR_PONTA_A = 0,
  SENSOR_MEIO    = 1,
  SENSOR_PONTA_B = 2
};

// --- Geometria do cesto (metros) — alinhada ao modelo SJIII 3226 ---
static const float CESTO_SEMI_L_M    = 1.065f;
static const float CESTO_SEMI_W_M    = 0.355f;
static const float TOPO_RAIL_Z_M     = 2.16f;
static const float MARGEM_ENVELOPE_M = 0.15f;

static const float ENVELOPE_Z_MIN_M = TOPO_RAIL_Z_M;
static const float ENVELOPE_X_MIN_M = -(CESTO_SEMI_L_M + MARGEM_ENVELOPE_M);
static const float ENVELOPE_X_MAX_M =  (CESTO_SEMI_L_M + MARGEM_ENVELOPE_M);
static const float ENVELOPE_Y_MIN_M = -(CESTO_SEMI_W_M + MARGEM_ENVELOPE_M);
static const float ENVELOPE_Y_MAX_M =  (CESTO_SEMI_W_M + MARGEM_ENVELOPE_M);

static const float PLANO_Z_TOL_M  = 0.25f;
static const float PLANO_XY_TOL_M = 0.20f;

static const float DH_MIN_PARA_CLASSIFICAR_M = 0.05f;
static const float FRACAO_FECHA_TETO       = 0.55f;
static const float FRACAO_ESTAVEL_PAREDE   = 0.25f;

static const int MIN_SENSORES_CONSENSO_BLOQUEIO = 2;

struct Vec3 {
  float x, y, z;
};

static const Vec3 SENSOR_POS[NUM_SENSORES] = {
  { -1.015f,  0.355f, TOPO_RAIL_Z_M },
  {  0.000f, -0.355f, TOPO_RAIL_Z_M },
  {  1.015f,  0.000f, TOPO_RAIL_Z_M }
};

static const Vec3 SENSOR_DIR[NUM_SENSORES] = {
  {  0.115f, -0.040f, 0.993f },
  {  0.000f,  0.000f, 1.000f },
  { -0.122f,  0.000f, 0.993f }
};

// --- Pinos (SafeAlert MVP: evoluir para I2C + TCA9548A) ---
static const int PIN_TRIG[NUM_SENSORES] = {16, 17, 18};
static const int PIN_ECHO[NUM_SENSORES] = {19, 21, 22};

static const int PIN_LED_VERDE       = 14;
static const int PIN_LED_AMARELO     = 25;
static const int PIN_LED_VERMELHO    = 26;
static const int PIN_LED_AZUL        = 13;
static const int PIN_BUZZER          = 27;
static const int PIN_BLOQUEIO_SUBIDA = 32;

static const bool RELE_HIGH_PERMITE_SUBIDA = true;

static const int  PIN_SUBINDO = 33;
static const bool USAR_SINAL_SUBINDO = false;
static const int  PIN_ALTURA_ANALOG = -1;

static const unsigned long PERIODO_LOOP_MS    = 50;
static const unsigned long BUZZER_BEEP_ON_MS  = 120;
static const unsigned long BUZZER_BEEP_OFF_MS = 180;
static const int           MEDIAS_POR_SENSOR  = 3;
