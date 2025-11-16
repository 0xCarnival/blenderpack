# BlenderPack Installation

This guide explains how to install the BlenderPack addon and its dependencies.

## 1. File Structure

The addon's file structure is as follows:

```
Blenderpack/
├── __init__.py
├── requirements.txt
└── blenderpack/
    ├── __init__.py
    ├── blenderpack_panel.py
    ├── install_dependencies.py
    ├── pack_blend_operator.py
    └── render_panel.py
```

## 2. Installation

1.  **Download the Addon**: Download the BlenderPack addon as a ZIP file from the GitHub repository.
2.  **Install the Addon**: In Blender, go to `Edit > Preferences > Add-ons` and click `Install`. Select the downloaded ZIP file.
3.  **Enable the Addon**: Search for "BlenderPack" and enable it by checking the box.
4.  **Install Dependencies**: In the addon preferences, click the "Install Dependencies" button to install the required Python packages.

## 3. How It Works

-   **`__init__.py`**: The main addon file that registers all the panels, operators, and preferences.
-   **`requirements.txt`**: A list of Python packages required by the addon.
-   **`blenderpack/install_dependencies.py`**: A script that handles the installation and uninstallation of the required dependencies.
-   **`blenderpack/blenderpack_panel.py`**: The UI panel for the addon in the 3D View's N-panel.
-   **`blenderpack/render_panel.py`**: The UI panel for the addon in the Render Properties tab.
-   **`blenderpack/pack_blend_operator.py`**: The operator that packs the blend file and its dependencies into a ZIP file.
