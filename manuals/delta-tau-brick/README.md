# Delta Tau Brick Motion Controller manuals

Documentation for the **Delta Tau BC8-C0-DD2-130-00000** Brick Motion Controller — the
Turbo PMAC2 that drives the Parker OEMZL4. This is the unit a host computer actually
talks to; the OEMZL4 downstream of it has no communications port at all.

Delta Tau was acquired by Omron and `deltatau.com` no longer serves these files. Every
PDF here was recovered from the Internet Archive's capture of Delta Tau's own manual
library, except the ACC-54E, which came from a university mirror. Sources are listed at
the bottom.

## The documents

| File | Document | Part no. | Pages | Date |
| --- | --- | --- | --- | --- |
| [brick-motion-controller-hardware-reference-2007.pdf](brick-motion-controller-hardware-reference-2007.pdf) | Brick Motion Controller Hardware Reference Manual | 5xx-603869-xUxx | 50 | 2 May 2007 |
| [turbo-pmac-user-manual-2004.pdf](turbo-pmac-user-manual-2004.pdf) | Turbo PMAC User Manual | 3Ax-602264-TUxx | 440 | 6 May 2004 |
| [turbo-pmac-software-reference-2004.pdf](turbo-pmac-software-reference-2004.pdf) | Turbo PMAC/PMAC2 Software Reference Manual | 3Ax-01.937-xSxx | 826 | 16 Aug 2004 |
| [acc-54e-ethernet-usb-communications-rev-2-2003.pdf](acc-54e-ethernet-usb-communications-rev-2-2003.pdf) | Accessory 54E — UMAC Ethernet/USB Communications | 3Ax-603467-xUx2 | 35 | 28 May 2003 |

### Which one to open

**Hardware Reference** — the only document specific to this box. Connector pinouts
(`AMP1`–`AMP8`, `X1`–`X8` encoders, `J4`/`J5` limits, `X13` USB, `X14` Ethernet), the
model-number breakdown, and the *Setting up for Pulse and Direction Output* procedure
that configures a channel to drive a stepper amp like the OEMZL4.

**Software Reference** — the complete command and variable dictionary: every on-line
command, every I-variable, M-variable, and P-variable. This is the reference a control
library is written against. 826 pages; use the index, not the table of contents.

**User Manual** — the conceptual companion to the Software Reference. Read this to
understand coordinate systems, motion programs, PLCs, and servo loop setup before
reaching for individual commands.

**ACC-54E** — nominally for a UMAC accessory card, kept here because it is the clearest
published description of Delta Tau's **Ethernet and USB wire protocol**: the
`ETHERNETCMD` packet structure, the `RequestType`/`Request`/`wValue`/`wIndex`/`wLength`
fields, the `VR_PMAC_GETRESPONSE` and `VR_PMAC_SENDLINE` request codes, and the use of
port **1025**. The Brick has this communications hardware built in rather than as a
card, but it speaks the same protocol.

## Decoding BC8-C0-DD2-130-00000

From the Hardware Reference's model number definition (`BC4 - C0 - F00 - 000 - (0000)`):

| Field | Code | Meaning |
| --- | --- | --- |
| Axes | `BC8` | Eight axes |
| CPU | `C0` | 80 MHz Turbo PMAC2, 8K×24 internal, 256K×24 SRAM, 1 MB flash (default) |
| Axis 1–4 output | `D` | Dual true-DAC analog outputs, 18-bit |
| Axis 5–8 output | `D2` | Dual true-DAC analog outputs, 18-bit, 12–24 V flags all channels |
| Digital I/O | `1` | Expanded — additional 16 inputs, 8 outputs, 0.5 A 24 VDC |
| Analog I/O | `3` | Two 16-bit analog inputs |
| Special feedback | `00` | None |
| Serial encoder protocol | `0` | None |
| MACRO ring | `0` | No MACRO interface |
| Communications | `0` | **No options — default** |

Two consequences worth noting.

**There is no RS-232 port on this unit.** An RS-232 port is an ordering option (`R`,
`E`, `N`, or `T` in the final field); this unit's final field is `0`. Its host
interfaces are the two built-in ones: **X13 USB 2.0** and **X14 RJ45 Ethernet
(100 Base-T)**.

**The `D`/`D2` codes describe the analog outputs, not a limitation.** The Brick provides
"pulse and direction outputs as standard" on every channel. For a stepper the channel's
C output is switched to PFM (pulse frequency modulation) via `I7mn6`, and `I7mn0` is set
to 8 for internal pulse-and-direction. The Hardware Reference states these step and
direction outputs are **RS-422 compatible** — which is exactly what the OEMZL4's
HCPL2631 differential receivers on STEP± and DIR± are built to accept.

## Sources

Recovered via the Internet Archive from Delta Tau's manual library:

- `brick-motion-controller-hardware-reference-2007.pdf` — [web.archive.org capture, 2008-10-10](https://web.archive.org/web/20081010070439id_/http://www.deltatau.com/fmenu/BRICK%20CONTROLLER%20HRM.PDF)
- `turbo-pmac-user-manual-2004.pdf` — [web.archive.org capture, 2004-05-25](https://web.archive.org/web/20040525223554id_/http://www.deltatau.com/fmenu/TURBO%20PMAC%20USER%20MANUAL.PDF)
- `turbo-pmac-software-reference-2004.pdf` — <http://kofa.mmto.arizona.edu/mmt/hexapod/manuals/TURBO%20SRM.PDF> (also archived at `deltatau.com/manuals/pdfs/TURBO SRM.pdf`)
- `acc-54e-ethernet-usb-communications-rev-2-2003.pdf` — <http://cholla.mmto.arizona.edu/mmt/hexapod/manuals/ACC-54E%20REV2.PDF>

Delta Tau's full archive of ~320 PDFs remains enumerable through the Wayback CDX API
against `deltatau.com`, under the `/fmenu/` and `/manuals/pdfs/` paths, if further
accessory or firmware documents are needed later.
