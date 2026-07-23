/**
 * SafeAlert / anti-esmagamento — ESP32
 *
 * Modelo geométrico forte (não é trilateração clássica de 1 ponto):
 *   h_i = s_i + r_i * u_i
 *   classificar: dentro do envelope do cesto? teto vs parede?
 *   reforçar com Δh da elevação
 *   só então aplicar faixas:
 *     d > 6.0          -> LIVRE
 *     3.5 < d <= 6.0   -> AMARELO
 *     1.5 < d <= 3.5   -> VERMELHO + buzzer
 *     d <= 1.5         -> BLOQUEIO (se geométrica recomendar)
 *
 * Hardware exemplo: HC-SR04 (3x). SafeAlert MVP: VL53L1X + TCA9548A.
 */

#include <Arduino.h>
#include "config.h"
#include "geometry.h"

enum EstadoSeguranca {
  LIVRE = 0,
  AMARELO,
  VERMELHO,
  BLOQUEIO
};

EstadoSeguranca estado = LIVRE;
DiagnosticoGeometrico diag{};
float distAmeacaM = NAN;
bool bloqueioAtivo = false;

float rAtual[NUM_SENSORES];
float rPrev[NUM_SENSORES];
HitPoint hits[NUM_SENSORES];

float alturaAtualM = 0.0f;
float alturaPrevM = 0.0f;

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

  unsigned long duracao = pulseIn(echoPin, HIGH, 30000UL);
  if (duracao == 0) return NAN;
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
  if (ok == 0) return NAN;
  return (soma / ok) / 100.0f;
}

void lerTodosSensores() {
  for (int i = 0; i < NUM_SENSORES; i++) {
    rPrev[i] = rAtual[i];
    rAtual[i] = lerSensorMetros(i);
    hits[i] = calcularHit(i, rAtual[i], rPrev[i]);
  }
}

// -------------------- Elevação --------------------

float lerAlturaPlataformaM() {
  if (PIN_ALTURA_ANALOG >= 0) {
    // Exemplo: mapear 0..3.3V -> 0..8 m (ajuste à sua calibração)
    int raw = analogRead(PIN_ALTURA_ANALOG);
    return (raw / 4095.0f) * 8.0f;
  }
  // Sem sensor de altura: Δh=0 → classificador usa envelope/planos
  return alturaAtualM;
}

bool plataformaSubindo(float deltaH) {
  if (USAR_SINAL_SUBINDO) {
    return digitalRead(PIN_SUBINDO) == HIGH;
  }
  (void)deltaH;
  return true;  // protótipo: sempre avalia geometria
}

// -------------------- Severidade (faixas) --------------------

EstadoSeguranca severidadePorDistancia(float d, bool jaBloqueado) {
  if (isnan(d)) {
    // Sem ameaça geométrica medida: livre (leituras inválidas já tratadas à parte)
    return LIVRE;
  }

  if (jaBloqueado) {
    if (d > DIST_LIBERA_BLOQUEIO_M) {
      // libera histerese e reclassifica abaixo
    } else {
      return BLOQUEIO;
    }
  }

  if (d <= DIST_BLOQUEIO_M) return BLOQUEIO;
  if (d <= DIST_VERMELHO_M) return VERMELHO;
  if (d <= DIST_AMARELO_M)  return AMARELO;
  return LIVRE;
}

EstadoSeguranca decidirEstado(const DiagnosticoGeometrico& g, bool jaBloqueado) {
  // Fail-safe: se esperávamos leituras e todas caíram, bloqueia
  // (no protótipo só quando já havia bloqueio / ameaça recente — evite travar no boot sem alvos)
  if (g.classe == CLASSE_NENHUM) {
    return jaBloqueado ? BLOQUEIO : LIVRE;
  }

  // Parede / fora do escopo: NÃO sobe severidade de bloqueio
  if (g.classe == CLASSE_FORA_ESCOPO || g.classe == CLASSE_PAREDE) {
    EstadoSeguranca s = severidadePorDistancia(g.dAmeaca, false);
    // no máximo AMARELO fraco para monitorar (sem bloqueio)
    if (s == BLOQUEIO || s == VERMELHO) return AMARELO;
    return s;
  }

  // Teto / pontual no envelope / indefinido com consenso
  EstadoSeguranca s = severidadePorDistancia(g.dAmeaca, jaBloqueado);

  if (s == BLOQUEIO && !g.bloqueioRecomendado) {
    // geometria não confirma bloqueio duro → desce um nível
    return VERMELHO;
  }
  return s;
}

// -------------------- Atuadores --------------------

