/**
 * Protótipo ESP32 — Anti-esmagamento plataforma elevatória
 *
 * Lógica (sensores no TOPO, apontando para CIMA):
 *   d > 6.0 m              -> LIVRE
 *   3.5 < d <= 6.0 m       -> AMARELO
 *   1.5 < d <= 3.5 m       -> VERMELHO + BUZZER
 *   d <= 1.5 m             -> BLOQUEAR SUBIDA
 *
 * Usa a MENOR distância válida entre os 3 sensores.
 * Opcional: correlacionar com “subindo” para filtrar parede lateral depois.
 *
 * Hardware exemplo: ESP32 + 3x HC-SR04 + LEDs + buzzer + relé
 * (Troque lerUltrassonico() por ToF VL53L1X se quiser.)
 */

#include <Arduino.h>
#include "config.h"

enum EstadoSeguranca {
  LIVRE = 0,
  AMARELO,
  VERMELHO,
  BLOQUEIO
};

EstadoSeguranca estado = LIVRE;
float distMinM = DIST_MAX_VALIDA_M;
bool bloqueioAtivo = false;

unsigned long ultimoLoopMs = 0;
unsigned long buzzerTickMs = 0;
bool buzzerFaseOn = false;

// -------------------- Sensores HC-SR04 --------------------

float lerUltrassonicoCm(int trigPin, int echoPin) {
  digitalWrite(trigPin, LOW);
  delayMicroseconds(2);
  digitalWrite(trigPin, HIGH);
  delayMicroseconds(10);
  digitalWrite(trigPin, LOW);

  // timeout ~30 ms (~5 m ida/volta com folga)
  unsigned long duracao = pulseIn(echoPin, HIGH, 30000UL);
  if (duracao == 0) {
    return NAN;
  }
  // som ~343 m/s => cm = us / 58
  return duracao / 58.0f;
}

float lerSensorMetros(int idx) {
  float soma = 0.0f;
  int ok = 0;
  for (int i = 0; i < MEDIAS_POR_SENSOR; i++) {
    float cm = lerUltrassonicoCm(PIN_TRIG[idx], PIN_ECHO[idx]);
    if (!isnan(cm) && cm > 0.0f) {
      soma += cm;
      ok++;
    }
    delay(5);
  }
  if (ok == 0) {
    return NAN;
  }
  return (soma / ok) / 100.0f;  // m
}

float menorDistanciaValida() {
  float melhor = NAN;
  for (int i = 0; i < 3; i++) {
    float d = lerSensorMetros(i);
    if (isnan(d)) {
      continue;
    }
    if (d < DIST_MIN_VALIDA_M || d > DIST_MAX_VALIDA_M) {
      continue;
    }
    if (isnan(melhor) || d < melhor) {
      melhor = d;
    }
  }
  return melhor;
}

// -------------------- Máquina de estados --------------------

EstadoSeguranca decidirEstado(float d, bool jaBloqueado) {
  // Sem leitura válida: fail-safe -> bloqueio (protótipo conservador)
  if (isnan(d)) {
    return BLOQUEIO;
  }

  // Histerese do bloqueio
  if (jaBloqueado) {
    if (d > DIST_LIBERA_BLOQUEIO_M) {
      // cai para a faixa correspondente abaixo
    } else {
      return BLOQUEIO;
    }
  }

  if (d <= DIST_BLOQUEIO_M) {
    return BLOQUEIO;
  }
  if (d <= DIST_VERMELHO_M) {
    return VERMELHO;
  }
  if (d <= DIST_AMARELO_M) {
    return AMARELO;
  }
  return LIVRE;
}

bool plataformaSubindo() {
  if (!USAR_SINAL_SUBINDO) {
    return true;  // no protótipo, sempre avalia
  }
  return digitalRead(PIN_SUBINDO) == HIGH;
}

/**
 * Esboço para o problema da parede lateral (próxima evolução):
 * se estiver subindo e a distância quase NÃO muda, tende a ser lateral.
 * Aqui só documentado — não altera o bloqueio ainda.
 */
