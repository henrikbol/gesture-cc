# gesture-cc

Real-time hand gesture tracking that sends MIDI Control Change (CC) messages based on finger distances. Use your hands to control music software, VJ tools, or any MIDI-compatible application.

<img src="img/img.png" width="500">

## Features

- Tracks thumb and index fingertips on both hands using MediaPipe
- Ableton Live (or any DAW) running on the same computer can directly use the CC messages
- Sends 4 independent MIDI CC signals:
  - **CC 20**: Left hand thumb-to-index distance
  - **CC 21**: Right hand thumb-to-index distance
  - **CC 22**: Left thumb to right thumb distance
  - **CC 23**: Left index to right index distance
- Visual feedback with OpenCV showing hand skeleton, distances, and angles
- ~30 MIDI messages per second for smooth control

## Requirements

- Python 3.12+
- Webcam (the system default camera will be used)
- macOS

## Installation

1. Clone the repository:

   ```bash
   git clone https://github.com/henrikbol/gesture-cc.git
   cd gesture-cc
   ```

2. Install dependencies using [uv](https://docs.astral.sh/uv/):

   ```bash
   uv sync
   ```

## macOS: Audio MIDI Setup

On macOS, you need to create a virtual MIDI port using **Audio MIDI Setup** before running the app:

1. Open **Audio MIDI Setup** (found in `/Applications/Utilities/`)
2. Go to **Window → Show MIDI Studio** (or press `⌘2`)
3. Double-click on **IAC Driver**
4. Check **Device is online**
5. Add a port if needed (e.g., "Bus 1")
6. Click **Apply**

The app looks for MIDI ports containing "IAC" in the name. If no IAC port is found, it will create a virtual port named "PoseHandControl".

## Usage

Run the application:

```bash
uv run python -m app.main
```

Press **q** to quit the application.

## Configuration

Configuration is done by editing constants in `app/handler.py`:

| Constant | Default | Description |
|----------|---------|-------------|
| `MIDI_PORT_NAME_SUBSTRING` | `"IAC"` | Substring to match MIDI port name |
| `MIDI_CHANNEL` | `0` | MIDI channel (0 = channel 1) |
| `CC_LEFT_HAND` | `20` | CC number for left thumb-index |
| `CC_RIGHT_HAND` | `21` | CC number for right thumb-index |
| `CC_THUMB_TO_THUMB` | `22` | CC number for thumb-to-thumb |
| `CC_INDEX_TO_INDEX` | `23` | CC number for index-to-index |
| `MIN_DIST_PX` | `20` | Minimum distance in pixels (maps to CC 0) |
| `MAX_DIST_PX` | `400` | Maximum distance in pixels (maps to CC 127) |

Adjust `MIN_DIST_PX` and `MAX_DIST_PX` based on your camera distance and hand size for optimal sensitivity.

## How It Works

1. Captures video from the default webcam
2. Uses MediaPipe Hands to detect up to 2 hands and extract landmark positions
3. Calculates pixel distances between fingertips
4. Normalizes distances to MIDI CC values (0–127)
5. Sends CC messages via rtmidi to the configured MIDI port
6. Displays visual feedback in an OpenCV window

## Documentation & Resources

- [MediaPipe Hands](https://ai.google.dev/edge/mediapipe/solutions/vision/hand_landmarker) — Hand tracking solution
- [python-rtmidi](https://spotlightkid.github.io/python-rtmidi/) — Python bindings for RtMidi
- [uv](https://docs.astral.sh/uv/) — Fast Python package manager

## License

MIT
