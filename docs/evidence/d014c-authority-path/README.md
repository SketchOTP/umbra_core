# UMBRA-D-014C — Authority-path diagnosis closeout

Status: terminal bounded failure; returned to Architect.

Baseline and remote `master`: `d60cbc7d750697f45f94a63713c1408e0a992277`

Verdict: `D014C_AUTHORITY_ORDER_CONFIRMED_BUT_RECOVERY_DEFECT_PERSISTS`

D-014C reconstructed the D-014B failure lineage through A0–A9. The downstream
world-model replacement was contributory in the seed `79871850` failure, while
the `27526357` failure did not show an authority-order replacement at the
failure decision. The conditional final-boundary correction was evaluated but
failed the required eight-seed R0, 7,200-tick viability gate. It was reverted;
no production correction is retained.

Evidence is preserved at:

`/mnt/storage1tb/project-archives/UMBRA-CORE/live-evidence/d014c-authority-path-r1/`

The D-014C result does not supersede historical D-014, D-014A, or D-014B
results. No formal D-014 tag or P0 run was created.
