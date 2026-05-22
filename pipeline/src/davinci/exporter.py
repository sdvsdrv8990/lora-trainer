from pathlib import Path
from xml.dom import minidom
from xml.etree.ElementTree import Element, SubElement, tostring


def export_fcpxml(timeline_scenes: list[dict], output_path: Path, project_name: str = "Video") -> Path:
    """
    Generate an FCPXML 1.10 file pointing to Remotion-rendered scene mp4s.

    timeline_scenes: list of dicts from pipeline_get_timeline, each with:
        scene_id, audio_file, start, end, duration, chapter (optional)

    Output file can be imported in DaVinci Resolve 18+ via File → Import → Timeline.
    """
    fcpxml = Element("fcpxml", version="1.10")
    resources = SubElement(fcpxml, "resources")
    library = SubElement(fcpxml, "library")
    event = SubElement(library, "event", name=project_name)
    project = SubElement(event, "project", name=project_name)

    total_dur = sum(float(s.get("duration", 0)) for s in timeline_scenes)
    sequence = SubElement(
        project,
        "sequence",
        duration=f"{total_dur:.3f}s",
        tcFormat="NDF",
        audioLayout="stereo",
        audioRate="48k",
    )
    spine = SubElement(sequence, "spine")

    frame_dur = "100/3000s"  # 30 fps
    fmt_id = "r_fmt_1080p30"
    SubElement(
        resources,
        "format",
        id=fmt_id,
        name="FFVideoFormat1080p30",
        width="1920",
        height="1080",
        frameDuration=frame_dur,
    )

    offset_accum = 0.0
    for scene in timeline_scenes:
        sid = scene["scene_id"]
        dur = float(scene.get("duration", 0))
        chapter = scene.get("chapter", f"Scene {sid}")

        asset_id = f"r_asset_{sid:03d}"
        mp4_rel = f"renders/scenes/scene_{sid:03d}.mp4"

        SubElement(
            resources,
            "asset",
            id=asset_id,
            name=f"scene_{sid:03d}",
            src=f"file://{mp4_rel}",
            format=fmt_id,
            duration=f"{dur:.3f}s",
            hasVideo="1",
            hasAudio="1",
        )

        SubElement(
            spine,
            "asset-clip",
            ref=asset_id,
            offset=f"{offset_accum:.3f}s",
            duration=f"{dur:.3f}s",
            name=chapter,
            tcFormat="NDF",
        )
        offset_accum += dur

    raw = tostring(fcpxml, encoding="unicode")
    pretty = minidom.parseString(raw).toprettyxml(indent="  ")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(pretty, encoding="utf-8")
    return output_path
