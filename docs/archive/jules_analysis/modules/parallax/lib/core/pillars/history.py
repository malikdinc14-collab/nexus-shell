import os
import glob

def render(context, config, paths):
    """
    Renders the 'History' pillar and its sub-contexts.
    """
    output = []
    
    # 1. Main History View
    if context == "history":
        output.append({"label": "📍 Staged Context (Facts)", "type": "FOLDER", "payload": "contexts"})
        output.append({"label": "📁 Past Sessions", "type": "FOLDER", "payload": "history:sessions"})
        return output

    # 2. Past Sessions
    elif context == "history:sessions":
        logs = glob.glob("/tmp/px-ctx-*.log")
        for log in sorted(logs, key=os.path.getmtime, reverse=True)[:10]:
            name = os.path.basename(log).replace("px-ctx-", "").replace(".log", "")
            output.append({"label": f"🕒 Session {name}", "type": "ACTION", "path": f"px-session-load {name}"})
        return output

    return None
