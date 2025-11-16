# Blender Addon Dependency Installer

This guide explains how to integrate a Python dependency installer into your Blender addon. The installer will check for required packages from a `requirements.txt` file and provide buttons in the addon preferences to install or uninstall them.

## 1. File Structure

Your addon's file structure should look like this:

```
my_addon/
├── __init__.py
├── requirements.txt
└── blenderpack/
    └── install_dependencies.py
```
*Note: The `__init__.py` file inside `blenderpack` is necessary for Blender to recognize it as a package, allowing you to import the script from your main addon file.*

### `requirements.txt`

This file should contain the list of packages to install. For `blender_asset_tracer`, it is:

```
zstandard
boto3
requests
```

### `blenderpack/install_dependencies.py`

This file contains the `InstallDependenciesOperator` which handles the installation and uninstallation of the packages.

## 2. Addon Integration (`__init__.py`)

To integrate the dependency installer into your addon, you need to make the following changes to your `__init__.py` file.

### a. Import the Operator

At the top of your addon's main `__init__.py`, import the `InstallDependenciesOperator`:

```python
from .blenderpack.install_dependencies import InstallDependenciesOperator
```

### b. Create the Addon Preferences UI

If you don't already have an `AddonPreferences` class, create one. The `draw` method is where you will add the UI for the installer.

```python
class MyAddon_Preferences(bpy.types.AddonPreferences):
    bl_idname = __name__

    def draw(self, context):
        layout = self.layout

        # --- Dependency Installer UI ---
        if not InstallDependenciesOperator.get_installed_packages_initialized():
            InstallDependenciesOperator.set_installed_packages()

        _, missing_packages = InstallDependenciesOperator.check_dependencies_installed()

        is_installing = InstallDependenciesOperator.get_running()

        if is_installing:
            row = layout.row()
            row.label(icon=InstallDependenciesOperator.get_progress_icon(), text="")
            row.progress(
                text=InstallDependenciesOperator.get_progress_name(),
                factor=InstallDependenciesOperator.get_progress(),
            )

        if len(missing_packages) > 0:
            row = layout.row()
            if not is_installing:
                row.label(text="Missing dependencies", icon="ERROR")

            row = layout.row()
            install_op = row.operator(
                InstallDependenciesOperator.bl_idname,
                icon="IMPORT",
                text="Install Dependencies",
            )
            install_op.uninstall = False
            if not is_installing:
                row.enabled = True
        else:
            row = layout.row()
            if not is_installing:
                row.label(text="All dependencies are installed", icon="SOLO_ON")

            row = layout.row()
            uninstall_op = row.operator(
                InstallDependenciesOperator.bl_idname,
                icon="TRASH",
                text="Uninstall Dependencies",
            )
            uninstall_op.uninstall = True

            if not is_installing:
                row.enabled = True
```

### c. Register the Operator

In your addon's `register` function, make sure to register both your `AddonPreferences` class and the `InstallDependenciesOperator`.

```python
classes = (
    MyAddon_Preferences,
    InstallDependenciesOperator,
    # ... other classes
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
```

## 3. How It Works

1.  **`__init__.py`**:
    *   The `draw` method in the `AddonPreferences` class calls `InstallDependenciesOperator.check_dependencies_installed()` to see which packages from `requirements.txt` are missing.
    *   Based on whether there are missing packages, it displays either an "Install Dependencies" button or an "Uninstall Dependencies" button.
    *   Both buttons call the `addon.install_dependencies` operator (`InstallDependenciesOperator`).

2.  **`install_dependencies.py`**:
    *   The `InstallDependenciesOperator` reads the `requirements.txt` file.
    *   When the "Install" button is pressed, it downloads the packages as wheels to a `wheels` directory and then installs them into Blender's Python environment.
    *   When the "Uninstall" button is pressed, it removes the packages and deletes the `wheels` directory.
    *   The operator runs in a separate thread to avoid freezing Blender's UI and provides progress updates.

By following these steps, you can add a robust dependency installer to any Blender addon.
