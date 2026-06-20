# Sensor Adaptive Chunking Evaluation

**Run ID:** `sensor-adaptive-chunking`  
**Recommendation:** `recommended`

## Aggregate

| Metric | Value |
|--------|-------|
| Documents | 3 |
| Evaluable documents | 3 |
| Average candidate coverage delta | 0.0 |
| Average noise delta | -0.333333 |

## Documents

### omron-e3z

**Source:** `D:\Robolinks Intern\Project\SecondBrain\local-nas\projects\Demo\Sensor\Omron\Datasheet-cam-bien-tiem-can-Omron-E3Z-Series.pdf`  
**Winner:** `paragraph_merge`  
**Status:** `ok`

| Strategy | Score | Candidate Coverage | Expected Coverage | Noise Hits | Max Chunk Chars |
|----------|-------|--------------------|-------------------|------------|-----------------|
| fixed_chars | 21.83332 | 0.333333 | 0.5 | 10 | 2200 |
| paragraph_merge | 22.23332 | 0.333333 | 0.5 | 9 | 3623 |
| heading_table_aware | 22.23332 | 0.333333 | 0.5 | 9 | 2266 |

#### Top Evidence

- score `98`, chunk `1`, chars `3463`

```text
E3Z
Ordering Information
Sensors [Refer to Dimensions on page 14.] Red light Infrared light
Model
Sensing method Appearance Connection method Sensing distance
NPN output PNP output
E3Z-T61 2M *4 *5 E3Z-T81 2M *4 *5
Pre-wired (2 m) Emitter E3Z-T61-L 2M Emitter E3Z-T81-L 2M
Receiver E3Z-T61-D 2M Receiver E3Z-T81-D 2M
15 m
E3Z-T66 E3Z-T86
Standard M8 connector Emitter E3Z-T66-L Emitter E3Z-T86-L
Receiver E3Z-T66-D Receiver E3Z-T86-D
E3Z-T61A 2M *4 E3Z-T81A 2M *4
Pre-wired (2 m) Emitter E3Z-T61-A-L 2M Emitter E3Z-T81-A-L 2M
Through-beam Receiver E3Z-T61-A-D 2M Receiver E3Z-T81-A-D 2M
(Emitter + Receiver) 10 m
*3 E3Z-T66A E3Z-T86A
Standard M8 connector Emitter E3Z-T66-A-L Emitter E3Z-T86-A-L
Receiver E3Z-T66-A-D Receiver E3Z-T86-A-D
E3Z-T62 2M *4 E3Z-T82 2M
Pre-wired (2 m) Emitter E3Z-T62-L 2M Emitter E3Z-T82-L 2M
Receiver E3Z-T62-D 2M Receiver E3Z-T82-D 2M
30m
E3Z-T67 E3Z-T87
Standard M8 connector Emitter E3Z-T67-L Emitter E3Z-T87-L
Receiver E3Z-T67-D Receiver E3Z-T87-D
Retro-reflective wi
```

- score `51`, chunk `5`, chars `3250`

```text
E3Z
Ratings and Specifications
Retro-reflective with (Narrow-
Sensing method Through-beam Diffuse-reflective
MSR function beam Models)
NPN Pre-wired E3Z-T61 E3Z-T62 E3Z-T61A E3Z-R61 E3Z-D61 E3Z-D62 E3Z-L61
out-
put Connector (M8) E3Z-T66 E3Z-T67 E3Z-T66A E3Z-R66 E3Z-D66 E3Z-D67 E3Z-L66
Model
PNP Pre-wired E3Z-T81 E3Z-T82 E3Z-T81A E3Z-R81 E3Z-D81 E3Z-D82 E3Z-L81
out-
Item put Connector (M8) E3Z-T86 E3Z-T87 E3Z-T86A E3Z-R86 E3Z-D86 E3Z-D87 E3Z-L86
4 m (100 mm) *1
100 mm 1 m 90 + 30 mm
(when using E39-R1S)
Sensing distance 15 m 30 m 10 m (white paper: (white paper: (white paper,
3 m (100 mm) *1 100 × 100 mm) 300 × 300 mm) 100 x 100 mm)
(when using E39-R1)
(2.5 dia. and
sensing dis-
Spot diameter (reference value) ---
tance of
90 mm)
Standard sensing object Opaque: 12-mm dia. min. Opaque: 75-mm dia. min. ---
Minimum detectable object 0.1 mm (cop-
---
(reference value) per wire)
Refer to Engi-
Differential travel --- 20% max. of setting distance neering data
on page 8.
Directional angle Bot
```

- score `47`, chunk `15`, chars `2001`

