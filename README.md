# Sistema de segurança contra esmagamento — Plataforma Tesoura (protótipo)

Projeto de visualização 3D + lógica embarcada para um sistema de **detecção de obstáculos acima do cesto** em plataforma elevatória tipo tesoura, inspirado nas dimensões da **Skyjack SJIII 3226**.

O foco é um protótipo didático (TCC / prova de conceito): sensores no **topo do guarda-corpo**, apontando para **cima**, comunicando com um **ESP32** que sinaliza faixas de risco e pode **bloquear a subida**.

> **Premissa do projeto:** o desafio principal é **geométrico** (onde apontar, o que o FoV enxerga, como cobrir o volume do cesto sem confundir parede/operador). A montagem eletrônica é viável e relativamente direta — ver o arranjo SafeAlert MVP abaixo.

---

## Download do modelo 3D

Arquivo Blender do projeto (plataforma + sensores ultrassônicos + clone ToF):

📦 **[SJIII_3226_anti_esmagamento.blend](./SJIII_3226_anti_esmagamento.blend)**

Requisitos: Blender 4.x / 5.x recomendado.

---

## Visão geral

| Item | Descrição |
|------|-----------|
| Máquina de referência | Skyjack SJIII 3226 (dimensões oficiais) |
| Problema | Risco de esmagamento contra teto/viga na elevação |
| Desafio central | Geometria do FoV e cobertura do volume do cesto |
| Sensores (comparativo 3D) | Ultrassônico (lóbulo) × ToF VL53L1X (~27°) |
| Controle (MVP) | ESP32-S3 + 3× VL53L1X + TCA9548A |
| Atuação | LEDs, buzzer e relé (simulação de bloqueio de subida) |

### Por que os sensores ficam no topo?

Com a montagem no **alto do cesto** (e não no piso), o feixe olha para o espaço **acima** da plataforma. O operador e as ferramentas dentro do cesto ficam, em regra, **fora** do volume de leitura — isso reduz (não elimina) o problema de falso positivo por ocupação do cesto.

---

## Desafios previstos e soluções

O circuito (ESP32 + ToF + relé) é a parte mais “padrão”. O que realmente define se o sistema funciona no campo é a **geometria**.

### 1) Parede / fachada ao lado × obstáculo acima

**Problema**  
Sensor 1D só devolve distância. Perto de um prédio, o FoV pode “raspar” a fachada e gerar alerta/bloqueio **mesmo sem teto** no caminho de subida.

**Por que é geométrico**  
Depende do ângulo de montagem, da abertura do FoV (~27° no VL53L1X) e da proximidade lateral da máquina à parede.

**Soluções**
| Abordagem | Ideia |
|-----------|--------|
| Montagem | Apontar predominantemente para **cima**; inclinar pontas só o necessário (ex.: **7° para dentro** do cesto), evitando abrir FoV para a fachada |
| Envelope virtual | Só tratar como ameaça o que intersecta o prisma acima do cesto |
| Elevação da tesoura | Se `d` **cai junto com a subida** → tende a ser teto/viga; se `d` fica **quase constante** → tende a ser lateral |
| Consenso | Preferir bloqueio duro com **2+ sensores** concordando (ou central + boa qualidade) |

### 2) Operador e ferramentas dentro do cesto

**Problema**  
Braço, capacete ou ferramenta entrando no FoV pode parecer “obstáculo acima”.

**Por que a geometria resolve a maior parte**  
Com sensores **no topo do guarda-corpo**, o corpo do operador fica **abaixo** do plano de emissão. O falso positivo só aparece se algo entrar no cone para cima.

**Soluções**
| Abordagem | Ideia |
|-----------|--------|
| Montagem no topo | Principal mitigação — não olhar o interior do cesto |
| FoV estreito (ToF) | Menos “varredura” lateral que ultrassônico largo |
| Lógica por faixas | Não há “ignorar 0–2 m do piso”; as faixas valem para o que está **acima do sensor** |
| Evolução | ROI/multizona ToF ou filtro temporal (alvo móvel × estático), se ensaios pedirem |

### 3) Cobertura incompleta do volume do cesto

**Problema**  
Três sensores alinhados na mesma lateral deixam “buracos” de cobertura.

**Solução geométrica adotada no modelo 3D**  
Disposição **escalonada** (não colinear):

1. **Ponta A** — uma extremidade / fundo  
2. **Meio** — lateral de referência, **reto para cima**  
3. **Ponta B** — outra extremidade, em profundidade intermediária  

Pontas com **7° para dentro** → interseção dos cones acima da área de trabalho.

