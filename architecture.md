# Blenderpack Addon Architecture Specification

## High-Level Overview

The Blenderpack addon is a simple Blender extension designed to pack the current `.blend` file and its dependencies into a self-contained ZIP archive using the `blender_asset_tracer` (BAT) library. The addon follows standard Blender addon structure:

- **`__init__.py`**: Contains `bl_info` metadata, registration/unregistration functions, and imports/registration for panels, operators, and properties.
- **Panel**: A custom panel in the 3D Viewport's N-panel (Sidebar) under a "Blenderpack" tab.
- **Operator**: A custom operator invoked by the panel's button to perform the packing logic.
- **Properties**: Scene-level properties for UI state (e.g., ZIP output path).
- **BAT Integration**: Local `blender_asset_tracer` module imported via `sys.path` manipulation.

The addon registers classes during Blender startup and unregisters on disable. No external dependencies beyond Blender's `bpy` API and the local BAT library.

```
graph TD
    A[Blender Loads Addon] --> B[register_all: Panels, Operators, Properties]
    B --> C[User: 3D View > N > Blenderpack Tab]
    C --> D[Select ZIP Path]
    D --> E[Click 'Pack Blend File']
    E --> F[Operator: Validate + BAT ZipPacker]
    F --> G[Strategise + Execute with Progress]
    G --> H[ZIP Created + Report Success/Error]
```

## UI Design

- **Panel Class**: `VIEW3D_PT_blenderpack`
  - Location: 3D Viewport > Sidebar (N-panel) > Blenderpack tab.
  - `bl_space_type = 'VIEW_3D'`, `bl_region_type = 'UI`, `bl_category = "Blenderpack"`.
- **Layout** (`draw` method):
  - Property field: `layout.prop(context.scene.blenderpack_properties, "zip_path")` with folder icon.
  - Button: `layout.operator("wm.pack_blend", text="Pack Blend File", icon="PACKAGE")`.
- **Properties**:
  - `bpy.types.Scene.blenderpack_properties = PointerProperty(type=BlenderpackProperties)`.
  - `BlenderpackProperties` (PropertyGroup):
    ```
    zip_path: StringProperty(
        name="ZIP Output Path",
        description="Path for the output ZIP file",
        subtype="FILE_PATH",
        update=update_zip_path_preview  # Optional: preview filename
    )
    ```

The file browser opens on property click/edit for intuitive path selection. Default to current blend's parent directory with `{stem}_packed.zip`.

## Operator Logic

- **Operator Class**: `WM_OT_pack_blend`
  - `bl_idname = "wm.pack_blend"`, `bl_label = "Pack Blend File"`, `bl_description = "Pack current .blend and dependencies into ZIP"`.
- **Execute Method**:
  1. Retrieve `blend_path = Path(bpy.data.filepath)`.
  2. Validate: Exists, not empty (unsaved file).
  3. Get `zip_path` from `context.scene.blenderpack_properties.zip_path`; default if empty: `blend_path.parent / f"{blend_path.stem}_packed.zip"`.
  4. Validate `zip_path.parent` writable.
  5. Initialize `packer = ZipPacker(blend_path, project=blend_path.parent, zip_path=zip_path)`.
  6. `packer.strategise()`.
  7. `packer.execute(callback=BlenderpackProgressCallback(operator=self))`.
  8. Report `{'INFO'}` on success, `{'ERROR'}` on failure.
- **Progress Reporting**: Custom `BlenderpackProgressCallback` subclassing BAT's base:
  - Uses `context.window_manager.progress_begin(0, total_steps)`.
  - `update(current)` calls `wm.progress_update(current / total)`.
  - `finish()` calls `wm.progress_end()`.
  - Errors reported via `operator.report`.

## BAT Integration

- **Import Strategy**: Dynamic `sys.path.insert(0, addon_root)` where `addon_root = Path(__file__).parent.parent` (workspace root containing `blender_asset_tracer/`).
  - Placed at module top of `pack_blend_operator.py` (existing pattern).
  - Imports: `from blender_asset_tracer.pack.zipped import ZipPacker`.
- **Configuration**:
  - `blend_path`: Current `.blend`.
  - `project=blend_path.parent`: Treats blend's directory as project root.
  - `zip_path`: User-selected.
  - `relative_only=True` optional to skip pure absolute paths (place in `_outside_project/`).
- **No Packaging Changes**: BAT preserves relative paths (`//`), packs structure faithfully. No custom "dependencies/" folder needed; BAT outputs blend at ZIP root, deps in mirrored paths.

## ZIP Structure

```
packed_blend.zip
├── my_scene.blend          # Original .blend at root
├── textures/               # Relative paths preserved (e.g., //textures/tex.png -> textures/tex.png)
│   └── tex.png
├── shaders/                # Nested structure intact
│   └── material.mtl
└── _outside_project/       # Absolute paths (if not skipped)
    └── /abs/path/file.ext
```

BAT handles this natively; no post-processing required.

## Edge Cases

| Case | Handling |
|------|----------|
| Unsaved Blend | Check `bpy.data.filepath`; report `'ERROR: Save blend first.'` |
| Empty/Invalid ZIP Path | Default to `{stem}_packed.zip`; validate parent writable |
| Missing Dependencies | BAT `strategise()` skips/logs; report non-critical |
| Permissions (read/write) | Try-except `OSError`; report `'ERROR: Permission denied: {path}'` |
| Large Files/Progress | Custom callback with `wm.progress_*`; timeout? BAT handles |
| BAT Import Failure | Try-except `ImportError`; fallback report `'ERROR: BAT unavailable'` |
| Running Blender | Operator cancellable via `{'CANCELLED'}` on context loss |

## File Structure Updates

- **Existing**:
  - `__init__.py`: Update `bl_info` (location: "View3D > Sidebar", category: "3D View").
  - `blenderpack/blenderpack_panel.py`: Populate panel class, properties register.
  - `blenderpack/pack_blend_operator.py`: Rename "octa" to "blenderpack", add progress callback, properties access, error handling.
- **New/Edits**:
  - `blenderpack/properties.py`: `BlenderpackProperties` class + register/unregister.
  - `blenderpack/__init__.py`: No new; subpackage.
  - `__init__.py`: Add `from blenderpack import register, unregister; def register(): ...; def unregister(): ...`.
- **Full List**:
  ```
  __init__.py (edit)
  blenderpack/
  ├── __init__.py (create)
  ├── properties.py (create)
  ├── blenderpack_panel.py (edit)
  └── pack_blend_operator.py (edit)
  └── architecture.md (this file)
  ```

## Dependencies

- **Runtime**: Blender 2.80+ (`bpy`, `bpy.types`, `bpy.props`, `pathlib`).
- **Libraries**: Local `blender_asset_tracer/` (no `pip install` needed).
- **No External**: Self-contained.

## Installation and Usage

1. **Install**: Blender > Edit > Preferences > Add-ons > Install > Select `__init__.py` or ZIP of `blenderpack/`.
2. **Enable**: Search "Blenderpack" > Check box.
3. **Use**:
   - Save your `.blend` file.
   - 3D Viewport > Press `N` > Blenderpack tab.
   - Set ZIP path (click field for browser).
   - Click "Pack Blend File".
4. **Uninstall**: Disable/uninstall via Preferences.

---

**Key Decisions**:
- Panel in N-panel for workflow fit.
- File-path prop for precise ZIP control.
- BAT unchanged for simplicity/reliability.
- Progress via custom callback.
- Defaults/minimal UI for usability.