# Implementation Spec Profile Contract

An implementation-spec profile is the target library's governing standard for one family of builder-ready
specs.

## Required Profile Content

A profile is ready when its standard defines:

- target folder or document contract;
- required files or sections;
- completeness checklist;
- mechanical verification expectations;
- review or probe definition of done;
- exact probe inputs when a buildability probe is required.

If any of these are missing, `saga:implementation-spec` records a profile gap and asks the operator for
the governing standard before authoring.

## Built-In Profiles

| Profile | Detection path | Behavior |
|---|---|---|
| service implementation | `platform-specs/06-service-implementations/README.md` | Use the service folder contract, checklist, mechanical verification, and buildability probe defined by that standard. |
| feature module | `platform-specs/06-feature-modules/README.md` | Use only the target library's own standard. If the README is just an index, stop for profile definition. |

## Output Discipline

Implementation specs are durable context-library artifacts. They should be sufficient for a later builder
to implement without relying on the authoring chat.

The standard owns exact file names, not Saga. Saga owns the authoring and verification protocol.
