import ttkbootstrap as ttk

def configure_styles():
    style = ttk.Style()
    style.configure("white.TFrame", background="white")
    style.configure("large.TButton", font=("Roboto", 12))
    style.configure("TCheckbutton", font=("Roboto", 12))  # Apply font globally to TCheckbutton
    return style
