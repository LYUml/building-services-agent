# Synthetic electric-light sensor calculation

Use project.json and its explicitly synthetic 1000 cd Type C IES file to calculate maintained electric-light illuminance at the given horizontal sensor positions. Include the specified rectangular room reflectances and neutral light assumption. Calculate direct and reflected results, point mean/minimum and minimum-over-mean ratio. Check the supplied synthetic targets; do not treat them as regulatory office lighting criteria.

Increase ambient bounces and ray divisions using the prescribed verification settings, compare sensor changes and retain failures. Preserve the IES file hash, Radiance version, scene, engine calls and numerical output. This example does not establish real manufacturer photometry, glare, daylight, furniture obstruction or full room/design acceptance.
