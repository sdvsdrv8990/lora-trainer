_TEMPLATES: dict[str, str] = {

    # ── Step 0 / 1: project setup ─────────────────────────────────────────────

    "pipeline_create_project": (
        "Project created. Next step — save project settings (pipeline_save_project_config).\n"
        "Initialize project registry: pipeline_add_registry_row(scope='project', sheet='assets')\n"
        "  to record base fields (video_id, platform, estimated duration).\n\n"
        "Conduct a dialogue with the user to determine:\n"
        "- content type (slideshow / animation / mixed)\n"
        "- target platform and audience\n"
        "- reward type: educational / story / entertainment / visual_loop\n"
        "- estimated video length and frame batch size\n"
        "- visual style\n\n"
        "Do not proceed to the scenario until project config is saved."
    ),

    "pipeline_save_project_config": (
        "Config saved. Before writing the scenario, gather intelligence:\n"
        "  1. pipeline_get_analytics — find retention patterns from past videos\n"
        "  2. pipeline_query_registry(scope='global', sheet='hooks') — which hook types performed best\n"
        "  3. pipeline_list_assets — inventory available assets\n"
        "  4. pipeline_get_global_stats — overall performance context\n\n"
        "Then write the scenario using the Hook Engine model:\n"
        "- Define reward type: educational / story / entertainment / visual_loop\n"
        "- Define audience_expectation_profile\n"
        "- Map 7 modules: HOOK → SETUP → STABILITY → DISRUPTION → ESCALATION → PAYOFF → AFTERTASTE\n"
        "- Place reset points based on video length and audience fatigue curve\n"
        "- Select psychological triggers per module (context-specific, not hardcoded)\n\n"
        "Show the user the structure plan before writing the full scenario text."
    ),

    "pipeline_submit_scenario": (
        "Scenario saved. Scenes: {scene_count}.\n"
        "Record the video structure now:\n"
        "  1. pipeline_set_video_structure — modules, reset points, reward type, hook type\n"
        "  2. pipeline_add_emotion_map — emotion timeline\n"
        "  3. pipeline_add_registry_row(sheet='hooks') — record hook details\n\n"
        "Next step — start voiceover (pipeline_start_voiceover).\n"
        "Ask the user: start now?\n"
        "wait='true' — synchronous (suitable for short scenarios).\n"
        "wait='false' — background mode; use pipeline_get_voiceover_status to monitor."
    ),

    "pipeline_start_voiceover_complete": (
        "Voiceover complete. Scenes: {completed}/{total}.\n"
        "Next step — pipeline_build_timeline to extract timings.\n"
        "After receiving the timeline, show the user the structure: scene count, total duration,\n"
        "shortest and longest lines. Then suggest moving to the storyboard."
    ),

    "pipeline_start_voiceover_running": (
        "Voiceover started in background. Scenes: {total}.\n"
        "Use pipeline_get_voiceover_status to check progress.\n"
        "When status becomes 'complete', run pipeline_build_timeline."
    ),

    "pipeline_build_timeline": (
        "Timeline built. Scenes: {scene_count}. Total duration: {total_duration}s.\n"
        "Next step — pipeline_get_timeline to retrieve full timing data.\n"
        "After receiving the timeline, suggest moving to the storyboard."
    ),

    "pipeline_get_timeline": (
        "Timeline received. Scenes: {scene_count}. Total duration: {total_duration}s.\n\n"
        "Before creating frame layouts:\n"
        "  1. pipeline_list_assets — check available assets by category\n"
        "  2. pipeline_search_assets — find specific elements needed for this scenario\n"
        "  3. pipeline_get_asset_stats — identify most reused assets\n\n"
        "Use existing assets. Create new ones only when nothing suitable exists.\n"
        "Apply appearance_order to animate element appearance per frame.\n"
        "Each element in appearance_order = separate intermediate PNG frame.\n\n"
        "Propose frame breakdown to user before submitting scene_layout."
    ),

    "pipeline_transcribe_scenes": (
        "Transcription complete (stable-whisper). Scenes: {scene_count}. Words: {total_words}.\n"
        "timeline.json now contains per-scene:\n"
        "  words[]: flat list with {word, start, end, confidence}\n"
        "  segments[]: natural linguistic groups with {start, end, text, words[]}\n"
        "Saved md/stable_result_scene_NNN.json for subtitle export and re-alignment.\n\n"
        "Next steps:\n"
        "  pipeline_get_timeline — analyze timings, find pauses > 0.5s as cut-points\n"
        "  pipeline_export_subtitles — export SRT/VTT/ASS for DaVinci or web (run any time after this)\n"
        "  pipeline_align_scene(scene_id, corrected_text) — fix timestamps for a specific scene\n"
        "    without re-transcribing (much faster)\n\n"
        "Use segments[] (not words[]) for v2 animation event timing — segments are\n"
        "natural speech units that map cleanly to caption events."
    ),

    "pipeline_export_subtitles": (
        "Exported {count} subtitle file(s) in {format} format.\n"
        "Files saved to md/subtitles/scene_NNN.{format}.\n\n"
        "Usage:\n"
        "  SRT — import into DaVinci Resolve as subtitle track, or upload to YouTube\n"
        "  VTT — embed in web player\n"
        "  ASS — karaoke highlighting; set word_level='true' for word-by-word highlight\n"
        "  TXT — plain transcript for review or prompt generation\n\n"
        "To re-export with different settings, just call pipeline_export_subtitles again —\n"
        "it reads from the saved stable-ts JSON, no re-transcription needed."
    ),

    "pipeline_align_scene": (
        "Re-alignment complete. Scene {scene_id}. Words re-timed: {word_count}.\n"
        "Updated: timeline.json words[] and segments[] for this scene.\n"
        "Updated: md/stable_result_scene_{scene_id:03d}.json\n\n"
        "Next:\n"
        "  pipeline_export_subtitles(scene_ids='{scene_id}') — export subtitles with corrected text\n"
        "  pipeline_render_scene(scene_id={scene_id}) — re-render animation with corrected timings\n"
        "Other scenes are not affected."
    ),

    # ── Step 4: scene layout and compositing ─────────────────────────────────

    "pipeline_submit_scene_layouts": (
        "Scene layout saved. Frames: {frame_count}. Canvas: {canvas_width}×{canvas_height}.\n"
        "Next step — pipeline_render_frames to render all frames.\n"
        "frame_ids='' renders all frames. Use '1,2,5' for targeted render.\n"
        "wait='true' — synchronous (suitable for stub rendering and tests).\n"
        "wait='false' — background mode; use pipeline_get_render_frames_status to monitor.\n"
        "To verify a single frame without a full render, use pipeline_preview_frame."
    ),

    "pipeline_render_frames_complete": (
        "Render complete. Frames ready: {completed}/{total}.\n"
        "Check results: pipeline_list_frames\n"
        "If a frame needs correction: pipeline_update_frame_layout + pipeline_preview_frame\n"
        "  before full resubmit.\n"
        "Next step — pipeline_assemble_scenes."
    ),

    "pipeline_render_frames_running": (
        "Render started in background. Total frames: {total}.\n"
        "Use pipeline_get_render_frames_status to monitor progress.\n"
        "When status becomes 'complete', run pipeline_list_frames then pipeline_assemble_scenes."
    ),

    "pipeline_get_render_frames_status": (
        "Frame render status: {status}. Complete: {completed}/{total}.\n"
        "When status is 'complete' and failed_frames is empty — run pipeline_list_frames.\n"
        "If there are failed_frames — check errors. Re-render specific frames via\n"
        "  pipeline_render_frames with frame_ids."
    ),

    "pipeline_list_frames": (
        "Frames ready: {total_ready}/{total_expected}.\n"
        "If total_ready == total_expected — all frames ready for assembly.\n"
        "  Run pipeline_assemble_scenes.\n"
        "If there are missing frames — run pipeline_render_frames with specific frame_ids."
    ),

    "pipeline_preview_frame": (
        "Preview of frame {frame_id} ready: {path}.\n"
        "Show the user the file path for review. If layer adjustments are needed —\n"
        "use pipeline_update_frame_layout, then pipeline_preview_frame again."
    ),

    "pipeline_update_frame_layout": (
        "Frame {frame_id} updated.\n"
        "Verify: pipeline_preview_frame(frame_id=\"{frame_id}\")\n"
        "If correct → re-render only: pipeline_render_frames(frame_ids=\"{frame_id}\")\n"
        "No need to re-render all frames — targeted re-render saves time."
    ),

    # ── Asset tools ──────────────────────────────────────────────────────────

    "pipeline_list_assets": (
        "Available assets: {total}.\n"
        "Categories and asset names are in data.assets.\n"
        "overuse_warnings lists assets exceeding usage thresholds.\n"
        "Reference assets in scene_layout via asset_path: 'global_assets/category/name.svg'\n"
        "  or 'assets/category/name.svg' for project-scoped assets.\n"
        "If a needed asset is missing — create it via pipeline_upload_asset (SVG source)\n"
        "  or pipeline_generate_asset (diffusion model generation).\n"
        "Search by semantic meaning: pipeline_search_assets(semantic=\"tension urgency\")"
    ),

    "pipeline_upload_asset": (
        "Asset uploaded: {category}/{name} (ID: {id}, role: {role}).\n"
        "Group: {group_id}. Group sheet updated in global_registry.json.\n"
        "Use in scene_layout via asset_path:\n"
        "  'global_assets/{category}/{name}.svg' for global scope\n"
        "  'assets/{category}/{name}.svg' for project scope.\n"
        "For character composites: use asset_id directly in character_composite layer."
    ),

    "pipeline_generate_asset": (
        "Asset generated. PNG: {png_path}.\n"
        "{svg_hint}"
        "If the asset was saved to assets/ — it is available in pipeline_list_assets."
    ),

    "pipeline_search_assets": (
        "Search results: {total} assets found.\n"
        "overuse_warnings lists assets exceeding usage thresholds.\n"
        "Use asset IDs and paths to reference them in scene_layout layers.\n"
        "For semantic search: pipeline_search_assets(semantic=\"tension money\", emotion=\"fear\")"
    ),

    "pipeline_get_asset_stats": (
        "Asset {asset_id}: global_uses={global_uses}, project_uses={project_uses}\n"
        "Thresholds: global > {global_threshold}, project > {project_threshold}\n"
        "Exempt roles: BASE, LORA\n"
        "If overused → options (discuss with user):\n"
        "  A) pipeline_upload_asset(scope=\"project\") → project-specific variant\n"
        "  B) Assemble via asset_composite with different PART components\n"
        "  C) pipeline_generate_asset → new variant in channel style\n"
        "  D) Continue using — acceptable if visual variety not priority"
    ),

    "pipeline_delete_asset": (
        "Asset deleted.\n"
        "Group sheet and assets sheet updated in global_registry.json."
    ),

    # ── Engine profile tools ─────────────────────────────────────────────────

    "pipeline_list_engine_profiles": (
        "Available profiles: {total}. Active: {active_id}.\n"
        "To switch model, use pipeline_switch_engine_profile with the desired profile_id.\n"
        "Stub — for testing without GPU. diffusers profiles require GPU and installed dependencies."
    ),

    "pipeline_switch_engine_profile": (
        "Active profile switched to: {active_profile} ({profile_name}, engine={engine}).\n"
        "Next pipeline_render_frames call will use this profile.\n"
        "To verify: render one frame with pipeline_preview_frame.\n"
        "To revert: pipeline_switch_engine_profile(profile_id='stub') for testing\n"
        "  or pipeline_list_engine_profiles to see available options."
    ),

    # ── Character tools ──────────────────────────────────────────────────────

    "pipeline_generate_character_complete": (
        "Character '{name}' generated.\n"
        "PNG: {png_path}\n"
        "SVG: {svg_path}\n"
        "Use in scene_layout as type='character_composite' referencing BODY+FACE+EYES asset_ids."
    ),

    "pipeline_generate_character_running": (
        "Character '{name}' generation started in background.\n"
        "Use pipeline_get_character_status to track progress."
    ),

    "pipeline_get_character_status": (
        "Character generation: {status}\n"
        "If complete → pipeline_list_characters to see components\n"
        "  Use type='character_composite' in scene_layout\n"
        "If running → poll in 15-20 seconds\n"
        "If failed → pipeline_switch_engine_profile → retry"
    ),

    "pipeline_list_characters": (
        "Characters in global_assets/characters/main/: {count}\n"
        "Assemble in scene_layout:\n"
        "  type='character_composite', group_id='{group_id}'\n"
        "  components: BODY + FACE + EYES asset_ids\n"
        "  save_as_comp=true → caches COMP for reuse\n"
        "Find LoRA: search same group for asset ending in -LORA"
    ),

    # ── Registry and analytics ───────────────────────────────────────────────

    "pipeline_set_video_structure": (
        "Structure recorded. Modules: {modules}. Reset points: {reset_points}.\n"
        "Next step — pipeline_submit_scenario.\n"
        "Form tts_input as scene list aligned with module structure.\n"
        "One scene = one semantic block. Do not split smaller than one module."
    ),

    "pipeline_import_platform_stats": (
        "Metrics loaded for {video_id} from {platform}.\n"
        "Run analysis now:\n"
        "  1. pipeline_get_video_structure — this video's module map\n"
        "  2. pipeline_get_project_registry(sheet='emotion_map') — emotion timeline\n"
        "  3. pipeline_get_project_registry(sheet='attention_graph') — attention plan\n"
        "  4. pipeline_get_analytics — compare against other videos\n\n"
        "Cross-reference retention curve with emotion_map.\n"
        "Identify drop points and what was happening in the scene at those moments.\n"
        "Record findings: pipeline_add_registry_row(sheet='insights')\n"
        "If this was an experiment: pipeline_update_experiment"
    ),

    "pipeline_get_project_config": (
        "Project config loaded. Channel: {channel_id}\n"
        "user_preferences to note:\n"
        "  analytics_review_before_scenario: {analytics_review}\n"
        "  competitor_review_before_scenario: {competitor_review}\n"
        "  frame_change_conditions: {frame_change_conditions}\n"
        "  scene_count: {scene_count}\n"
        "  platform_target: {platform_target}\n"
        "If user_preferences is empty → fill in dialogue before proceeding.\n"
        "Channel skills should already be loaded for this session."
    ),

    "pipeline_get_voiceover_status": (
        "Voiceover: {status}. Completed: {completed}/{total}.\n"
        "If complete → pipeline_build_timeline\n"
        "If running → poll in 10-15 seconds\n"
        "If failed → check error, retry pipeline_start_voiceover\n"
        "If cancelled → partial audio exists for completed scenes, restart if needed"
    ),

    "pipeline_stop_voiceover": (
        "Stop requested. Check: pipeline_get_voiceover_status\n"
        "Partial audio in audio/ is valid for completed scenes.\n"
        "Partial timeline can be built from completed scenes only.\n"
        "Restart from any scene: pipeline_start_voiceover"
    ),

    "pipeline_get_global_registry": (
        "Global registry loaded. Sheets: {sheet_names}\n"
        "Group sheets (G-CHR-XXX, G-OBJ-XXX) → per-asset usage and semantic data.\n"
        "Use BEFORE new project:\n"
        "  Find assets by semantic/emotion tags: pipeline_search_assets(semantic=\"...\")\n"
        "  Identify overused assets\n"
        "  Find LoRA IDs for main characters (lora_id in group sheet header)"
    ),

    "pipeline_get_project_registry": (
        "Project registry: {scenario}. Sheets: {sheet_names}\n"
        "Record throughout production:\n"
        "  scenes → module_type, emotion per scene\n"
        "  hooks → hook type, duration, trigger\n"
        "  performance → platform metrics after publishing\n"
        "  insights → what worked and why\n"
        "Add dimensions: pipeline_add_registry_column / pipeline_add_registry_sheet"
    ),

    "pipeline_add_registry_row": (
        "Row added to {scope}/{sheet}. Total: {row_count}\n"
        "Key recording moments:\n"
        "  After scenario → hooks sheet, emotion_map\n"
        "  After render → scenes sheet\n"
        "  After publishing → performance sheet\n"
        "  After analysis → insights sheet"
    ),

    "pipeline_update_registry": (
        "Registry record updated: {scope}/{sheet}/row {row_id}, field \"{field}\" = \"{value}\"\n"
        "If updating performance metrics — consider running analysis after:\n"
        "  pipeline_get_analytics → pipeline_get_insights"
    ),

    "pipeline_add_registry_column": (
        "Column \"{column_name}\" added to {scope}/{sheet}.\n"
        "Default: \"{default_value}\" for all existing rows.\n"
        "Examples: \"meme_density\", \"pattern_interrupt_count\", \"music_sync_quality\""
    ),

    "pipeline_add_registry_sheet": (
        "Sheet \"{sheet_name}\" created in {scope}. Columns: {columns}\n"
        "Available for: pipeline_add_registry_row, pipeline_query_registry"
    ),

    "pipeline_query_registry": (
        "Query: {row_count} rows in {scope}/{sheet}.\n"
        "If 0 and new project → no historical data, proceed without it.\n"
        "If results → apply:\n"
        "  hooks sheet → prefer types with higher effectiveness_score\n"
        "  insights sheet → apply lessons to current structure"
    ),

    "pipeline_get_global_stats": (
        "Global: {video_count} videos analyzed.\n"
        "If 0 → no data yet. Start with general best practices.\n"
        "  Recommend: conflict or curiosity_gap hook\n"
        "  Create baseline: pipeline_create_experiment\n"
        "If >= 3 → directional patterns emerging.\n"
        "If >= 10 → statistically meaningful."
    ),

    "pipeline_get_video_structure": (
        "Structure: {scenario}. Modules: {module_count}. Resets: {reset_count}.\n"
        "Hook: {hook_type}. Reward: {reward_type}.\n"
        "Use for post-publish analysis and comparison.\n"
        "Do not modify past structure — it is historical record.\n"
        "Note findings in insights sheet for next video."
    ),

    "pipeline_add_emotion_map": (
        "Emotion map: {entry_count} segments recorded.\n"
        "After importing platform stats:\n"
        "  Cross-reference emotion at time T vs retention drop at time T\n"
        "  Drop during STABILITY → add reset point next time\n"
        "  Drop during ESCALATION → pacing too slow\n"
        "  Strong retention through PAYOFF → hook promise fulfilled"
    ),

    "pipeline_create_experiment": (
        "Experiment: {experiment_id}. Testing: {variable}\n"
        "Record hypothesis now: what do you expect and why?\n"
        "Steps:\n"
        "  1. Produce both videos\n"
        "  2. Publish to comparable audience\n"
        "  3. pipeline_import_platform_stats for each\n"
        "  4. pipeline_update_experiment with results\n"
        "  5. pipeline_compare_videos"
    ),

    "pipeline_update_experiment": (
        "Experiment updated. Winner: {winner}.\n"
        "Add to global: pipeline_add_registry_row(scope=\"global\", sheet=\"experiments\")\n"
        "If unexpected result → record why hypothesis was wrong.\n"
        "Unexpected results are the most valuable learning."
    ),

    "pipeline_get_analytics": (
        "Analytics: {video_count} videos.\n"
        "< 3: directional only. >= 10: statistically meaningful.\n"
        "Apply:\n"
        "  hook types with avg_retention > 0.7 → use more often\n"
        "  modules where drops consistently occur → restructure\n"
        "Combine with competitor data: pipeline_get_competitor_index"
    ),

    "pipeline_get_insights": (
        "{insight_count} insights. Min evidence: {min_evidence}\n"
        "Priority:\n"
        "  evidence >= 5 → established pattern\n"
        "  evidence 2-4 → strong signal, still test\n"
        "  evidence 1 → note only\n"
        "If none → pipeline_create_experiment for first baseline."
    ),

    "pipeline_compare_videos": (
        "{video_id_a} vs {video_id_b}. Retention delta: {retention_delta}\n"
        "Analyze: which structural differences correlate with delta?\n"
        "Record: pipeline_add_registry_row(scope=\"global\", sheet=\"experiments\")"
    ),

    # ── Audio import tools ────────────────────────────────────────────────────

    "pipeline_search_free_audio": (
        "{result_count} tracks from {source}. License: {license_type}\n"
        "Match mood to module:\n"
        "  HOOK → striking or high energy\n"
        "  SETUP → neutral background\n"
        "  ESCALATION → tension or acceleration\n"
        "  PAYOFF → resolution\n"
        "Save: pipeline_save_free_audio(import_id=\"{import_id}\")"
    ),

    "pipeline_save_free_audio": (
        "Audio saved: {asset_id}\n"
        "Path: {path}\n"
        "Registry updated. Track mood in emotion_map entries → enables future music-retention analysis."
    ),

    # ── FFmpeg assembly ──────────────────────────────────────────────────────

    "pipeline_submit_prompts": (
        "Image prompts saved. Total frames: {total_frames}. Batches: {batch_count} × {batch_size}.\n"
        "Next step — pipeline_generate_images to generate all frames.\n"
        "Use batch_id to target a specific batch, or leave empty for all batches.\n"
        "wait='false' for background generation (recommended for large batches)."
    ),

    "pipeline_generate_images_complete": (
        "Image generation complete. Frames: {completed}/{total}.\n"
        "Next step — pipeline_list_images to verify all frames are on disk.\n"
        "If all frames ready — run pipeline_assemble_scenes."
    ),

    "pipeline_generate_images_running": (
        "Image generation started. Total frames: {total}.\n"
        "Use pipeline_get_generation_status to check progress."
    ),

    "pipeline_assemble_scenes": (
        "Scenes assembled. Scenes: {scenes_done}/{scenes_total}.\n"
        "Next step — pipeline_concat_scenes to concatenate scenes into a single draft.\n"
        "Output: renders/<scenario>_draft.mp4."
    ),

    "pipeline_concat_scenes": (
        "Draft video ready: {output_file}\n"
        "Duration: {duration}s.\n"
        "Use pipeline_get_output_file to get the full path and file size.\n"
        "Inform the user that the draft is ready for review."
    ),

    "pipeline_get_render_status": (
        "Render status: scene assembly — {assemble_status}, concatenation — {concat_status}.\n"
        "Scenes complete: {scenes_done}/{scenes_total}.\n"
        "When both statuses are 'complete' — run pipeline_get_output_file."
    ),

    "pipeline_get_output_file": (
        "Draft file: {path}\n"
        "Size: {size_mb} MB. Duration: {duration_sec}s.\n"
        "Step 5 complete. Draft is ready for final editing (Step 6).\n"
        "Inform the user of the file path."
    ),

    "pipeline_get_generation_status": (
        "Generation status: {status}. Complete: {completed}/{total}.\n"
        "When status is 'complete' and failed_frames is empty — run pipeline_list_images.\n"
        "If there are failed_frames — check errors. Re-render specific frames via\n"
        "  pipeline_generate_images with a batch_id."
    ),

    "pipeline_list_images": (
        "Frames ready: {total_ready}/{total_expected}.\n"
        "If total_ready == total_expected — all ready for assembly. Run pipeline_assemble_scenes.\n"
        "If there are missing frames — run pipeline_generate_images with a specific batch_id."
    ),

    # ── Competitor intelligence tools ─────────────────────────────────────────

    "pipeline_add_competitor_channel": (
        "Competitor channel added: {channel_id}\n"
        "Next steps:\n"
        "  1. pipeline_add_competitor_video → add top performing videos\n"
        "  2. pipeline_import_transcript → import transcript from online service\n"
        "  3. Claude analyzes transcript → fills structure, modules, hooks, viewer_timeline\n"
        "  4. Claude recommends reviewing actual video to add:\n"
        "       visual style, animation type, frame change frequency,\n"
        "       audio-visual relationship, visual techniques\n"
        "  5. User watches → reports observations\n"
        "  6. pipeline_update_competitor_video → save visual observations\n"
        "Minimum 3 videos per competitor before drawing conclusions."
    ),

    "pipeline_import_transcript": (
        "Transcript imported: {segment_count} segments. Duration: {duration}s\n"
        "Run analysis now — Claude reads segments and identifies:\n"
        "  Hook (first 10-15s): what technique opens the video?\n"
        "  Module transitions: where does topic/energy shift?\n"
        "  Reset points: where is attention refreshed?\n"
        "  Payoff moments: where is the promise delivered?\n"
        "  Language patterns: tone, sentence length, key phrases\n"
        "  Viewer timeline: emotional state at each segment\n\n"
        "Save via:\n"
        "  pipeline_update_competitor_video(field=\"structure.hook_type\", value=\"...\")\n"
        "  pipeline_update_competitor_video(field=\"analyzed_by_claude\", value=\"true\")\n\n"
        "Then update global index:\n"
        "  pipeline_add_registry_row in _global_index hooks/pacing/patterns sheets"
    ),

    "pipeline_get_transcript": (
        "Transcript loaded. Analyse it for:\n"
        "  Hook (first 10-15s): opening technique\n"
        "  Module transitions: topic/energy shifts\n"
        "  Reset points: attention refresh moments\n"
        "  Payoff: where the promise is delivered\n"
        "Save findings to global index:\n"
        "  pipeline_add_competitor_index_row(sheet='hooks', row_json='{...}')\n"
        "  pipeline_add_competitor_index_row(sheet='pacing', row_json='{...}')"
    ),

    "pipeline_add_competitor_index_row": (
        "Row added to '{sheet}' (total: {row_count}).\n"
        "Continue building the index — add rows for hooks, pacing, thumbnails, patterns.\n"
        "When enough rows exist, run pipeline_get_insights to surface validated patterns."
    ),

    "pipeline_get_competitor_index": (
        "Global competitor index: {channel_count} channels, {video_count} videos\n"
        "Sheets: hooks, thumbnails, pacing, patterns, platform_models\n"
        "Use before writing scenario:\n"
        "  hooks → which hook types show high click_quality_score in this niche?\n"
        "  pacing → what cut interval works for your platform/format?\n"
        "  thumbnails → CTR vs retention tradeoffs by thumbnail type?\n"
        "  platform_models → what works differently on shorts vs longform?\n"
        "Extract principles — do not copy structure directly."
    ),

    "pipeline_query_competitor_data": (
        "Query {sheet}: {row_count} results found.\n"
        "If 0 → no competitor data for this filter yet.\n"
        "If results → Claude analyzes:\n"
        "  Look for patterns consistent across multiple channels\n"
        "  Identify correlation between technique and performance metric\n"
        "  Apply: pipeline_add_registry_row(scope=\"global\", sheet=\"patterns\")"
    ),

    # ── Channel config and skills tools ───────────────────────────────────────

    "pipeline_save_channel_config": (
        "Channel config saved: {channel_id}\n"
        "Next step: pipeline_create_channel_skills\n"
        "  → creates skill file templates\n"
        "  → Claude fills each skill based on config + competitor analysis\n"
        "Skills encode all style decisions — they will guide every future video.\n"
        "After skills are created: pipeline_create_project to start first video."
    ),

    "pipeline_get_channel_config": (
        "Channel config loaded: {channel_name}\n"
        "Load skills before starting production:\n"
        "  pipeline_get_channel_skill(\"{channel_id}\", \"SCENARIO_WRITER\")\n"
        "  pipeline_get_channel_skill(\"{channel_id}\", \"IMAGE_PROMPTS\")\n"
        "  pipeline_get_channel_skill(\"{channel_id}\", \"FRAME_RULES\")\n"
        "  pipeline_get_channel_skill(\"{channel_id}\", \"HOOK_ENGINE\")\n"
        "Channel style is already decided — follow it consistently.\n"
        "Deviations require explicit user approval and should be noted."
    ),

    "pipeline_get_channel_skill": (
        "Skill loaded: {skill_name} for channel {channel_id}\n"
        "Apply this skill throughout the relevant production phase.\n"
        "If skill content seems outdated or incomplete:\n"
        "  Discuss with user → pipeline_update_channel_skill with improved content\n"
        "Skills evolve with the channel — update when better approaches are found."
    ),

    "pipeline_create_channel_skills": (
        "Skill templates created at channels/{channel_id}/skills/\n"
        "Now fill each skill with channel-specific content:\n"
        "  pipeline_update_channel_skill(\"{channel_id}\", \"SCENARIO_WRITER\", content)\n"
        "  pipeline_update_channel_skill(\"{channel_id}\", \"IMAGE_PROMPTS\", content)\n"
        "  pipeline_update_channel_skill(\"{channel_id}\", \"FRAME_RULES\", content)\n"
        "  pipeline_update_channel_skill(\"{channel_id}\", \"HOOK_ENGINE\", content)\n"
        "  pipeline_update_channel_skill(\"{channel_id}\", \"CHANNEL_VOICE\", content)\n"
        "Base content on channel_config and competitor analysis findings.\n"
        "These skills will be loaded at the start of every production session."
    ),

    # ── Remotion render (v2 layout) ───────────────────────────────────────────

    "pipeline_render_scene": (
        "Scene {scene_id} queued for Remotion render.\n"
        "Check progress: pipeline_get_remotion_status\n"
        "When complete, re-render other scenes or proceed to pipeline_render_all_scenes.\n"
        "Do NOT run pipeline_assemble_scenes — Remotion produces individual scene MP4s directly.\n"
        "After all scenes are done: pipeline_export_davinci"
    ),

    "pipeline_render_all_scenes_complete": (
        "All {total} scenes rendered by Remotion.\n"
        "Output: renders/scenes/scene_NNN.mp4\n\n"
        "Next step: pipeline_export_davinci\n"
        "  → generates FCPXML timeline\n"
        "  → open in DaVinci Resolve: File → Import → Timeline\n"
        "  → add transitions, color grade, export final mp4\n\n"
        "Do NOT run pipeline_assemble_scenes or pipeline_concat_scenes —\n"
        "Remotion already produced individual scene mp4s ready for DaVinci."
    ),

    "pipeline_render_all_scenes_running": (
        "Remotion render started in background. Total scenes: {total}.\n"
        "Use pipeline_get_remotion_status to check progress.\n"
        "When status is 'complete', run pipeline_export_davinci."
    ),

    "pipeline_update_scene_event": (
        "Event updated in scene {scene_id}.\n"
        "To preview the change: pipeline_preview_scene_event(scene_id={scene_id}, time=<event_time>)\n"
        "To apply: pipeline_render_scene(scene_id={scene_id})\n"
        "No need to re-render other scenes."
    ),

    # ── DaVinci export ────────────────────────────────────────────────────────

    "pipeline_export_davinci": (
        "FCPXML exported: {export_path}\n"
        "Scenes: {scenes_included}. Total duration: {total_duration}s.\n\n"
        "In DaVinci Resolve:\n"
        "  1. File → Import → Timeline → select .fcpxml\n"
        "  2. All scenes appear in timeline in correct order\n"
        "  3. Add transitions between scenes\n"
        "  4. Add subtitles if needed (Subtitles track)\n"
        "  5. Color grade if needed\n"
        "  6. Deliver → YouTube 1080p preset\n\n"
        "Claude's work ends here. DaVinci handles the rest."
    ),
}


