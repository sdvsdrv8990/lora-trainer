# lora-trainer — Test Scenario Matrix

> Append-only. Never delete rows — use `status: deprecated` instead.
> ID format: `SCN-<PREFIX>-<NNN>` where PREFIX ∈ {TRAIN, DATA, VALID, ROCM, CLI, CFG, INTG}

---

## SCN-ROCM-001

- **User intent:** Detect RDNA 2 GPU and apply correct HSA_OVERRIDE_GFX_VERSION
- **Module:** `src/rocm_utils.py`
- **Expected contract:** Returns `"10.3.0"` for RDNA 2 hardware; env var is set before subprocess launch
- **Failure modes:** No GPU found → return `None`; unknown GFX family → return `None` with warning
- **Anti-hardcode risks:** GFX version strings must come from `config/default.yaml`, not literals in rocm_utils.py
- **Test files:** `tests/test_rocm_utils.py`
- **Update policy:** update if ROCm adds new GFX families or version strings change
- **Status:** active

---

## SCN-ROCM-002

- **User intent:** Detect RDNA 3 GPU and apply correct HSA_OVERRIDE_GFX_VERSION
- **Module:** `src/rocm_utils.py`
- **Expected contract:** Returns `"11.0.0"` for RDNA 3 hardware
- **Failure modes:** Same as SCN-ROCM-001
- **Anti-hardcode risks:** Same as SCN-ROCM-001
- **Test files:** `tests/test_rocm_utils.py`
- **Update policy:** update if RDNA 3 GFX version changes
- **Status:** active

---

## SCN-DATA-001

- **User intent:** Prepare an image folder into kohya-compatible dataset structure
- **Module:** `src/dataset.py`
- **Expected contract:** Output dir contains `{repeats}_{trigger}/` subdirectory with images and `.txt` caption files
- **Failure modes:** Non-image files are skipped without error; zero images raises `DatasetError` with clear message
- **Anti-hardcode risks:** Trigger word and repeat count come from config/CLI, not hardcoded; supported extensions from `config/default.yaml`
- **Test files:** `tests/test_dataset.py`
- **Update policy:** update if kohya changes expected folder structure
- **Status:** active

---

## SCN-DATA-002

- **User intent:** Generate empty caption files for images that have no captions
- **Module:** `src/dataset.py`
- **Expected contract:** Each image gets a paired `.txt` file; existing `.txt` files are not overwritten
- **Failure modes:** Read-only directory raises clear error
- **Anti-hardcode risks:** Caption extension from `config/default.yaml` (`caption_extension: .txt`)
- **Test files:** `tests/test_dataset.py`
- **Update policy:** update if caption pairing behavior changes
- **Status:** active

---

## SCN-CFG-001

- **User intent:** Load training config from config/default.yaml with CLI flag overrides
- **Module:** `train.py` + `src/trainer.py`
- **Expected contract:** CLI flags override YAML defaults; YAML provides all required keys; None-valued CLI flags do not override
- **Failure modes:** Missing required key → `ValidationError` with field name; invalid type → clear error
- **Anti-hardcode risks:** All defaults in YAML — no default values hardcoded in Python
- **Test files:** `tests/test_trainer_config.py`
- **Update policy:** update if merge order changes
- **Status:** active

---

## SCN-VALID-001

- **User intent:** Validate environment before starting training
- **Module:** `src/validator.py`
- **Expected contract:** Returns list of validation errors; empty list = ready to train; each error has a human-readable message
- **Failure modes:** ROCm not installed; Python version wrong; sd-scripts not found; image dir empty
- **Anti-hardcode risks:** Paths to sd-scripts and image dir come from config, not hardcoded
- **Test files:** `tests/test_validator.py` (to be created)
- **Update policy:** update when new required checks are added
- **Status:** active

---

## SCN-INTG-001

- **User intent:** Run full training pipeline in dry-run mode without a GPU
- **Module:** `train.py` (integration)
- **Expected contract:** `--dry-run` prints assembled command to stdout and exits 0; no subprocess launched; no files modified
- **Failure modes:** Missing --images flag → exit 1 with usage; invalid image dir → clear error before dry-run output
- **Anti-hardcode risks:** Command construction uses config values, not hardcoded flags
- **Test files:** `tests/test_trainer_config.py` (integration section)
- **Update policy:** update if dry-run behavior changes
- **Status:** active
