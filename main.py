import tkinter as tk
from gui import DatabaseApp

def main():
    root = tk.Tk()
    app = DatabaseApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
