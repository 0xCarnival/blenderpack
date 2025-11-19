import bpy
import ensurepip
import os
import asyncio
import subprocess
import sys
from threading import Thread
import re
import shutil
import functools
import site

def redraw_preferences():
    for window in bpy.context.window_manager.windows:
        for area in window.screen.areas:
            if area.type == "PREFERENCES":
                area.tag_redraw()

def handle_windows_permission_error(e, operator, description) -> bool:
    if sys.platform.startswith("win") and (
        "Access is denied" in str(e) or "[Error 5]" in str(e)
    ):
        msg = "Windows Access Denied. Please run Blender as Administrator."
        print(msg)
        operator.report({"ERROR"}, msg)
        operator.set_progress_name(msg)
        operator.finish(bpy.context)
        operator.set_progress(1)
        operator._set_running(False)
        return True
    return False

class InstallDependenciesOperator(bpy.types.Operator):
    """Install Python dependencies from a requirements.txt file."""

    bl_idname = "addon.install_dependencies"
    bl_label = "Install Python Dependencies"
    _timer = None
    _running = False
    _progress = 0
    _progress_name = ""
    _progress_icon = "NONE"

    _installed_packages_initialized = False
    _installed_packages = {}

    script_dir = os.path.dirname(os.path.abspath(__file__))
    # Assuming requirements.txt is one level up
    requirements_path = os.path.join(os.path.dirname(script_dir), "requirements.txt")
    download_directory = os.path.join(script_dir, "wheels")

    uninstall: bpy.props.BoolProperty(name="Uninstall", default=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @classmethod
    def get_user_modules_path(cls):
        """Helper to get the user modules path consistently."""
        path = bpy.utils.user_resource('SCRIPTS', path="modules")
        if not os.path.exists(path):
            os.makedirs(path)
        return path

    @classmethod
    def check_dependencies_installed(cls):
        """Check which packages from requirements.txt are installed."""
        modules_path = cls.get_user_modules_path()
        
        # Ensure sys.path has our target path so importlib can see it
        if modules_path not in sys.path:
            sys.path.append(modules_path)

        try:
            from importlib.metadata import distributions
        except ImportError:
            print("Warning: importlib.metadata not available.")
            return [], []

        def normalize_package_name(name):
            return name.lower().replace("-", "_").replace(".", "_")

        if not os.path.isfile(cls.requirements_path):
            print(f"Error: Requirements file not found at {cls.requirements_path}")
            return [], []

        requirements = cls.read_requirements(cls.requirements_path)
        if not requirements:
            return [], []

        installed_packages = {}
        # invalidate caches to ensure we see fresh uninstall results
        import importlib
        importlib.invalidate_caches()
        
        for dist in distributions():
            try:
                dist_name = dist.metadata.get("Name")
                if dist_name:
                    package_name = normalize_package_name(dist_name)
                    installed_packages[package_name] = dist.version
            except Exception as e:
                pass

        installed_correctly = []
        missing_or_incorrect = []

        for requirement in requirements:
            package_name, _, required_version = requirement.partition("==")
            package_name = package_name.strip()
            normalized_name = normalize_package_name(package_name)

            installed_version = installed_packages.get(normalized_name)

            if installed_version:
                if required_version:
                    if installed_version == required_version:
                        installed_correctly.append(f"{package_name}=={installed_version}")
                    else:
                        missing_or_incorrect.append(f"{package_name}=={required_version} (found {installed_version})")
                else:
                    installed_correctly.append(package_name)
            else:
                missing_or_incorrect.append(package_name)

        return installed_correctly, missing_or_incorrect

    @classmethod
    def get_installed_packages_initialized(cls):
        return cls._installed_packages_initialized

    @classmethod
    def set_installed_packages(cls):
        python_exe = sys.executable
        try:
            modules_path = cls.get_user_modules_path()
            env = os.environ.copy()
            # Point PYTHONPATH to our custom folder so pip list sees it
            env["PYTHONPATH"] = modules_path + os.pathsep + env.get("PYTHONPATH", "")

            result = subprocess.run(
                [python_exe, "-m", "pip", "list"],
                stdout=subprocess.PIPE,
                text=True,
                check=True,
                env=env
            )
            packages = {}
            for line in result.stdout.splitlines():
                if "Package" in line and "Version" in line:
                    continue
                match = re.match(r"(\S+)\s+(\S+)", line)
                if match:
                    packages[match.group(1)] = match.group(2)
            cls._installed_packages_initialized = True
            cls._installed_packages = packages
        except subprocess.CalledProcessError as e:
            print("Error: Failed to retrieve installed packages:", e)
            cls._installed_packages_initialized = False
            cls._installed_packages = {}

    @classmethod
    def get_installed_packages(cls):
        return cls._installed_packages

    @classmethod
    def poll(cls, context):
        return not cls._running

    @classmethod
    def _set_running(cls, value: bool):
        cls._running = value

    @classmethod
    def get_running(cls) -> bool:
        return cls._running

    @classmethod
    def get_progress(cls):
        return cls._progress

    @classmethod
    def set_progress(cls, value: float):
        cls._progress = value
        redraw_preferences()

    @classmethod
    def set_progress_name(cls, value: str):
        cls._progress_name = value

    @classmethod
    def get_progress_name(cls):
        return cls._progress_name

    @classmethod
    def get_progress_icon(cls):
        return cls._progress_icon

    @classmethod
    def set_progress_icon(cls, value: str):
        cls._progress_icon = value

    @classmethod
    def read_requirements(cls, file_path):
        if not os.path.exists(file_path):
            return []
        try:
            with open(file_path, "r") as file:
                requirements = file.readlines()
            requirements = [req.strip() for req in requirements if req.strip()]
            return requirements
        except Exception:
            return []

    def modal(self, context, event):
        if event.type == "TIMER":
            if not self.get_running():
                self.finish(context)
                return {"FINISHED"}
        return {"PASS_THROUGH"}

    def cancel(self, context):
        self.report({"INFO"}, "Dependency installation cancelled")

    def invoke(self, context, event):
        if self.get_running():
            return {"CANCELLED"}

        self._set_running(True)
        installed_correctly, missing_or_incorrect = self.check_dependencies_installed()

        if not self.uninstall and not missing_or_incorrect:
            self._set_running(False)
            return {"CANCELLED"}

        self.packages_to_install = missing_or_incorrect
        self._run_thread = Thread(
            target=self.async_install,
            args=(self.packages_to_install, installed_correctly),
        )
        self._run_thread.start()
        wm = context.window_manager
        self._timer = wm.event_timer_add(0.5, window=context.window)
        wm.modal_handler_add(self)
        return {"RUNNING_MODAL"}

    def finish(self, context):
        wm = context.window_manager
        if self._timer:
            wm.event_timer_remove(self._timer)
        self._timer = None
        self._run_thread = None
        self._set_running(False)
        msg = "All packages installed" if not self.uninstall else "All packages uninstalled"
        self.report({"INFO"}, msg)
        
        # Force check dependencies again to update UI immediately
        self.check_dependencies_installed()

    def async_install(self, requirements, installed_correctly):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        self.set_progress(0)

        action = "uninstall" if self.uninstall else "install"
        self.set_progress_name(f"Preparing to {action}")
        self.set_progress_icon("SHADERFX" if not self.uninstall else "X")

        try:
            ensurepip.bootstrap()
        except Exception as e:
            print("Error: ensurepip bootstrap failed:", e)

        python_exe = sys.executable
        modules_path = self.get_user_modules_path()
        
        # Add user modules path to sys.path if missing
        if modules_path not in sys.path:
            sys.path.append(modules_path)

        total_requirements = len(requirements)

        # --- FIX: Updated run_subprocess to accept 'env' ---
        async def run_subprocess(cmd, description, env=None):
            print(f"Running command for {description}: {' '.join(cmd)}")
            try:
                await loop.run_in_executor(
                    None,
                    functools.partial(
                        subprocess.run,
                        cmd,
                        check=True,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True,
                        env=env # Pass the environment here
                    ),
                )
            except subprocess.CalledProcessError as e:
                if handle_windows_permission_error(e.stderr, self, description):
                    return
                else:
                    print(f"Command failed ({description}): {e.stderr}")

        async def install_async():
            if not os.path.exists(self.download_directory):
                os.makedirs(self.download_directory)

            total_tasks = total_requirements * 2
            downloaded_wheels = []

            for index, req in enumerate(requirements, start=1):
                self.set_progress_name(f"Downloading {req}")
                self.set_progress_icon("IMPORT")

                download_cmd = [
                    python_exe, "-m", "pip", "download",
                    "--only-binary=:all:",
                    "-d", self.download_directory,
                    req,
                ]
                await run_subprocess(download_cmd, f"downloading {req}")

                current_percentage = (index - 1) / total_tasks
                self.set_progress(current_percentage)

                normalized_req_name = req.split("==")[0].lower().replace("-", "_")
                wheel_files = [
                    os.path.join(self.download_directory, file)
                    for file in os.listdir(self.download_directory)
                    if file.endswith(".whl") and normalized_req_name in file.lower()
                ]
                downloaded_wheels.extend(wheel_files)

            for index, wheel in enumerate(downloaded_wheels, start=1):
                wheel_name = os.path.basename(wheel)
                self.set_progress_name(f"Installing {wheel_name}")
                self.set_progress_icon("DISC")

                install_cmd = [
                    python_exe, "-m", "pip", "install",
                    wheel,
                    "-t", modules_path,
                    "--no-deps"
                ]
                await run_subprocess(install_cmd, f"installing {wheel}")

                current_percentage = (total_requirements + index - 1) / total_tasks
                self.set_progress(current_percentage)

            self.set_progress(1)
            self.set_progress_name("All packages installed")
            self.set_progress_icon("SOLO_ON")
            self.set_installed_packages()

        async def uninstall_async():
            self.set_progress(0)
            self.set_progress_name("Deleting downloaded wheels")
            self.set_progress_icon("TRASH")

            if os.path.exists(self.download_directory):
                shutil.rmtree(self.download_directory)

            # --- FIX: Prepare Environment with PYTHONPATH ---
            # Pip uninstall needs to know where to look to remove the packages
            env = os.environ.copy()
            env["PYTHONPATH"] = modules_path + os.pathsep + env.get("PYTHONPATH", "")
            # ------------------------------------------------

            total_tasks = len(installed_correctly)
            for index, req in enumerate(installed_correctly, start=1):
                self.set_progress_name(f"Uninstalling {req}")
                self.set_progress_icon("UNLINKED")

                uninstall_cmd = [python_exe, "-m", "pip", "uninstall", req, "-y"]
                
                # Pass the env with PYTHONPATH so pip finds the packages in user modules
                await run_subprocess(uninstall_cmd, f"uninstalling {req}", env=env)

                current_percentage = index / total_tasks
                self.set_progress(current_percentage)

            self.set_progress(1)
            self.set_progress_name("All packages uninstalled")
            self.set_progress_icon("X")
            self.set_installed_packages()

        try:
            if not self.uninstall:
                loop.run_until_complete(install_async())
            else:
                loop.run_until_complete(uninstall_async())
        except Exception as e:
            print(f"Unexpected error during {action}: {e}")
        finally:
            self.finish(bpy.context)
            self.set_progress(1)
            self._set_running(False)
            loop.close()