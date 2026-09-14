#!/usr/bin/env bash
# Build the Chartmetric Codex configuration profile from mdm/codex-config.toml.
# Usage: ./mdm/build-profile.sh > chartmetric-codex.mobileconfig
set -euo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
config_b64="$(base64 < "$here/codex-config.toml" | tr -d '\n')"
uuid_payload="$(uuidgen)"
uuid_profile="$(uuidgen)"

cat <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>PayloadContent</key>
  <array>
    <dict>
      <key>PayloadType</key><string>com.openai.codex</string>
      <key>PayloadIdentifier</key><string>com.chartmetric.codex.settings</string>
      <key>PayloadUUID</key><string>${uuid_payload}</string>
      <key>PayloadVersion</key><integer>1</integer>
      <key>PayloadDisplayName</key><string>Codex settings</string>
      <key>config_toml_base64</key><string>${config_b64}</string>
    </dict>
  </array>
  <key>PayloadType</key><string>Configuration</string>
  <key>PayloadIdentifier</key><string>com.chartmetric.codex</string>
  <key>PayloadUUID</key><string>${uuid_profile}</string>
  <key>PayloadVersion</key><integer>1</integer>
  <key>PayloadDisplayName</key><string>Chartmetric Codex</string>
  <key>PayloadOrganization</key><string>Chartmetric</string>
  <key>PayloadScope</key><string>System</string>
</dict>
</plist>
PLIST
