# Device pairing retired

**Status: permanently removed from the ULTRON product design.**

On 2026-11-18 the owner requested removal of device pairing to prevent any possibility of remote device control. The dashboard no longer creates pairing challenges, stores paired-device UI state, or calls the device-control endpoint. The Python heartbeat agent is removed from the repository. The deployed Edge Function must be replaced with a fail-closed retirement response before this change is considered fully decommissioned.

The former agent was heartbeat-only and did not execute commands, but its device credential and network connection are no longer needed. ULTRON's future training controls will be local to the device running training: the local user selects the RAM limit and starts/stops training on that device. No dashboard-to-device command channel will be built.

The historical database migration is retained for auditability. Its tables have no direct browser grants and remain unused. No training has started and no checkpoints are deleted.
