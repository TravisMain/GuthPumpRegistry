import sys
import os

# Log bootloader start
with open("boot_hook.log", "w", encoding='utf-8') as f:
    f.write(f"Bootloader hook executed: sys.argv={sys.argv}\n")
    f.write(f"sys.executable={sys.executable}\n")
    f.write(f"os.getcwd()={os.getcwd()}\n")
