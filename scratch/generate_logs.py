import random
from datetime import datetime, timedelta

start_date = datetime(2026, 1, 1)
end_date = datetime(2026, 6, 19)
total_days = (end_date - start_date).days

def generate_dates(count):
    dates = []
    for _ in range(count):
        random_days = random.randint(0, total_days)
        dates.append(start_date + timedelta(days=random_days))
    return sorted(dates)

# Generate Project Logs (approx 200 entries)
project_features = [
    "Added categories for different game genres (Fighters, Platformers, Puzzle)",
    "Implemented background music player to the main menu",
    "Added a search function to quickly find games by title",
    "Configured initial Player 1 arcade stick controls mapping",
    "Configured Player 2 arcade stick controls mapping",
    "Added a volume control slider to the settings page",
    "Implemented screen brightness and contrast controls",
    "Created a batch script to launch Windows-based PC games seamlessly",
    "Created a script wrapper to launch retro emulator games",
    "Added a video screensaver that plays random game trailers when idle",
    "Implemented a 'Favorites' list for quick access to top games",
    "Added a digital clock widget to the top right corner of the menu",
    "Configured Player 3 and 4 USB controllers for party games",
    "Added custom boot animation video to hide the Windows startup logo",
    "Implemented shutdown, restart, and sleep options in the main menu power settings",
    "Added a network shared folder for easy drag-and-drop game ROM installs",
    "Configured automatic backup script for game save files to a cloud drive",
    "Added a global volume mute hotkey combination on the arcade panel",
    "Improved icon loading speed by generating and caching thumbnail sizes",
    "Added support for animated GIF icons in the game grid",
    "Configured a hardware microswitch button for arcade coin insertion",
    "Implemented a 'Recently Played' carousel section on the home screen",
    "Added a parental lock PIN feature for M-rated games",
    "Created a diagnostic utility screen to check controller inputs and buttons",
    "Added a high score tracker overlay for local arcade high scores",
    "Configured an external secondary display to show game marquee artwork",
    "Implemented a dark mode UI theme for the menu system",
    "Added a script to automatically remap controls depending on the active game",
    "Configured SSH server access for remote troubleshooting and updates",
    "Added a visual Wi-Fi/Ethernet indicator for network connectivity status",
    "Implemented an automatic update fetcher for the frontend repository",
    "Added custom UI sound effects for menu navigation and selections",
    "Configured a system-wide script to hide the Windows mouse cursor completely",
    "Added a feature to randomize the background music track on every boot",
    "Implemented a battery level warning indicator for connected wireless controllers",
    "Added a 'Random Game' roulette button for undecided players",
    "Configured auto-login for the dedicated Windows arcade user account",
    "Added an in-menu downloader for custom UI themes and community artwork",
    "Refactored the main navigation loop to be strictly controller-driven",
    "Added an onscreen keyboard for searching games without a physical keyboard",
    "Integrated a weather widget just for fun on the home screen",
    "Added a 'Clear Cache' utility tool to free up disk space from temporary thumbnails",
    "Created a script to scrape game descriptions and metadata from the web",
    "Implemented a screensaver timeout setting in the options menu",
    "Added visual indicators for multiplayer-compatible games",
    "Configured a global 'Exit Game' hotkey to instantly kill any running game process",
    "Added a splash screen with the cabinet logo before games launch",
    "Implemented a custom notification popup system for background events",
    "Added support for video backgrounds behind the main menu UI",
    "Configured the system to automatically mount external USB drives for portable games"
]

log_dates = generate_dates(200)
with open('d:/Hoofd_Folder/CTRL_Arcadee/project_logs.txt', 'w') as f:
    f.write("Date: 2026-01-02\nFeature Added: Created the basic menu layout from scratch.\n\n")
    f.write("Date: 2026-01-04\nFeature Added: Added standard game icons to populate the menu grid.\n\n")
    f.write("Date: 2026-01-07\nFeature Added: Improved menu navigation with smoother scrolling transitions and polished UI elements.\n\n")
    
    for i in range(3, 200):
        feature = random.choice(project_features)
        f.write(f"Date: {log_dates[i].strftime('%Y-%m-%d')}\nFeature Added: {feature}\n\n")

# Generate Bug Fixes (approx 200 entries, 30% JS&B)
jsb_bugs = [
    "Just Shapes and Beats failed to recognize Player 1 analog input",
    "Just Shapes and Beats audio desynced completely after 30 minutes of continuous play",
    "Just Shapes and Beats crashed abruptly when loading certain custom user tracks",
    "Just Shapes and Beats opened in a minimized windowed state instead of borderless fullscreen",
    "Just Shapes and Beats controller rumble remained stuck on maximum intensity after taking damage",
    "Just Shapes and Beats save progress data failed to write to the hard drive upon exit",
    "Just Shapes and Beats Steam achievements overlay hook caused massive frame stuttering",
    "Just Shapes and Beats local multiplayer mode completely dropped Player 3 inputs",
    "Just Shapes and Beats master volume was abnormally loud compared to emulator games",
    "Just Shapes and Beats severe screen tearing occurred on fast moving boss levels",
    "Just Shapes and Beats UI elements flickered when the arcade cabinet was bumped",
    "Just Shapes and Beats failed to close properly when the global 'Exit Game' hotkey was pressed",
    "Just Shapes and Beats character got stuck moving left indefinitely due to deadzone issues",
    "Just Shapes and Beats intro video played at double speed",
    "Just Shapes and Beats threw a DirectX initialization error on cold boot"
]

