# Mandatory Human Decisions

These decisions require explicit human product approval before live deployment or product development:

1. **D-06: Failover Authority**
   - Unresolved choice between automatic client-side offline failover versus operator-confirmed failover.
   - *Recommendation:* Require stage-operator confirmation at phase boundaries to prevent mid-turn state divergence.

2. **D-07: Data-Only Hotfix Trust and Signing**
   - Cryptographic signing keys, manifest distribution, and emergency rollback trust boundaries for in-booth patches.
   - *Recommendation:* Offline asymmetric Ed25519 signature verification against hardcoded public key before turn boundary activation.

3. **D-08: Submission Readiness & Live Demonstration**
   - Actual Twitch account integration, brand permissions for booth fiction, and video demo recording.
   - *Recommendation:* Keep all booth fictions explicitly labeled as non-sponsor in-game metaphors.
