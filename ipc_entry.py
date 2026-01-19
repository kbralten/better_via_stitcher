import os
import sys
import tempfile
import traceback
import time

# Setup Logging
temp_dir = tempfile.gettempdir()
log_file = os.path.join(temp_dir, 'better_via_stitcher.log')

def log(msg):
    with open(log_file, 'a') as f:
        f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - {msg}\n")

# Log start immediately
log("Plugin process started.")
log(f"Executable: {sys.executable}")
log(f"Arguments: {sys.argv}")
log(f"Environment: KICAD_API_SOCKET={os.environ.get('KICAD_API_SOCKET')}")

try:
    import kipy
    import wx
    from ui import ViaStitcherDialog
except Exception as e:
    log(f"Callback Import Error: {traceback.format_exc()}")
    sys.exit(1)

def get_socket_path():
    """Robustly retrieve the KiCad API socket path."""
    socket_path = os.environ.get("KICAD_API_SOCKET")
    if not socket_path:
        # Fallback for manual testing or edge cases
        temp_dir = tempfile.gettempdir()
        socket_path = os.path.join(temp_dir, 'kicad', 'api.sock')
        
    # Ensure protocol prefix for kipy
    # kipy requires an 'ipc://' prefix for standard paths, 
    # but not if it's already there or if it's a named pipe.
    if socket_path.startswith('ipc://'):
        return socket_path
        
    if sys.platform == 'win32':
        # Windows requires named pipe format if not already present
        if socket_path.startswith('\\\\.\\pipe\\'):
             return socket_path
             
    # Default case: prepend ipc://
    return f"ipc://{socket_path}"

def connect():
    """Initialize KiCad client with robust connection logic."""
    socket_path = get_socket_path()
    log(f"Connecting to socket: {socket_path}")
    # Initialize client with a reasonable timeout
    client = kipy.KiCad(socket_path=socket_path, timeout_ms=3000)
    return client

def main():
    try:
        log("Attempting to connect to KiCad...")
        client = connect()
        log("Connected. Getting board...")
        board = client.get_board()
        log("Board retrieved.")
    except Exception as e:
        log(f"Failed to connect to KiCad: {traceback.format_exc()}")
        return

    try:
        log("Initializing wx.App...")
        app = wx.App(False) # False = do not redirect stdout/stderr to window
        
        log("Creating dialog...")
        # Create the plugin dialog
        dlg = ViaStitcherDialog(None, board=board, client=client)
        
        log("Showing dialog...")
        dlg.ShowModal()
        log("Dialog closed.")
    except Exception as e:
        log(f"UI Error: {traceback.format_exc()}")
    finally:
        if 'dlg' in locals():
            dlg.Destroy()
        
    # Cleanup client connection if necessary
    try:
        del client
        log("Client cleaned up.")
    except:
        pass

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        log(f"Unhandled Global Error: {traceback.format_exc()}")