def get_instructions(step: str, context: dict | None = None) -> str:
    template = _TEMPLATES.get(step, "")
    if not template:
        return ""
    try:
        return template.format(**(context or {}))
    except KeyError:
        return template


def get_workflow_guidance(context: str, data: dict) -> str:
    """Return contextual workflow guidance for key decision points."""

    if context == "session_start":
        channel_name = data.get("channel_name", "")
        channel_id = data.get("channel_id", "")
        return (
            f"Channel loaded: {channel_name}\n"
            f"Load skills before starting:\n"
            f"  pipeline_get_channel_skill(\"{channel_id}\", \"SCENARIO_WRITER\")\n"
            f"  pipeline_get_channel_skill(\"{channel_id}\", \"IMAGE_PROMPTS\")\n"
            f"  pipeline_get_channel_skill(\"{channel_id}\", \"FRAME_RULES\")\n"
            f"  pipeline_get_channel_skill(\"{channel_id}\", \"HOOK_ENGINE\")\n\n"
            f"Then identify session type:\n"
            f"  New channel → start with channel style development\n"
            f"  Existing channel, new competitor data → analyze transcripts first\n"
            f"  Existing channel, regular production → check user_preferences for phase 0\n\n"
            f"Ask user: \"What are we working on today?\""
        )

    if context == "new_channel_no_data":
        return (
            "New channel — no historical data available.\n"
            "Recommended starting path:\n\n"
            "If competitor data available:\n"
            "  1. Analyze competitor transcripts → extract patterns\n"
            "  2. User reviews actual videos → adds visual observations\n"
            "  3. Develop channel style based on findings\n\n"
            "If no competitor data:\n"
            "  1. Discuss channel vision with user directly\n"
            "  2. Define narrative style, visual style, frame rules\n"
            "  3. Set up first video as experiment baseline\n\n"
            "Either path ends with:\n"
            "  pipeline_save_channel_config\n"
            "  pipeline_create_channel_skills\n"
            "  → Claude fills skill files based on style decisions\n\n"
            "First video is most important — it establishes what 'this channel' means."
        )

    if context == "before_scenario_writing":
        user_prefs = data.get("user_preferences", {})
        analytics = user_prefs.get("analytics_review_before_scenario", True)
        competitor = user_prefs.get("competitor_review_before_scenario", False)
        lines = [
            "Config saved. Ready to write scenario.",
            "Channel skills should be loaded — if not: pipeline_get_channel_skill(\"SCENARIO_WRITER\")\n",
            "Optional intelligence gathering (discuss with user):",
        ]
        if analytics:
            lines.append("  Own analytics: pipeline_get_analytics + pipeline_get_insights")
        if competitor:
            lines.append("  Competitor data: pipeline_get_competitor_index + pipeline_query_competitor_data")
        if not analytics and not competitor:
            lines.append("  Skipped per user_preferences — proceed with channel skills only.")
        lines += [
            "",
            "Always propose structure BEFORE writing full text:",
            "  Module sequence with timestamps",
            "  Hook type and opening technique (per HOOK_ENGINE skill)",
            "  Reset point placement (per FRAME_RULES skill)",
            "  Reward type and payoff",
            "",
            "User approves → pipeline_set_video_structure → write full scenario.",
        ]
        return "\n".join(lines)

    if context == "asset_overuse_detected":
        overused_count = data.get("overused_count", 0)
        return (
            f"Overuse: {overused_count} assets exceed thresholds.\n"
            "Options (discuss with user):\n"
            "  A) Project variant: pipeline_upload_asset(scope=\"project\")\n"
            "  B) New composite: different PART components → auto-cached COMP\n"
            "  C) Generate new: pipeline_generate_asset (apply IMAGE_PROMPTS skill)\n"
            "  D) Continue using — acceptable if visual variety not priority\n"
            "Save preference in user_preferences if user has a standing rule."
        )

    if context == "frame_layout_proposal":
        total_duration = data.get("total_duration", 0)
        scene_count = data.get("scene_count", 0)
        return (
            f"Timeline ready. Duration: {total_duration}s. Scenes: {scene_count}.\n"
            "Apply FRAME_RULES skill for this channel.\n\n"
            "Propose breakdown:\n"
            "  Scene 1 (Xs-Ys, module: HOOK): N frames\n"
            "    Frame 1: background + [elements]\n"
            "    Frame 2: add [new element] — triggered by: [reason]\n"
            "  Scene 2...\n\n"
            "User reviews and adjusts.\n"
            "User approves → pipeline_submit_scene_layouts"
        )

    return ""