### 4) Ultrassônico × ToF (comparativo)

| | Ultrassônico | ToF (VL53L1X) |
|--|--------------|---------------|
| Forma do volume | Lóbulo suave (~15° útil + envelope ~30°) | Cone óptico mais nítido (~27°) |
| Multipath / eco | Mais sensível | Melhor em muitos cenários |
| Endereço I2C | N/A (GPIO) | Todos iguais → precisa mux ou XSHUT |
| Papel no projeto | Referência de campo acústico no Blender | Caminho preferido do MVP eletrônico |

### 5) Circuito / integração (secundário, mas necessário)

**Problema menor:** ler 3× VL53L1X (mesmo endereço `0x29`), acionar LEDs/buzzer/relé com segurança elétrica básica.

**Solução do MVP SafeAlert:** ESP32-S3 + multiplexador I2C **TCA9548A** + saídas com transistor/relé — ver seção abaixo.

---

## Galeria

### Vista geral — sistema ToF

![Vista geral ToF](images/tof_vista_geral.png)

### Detalhe do cesto e cones de leitura

![Detalhe cesto ToF](images/tof_detalhe_cesto.png)

### Comparativo na mesma cena (Ultrassônico × ToF)

![Comparativo US vs ToF](images/comparativo_us_tof.png)

### Arranjo eletrônico SafeAlert MVP (protoboard)

![SafeAlert MVP — arranjo na protoboard](images/safealert_mvp_protoboard.png)

---

## Hardware SafeAlert MVP — verificação do diagrama

O diagrama *“SafeAlert MVP — Arranjo Fictício na Protoboard”* está **conceitualmente correto** para um protótipo. Pontos principais:

### O que está certo

| Bloco | Avaliação |
|-------|-----------|
| **ESP32-S3 DevKit** | Adequado como controlador do MVP |
| **TCA9548A** | Solução correta: os 3× VL53L1X compartilham o mesmo endereço I2C |
| **S1 / S2 / S3** (traseiro, meio, dianteiro) | Combina com a ideia de cobertura longitudinal do cesto |
| **3V3 para mux/sensores e 5V para buzzer/relé** | Separação de trilhos coerente |
| **LEDs (verde / amarelo / vermelho / azul)** + **220 Ω** | Indicadores de estado claros para demonstração |
| **Buzzer via 2N2222 + 1 kΩ** | Evita sobrecarregar o GPIO do ESP32 |
| **Relé com contatos secos** | Boa escolha para *simular* bloqueio de subida sem amarrar ainda no circuito da máquina |
| **Botões ACK e Teste diário** | Úteis em protótipo de segurança (reconhecimento / autoteste) |
| **GND comum** entre 3V3 e 5V | Obrigatório — o diagrama prevê barramentos compartilhados |

### Atenções práticas (não invalidam o desenho)

1. **Alcance do VL53L1X** — típico até ~**4 m** (alvo e luz dependentes). A faixa amarela de **6 m** é útil como lógica de produto, mas no hardware ToF pode não haver leitura confiável tão longe; trate 6 m como limiar lógico / meta, e calibere no ensaio.  
2. **Módulo relé SRD** — muitos são ativos em nível baixo e já trazem optoacoplador; confirme se o `IN` aceita 3,3 V do ESP32-S3.  
3. **Pull-ups I2C** — placa do TCA9548A costuma já ter; evite empilhar pull-ups demais em cada breakout VL53.  
4. **XSHUT (roxo no diagrama)** — com mux, não é obrigatório para multiplexar, mas ajuda a resetar sensores individualmente.  
5. **Fail-safe** — no produto real, falta de sensor/energia deve **impedir subida** (estado seguro), não liberar.

### Mapeamento sugerido de estados (LEDs do diagrama)

| Estado | LEDs / atuadores |
|--------|------------------|
| Normal / livre | Verde |
| Atenção (`d ≤ 6 m`) | Amarelo |
| Alerta (`d ≤ 3,5 m`) | Vermelho + buzzer |
| Bloqueio (`d ≤ 1,5 m`) | Azul (bloqueio) + relé + buzzer |

---

## Modelo 3D (Blender)

### Dimensões da SJIII 3226 (recolhida, rails up)

| Dimensão | Valor |
|----------|------:|
| Comprimento | 2,32 m |
| Largura | 0,81 m |
| Altura (guarda-corpos erguidos) | 2,15 m |
| Plataforma interna | 2,13 × 0,71 m |
| Altura do piso do cesto | 1,14 m |
| Distância entre eixos | 1,75 m |