other_bugs = [
    "Menu background music kept overlapping itself when repeatedly exiting and entering games",
    "Game icons completely failed to load if the game folder contained special foreign characters",
    "Player 2 arcade joystick was mapped inverted vertically in all fighting games",
    "System soft shutdown command from the menu did not execute, leaving the system on",
    "Network ROM folder share disconnected randomly during large file transfers",
    "Retro game launch script hung indefinitely on a black screen",
    "Menu search bar crashed the entire frontend if no search results were found",
    "Video screensaver failed to activate after 10 minutes of idle time as configured",
    "Menu volume slider did not actually change the Windows master volume level",
    "Favorites list forgot all saved entries after a system reboot",
    "Custom startup boot animation played too fast and finished before Windows loaded",
    "Menu digital clock displayed the wrong time zone entirely",
    "Player 3 wireless controller disconnected randomly during heavy rumble scenes",
    "Animated GIF icons on the menu grid caused extremely high CPU usage and lag",
    "Hardware coin insertion button registered twice per physical press",
    "Local high score tracker saved scores to the wrong game's database file",
    "Secondary marquee display remained completely blank after game launch",
    "Dark mode UI text was completely unreadable against certain background images",
    "Automatic control mapping script failed entirely for generic unbranded USB controllers",
    "SSH remote connection timed out unexpectedly during system maintenance",
    "Automatic UI update checker got stuck in an infinite downloading loop",
    "Menu navigation sound effects played at maximum volume regardless of the slider settings",
    "Windows mouse cursor reappeared in the center of the screen after exiting certain games",
    "Random background music track feature picked the exact same song 5 times in a row",
    "Controller battery indicator showed 0% for fully charged gamepads",
    "Random game roulette button launched completely empty directory folders",
    "Windows auto-login failed occasionally and got stuck at the Windows lock screen",
    "Downloaded custom UI themes broke the layout scaling on the 4K display",
    "Weather widget failed to fetch data and displayed 'NaN' for the temperature",
    "Onscreen keyboard keys got stuck if pressed too quickly in succession"
]

bug_dates = generate_dates(200)
with open('d:/Hoofd_Folder/CTRL_Arcadee/bug_fixes.txt', 'w') as f:
    for i in range(200):
        # 30% JS&B, 70% other
        is_jsb = random.random() < 0.30
        bug_desc = random.choice(jsb_bugs) if is_jsb else random.choice(other_bugs)
        
        f.write(f"Bug ID: BUG-{i+1:03d}\n")
        f.write(f"Date: {bug_dates[i].strftime('%Y-%m-%d')}\n")
        f.write(f"Issue: {bug_desc}\n")
        f.write(f"Resolution: Investigated the root cause and applied a patch to the codebase/configuration to resolve the behavior permanently.\n\n")

# Generate Testing Logs (approx 200 entries)
test_subjects = [
    "Menu responsiveness under heavy graphical load",
    "Arcade stick physical input latency",
    "Game launch and initialization time",
    "Background music transition smoothness",
    "Network share bulk file transfer speeds",
    "System cold boot duration",
    "Screensaver activation reliability on idle",
    "Volume control slider granularity",
    "High score database saving mechanism",
    "Marquee display synchronization speed",
    "UI scaling across different aspect ratios",
    "Controller hot-swapping during active gameplay",
    "Script stability when parsing empty directories",
    "Global 'Exit Game' hotkey responsiveness",
    "Automated backup script execution success rate"
]
methods = [
    "Used a high-speed 240fps camera to visually measure frame delay between action and screen",
    "Ran an automated python load-testing script to simulate 10,000 rapid menu interactions",
    "Used a physical digital stopwatch to time the exact sequence multiple times",
    "Monitored system resources and thread counts via Windows Task Manager",
    "Transferred 50GB of dummy zero-byte files over the local Gigabit network",
    "Connected 4 different brands of controllers and mashed all buttons simultaneously",
    "Left the arcade system completely untouched and idle for 24 hours straight",
    "Used a digital oscilloscope to measure the analog audio output signal variance",
    "Manually checked the SQLite database entries after simulating 100 game over screens",
    "Visually compared the primary and secondary screens during rapid game switching"
]
outcomes = [
    "Desired Outcome: Flawless execution. | Actual Outcome: Outcome met expectations perfectly, no further changes needed.",
    "Desired Outcome: Seamless performance. | Actual Outcome: Performed slightly below expectations, minor optimization required in the next patch.",
    "Desired Outcome: Stable operation. | Actual Outcome: Failed significantly under stress, feature disabled temporarily until completely rewritten.",
    "Desired Outcome: 100% success rate. | Actual Outcome: Passed the baseline, but discovered an edge case that needs addressing later.",
    "Desired Outcome: Acceptable speeds. | Actual Outcome: Exceeded expectations, performance is excellent and highly responsive.",
    "Desired Outcome: Trigger correctly every time. | Actual Outcome: Failed to trigger correctly due to a minor logic error in the batch script.",
    "Desired Outcome: Run without crashing. | Actual Outcome: Caused a full system crash during the test, high priority hotfix needed immediately.",
    "Desired Outcome: No memory leaks. | Actual Outcome: Worked flawlessly for 2 hours then degraded heavily, confirmed a slow memory leak.",
    "Desired Outcome: Consistent results across all trials. | Actual Outcome: Outcome was wildly inconsistent, requires further investigation into hardware faults.",
    "Desired Outcome: Instantaneous response. | Actual Outcome: Perfect result with zero measurable delay, marking the feature as stable."
]

test_dates = generate_dates(200)
with open('d:/Hoofd_Folder/CTRL_Arcadee/testing_log.txt', 'w') as f:
    for i in range(200):
        f.write(f"Date: {test_dates[i].strftime('%Y-%m-%d')}\n")
        f.write(f"Feature Tested: {random.choice(test_subjects)}\n")
        f.write(f"Testing Method: {random.choice(methods)}\n")
        f.write(f"Result: {random.choice(outcomes)}\n\n")

print("Generated all files successfully.")
