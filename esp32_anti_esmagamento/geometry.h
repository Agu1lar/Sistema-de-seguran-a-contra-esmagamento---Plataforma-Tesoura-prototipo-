#pragma once

#include "config.h"
#include <math.h>

// ============================================================
// Modelo geométrico forte
// ----------------------------------------------------------
// NÃO usamos trilateração clássica de um único ponto P.
// Cada ToF/US mede alcance ao longo do seu eixo/FoV.
//
// Pipeline:
//   1) h_i = s_i + r_i * u_i          (ponto de impacto)
//   2) h_i ∈ V_colisao ?              (escopo da máquina)
//   3) classificar plano teto/parede  (se 2+ hits)
//   4) correlacionar com elevação Δh
//   5) só então aplicar faixas (folga op. 1,8 m):
//        >2.50 livre | ≤2.50 amarelo | ≤1.20 vermelho | ≤0.60 bloqueio
// ============================================================

enum ClasseObstaculo {
  CLASSE_NENHUM = 0,
  CLASSE_FORA_ESCOPO,     // impacto fora do envelope (ex.: fachada)
  CLASSE_PAREDE,          // plano vertical / Δr≈0 na subida
  CLASSE_TETO,            // plano horizontal / fecha com Δh
  CLASSE_PONTUAL_ESCOPO,  // 1 hit dentro do envelope (indefinido)
  CLASSE_INDEFINIDO
};

struct HitPoint {
  bool  valido;
  float r;       // distância medida (m)
  float rPrev;   // distância anterior (m)
  Vec3  h;       // ponto de impacto estimado
  bool  noEnvelope;
};

struct DiagnosticoGeometrico {
  ClasseObstaculo classe;
  int   hitsValidos;
  int   hitsNoEnvelope;
  float dAmeaca;          // menor r entre hits no envelope (NaN se nenhum)
  bool  bloqueioRecomendado;
  bool  alertaFraco;      // fora do escopo / parede: monitorar, não bloquear
};

inline Vec3 vadd(Vec3 a, Vec3 b) { return {a.x + b.x, a.y + b.y, a.z + b.z}; }
inline Vec3 vscale(Vec3 a, float s) { return {a.x * s, a.y * s, a.z * s}; }
inline float vdist(Vec3 a, Vec3 b) {
  float dx = a.x - b.x, dy = a.y - b.y, dz = a.z - b.z;
  return sqrtf(dx * dx + dy * dy + dz * dz);
}

inline bool pontoNoEnvelope(const Vec3& h) {
  return (h.x >= ENVELOPE_X_MIN_M && h.x <= ENVELOPE_X_MAX_M &&
          h.y >= ENVELOPE_Y_MIN_M && h.y <= ENVELOPE_Y_MAX_M &&
          h.z >= ENVELOPE_Z_MIN_M);
}

inline HitPoint calcularHit(int i, float r, float rPrev) {
  HitPoint hp{};
  hp.valido = false;
  hp.r = r;
  hp.rPrev = rPrev;
  hp.noEnvelope = false;
  if (isnan(r) || r < DIST_MIN_VALIDA_M || r > DIST_MAX_VALIDA_M) {
    return hp;
  }
  hp.valido = true;
  hp.h = vadd(SENSOR_POS[i], vscale(SENSOR_DIR[i], r));
  hp.noEnvelope = pontoNoEnvelope(hp.h);
  return hp;
}

inline bool pareceTetoPorPlano(const HitPoint* hits, int n) {
  // Z semelhante entre hits válidos no envelope
  float zMin = 1e9f, zMax = -1e9f;
  int c = 0;
  for (int i = 0; i < n; i++) {
    if (!hits[i].valido || !hits[i].noEnvelope) continue;
    zMin = fminf(zMin, hits[i].h.z);
    zMax = fmaxf(zMax, hits[i].h.z);
    c++;
  }
  if (c < 2) return false;
  return (zMax - zMin) <= PLANO_Z_TOL_M;
}

inline bool pareceParedePorPlano(const HitPoint* hits, int n) {
  // X ou Y semelhante (plano vertical), com Z variando mais
  float xMin = 1e9f, xMax = -1e9f;
  float yMin = 1e9f, yMax = -1e9f;
  float zMin = 1e9f, zMax = -1e9f;
  int c = 0;
  for (int i = 0; i < n; i++) {
    if (!hits[i].valido) continue;
    xMin = fminf(xMin, hits[i].h.x); xMax = fmaxf(xMax, hits[i].h.x);
    yMin = fminf(yMin, hits[i].h.y); yMax = fmaxf(yMax, hits[i].h.y);
    zMin = fminf(zMin, hits[i].h.z); zMax = fmaxf(zMax, hits[i].h.z);
    c++;
  }
  if (c < 2) return false;
  bool verticalX = (xMax - xMin) <= PLANO_XY_TOL_M;
  bool verticalY = (yMax - yMin) <= PLANO_XY_TOL_M;
  bool zEspalha = (zMax - zMin) > PLANO_Z_TOL_M;
  return (verticalX || verticalY) && zEspalha;
}

