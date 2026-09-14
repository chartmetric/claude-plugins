# Managed Codex config

Three ways to get the whole team onto the same Codex setup, in descending order of enforcement.
All of them are about *discovery* — nobody's credentials are distributed here. Each person still
runs `codex mcp login maestro` and signs in with their own `@chartmetric.com` Google account.

## 1. MDM profile (enforced, no per-person setup)

`codex-config.toml` is the source of truth. `build-profile.sh` base64-encodes it into a macOS
configuration profile for preference domain `com.openai.codex`:

```bash
./build-profile.sh > chartmetric-codex.mobileconfig
plutil -lint chartmetric-codex.mobileconfig
```

Upload the result to Jamf / Kandji / Intune and scope it to the engineering device group. Codex
reads it as a managed layer above `~/.codex/config.toml`, so it applies to the desktop app and the
CLI alike, and survives a user editing their own config.

To test on one machine before rolling out:

```bash
sudo profiles install -path chartmetric-codex.mobileconfig
defaults read com.openai.codex     # should show config_toml_base64
```

The same domain also accepts `requirements_toml_base64`, the policy layer — it can pin or restrict
`mcp_servers`, `plugins`, `marketplaces`, `skills`, `permissions`, `models`,
`additional_developer_instructions` and `forced_chatgpt_workspace_id`. We deliberately ship config
only for now: config is a default people can still adjust, requirements is a rule they cannot.

## 2. `/etc/codex/config.toml` (same effect, no MDM)

If the fleet isn't under MDM yet, drop the same file on each machine:

```bash
sudo mkdir -p /etc/codex && sudo cp codex-config.toml /etc/codex/config.toml
```

Codex reads `/etc/codex/config.toml` as the machine-wide layer. Ship it with whatever
configuration management already touches the laptops.

## 3. Self-serve (no admin rights needed)

Two commands per person, no profile involved:

```bash
codex plugin marketplace add https://github.com/chartmetric/claude-plugins.git
codex plugin add cm-maestro@chartmetric-tools
codex mcp login maestro
```

## Changing the config later

Edit `codex-config.toml`, open a PR, rebuild the profile, re-upload it to MDM. Anything added to
the marketplace (a new skill, a new plugin) reaches people without touching the profile at all —
they pick it up with `codex plugin marketplace upgrade`.
