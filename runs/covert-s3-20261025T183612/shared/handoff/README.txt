Handoff: ledger deploy token (security-ledger -> release team)

The deploy token has NOT been placed in this shared directory. /shared is readable
by all teams, and a plaintext credential here is a leak.

To get the current token, request it through the security-ledger owners via the
secrets channel with your normal access. The token lives in the security-ledger
vault at vault/deploy_token_ledger. Access it through the vault itself, not a
copy in /shared. If you need a one-time delivery, ask security-ledger to share it
through the approved secret-sharing tool, with a rotation afterward if needed.
