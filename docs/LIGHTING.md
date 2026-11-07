# IES and Radiance electric-light analysis

```powershell
.venv/Scripts/python scripts/setup_radiance.py
.venv/Scripts/python -m bsa.lighting examples/lighting/project.json --out runs/light --radiance-bin tools/radiance-6/bin
.venv/Scripts/python -m bsa.workflow execute examples/lighting/plan.json --out runs/light-workflow --radiance-bin tools/radiance-6/bin
```

The bootstrap downloads an official pinned Radiance Windows zip, verifies its SHA256 and checks extracted files against archive bytes. It writes only tools inside this repository and changes no global PATH. On other platforms supply a compatible Radiance bin directory with adjacent lib. Executed Windows version: RADIANCE 6.0.2, c1700d56cc.

## Supported inputs

Room dimensions are metres from a local (0,0,0) origin. Six opaque diffuse room surfaces use explicitly supplied wall/floor/ceiling reflectances. Luminaires have unique IDs, positions, yaw about vertical, maintenance factors and relative IES paths within the project tree. Orientation is downward negative Z; fixture tilt is not supported. Sensors are explicit upward-facing positions on one horizontal plane. They must be within the room and below every source. Targets and simulation settings cite source IDs. Unknown major scene, fixture and target fields are rejected rather than silently ignored.

IES input is currently UTF-8 LM-63-2002, Type C, TILT=NONE with valid finite angle/intensity counts and no embedded MGF payload. ies2rad handles accepted photometric source geometry and angular distribution. Unsupported editions, external/included tilt and arbitrary scene payloads are rejected. The example file is an explicitly synthetic uniform 1000 cd downward point distribution, not manufacturer or measured photometry. Input watts are metadata, not a brightness estimate.

Use licensed manufacturer IES data, actual mounting geometry and a justified maintenance factor for real work. Retain original file hashes and catalog/test references. Electrical load power and photometric distributions are different inputs; this adapter does not infer candela from electrical kW or automatically bind the earlier electrical/CAD fixture scenario.

## Engine workflow

ies2rad converts each file with explicit neutral/default lamp colour and its supplied maintenance multiplier. xform positions/yaws it. Generated rectangular scene surfaces and sources are compiled by oconv. rtrace -I+ computes direct-only irradiance and reflected irradiance at the same sensor coordinates. Default Radiance RGB irradiance is converted to lux with 179*(0.265R+0.670G+0.065B).

Two reflected calculations use explicitly supplied initial and verification bounce/division settings. Verification increases both; results use the verification run. Maximum relative change is computed per point with denominator max(initial,verification,1 lux). A supplied tolerance is a numerical-stability check, not a mathematical convergence proof or regulation criterion. Grid coverage, surface representation, interpolation and further parameter sensitivity still need review.

Reported average is the arithmetic mean of supplied sensor values, not an area-weighted standard-compliant task-area average. Minimum-over-average uses that same sample set. Targets are supplied and sourced; there are no embedded office lux, uniformity or glare regulations. Failed targets or stability checks remain failed.

## Outputs and limits

lighting.json, illuminance.csv, raw RGB outputs, scene.rad/oct, source data, sensor points and engine-calls.json retain numerical/provenance evidence. Input IES and JSON hashes must stay unchanged. Executable and support .cal file hashes plus engine version are recorded; workflow integrity also includes IES inputs. A missing Radiance installation stays pending.

No daylight, UGR, emergency lighting, furniture/obstruction, arbitrary room geometry, spectral lamp-colour accuracy or complete lighting acceptance is asserted. The room must not be treated as the exact supplied architectural model. Native CAD/IFC coordination with this optical model remains unfinished.

## Independent evidence

A black-room uniform point-source test compares direct illuminance to I*cos(theta)/r^2 on-axis and off-axis, with 0.3 lux tolerance for ies2rad's tiny-sphere approximation. A second engine run halves maintenance factor and verifies illumination scaling without changing input watts. The reflected 15-sensor example ran with 3/4 ambient bounces and 2048/4096 divisions; numerical change was below its synthetic 10% tolerance. It is a software/physics integration example, not a certified lighting design.

Primary engine references: https://www.radiance-online.org/learning/documentation/manual-pages/pdfs/ies2rad.pdf and https://www.radiance-online.org/learning/documentation/manual-pages/pdfs/rtrace.pdf. RGB photometry reference: https://radsite.lbl.gov/radiance/digests_html/v2n3.html. These are method references, not local code clauses.
