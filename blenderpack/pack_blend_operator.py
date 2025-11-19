import bpy
import os
import pathlib
import sys
import traceback
import threading
import queue
import time

# Helper to bridge the background thread progress to the main thread
class PackingState:
    def __init__(self):
        self.lock = threading.Lock()
        self.status = "Initializing..."
        self.progress = 0.0
        self.error = None
        self.success = False
        self.finished = False
        self.output_path = None
        self.missing_files = []

    def update(self, status=None, progress=None):
        with self.lock:
            if status is not None:
                self.status = status
            if progress is not None:
                self.progress = progress

    def finish(self, success, output_path=None, missing_files=None, error=None):
        with self.lock:
            self.finished = True
            self.success = success
            self.output_path = output_path
            self.missing_files = missing_files or []
            self.error = error

class ThreadSafeProgressCallback:
    def __init__(self, state):
        self.state = state
        self.total_files = 0
        self.processed_files = 0

    # --- Tracing Phase ---
    def pack_start(self):
        self.state.update(status="Tracing assets...", progress=0.0)

    def trace_asset(self, path):
        # Tracing is usually fast, we might not know total yet
        pass

    def missing_file(self, path):
        pass

    def rewrite_blendfile(self, path):
        self.state.update(status=f"Rewriting {path.name}...")

    # --- Transfer Phase ---
    def transfer_progress(self, total_bytes, transferred_bytes):
        if total_bytes > 0:
            p = (transferred_bytes / total_bytes) * 100.0
            self.state.update(status="Packing files...", progress=p)

    def transfer_file(self, src, dst):
        # self.state.update(status=f"Packing {src.name}...")
        pass

    # --- Completion ---
    def pack_done(self, output_path, missing_files):
        # Handled by the wrapper, but good to know
        pass

    def pack_aborted(self, reason):
        self.state.update(status=f"Aborted: {reason}")

    # Catch-all for other methods the library might call
    def __getattr__(self, name):
        return lambda *a, **k: None


def run_packer_thread(blend_path, zip_path, state):
    try:
        # Import here to ensure it's available
        from blender_asset_tracer.pack import zipped
        
        # Create callback
        cb = ThreadSafeProgressCallback(state)
        
        packer = zipped.ZipPacker(
            blend_path, 
            project=blend_path.parent, 
            target=str(zip_path), 
            relative_only=True
        )
        
        # Inject callback
        # The Packer wraps this in a ThreadSafeCallback internally
        packer.progress_cb = cb
        
        state.update(status="Strategizing...", progress=0.0)
        packer.strategise()
        
        state.update(status="Starting transfer...", progress=0.0)
        packer.execute()
        
        state.finish(success=True, output_path=zip_path, missing_files=packer.missing_files)
        
    except Exception as e:
        traceback.print_exc()
        state.finish(success=False, error=str(e))


class WM_OT_pack_blend(bpy.types.Operator):
    bl_idname = "wm.pack_blend"
    bl_label = "Pack this Blend File"
    bl_description = "Pack current .blend file and dependencies into ZIP"
    bl_options = {'REGISTER', 'UNDO'}

    _timer = None
    _thread = None
    _state = None

    def execute(self, context):
        # This shouldn't be called directly in modal ops usually, 
        # but we'll leave it for fallback if needed, though INVOKE is better.
        return self.invoke(context, None)

    def invoke(self, context, event):
        blend_path_str = bpy.data.filepath
        if not blend_path_str or not os.path.exists(blend_path_str):
            self.report({'ERROR'}, "Save the .blend file first.")
            return {'CANCELLED'}
        
        blend_path = pathlib.Path(blend_path_str)
        
        zip_path_str = context.scene.blenderpack_zip_path
        if not zip_path_str:
            zip_path = blend_path.with_stem(blend_path.stem + "_packed").with_suffix('.zip')
        else:
            prop_path = pathlib.Path(zip_path_str)
            if prop_path.is_dir():
                zip_path = prop_path / f"{blend_path.stem}_packed.zip"
            elif prop_path.suffix.lower() not in {'.zip', ''}:
                zip_path = prop_path.with_suffix('.zip')
            else:
                zip_path = prop_path
                
        if zip_path.exists():
            self.report({'ERROR'}, f"ZIP exists: {zip_path}. Delete or choose another path.")
            return {'CANCELLED'}
            
        # Set path property to used path
        context.scene.blenderpack_zip_path = str(zip_path.parent if zip_path.parent != blend_path.parent else zip_path)

        # Initialize State
        self._state = PackingState()
        
        # Initialize UI
        context.scene.blenderpack_is_packing = True
        context.scene.blenderpack_progress = 0.0
        context.scene.blenderpack_status = "Initializing..."
        context.scene.blenderpack_result_msg = ""
        context.scene.blenderpack_result_type = "INFO"

        # Start Thread
        self._thread = threading.Thread(
            target=run_packer_thread, 
            args=(blend_path, zip_path, self._state)
        )
        self._thread.start()

        # Start Timer
        wm = context.window_manager
        self._timer = wm.event_timer_add(0.1, window=context.window)
        wm.modal_handler_add(self)

        return {'RUNNING_MODAL'}

    def modal(self, context, event):
        if event.type == 'TIMER':
            # Poll state
            with self._state.lock:
                status = self._state.status
                progress = self._state.progress
                finished = self._state.finished
                success = self._state.success
                error = self._state.error
                missing = self._state.missing_files

            # Update UI
            context.scene.blenderpack_status = status
            context.scene.blenderpack_progress = progress
            
            if context.area:
                context.area.tag_redraw()

            if finished:
                # Thread is done
                context.scene.blenderpack_is_packing = False
                self._thread.join()
                
                if success:
                    msg = "Successfully packed!"
                    if missing:
                        msg += f" (Warning: {len(missing)} missing files)"
                    
                    context.scene.blenderpack_result_msg = msg
                    context.scene.blenderpack_result_type = "INFO"
                    context.scene.blenderpack_status = "Done"
                    context.scene.blenderpack_progress = 100.0
                    self.report({'INFO'}, msg)
                else:
                    msg = f"Failed: {error}"
                    context.scene.blenderpack_result_msg = msg
                    context.scene.blenderpack_result_type = "ERROR"
                    context.scene.blenderpack_status = "Error"
                    self.report({'ERROR'}, msg)

                # Remove timer
                context.window_manager.event_timer_remove(self._timer)
                return {'FINISHED'}

        return {'PASS_THROUGH'}

    def cancel(self, context):
        context.scene.blenderpack_is_packing = False
        context.window_manager.event_timer_remove(self._timer)
        return {'CANCELLED'}
