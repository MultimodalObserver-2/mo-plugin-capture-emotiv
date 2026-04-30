# Emotiv Capture Plugin

A plugin for [**Multimodal Observer**](https://github.com/MultimodalObserver-2/mo) that records EEG-based emotional and cognitive metrics from an Emotiv EPOC X headset over the Cortex API, saving timestamped data to a JSON file.

## Features

- Records performance metrics: stress, engagement, interest, excitement, focus, and relaxation
- Records EEG band power: theta, alpha, low beta, high beta, and gamma
- Records battery level and headset status
- Supports pause and resume during a recording session
- Saves data in `.json` format

## Configuration Options

| Property | Description | Default |
| -------- | ----------- | ------- |
| `client_id` | Cortex API client ID | `` |
| `client_secret` | Cortex API client secret | `` |

These can be set in the plugin configuration interface of Multimodal Observer.

## Output Format

The plugin outputs a JSON array where each entry represents a captured frame. Example:

```json
{
  "timestamp": 1000.0,
  "metrics": {
    "stress": 0.3,
    "engagement": 0.5,
    "interest": 0.4,
    "excitement": 0.2,
    "focus": 0.6,
    "relaxation": 0.7
  },
  "power": {
    "theta": 0.01,
    "alpha": 0.02,
    "low_beta": 0.03,
    "high_beta": 0.04,
    "gamma": 0.05
  },
  "status": {
    "battery": 80,
    "headset": "EPOCX-001"
  }
}
```

## Installation

### 1. Build the plugin

```
build-mop -r requirements.txt
```

This generates the distributable `.zip` file inside the `dist/` folder.

### 2. Register the plugin

Open Multimodal Observer, go to the plugin interface, and register the `.zip` file located in the `dist/` folder.

## How It Works

- Connects to the Emotiv Cortex API via WebSocket using the provided client credentials.
- Subscribes to `met` (metrics), `pow` (band power), and `sys` (status) data streams.
- Forwards each incoming data packet to Multimodal Observer as a `CaptureData` object.
- Pause and resume are handled by discarding incoming packets while paused.
- On stop, the WebSocket connection is closed and the output file is finalized.
