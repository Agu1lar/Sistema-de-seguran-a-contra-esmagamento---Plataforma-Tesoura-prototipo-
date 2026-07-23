#pragma once

// ============================================================
// SafeAlert / anti-esmagamento — ESP32
// Sensores no TOPO do cesto, apontando para CIMA
// ============================================================

#include <math.h>

#ifndef PI
#define PI 3.14159265f
#endif

// --- Modelo de folga do operador (arquitetura de distâncias) ---
// Sensor no TOPO do guarda-corpo; operador médio no piso do cesto.
// A máquina NÃO deve travar na altura de trabalho normal: o operador
// precisa conseguir alcançar o objeto acima. Só bloqueia em colisão iminente.
static const float H_OPERADOR_M           = 1.80f;  // altura média
static const float H_SENSOR_ACIMA_DECK_M  = 1.01f;  // topo do rail ≈ 1 m acima do piso do cesto
// Folga sobre a cabeça ≈ d - (H_OPERADOR - H_SENSOR_ACIMA_DECK)
// Trabalho confortável: folga cabeça ≳ 0,40 m  =>  d ≳ 1,20 m
// Bloqueio só em iminência: d ≤ 0,60 m (sensor → objeto)

// --- Faixas de severidade (metros), aplicadas APÓS filtro geométrico ---
// LIVRE:     d > 2,50 m     (folga ampla para trabalhar)
// AMARELO:   1,20 < d ≤ 2,50
// VERMELHO:  0,60 < d ≤ 1,20  (apertado — alarme, ainda sobe)
// BLOQUEIO:  d ≤ 0,60 m       (iminente)
static const float DIST_AMARELO_M          = 2.50f;
static const float DIST_VERMELHO_M         = 1.20f;
static const float DIST_BLOQUEIO_M         = 0.60f;
static const float DIST_LIBERA_BLOQUEIO_M  = 0.75f;  // histerese

// Alcance útil típico VL53L1X (visualização / validação)
static const float DIST_ALCANCE_UTIL_TOF_M = 4.00f;

static const float DIST_MAX_VALIDA_M = 5.00f;
static const float DIST_MIN_VALIDA_M = 0.03f;

static const int NUM_SENSORES = 3;

enum SensorId {
  SENSOR_TRASEIRA_L = 0,  // canto traseiro +Y
  SENSOR_TRASEIRA_R = 1,  // canto traseiro -Y
  SENSOR_LATERAL_R  = 2   // poste rail -Y em X≈-0,53 (longe do limiar da extensão)
};

// --- Geometria do cesto (metros) — alinhada ao modelo SJIII 3226 ---
// Escopo MVP: só o DECK PRINCIPAL (fixo). A extensão roll-out (~+X,
// X ≳ 0,105 m) fica FORA da cobertura — o operador pode estender o
// deck sem mover sensores nem alterar a lógica de FoV do protótipo.
static const float CESTO_SEMI_L_M       = 1.065f;  // semi-comprimento total (ref. OEM)
static const float CESTO_SEMI_W_M       = 0.355f;
static const float EXTENSAO_X_INICIO_M  = 0.105f;  // início da zona roll-out (+X)
static const float TOPO_RAIL_Z_M        = 2.16f;
static const float MARGEM_ENVELOPE_M    = 0.15f;

static const float ENVELOPE_Z_MIN_M = TOPO_RAIL_Z_M;
static const float ENVELOPE_X_MIN_M = -(CESTO_SEMI_L_M + MARGEM_ENVELOPE_M);
// Envelope de colisão PARA no limiar da extensão (não cobre o roll-out)
static const float ENVELOPE_X_MAX_M =  (EXTENSAO_X_INICIO_M + MARGEM_ENVELOPE_M);
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

// DISPOSIÇÃO: 3 sensores só na TRASEIRA do deck FIXO (X ≤ -0,50).
// Nada no limiar fixo/extensão (X≈0,05) — a extensão abre sem interferir.
//   Traseira L (-1.015,+0.355) | Traseira R (-1.015,-0.355) | Lateral R (-0.533,-0.355)
// Blender ToF: +Z = SENSOR_DIR. US legado: +X = feixe.
static const Vec3 SENSOR_POS[NUM_SENSORES] = {
  { -1.015f,  0.355f, TOPO_RAIL_Z_M },  // Traseira L
  { -1.015f, -0.355f, TOPO_RAIL_Z_M },  // Traseira R
  { -0.533f, -0.355f, TOPO_RAIL_Z_M }   // Lateral R (poste, longe da extensão)
};

// ~8° do vertical → centro da zona traseira
static const Vec3 SENSOR_DIR[NUM_SENSORES] = {
  {  0.0782f, -0.1151f, 0.9903f },  // Traseira L
  {  0.0782f,  0.1151f, 0.9903f },  // Traseira R
  { -0.0782f,  0.1151f, 0.9903f }   // Lateral R
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
