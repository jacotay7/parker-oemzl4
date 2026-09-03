# Manuals

Documentation for both halves of this motion system, kept with the code so a future
reader can check any claim against the source. Nine PDFs in two sets.

```
Mac  ──USB / Ethernet──▶  Delta Tau Brick Controller  ──step + dir──▶  OEMZL4  ──▶  motor
                          delta-tau-brick/                             parker-oemzl4/
```

| Set | What it covers | Index |
| --- | --- | --- |
| [delta-tau-brick/](delta-tau-brick/) | **Delta Tau BC8-C0-DD2-130-00000** Brick Motion Controller (Turbo PMAC2) — the controller, and the thing a host talks to | [README](delta-tau-brick/README.md) |
| [parker-oemzl4/](parker-oemzl4/) | **Parker OEMZL4** step motor drive — the amplifier, which has no communications port | [README](parker-oemzl4/README.md) |

Start with `delta-tau-brick/` for anything about commanding motion, and
`parker-oemzl4/` for anything about the drive's wiring, DIP switches, or fault
behaviour.

Each index records the part number, revision and date of every file, states which
documents Parker and Delta Tau consider applicable to these exact models, and lists
what was downloaded and then discarded as belonging to a different product.