```text
E3Z
Retro-reflective Models
Pre-wired Models
E3Z-R61(K) E3Z-B61
E3Z-R81(K) E3Z-B81 11.2 4.5
E3Z-D61(K) E3Z-B62 Operation Indicator (orange) 7.5
E3Z-D81(K) E3Z-B82
E3Z-D62(K) E3Z-L63
E3Z-D82(K) E3Z-L83 Stability indicator (green) Operation selector
E3Z-L61 Sensitivity adjuster
E3Z-L81 2.1 1100..88 2200
Receiver 22..88 3
Lens 7 dia. M8 Pre-wired Connector (E3Z-T@@K-M3J)
4 dia. vinyl-insulated round cable
16.7 with 3 conductors,
3311 8 2255..44 Standard length: 0.3 m
2 4
Two, M3
Emitter 1 3
Lens 7 dia. M8
4 dia. vinyl-insulated round cable with 3
conductors (Conductor cross section:
0.2 mm2 (AWG24), Insulator diameter:1.1 mm),
Standard length: 2 m
Terminal Specifica-
No. tions
1 +V
2 ---
3 0V
4 Output
Retro-reflective Models
Connector Models
11.2 4.5
E3Z-R66 E3Z-B66
Operation Indicator (orange) 7.5
E3Z-R86 E3Z-B86
E3Z-D66 E3Z-B67
E3Z-D86 E3Z-B87 Operation selector
E3Z-D67 E3Z-L68 Stability indicator (green) Sensitivity adjuster
E3Z-D87 E3Z-L88
1100..88
E3Z-L66 2.1 Receiver 2.8 3 2200
E3Z-
```

### autonics-bms

**Source:** `D:\Robolinks Intern\Project\SecondBrain\local-nas\projects\Demo\Sensor\Autonics\Sensorguong.pdf`  
**Winner:** `fixed_chars`  
**Status:** `ok`

| Strategy | Score | Candidate Coverage | Expected Coverage | Noise Hits | Max Chunk Chars |
|----------|-------|--------------------|-------------------|------------|-----------------|
| fixed_chars | 20.43332 | 0.333333 | 0.3 | 1 | 2200 |
| paragraph_merge | 20.43332 | 0.333333 | 0.3 | 1 | 3340 |
| heading_table_aware | 20.43332 | 0.333333 | 0.3 | 1 | 2247 |

#### Top Evidence

- score `24`, chunk `2`, chars `2199`

```text
or angle characteristic
Measuring method Data
Reflector (MS-2)
2
θ L
1
0
40° 20° 0 20 40°
Left Center Right
Operation angle (θ)
)m(
L ecnatsid
gnisneS
Sensing area characteristic
Measuring method Data
400
300
200
100
0
20 10 0 10 20
ℓ ℓ
Reflective 1 1
Left Center Right
Sensing area ℓ (mm)
1
)mm(
L
ecnatsid
gnisneS
Parallel shifting characteristic Sensor angle characteristic
Measuring method Data Measuring method Data
Reflector (MS-2)
2
ℓ 1 L
1
0
120 60 0 60 120 ℓ ℓ 1 1
Left Center Right
Sensing area ℓ (mm)
1
Standard sensing target:
Non-glossy white paper
100×100mm
ℓ 1
L
Diffuse reflective
)m(
L
ecnatsid
gnisneS
Reflector (MS-2)
2
L
θ 1
0 40° 20° 0 20° 40° Left Center Right
Operation angle (θ)
)m(
L
ecnatsid
gnisneS
Reflective Reflective

BMS Series
Control Output Diagram
● NPN open collector output ● PNP open collector output
Photoelectric sensor circuit Connection Photoelectric sensor circuit Connection
(brown) +V
O ov u e tp rc u u t r s r h e o n r t t 1.5Ω (dark on)
protection 39V
```

- score `16`, chunk `0`, chars `2200`

```text
BMS Series
High Speed Response Type with Built-in Output Protection Circuit
Features
● Reverse power polarity and overcurrent
● Response time: Max. 1ms
● Light ON/Dark ON mode selectable by control wire
● Sensitivity adjuster (except for through-beam type)
Please read “Safety Considerations”
in the instruction manual before using.
(MS-2) (MS-5) (MST-□)
Specifications ※MS-5, MST-□ is sold separately.
NPN open collector output BMS5M-TDT BMS2M-MDT BMS300-DDT
Model
PNP open collector output BMS5M-TDT-P BMS2M-MDT-P BMS300-DDT-P
Sensing type Through-beam Retroreflective Diffuse reflective
Sensing distance 5m 2m※1 300mm※2
Sensing target Opaque materials of Min. Ø10mm Opaque materials of Min. Ø60mm Translucent, Opaque materials
Hysteresis - Max. 20% at rated setting distance
Response time Max. 1ms
Power supply 12-24VDCᜡ ±10% (ripple P-P: max. 10%)
Current consumption Max. 50mA Max. 45mA
Light source Infrared LED (940nm)
Sensitivity adjustment - Sensitivity adjuster
Operation mode Selectable Li
```

- score `12`, chunk `3`, chars `2200`

