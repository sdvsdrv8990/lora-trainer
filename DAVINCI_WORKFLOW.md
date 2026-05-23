# DaVinci Resolve Workflow

## What the pipeline produces

After `pipeline_export_davinci`, the pipeline writes an FCPXML 1.10 file at:
```
renders/<channel>_<scenario>_davinci.fcpxml
```

The FCPXML references Remotion-rendered scene MP4s at:
```
renders/scenes/scene_NNN.mp4
```

All paths are relative to the workspace directory.

## How to open in DaVinci Resolve

1. Open DaVinci Resolve 18+
2. File → Import → Timeline
3. Select the `.fcpxml` file
4. A new timeline appears with all scenes in order

## What to do in DaVinci

| Task | Where |
|---|---|
| Add transitions between scenes | Edit page → Effects → Transitions |
| Add subtitles | Edit page → Subtitles track → Auto Caption or manual |
| Color grade | Color page |
| Add background music | Cut/Edit page → audio track below scenes |
| Export | Deliver page → YouTube 1080p preset |

## Notes

- Scene durations come directly from `timeline.json` — no manual timing needed
- Chapter names from the scenario appear as clip names in DaVinci
- Audio is embedded in each scene MP4 (espeak-ng voiceover)
- If scenes are out of order, check that `pipeline_build_timeline` ran after all audio was generated

## Implementation

Pure Python, zero external dependencies:
```
pipeline/src/davinci/exporter.py
```

Uses only `xml.etree.ElementTree` and `xml.dom.minidom` from the standard library.
No lxml, no fcpxml library needed.

## MCP tool

```
pipeline_export_davinci(channel, scenario, format="fcpxml")
```

Returns the file path and an instruction string for DaVinci workflow.
