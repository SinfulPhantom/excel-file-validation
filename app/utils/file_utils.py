import wx
import os
from typing import Optional

def select_file(window_dialog: str, wildcard: str = '*.csv') -> Optional[str]:
    """
    Opens a file dialog and returns the selected file path

    Args:
        window_dialog (str): The title of the file dialog
        wildcard (str, optional): The file type filter. Defaults to '*.csv'.

    Returns:
        Optional[str]: The selected filepath or None if cancelled
    """
    app = wx.App(None)
    style = wx.FD_OPEN | wx.FD_FILE_MUST_EXIST
    dialog = wx.FileDialog(None, window_dialog, wildcard=wildcard, style=style)
    
    if dialog.ShowModal() == wx.ID_OK:
        path = dialog.GetPath()
        dialog.Destroy()
        return path
    dialog.Destroy()
    return None

def format_app_name(app_name: str) -> str:
    """
    Format the app name to remove the 'A-' prefix

    Args:
        app_name (str): The app name

    Returns:
        str: The formatted app name
    """
    return app_name[2:] if app_name.startswith('A-') else app_name
