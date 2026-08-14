# Negative contract tests

`tests/test_d013f_formal_contract_v2.py` covers:

- out-of-range CHARGE incorrectly accepted -> integrity failure;
- denied CHARGE with positive energy credit -> integrity failure;
- repeated denied action without new evidence or correction -> recovery failure;
- critical physiology boundary -> integrity failure;
- authority bypass -> integrity failure;
- authoritative positive CHARGE effect -> verified recovery success;
- denial, corrective APPROACH, new evidence, later CHARGE -> verified recovery success.

The tests use synthetic evidence rows and do not alter production behavior.
