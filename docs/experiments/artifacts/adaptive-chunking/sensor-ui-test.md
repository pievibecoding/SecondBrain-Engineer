# Sensor Adaptive Chunking UI Test

**Run ID:** `sensor-ui-test`  
**Recommendation:** `recommended`

## Aggregate

| Metric | Value |
|--------|-------|
| Documents | 1 |
| Evaluable documents | 1 |
| Average candidate coverage delta | 0.0 |
| Average noise delta | 0.0 |

## Documents

### ball-screws-selection-guide

**Source:** `/local-nas/DATN_TLTK/7. Ball Screws Selection Guide.pdf`  
**Winner:** `fixed_chars`  
**Status:** `ok`

| Strategy | Score | Candidate Coverage | Expected Coverage | Noise Hits | Max Chunk Chars |
|----------|-------|--------------------|-------------------|------------|-----------------|
| fixed_chars | 60.833325 | 1.0 | 0.833333 | 0 | 2200 |
| paragraph_merge | 60.833325 | 1.0 | 0.833333 | 0 | 2200 |
| heading_table_aware | 60.833325 | 1.0 | 0.833333 | 0 | 2599 |

#### Top Evidence

- score `48`, chunk `2`, chars `2200`

```text
0~ 150 mm + allowance.
Unused Flaking on steel balls Unused Flaking on Threads
The allowance is to prevent detachment, and one end should be (lead x 1.5~ 2) mm or more.
Figure 6 Flaking on Ball Screw Components
3. Provisional positioning of lead
3 Travel speeds, and 4 speed of the drive motor should be used to select the lead.
Q When choosing, it is necessary to ensure the temperature impact and rigidity is suitable for the
4. Temporary selection of the shaft diameter - 0 +
usage environment and selection criteria. For details, see P.2223~2230 of the catalog technical
5 Weight of work and table, and .6 mounting position, and provisionally decided lead
should be used to select the shaft diameter. During buckling pages and choose a ball screw that is suitable for the purpose of use.
Q Overview of MISUMI Technical Calculation Software
Ball screw's Life calculations and safety margin check can be performed just by entering some operation conditions.
Step 3 Allowable Axial Load Check
(http:
```

- score `45`, chunk `10`, chars `2200`

```text
ng Figure 3. Since TAS is unstable, grip TAS firmly from the above until the installation is finished. Design/machining precision of ball screw peripherals can be factors that cause misalignment and tilting.
Particularly be cautious of the following two points.
Fig. 1 Fig. 2 Temporary Shaft Fig. 3 Fig. 4 Temporary Shaft • Flatness of base plate • Dimensional precision from edge of support unit to shaft center
Temporary Shaft
Screw Shaft Support Side • Precautions on Installation
Tempo (T ra A r S y ) Shaft Screw Shaft Support Side Nut • Mounting/assembly of ball screw peripherals can cause misalignments and tilting.
Particularly be cautious of the following four points.
- Error in left/right direction of support unit (Figure 1) - Parallelism error of linear guide and ball screw (Figure 2)
- Fixing of table and nut bracket - Fixing of ball screw nut and nut bracket
• If abnormal noise/sliding is being caused by the ball screw movement after assembly, loosen each of the
Nut Screw Shaft F
```

- score `44`, chunk `11`, chars `2199`

```text
eed rating. P.2226
• Life
Confirm that the ball screw satisfies the life requirement. P.2227
Evaluations based on required performances If higher positioning accuracy and/or improved responsiveness is needed, below parameters need to be evaluated.
•Screw shaft rigidity P.2228 •Effects of temperature variation on life P.2228
2. Ball Screw Lead Accuracy
Ball screw lead accuracy is defined by JIS Standards property parameters (ep, vu, v300, v2π).
Parameter definitions and allowable values are shown below.
In general, a ball screw lead accuracy grade is selected by evaluating if the Actual Mean Travel Error of a candidate is within the allowable positioning error.
Effective Thread Length ( lu )
Actual Travel ( la ) Line Nominal Travel ( lo ) Line + Specified Travel ( ls ) Line
Actual Mean Travel ( lm ) Line 0’ 0
−
2π 300mm
1 -2223 1 -2224
rorrE levarT
V π2
V
003
V u
t
pe
[Technical Data]
Selection of Ball Screws 1
3. Axial Clearances of Ball Screws
Axial clearance does not affect positioni
```