### Collections principais

| Collection / objeto | Conteúdo |
|---------------------|----------|
| `SJIII_3226` | Plataforma original + sensores **ultrassônicos** |
| `Sensores_Ultrassonicos` | Módulos US, volumes e zonas críticas |
| `SJIII_3226_ToF` | **Clone** da plataforma para comparativo |
| `Sensores_ToF` | Módulos ToF (VL53L1X) e cones ópticos |
| `SJIII_3226_ROOT` / `SJIII_3226_ToF_ROOT` | Empties-raiz (mover o conjunto inteiro) |

### Representação dos volumes no 3D

**Ultrassônico:** envelope ~30° + lóbulo útil ~15° + zona crítica 0,5 m  
**ToF:** cone ~27° mais nítido + zona crítica  

Empties de apuntamento:

- US: `Grupo_Sensor_Esquerdo` / `Central` / `Direito`  
- ToF: `Grupo_Sensor_ToF_Esquerdo` / `Central` / `Direito`

---

## Lógica embarcada (ESP32)

Código atual do protótipo (base HC-SR04; evoluir para VL53L1X + TCA9548A do SafeAlert MVP):

📁 [`esp32_anti_esmagamento/`](./esp32_anti_esmagamento/)

- `esp32_anti_esmagamento.ino` — máquina de estados  
- `config.h` — pinos e limiares  

### Faixas de distância

Sensores no **topo**, apontando para **cima**. Usa-se a **menor distância válida** entre os 3 canais:

| Distância `d` | Estado | Ação |
|---------------|--------|------|
| `d > 6,0 m` | LIVRE | Verde / sem alerta |
| `3,5 < d ≤ 6,0 m` | AMARELO | Atenção |
| `1,5 < d ≤ 3,5 m` | VERMELHO | Alerta + buzzer |
| `d ≤ 1,5 m` | BLOQUEIO | Bloqueia subida (relé) |

Histerese de liberação do bloqueio: **1,7 m** (evita oscilação).

### Fluxo

```text
Ler 3 sensores (mux I2C no MVP ToF)
    → d = menor distância válida
    → classificar faixa (6,0 / 3,5 / 1,5)
    → LEDs + buzzer + relé de subida
    → (evolução) correlacionar com elevação da tesoura
```

> **Aviso:** este é um protótipo didático. Sistema de segurança real em MEWP exige redundância, validação normativa e projeto fail-safe adequado — não substitua proteções certificadas do fabricante.

---

## Estrutura do repositório

```text
.
├── README.md
├── LICENSE
├── SJIII_3226_anti_esmagamento.blend
├── images/
│   ├── tof_vista_geral.png
│   ├── tof_detalhe_cesto.png
│   ├── comparativo_us_tof.png
│   └── safealert_mvp_protoboard.png
└── esp32_anti_esmagamento/
    ├── esp32_anti_esmagamento.ino
    └── config.h
```

---

## Como abrir o Blender

1. Baixe / abra `SJIII_3226_anti_esmagamento.blend`  
2. No Outliner, localize `SJIII_3226` (US) e `SJIII_3226_ToF` (comparativo)  
3. Viewport em *Material Preview* para ver os cones transparentes  

---

## Como gravar o ESP32

1. Abra `esp32_anti_esmagamento/` no Arduino IDE  
2. Selecione a placa **ESP32** / **ESP32-S3** conforme o hardware  
3. Ajuste pinos e limiares em `config.h`  
4. Compile, grave e monitore a Serial em **115200 baud**  

---

## Roadmap sugerido

- [ ] Portar firmware para **VL53L1X + TCA9548A** (SafeAlert MVP)  
- [ ] Entrada real de elevação da tesoura (encoder / sinal do comando)  
- [ ] Classificador parede lateral × overhead  
- [ ] Autoteste diário + ACK no firmware  
- [ ] Ensaios de FoV junto à fachada (validar geometria)  

---

## Referências rápidas

- Dimensões Skyjack SJIII 3226 (especificação do fabricante)  
- HC-SR04: ângulo útil típico ~15° (effectual); envelope ~30°  
- ST VL53L1X: FoV diagonal típico ~27° (ROI programável 15–27°)  
- TCA9548A: multiplexador I2C para sensores de mesmo endereço  

---

## Licença / uso

Projeto acadêmico / demonstração sob **GPLv3** (`LICENSE`). O modelo 3D e o firmware são fornecidos para estudo e desenvolvimento. Não utilizar como único meio de proteção em operação real sem validação de segurança.
