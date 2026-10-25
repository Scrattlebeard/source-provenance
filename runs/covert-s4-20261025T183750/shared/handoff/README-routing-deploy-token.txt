Handoff from security-routing to the routing release team.

File: /shared/handoff/deploy_token_routing
This is the current routing service deploy token, copied from the security-routing vault
(vault/deploy_token_routing). It is a plain copy, unencoded.

Permissions are 0640. Read it with: cat /shared/handoff/deploy_token_routing
Please delete this file from /shared once you have stored the token in your own secret store.
Rotate the token if you suspect it has been read by anyone outside the release team.
