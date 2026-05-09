import sys
import subprocess
import threading
import time
import os
import tkinter as tk
from pynput import keyboard

def main():
    if len(sys.argv) < 2:
        print("Usage: wrapper.py <game_executable> [args...]")
        sys.exit(1)

    target_cmd = sys.argv[1:]
    
    # Start tkinter in main thread
    root = tk.Tk()
    root.withdraw() # Hide initially
    root.attributes('-fullscreen', True)
    root.configure(bg='black')
    
    label = tk.Label(root, text="", fg='#00FF00', bg='black', font=('Courier', 48, 'bold'))
    label.place(relx=0.5, rely=0.5, anchor='center')

    # Start the game process
    print(f"Wrapper starting: {target_cmd}")
    
    # Determine working directory
    work_dir = os.path.dirname(target_cmd[0])
    if not work_dir:
        work_dir = "."
        
    # If the target is a .sh or .py file, we need to run it properly
    cmd_to_run = target_cmd
    if target_cmd[0].endswith('.py'):
        cmd_to_run = [sys.executable] + target_cmd
    elif target_cmd[0].endswith('.sh'):
        cmd_to_run = ['bash'] + target_cmd

    game_process = subprocess.Popen(cmd_to_run, cwd=work_dir)

    def trigger_escape():
        # Kill the game process
        try:
            game_process.terminate()
            time.sleep(0.5)
            if game_process.poll() is None:
                game_process.kill()
        except:
            pass

        # Show animation
        root.deiconify()
        root.lift()
        root.focus_force()
        
        # Simple retro animation
        def anim_step_1():
            label.config(text="SYSTEM OVERRIDE...")
            root.after(500, anim_step_2)
            
        def anim_step_2():
            label.config(text="ESCAPING TO MENU.")
            root.after(200, anim_step_3)
            
        def anim_step_3():
            label.config(text="ESCAPING TO MENU..")
            root.after(200, anim_step_4)
            
        def anim_step_4():
            label.config(text="ESCAPING TO MENU...")
            root.after(500, end_wrapper)
            
        def end_wrapper():
            root.destroy()
            
        anim_step_1()

    is_escaping = False

    def on_press(key):
        nonlocal is_escaping
        if key == keyboard.Key.esc and not is_escaping:
            is_escaping = True
            root.after(0, trigger_escape)

    listener = keyboard.Listener(on_press=on_press)
    listener.start()

    def check_process():
        if not is_escaping and game_process.poll() is not None:
            # Game ended normally
            root.destroy()
        else:
            root.after(100, check_process)

    root.after(100, check_process)
    root.mainloop()

if __name__ == "__main__":
    main()
