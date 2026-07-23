#pragma once

// ============================================================
// Protótipo anti-esmagamento — ESP32
// Sensores no TOPO do cesto, apontando para CIMA
// ============================================================

// --- Faixas de distância (metros) ---
static const float DIST_AMARELO_M   = 6.0f;  // atenção
static const float DIST_VERMELHO_M  = 3.5f;  // alerta + buzzer
static const float DIST_BLOQUEIO_M  = 1.5f;  // bloqueia subida

// Histerese: só libera bloqueio quando afastar um pouco
static const float DIST_LIBERA_BLOQUEIO_M = 1.7f;

// Leitura inválida / sem eco
static const float DIST_MAX_VALIDA_M = 8.0f;
static const float DIST_MIN_VALIDA_M = 0.03f;

// --- Pinos (ajuste conforme seu hardware) ---
// Exemplo com 3x HC-SR04. Para VL53L1X use I2C + XSHUT.
static const int PIN_TRIG[3] = {16, 17, 18};
static const int PIN_ECHO[3] = {19, 21, 22};

static const int PIN_LED_AMARELO   = 25;
static const int PIN_LED_VERMELHO  = 26;
static const int PIN_BUZZER        = 27;
static const int PIN_BLOQUEIO_SUBIDA = 32;  // relé NC recomendado (ativo = permitir? ver abaixo)

// true  => GPIO HIGH energiza relé e PERMITE subida
// false => GPIO HIGH energiza relé e BLOQUEIA subida
static const bool RELE_HIGH_PERMITE_SUBIDA = true;

// Opcional: entrada de “plataforma subindo” (encoder/fim de curso/PLC)
static const int  PIN_SUBINDO = 33;
static const bool USAR_SINAL_SUBINDO = false;

// Timing
static const unsigned long PERIODO_LOOP_MS     = 50;
static const unsigned long BUZZER_BEEP_ON_MS   = 120;
static const unsigned long BUZZER_BEEP_OFF_MS  = 180;
static const int           MEDIAS_POR_SENSOR   = 3;