inline bool fechaComoTeto(float r, float rPrev, float deltaH) {
  if (isnan(r) || isnan(rPrev) || deltaH < DH_MIN_PARA_CLASSIFICAR_M) return false;
  float fechou = rPrev - r;  // positivo se aproximou
  return fechou >= (FRACAO_FECHA_TETO * deltaH);
}

inline bool estavelComoParede(float r, float rPrev, float deltaH) {
  if (isnan(r) || isnan(rPrev) || deltaH < DH_MIN_PARA_CLASSIFICAR_M) return false;
  float fechou = fabsf(rPrev - r);
  return fechou < (FRACAO_ESTAVEL_PAREDE * deltaH);
}

/**
 * Classifica o conjunto de hits.
 * deltaH: quanto a plataforma subiu desde a amostra anterior (m). 0 se desconhecido.
 */
inline DiagnosticoGeometrico classificarObstaculo(const HitPoint* hits, int n, float deltaH) {
  DiagnosticoGeometrico d{};
  d.classe = CLASSE_NENHUM;
  d.hitsValidos = 0;
  d.hitsNoEnvelope = 0;
  d.dAmeaca = NAN;
  d.bloqueioRecomendado = false;
  d.alertaFraco = false;

  for (int i = 0; i < n; i++) {
    if (!hits[i].valido) continue;
    d.hitsValidos++;
    if (hits[i].noEnvelope) {
      d.hitsNoEnvelope++;
      if (isnan(d.dAmeaca) || hits[i].r < d.dAmeaca) {
        d.dAmeaca = hits[i].r;
      }
    }
  }

  if (d.hitsValidos == 0) {
    d.classe = CLASSE_NENHUM;
    return d;
  }

  // Só hits fora do envelope → fora do escopo da máquina (parede lateral típica)
  if (d.hitsNoEnvelope == 0) {
    d.classe = CLASSE_FORA_ESCOPO;
    d.alertaFraco = true;
    return d;
  }

  bool tetoPlano = pareceTetoPorPlano(hits, n);
  bool paredePlano = pareceParedePorPlano(hits, n);

  // Reforço por elevação (usa o hit de menor r no envelope)
  bool tetoElev = false;
  bool paredeElev = false;
  for (int i = 0; i < n; i++) {
    if (!hits[i].valido || !hits[i].noEnvelope) continue;
    if (fechaComoTeto(hits[i].r, hits[i].rPrev, deltaH)) tetoElev = true;
    if (estavelComoParede(hits[i].r, hits[i].rPrev, deltaH)) paredeElev = true;
  }

  if (paredePlano && !tetoPlano) {
    d.classe = CLASSE_PAREDE;
    d.alertaFraco = true;
    return d;
  }
  if (paredeElev && !tetoElev && d.hitsNoEnvelope == 1) {
    // um único sensor “grudado” na lateral durante a subida
    d.classe = CLASSE_PAREDE;
    d.alertaFraco = true;
    return d;
  }

  if (tetoPlano || tetoElev) {
    d.classe = CLASSE_TETO;
    d.bloqueioRecomendado =
        (d.hitsNoEnvelope >= MIN_SENSORES_CONSENSO_BLOQUEIO) ||
        (d.hitsNoEnvelope >= 1 && tetoElev);
    return d;
  }

  if (d.hitsNoEnvelope == 1) {
    d.classe = CLASSE_PONTUAL_ESCOPO;
    // conservador no protótipo: permite alertas por faixa, bloqueio só se muito perto
    d.bloqueioRecomendado = (!isnan(d.dAmeaca) && d.dAmeaca <= DIST_BLOQUEIO_M);
    return d;
  }

  // 2+ no envelope sem plano claro → trata como ameaça (fail-safe)
  d.classe = CLASSE_INDEFINIDO;
  d.bloqueioRecomendado = (d.hitsNoEnvelope >= MIN_SENSORES_CONSENSO_BLOQUEIO);
  return d;
}

inline const char* nomeClasse(ClasseObstaculo c) {
  switch (c) {
    case CLASSE_NENHUM:          return "NENHUM";
    case CLASSE_FORA_ESCOPO:     return "FORA_ESCOPO";
    case CLASSE_PAREDE:          return "PAREDE";
    case CLASSE_TETO:            return "TETO";
    case CLASSE_PONTUAL_ESCOPO:  return "PONTUAL_ESCOPO";
    case CLASSE_INDEFINIDO:      return "INDEFINIDO";
    default:                     return "?";
  }
}