bool pareceParedeLateral(float dAtual, float dAnterior, float deltaAlturaM) {
  if (isnan(dAtual) || isnan(dAnterior) || deltaAlturaM < 0.05f) {
    return false;
  }
  float fechaEsperado = deltaAlturaM;      // teto: d cai ~ com a subida
  float fechou = dAnterior - dAtual;
  // se quase não fechou, provavelmente lateral
  return fabsf(fechou) < (0.25f * fechaEsperado);
}

// -------------------- Atuadores --------------------

void aplicarSaidas(EstadoSeguranca e) {
  digitalWrite(PIN_LED_AMARELO,  (e == AMARELO || e == VERMELHO || e == BLOQUEIO) ? HIGH : LOW);
  digitalWrite(PIN_LED_VERMELHO, (e == VERMELHO || e == BLOQUEIO) ? HIGH : LOW);

  // Bloqueio de subida
  bool permitirSubida = (e != BLOQUEIO);
  if (RELE_HIGH_PERMITE_SUBIDA) {
    digitalWrite(PIN_BLOQUEIO_SUBIDA, permitirSubida ? HIGH : LOW);
  } else {
    digitalWrite(PIN_BLOQUEIO_SUBIDA, permitirSubida ? LOW : HIGH);
  }

  // Buzzer só em vermelho/bloqueio
  if (e == VERMELHO || e == BLOQUEIO) {
    unsigned long agora = millis();
    unsigned long fase = buzzerFaseOn ? BUZZER_BEEP_ON_MS : BUZZER_BEEP_OFF_MS;
    if (agora - buzzerTickMs >= fase) {
      buzzerTickMs = agora;
      buzzerFaseOn = !buzzerFaseOn;
    }
    digitalWrite(PIN_BUZZER, buzzerFaseOn ? HIGH : LOW);
  } else {
    digitalWrite(PIN_BUZZER, LOW);
    buzzerFaseOn = false;
  }
}

const char* nomeEstado(EstadoSeguranca e) {
  switch (e) {
    case LIVRE:     return "LIVRE";
    case AMARELO:   return "AMARELO";
    case VERMELHO:  return "VERMELHO";
    case BLOQUEIO:  return "BLOQUEIO";
    default:        return "?";
  }
}

// -------------------- Setup / Loop --------------------

void setup() {
  Serial.begin(115200);
  delay(200);
  Serial.println();
  Serial.println(F("ESP32 anti-esmagamento — prototipo"));
  Serial.println(F("Faixas: 6.0 amarelo | 3.5 vermelho+buzzer | 1.5 bloqueio"));

  for (int i = 0; i < 3; i++) {
    pinMode(PIN_TRIG[i], OUTPUT);
    pinMode(PIN_ECHO[i], INPUT);
    digitalWrite(PIN_TRIG[i], LOW);
  }

  pinMode(PIN_LED_AMARELO, OUTPUT);
  pinMode(PIN_LED_VERMELHO, OUTPUT);
  pinMode(PIN_BUZZER, OUTPUT);
  pinMode(PIN_BLOQUEIO_SUBIDA, OUTPUT);

  if (USAR_SINAL_SUBINDO) {
    pinMode(PIN_SUBINDO, INPUT_PULLDOWN);
  }

  // Fail-safe inicial: não permitir subida até primeira leitura boa
  estado = BLOQUEIO;
  aplicarSaidas(estado);
}

void loop() {
  unsigned long agora = millis();
  if (agora - ultimoLoopMs < PERIODO_LOOP_MS) {
    return;
  }
  ultimoLoopMs = agora;

  distMinM = menorDistanciaValida();
  estado = decidirEstado(distMinM, bloqueioAtivo);
  bloqueioAtivo = (estado == BLOQUEIO);

  // Se no futuro quiser só alertar parado e bloquear só subindo:
  // if (!plataformaSubindo() && estado == BLOQUEIO) estado = VERMELHO;

  aplicarSaidas(estado);

  static unsigned long lastPrint = 0;
  if (agora - lastPrint > 250) {
    lastPrint = agora;
    Serial.print(F("d_min="));
    if (isnan(distMinM)) {
      Serial.print(F("NaN"));
    } else {
      Serial.print(distMinM, 2);
      Serial.print(F(" m"));
    }
    Serial.print(F(" | estado="));
    Serial.println(nomeEstado(estado));
  }
}
