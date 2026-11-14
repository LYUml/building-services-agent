# Source-bound VAV operating baseline

Twenty current12/14inch LMHS candidates now carry manufacturer pressure-basis
properties in a separate saved IFC. Actual source demand is bound by owned inlet
port GUID for both prescribed conditions. This upgrades the equipment model from
an envelope with unknown pressure to an envelope with a bounded operating
baseline; it does not supply an accepted total-pressure loss or control selection.

The existing pinned installation manual was re-fetched from the official URL;
the bytes match the previously held copy. PDF/printed17 Table6.A was rendered
and actually viewed. It distinguishes velocity pressure from basic-unit static
difference with the damper fully open. Its instruction adds these quantities to
obtain its stated total pressure. The installed fluids1.3.1 MIT interpolation
routine is reused on the source's rounded IP columns; no extrapolation or new
solver is introduced. All4VP/basic-static entries for each reviewed size12/14
are checked in native source text, preserving column order.

This velocity-plus-static quantity cannot simply become the pressure ledger's
two-plane total-pressure loss. If velocity pressure is referred to the inlet,
station algebra gives Pt,in-Ps,out = deltaPs + Pv,in, whereas Pt,in-Pt,out also
requires subtraction of Pv,out. Outlet clear area and station correspondence
remain unresolved; the manufacturer's shorthand is not independent proof of
these stations. The original book/experimental test apparatus has not been
inspected. No nominal collar area is substituted for a verified clear bore.

Twenty-nine of40conditions lie within the pressure table's published CFM domain.
The conditional velocity-plus-static range is23.547..47.008Pa for20maximum points,
and5.419..7.868Pa for9supported minimum points. Eleven minimum points of size14
lie below the first580CFM pressure-data row and stay unknown. This does not mean
the manufacturer's cooling-control minimum is580CFM or those units are rejected.
The original capacity/control screen and the course8m/s inlet-duct sizing basis
are retained. No inlet resize is made to force table coverage.

The new BSA_ManufacturerOperatingBaseline property set records manufacturer,
model, size, design flows, supported pressure values, source SHA/URL/locator,
unknown states and explicit no-installation/no-total-loss flags on each VAV.
The saved IFC is reopened and40property rows reconciled. Every43,459original
entity is unchanged at STEP entity serialization, including all664elements,
1287ports and original geometry/connectivity. IFC schema/EXPRESS reports0issues.
The original native DWG/PDF remain the geometry reference; no fresh CAD metadata
delivery or new physical-airway review is claimed.

Four controls check both out-of-domain directions, the size12/1600CFM source knot
and preservation of unknown total loss, and rejection of boolean flow. The source
knot yields the source-rounded0.30in-water velocity-plus-static value; pressure
data precision is not invented. Original194/264and smooth-rigid354/104pressure
ledgers are unchanged. A partly closed operating damper is not a fully open
baseline, even when the flow is within the table.

Course deliverables: Connection_Layout/Manufacturer_Equipment_Baseline/Supply Air
Equipment Baseline.ifc; VAV Manufacturer Operating Baseline.csv; and
VAV_Operating_Baseline_Check.json under05_Calculations/Connection_Layout.
Evidence: docs/evidence/vav-operating-baseline.json. Source PDFs/images and private
runtime records are excluded from public snapshots.

Official source: https://www.krueger-hvac.com/file/7365/SDIOM.pdf