```text
Ω (blue) 0V (light on)
10kΩ (white) Control
tiucric
niaM
※To prevent malfunction, this sensor maintains control output OFF for 0.5 sec after supplying the power.
BMS5M-TDT, BMS5M-TDT-P BMS2M-MDT, BMS2M-MDT-P BMS300-DDT, BMS300-DDT-P
Emitter Receiver Operation indicator Operation indicator
Power indicatot Operation indicator
Reflector (MS-2) Sensing
Reflective tape target
(MST Series)
Sensing
target Sensing
target
Brown Brown Brown Brown
Blue + - 12-24VDC B Bl l a u c e k L L o o a a d d ① ② + - 12-24 (d V a D r C k on) B B l l u a e ck L L o o a a d d ① ② + - 12-24V (d D a C rk on) B B l l u a e ck L L o o a a d d ① ② + - 12-24 ( V d D ar C k on)
White (control) (light on) White (control) (light on) White (control) (light on)
①Load connection for NPN output ①Load connection for NPN output ①Load connection for NPN output
②Load connection for PNP output ②Load connection for PNP output ②Load connection for PNP output

Amplifier Built-in Type by Side Sensing
Dimensions
(unit: mm)
SENSORS
C
```

### autonics-bf4

**Source:** `D:\Robolinks Intern\Project\SecondBrain\local-nas\projects\Demo\Sensor\Autonics\Khuech dai quang Autonic.pdf`  
**Winner:** `fixed_chars`  
**Status:** `ok`

| Strategy | Score | Candidate Coverage | Expected Coverage | Noise Hits | Max Chunk Chars |
|----------|-------|--------------------|-------------------|------------|-----------------|
| fixed_chars | 20.43332 | 0.333333 | 0.3 | 1 | 2200 |
| paragraph_merge | 20.43332 | 0.333333 | 0.3 | 1 | 2200 |
| heading_table_aware | 20.43332 | 0.333333 | 0.3 | 1 | 2316 |

#### Top Evidence

- score `22`, chunk `5`, chars `2200`

```text
nvironments. diagnosis output turns ON after 300ms
T3※ T4 T3※ T4 • T4≒40ms: ON time of self-diagnosis ①Indoors (in the environment condition rated in 'Specifications')
ON output ②Altitude max. 2,000m
OFF • T5≥500ms: when ON input of remote ③Pollution degree 2
sensitivity setting is applied, apply OFF
Sensing input of remote sensitivity setting after ④Installation category III possible 500ms
Major Products
tiucric niaM CDV42-21
Internal circuit External connection
(brown)+V 5V (pink) Input 1 + Load - 5V Load ※ (orange) Input 2 Load ※ (black) Load Control output
(white)
Self-diagnosis output
(blue)0V
CDV42-21 ※ ※ tiucric niaM
Bracket
BF4R / BF4G BF4RP / BF4GP
(brown) +V
Load
(black) Control output Load +
(white) Self-diagnosis output -
(blue) 0V
BF4 -E BF4 -R
Self-diagnosis function (common)
When fiber hood is contaminated by dust, transmitted light is lowered by element ability loss or received light is
lowered by missing of optical axis, the self-diagnosis output will turn on.
● Settin
```

- score `18`, chunk `0`, chars `2199`

```text
Specifications Dimensions
Fiber Optic Amplifier
BF4 SERIES Type Standard type E s in y x p n t u e c t r h n t r y a o p l n e ization R se e t m tin o g te t y s p e e nsitivity
Model BF4RP BF4GP BF4R BF4G BF4R-E BF4G-E BF4R-R BF4G-R I N S T R U C T I O N M A N U A L
L (m ig o h d t u s l o a u te rc d e light) Red Green Red Green Red Green Red Green
Power voltage 12-24VDCᜡ ±10% (Ripple P-P: Max. 10%)
Current consumption Max. 45mA
Operation mode Light ON/Dark ON switching
NPN or PNP open collector output
Control output • • R Lo e a s d id v u o a l l t a v g o e lta : g M e a x - . N 3 P 0 N V : D M C a ᜡ x. 1 V • ( L lo o a a d d c c u u r r r r e e n n t: t : 1 1 0 0 0 0 m m A A ), Max. 0.4V (load current: 16mA) /
Thank you for choosing our Autonics products. PNP: Max. 2.5V
Please read the following safety considerations before use. Protection circuit Power reverse polarity protection circuit, output short over current protection circuit
Response frequency Max. 0.5ms (frequency 1), 
```

- score `13`, chunk `3`, chars `2199`

```text
e) (orange) ※Connect diode at external terminal for inductive load.
Input of stop Input of stop Model BF4R/BF4RP/ BF4 -E BF4 -R
transmission transmission BF4G/BF4GP (external synchronization (remote sensitivity
High or Input cable (standard type) input type) setting type)
Open
External synchronization ON input of external
(blue)0V (blue)0V Input 1 - input sensitivity setting
① ① ① ① OFF input of external t I r n a p n u s t m o i f s s s t i o o p n Hi L g o h w ( O (O F N F) ) ② ② ② <Input signal condition for Input 2 - Emission disable input sensitivity setting
T T T stop transmission disable>
State Signal condition Installations
Se ( n D s a in rk g O ou N tp ) ut O O F N F Normal A ※1 bnormal H Lo ig w h 4 0 . - 5 1 - V 3 D 0V C DC or Open
※①: Transmission area
※②: Stop transmission area
※1: If transmission is stopped, control output must turn on, but if control output does not turn on, it seems that
sensor has some problems.
※T≥0.5ms (when using interference prevention function T
```