void aplicarSaidas(EstadoSeguranca e) {
  digitalWrite(PIN_LED_VERDE,    (e == LIVRE) ? HIGH : LOW);
  digitalWrite(PIN_LED_AMARELO,  (e == AMARELO || e == VERMELHO || e == BLOQUEIO) ? HIGH : LOW);
  digitalWrite(PIN_LED_VERMELHO, (e == VERMELHO || e == BLOQUEIO) ? HIGH : LOW);
  digitalWrite(PIN_LED_AZUL,     (e == BLOQUEIO) ? HIGH : LOW);

  bool permitirSubida = (e != BLOQUEIO);
  if (RELE_HIGH_PERMITE_SUBIDA) {
    digitalWrite(PIN_BLOQUEIO_SUBIDA, permitirSubida ? HIGH : LOW);
  } else {
    digitalWrite(PIN_BLOQUEIO_SUBIDA, permitirSubida ? LOW : HIGH);
  }

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
    case LIVRE:    return "LIVRE";
    case AMARELO:  return "AMARELO";
    case VERMELHO: return "VERMELHO";
    case BLOQUEIO: return "BLOQUEIO";
    default:       return "?";
  }
}

// -------------------- Setup / Loop --------------------

void setup() {
  Serial.begin(115200);
  delay(200);
  Serial.println();
  Serial.println(F("SafeAlert ESP32 — modelo geometrico forte"));
  Serial.println(F("Pipeline: hit = s + r*u | envelope | teto/parede | faixas"));

  for (int i = 0; i < NUM_SENSORES; i++) {
    pinMode(PIN_TRIG[i], OUTPUT);
    pinMode(PIN_ECHO[i], INPUT);
    digitalWrite(PIN_TRIG[i], LOW);
    rAtual[i] = NAN;
    rPrev[i] = NAN;
  }

  pinMode(PIN_LED_VERDE, OUTPUT);
  pinMode(PIN_LED_AMARELO, OUTPUT);
  pinMode(PIN_LED_VERMELHO, OUTPUT);
  pinMode(PIN_LED_AZUL, OUTPUT);
  pinMode(PIN_BUZZER, OUTPUT);
  pinMode(PIN_BLOQUEIO_SUBIDA, OUTPUT);

  if (USAR_SINAL_SUBINDO) {
    pinMode(PIN_SUBINDO, INPUT_PULLDOWN);
  }

  // Boot: permite subida até haver ameaça classificada ( protótipo ).
  // Em produto: preferir fail-safe BLOQUEIO até autoteste OK.
  estado = LIVRE;
  aplicarSaidas(estado);
}

void loop() {
  unsigned long agora = millis();
  if (agora - ultimoLoopMs < PERIODO_LOOP_MS) {
    return;
  }
  ultimoLoopMs = agora;

  alturaPrevM = alturaAtualM;
  alturaAtualM = lerAlturaPlataformaM();
  float deltaH = alturaAtualM - alturaPrevM;
  if (deltaH < 0.0f) deltaH = 0.0f;

  lerTodosSensores();
  diag = classificarObstaculo(hits, NUM_SENSORES, deltaH);
  distAmeacaM = diag.dAmeaca;

  estado = decidirEstado(diag, bloqueioAtivo);
  bloqueioAtivo = (estado == BLOQUEIO);
  aplicarSaidas(estado);

  static unsigned long lastPrint = 0;
  if (agora - lastPrint > 300) {
    lastPrint = agora;
    Serial.print(F("classe="));
    Serial.print(nomeClasse(diag.classe));
    Serial.print(F(" hitsEnv="));
    Serial.print(diag.hitsNoEnvelope);
    Serial.print(F("/"));
    Serial.print(diag.hitsValidos);
    Serial.print(F(" d_ameaca="));
    if (isnan(distAmeacaM)) Serial.print(F("NaN"));
    else {
      Serial.print(distAmeacaM, 2);
      Serial.print(F("m"));
    }
    Serial.print(F(" dH="));
    Serial.print(deltaH, 3);
    Serial.print(F(" estado="));
    Serial.print(nomeEstado(estado));
    Serial.print(F(" blkRec="));
    Serial.println(diag.bloqueioRecomendado ? F("1") : F("0"));

    for (int i = 0; i < NUM_SENSORES; i++) {
      Serial.print(F("  S"));
      Serial.print(i);
      if (!hits[i].valido) {
        Serial.println(F(": --"));
        continue;
      }
      Serial.print(F(": r="));
      Serial.print(hits[i].r, 2);
      Serial.print(F(" h=("));
      Serial.print(hits[i].h.x, 2);
      Serial.print(F(","));
      Serial.print(hits[i].h.y, 2);
      Serial.print(F(","));
      Serial.print(hits[i].h.z, 2);
      Serial.print(F(") env="));
      Serial.println(hits[i].noEnvelope ? F("1") : F("0"));
    }
  }
}
