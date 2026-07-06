# Runbook Template

Target repo runbooks should answer:

- what target was changed;
- where originals, finals, prompts, receipts, and JSON evidence live;
- what mode ran: generate-only, dry-run, publish, or partial-failure;
- how to rerun validation, post-processing, dry-run, and publish;
- what Discord readback proved;
- what remains out of scope.

For guild targets, runbooks should also name the guild ID environment variable, Manage Guild token environment variable, expected guild name, required `BANNER` feature for image banners, and any Server Profile color recommendation.

Do not include token values, guild ID values, vault contents, authorization headers, or browser session details.
