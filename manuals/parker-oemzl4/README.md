# Parker OEMZL4 manuals

Parker Hannifin / Compumotor documentation for the **OEMZL4** step motor drive.

Parker never published a standalone OEMZL4 user guide. The OEMZL4's own Quick
Reference Guide names the three documents that *do* apply to it, and the OEMZL6 kit
sheet states the relationship outright:

> ZETA Drive Installation Guide — 88-014027-01 — Complete user's manual to support the
> ZETA4, **OEMZL4**, and OEMZL6
>
> — [OEMZL6 Drive: Kit Instructions](https://www.parkermotion.com/manuals/OEMZL/OEMZL6_Kit.pdf)

## Applicable to the OEMZL4

| File | Document | Part no. | Pages | Date |
| --- | --- | --- | --- | --- |
| [oemzl4-quick-reference-guide-rev-b-1999.pdf](oemzl4-quick-reference-guide-rev-b-1999.pdf) | OEMZL4 Quick Reference Guide, Rev B | 88-018139-01B | 2 | 1 Sept 1999 |
| [zeta-drive-installation-guide-rev-a-1995.pdf](zeta-drive-installation-guide-rev-a-1995.pdf) | ZETA Drive Installation Guide, Rev A | 88-014027-01A | 51 | 1995 |
| [emc-installation-guide-rev-b-1997.pdf](emc-installation-guide-rev-b-1997.pdf) | EMC Installation Guide, Rev B | 88-015436-01B | 29 | July 1997 |

**Start with the Quick Reference Guide.** Two pages, and it carries everything specific
to the OEMZL4: the complete DIP switch tables (resolution, current, waveform,
anti-resonance, automatic standby), the motor wiring diagrams for series and parallel,
the 25-pin connector pinout, and the status LED meanings.

**The ZETA Drive Installation Guide is the full manual.** The OEMZL4 is a packaged
ZETA4, so this guide is the authority for signal specifications, drive/motor matching,
and mounting. Two caveats, both from the QRG's own table:

- **Ignore every reference to Active Damping.** The OEMZL4 does not have that feature —
  no rotary switch, and SW2-#5 through SW2-#12 are inactive.
- Electronic Viscosity *is* present on the OEMZL4 (it is on the front panel label).

In the EMC guide, read the **Step Motor Drives** section — it lists its applicable
products as "S, SX, ZETA4, ZETA6104".

## Reference: the RS-232 sibling

The OEMZL4 has no communications port of any kind (see [the top-level README](../../README.md)).
Its indexer/drive counterpart, the **OEMZL6104**, is the same power stage with a
6000-series indexer bolted on, and *that* product has RS-232. These two are kept for
comparison and as the reference for the serial upgrade path:

| File | Document | Part no. | Pages | Date |
| --- | --- | --- | --- | --- |
| [oemzl6104-quick-reference-guide-rev-a-1999.pdf](oemzl6104-quick-reference-guide-rev-a-1999.pdf) | OEMZL6104 Quick Reference Guide, Rev A | 88-018140-01A | 2 | 1 Sept 1999 |
| [zeta6104-indexer-drive-installation-guide-rev-b-1997.pdf](zeta6104-indexer-drive-installation-guide-rev-b-1997.pdf) | ZETA6104 Indexer/Drive Installation Guide, Rev B | 88-014782-02B | 63 | Sept 1997 |

Note the OEMZL6104's front panel in its QRG: `COM 1` / `COM 2` with `Rx Tx GND SHLD`
terminals. The OEMZL4's panel has no such block — only `INDEXER`, `MOTOR`, and
`AC POWER`.

## What was removed

Four documents were downloaded or supplied and then discarded as not applicable:

- `ZETA4_240_RevA__UG.pdf` and its `AppB` appendix — the **ZETA4-240** User Guide
  (88-015027-01). This is the 95–264 VAC variant. The OEMZL4 is 95–132 VAC only, so
  the power wiring and ratings in it are wrong for this drive. Its I/O chapter is
  near-identical to 88-014027-01, which is the correct guide and is kept above.
- `zeta__addend_lvd.pdf` — LVD Installation Instructions (88-015920-01). The OEMZL4
  QRG marks this one "applicable to the OEMZL6104", not the OEMZL4.
- `OEMZLfly_stpmtr.pdf` — a sales flyer for OEMZL series *motors*, with ordering
  information and drive dimensions. No technical content on the drive itself.
- `OEMZL6_Kit.pdf` — kit sheet for the OEMZL6, a different product. Quoted above for
  the one sentence that matters.

## Sources

All files were retrieved from Parker's manual archive, indexed at
<https://parkermotion.com/manuals/zeta/zeta.html>. That index lists the OEMZL4 Quick
Reference Guide as the *only* OEMZL4-specific document Parker published.
