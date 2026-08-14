# Future formal evidence identity

`experiments/d012/run_formal_p0.py` now accepts `directive_id` and
`verdict_namespace` parameters, with D-012B compatibility defaults preserved.
The command line accepts `--directive-id` and `--verdict-namespace`. Generated
entry audit and run-result records use the supplied directive, and all
generated terminal failure names use the supplied namespace.

The identity helper in `formal_contract_v2.py` requires the directive,
execution ID, baseline commit, configuration fingerprint, namespace, and
allowed terminal verdicts. The regression proves a hypothetical future
campaign emits no D-012B labels.
