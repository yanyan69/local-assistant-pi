# Jellyfin integration

The Raspberry Pi hosts the assistant and Jellyfin. Your phone or laptop runs the
Jellyfin client and remains the playback device.

## Configure the assistant

Create a Jellyfin API token in the Jellyfin dashboard and set these environment
variables before starting the assistant:

```bash
export JELLYFIN_URL=http://127.0.0.1:8096
export JELLYFIN_TOKEN=replace-with-your-token
python server.py
```

On Windows development, use PowerShell:

```powershell
$env:JELLYFIN_URL = "http://127.0.0.1:8096"
$env:JELLYFIN_TOKEN = "replace-with-your-token"
python server.py
```

Use the Raspberry Pi's LAN address instead of `127.0.0.1` only when the
assistant process is not running on the same machine as Jellyfin.

## Use it

Open Jellyfin on the phone or laptop and connect it to the Pi, for example:

```text
http://192.168.1.50:8096
```

Then use the assistant commands:

- `play Interstellar`
- `play Daft Punk`
- `pause music`
- `resume music`
- `next song`
- `previous song`
- `stop music`

The client must be open and connected before the assistant can control it.

## Offline and security notes

Streaming and control stay on the local network. Internet is only needed for
installation, updates, and optional metadata downloads. Keep the API token in
the environment, never in source control or a browser response. Do not expose
Jellyfin port 8096 directly to the public internet.