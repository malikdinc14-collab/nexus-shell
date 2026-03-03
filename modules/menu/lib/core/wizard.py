"""
Parallax Wizard Manager
=======================

This module (`lib.core.wizard`) handles the **Interactive Parameter Collection** for actions.
It parses scripts searching for `@param` annotations and generates a sequence of FZF prompts.
"""
import os
import glob
import re
import json
import time
from pathlib import Path

class WizardManager:
    def __init__(self, session_id, base_dir, bin_dir):
        self.session_id = session_id
        self.base_dir = base_dir
        self.bin_dir = bin_dir
        
        # Define paths
        self.params_file = f"/tmp/px-collected-params-{session_id}.sh"
        self.pending_file = f"/tmp/px-pending-action-{session_id}.log"
        self.params_meta_file = f"/tmp/px-params-meta-{session_id}.json"
        self.return_ctx_file = f"/tmp/px-prompt-return-{session_id}.log"
        self.ctx_file = os.environ.get("PX_CTX_FILE", f"/tmp/px-ctx-{session_id}.log")
        self.signal_file = os.environ.get("PX_SIGNAL_FILE", f"/tmp/px-signal-{session_id}.sh")
        self.link_dir = os.path.expanduser("~/.parallax/links")

    def _send_to_stage(self, message):
        """Helper to echo text to the Stage pane via tmux."""
        safe_msg = message.replace('"', '\\"').replace("'", "'\\''")
        # Use px-ask helper (defined in px-link) for clean output
        cmd = f"tmux send-keys -t 0 \" px-ask '{safe_msg}'\" Enter"
        os.system(cmd)

    def init_wizard(self, action_payload, context):
        """Initializes a new wizard session for an action."""
        try:
            # Save state
            with open(self.pending_file, 'w') as f: f.write(action_payload)
            with open(self.params_file, 'w') as f: f.write("") # Clear params
            with open(self.return_ctx_file, 'w') as f: f.write(context)
            
            # Parse Params
            params = self._get_params(action_payload)
            
            # Save Meta (params is already a list of dicts)
            with open(self.params_meta_file, 'w') as f: json.dump(params, f)
            
            # Trigger First Prompt to Stage: Handled by session.py Header (Zero Pollution)
            # if params:
            #     p0 = params[0]
            #     self._send_to_stage(f"{p0['desc']} ({p0['var']})")

            return params
        except Exception as e:
            with open('/tmp/px-debug.log', 'a') as f: f.write(f"  [WIZARD] ERROR: {str(e)}\\n")
            return []

    def process_query(self, ctx, query):
        """Processes free-form text input from the dashboard query field."""
        try:
            parts = ctx.split('-')
            idx = int(parts[1])
            
            # 1. Load Meta to get var name
            with open(self.params_meta_file, 'r') as f:
                params_meta = json.load(f)
                
            if idx >= len(params_meta):
                 return f"change-header( ❌ ERROR: Out of range )"
                 
            var = params_meta[idx].get("var", "UNKNOWN")
            
            # 2. Save Answer
            safe_query = query.replace("'", "'\\''")
            with open(self.params_file, 'a') as f:
                f.write(f"export {var}='{safe_query}'\n")
            
            # 3. Decision: Next Prompt or Execute?
            action_path = Path(self.pending_file).read_text().strip()
            params = self._get_params(action_path)
            next_i = idx + 1
            
            # Zero Pollution: No shell confirmation
            echo_cmd = ""
            
            if next_i < len(params):
                p = params[next_i]
                nv = p["var"]
                desc = p["desc"]
                next_ctx = f"prompt-{next_i}"
                
                # Zero Pollution: Question in Header
                import re
                safe_desc = re.sub(r"([()|\"\'])", r"\\\1", desc)
                header = f"PARALLAX │ INPUT │ {safe_desc} ({nv.upper()})"
                
                # Zero Pollution: No shell typing
                stage_send = ""
                
                cmd = (
                    f"execute-silent(echo '{next_ctx}' > {self.ctx_file}; {echo_cmd}; {stage_send})+"
                    f"reload('{self.bin_dir}/px-engine' --context '{next_ctx}')+"
                    f"change-header({header})+"
                    f"change-prompt(Input > )+"
                    f"clear-query"
                )
                return cmd
            else:
                 return f"execute-silent({echo_cmd})+" + self._finalize_execution(action_path) + "+change-prompt(Dashboard > )"
                 
        except Exception as e:
            return f"change-header( ❌ WIZARD ERROR: {str(e)} )"

    def process_input(self, payload, label):
        """Processes a PROMPT_VAL selection."""
        try:
            parts = payload.split('|')
            if len(parts) < 4:
                return f"change-header( ❌ ERROR: Invalid Payload )"

            idx, var, desc, next_idx = parts[:4]
            value = label
            
            with open(self.params_file, 'a') as f:
                f.write(f"export {var}='{value}'\n")
            
            action_path = Path(self.pending_file).read_text().strip()
            params = self._get_params(action_path)
            next_i = int(next_idx)

            next_i = int(next_idx)

            # Zero Pollution: No shell confirmation
            echo_cmd = ""

            if next_i < len(params):
                p = params[next_i]
                nv = p["var"]
                desc = p["desc"]
                next_ctx = f"prompt-{next_i}"
                
                # Zero Pollution: Question in Header
                import re
                safe_desc = re.sub(r"([()|\"\'])", r"\\\1", desc)
                header = f"PARALLAX │ INPUT │ {safe_desc} ({nv.upper()})"
                
                # Zero Pollution: No shell typing
                stage_send = ""
                
                cmd = (
                    f"execute-silent(echo '{next_ctx}' > {self.ctx_file}; {echo_cmd}; {stage_send})+"
                    f"reload('{self.bin_dir}/px-engine' --context '{next_ctx}')+"
                    f"change-header({header})+"
                    f"change-prompt(Input > )+"
                    f"clear-query"
                )
                return cmd
            else:
                return f"execute-silent({echo_cmd})+" + self._finalize_execution(action_path) + "+change-prompt(Dashboard > )"

        except Exception as e:
            return f"change-header( ❌ WIZARD ERROR: {str(e)} )"

    def render_prompt(self, idx):
        """Generates the FZF output for a prompt context."""
        if not os.path.exists(self.params_meta_file):
            return []
            
        with open(self.params_meta_file, 'r') as f:
            params_meta = json.load(f)
            
        if idx >= len(params_meta):
            return []
            
        param = params_meta[idx]
        var = param["var"]
        desc = param.get("desc", "")
        options_list = param.get("options", [])
        dynamic_cmd = param.get("dynamic_cmd")
        
        output = []
        
        # 1. Dynamic Options
        if dynamic_cmd:
            import subprocess
            try:
                result = subprocess.check_output(dynamic_cmd, shell=True, stderr=subprocess.DEVNULL).decode().strip()
                options = [o.strip() for o in result.splitlines() if o.strip()]
                for opt in options:
                    p_load = f"{idx}|{var}|{desc}|{idx+1}"
                    output.append({"label": opt, "type": "PROMPT_VAL", "payload": p_load})
                if output: return output
            except: pass
            
        # 2. Fixed Options (from brackets)
        if options_list:
            for opt in options_list:
                p_load = f"{idx}|{var}|{desc}|{idx+1}"
                output.append({"label": opt, "type": "PROMPT_VAL", "payload": p_load})
            return output

        # 3. Free-form input mode (No items in list - user types in prompt field)
        return [{"label": "  ⌨️  Type your answer and press Enter", "type": "DISABLED", "payload": "NONE"}]

    def _finalize_execution(self, action_path):
        """Generates the final shell command to run the action."""
        is_linked = False
        if os.path.exists(self.link_dir):
            for lk in glob.glob(f"{self.link_dir}/*.link"):
                try:
                    if Path(lk).read_text().strip() == self.session_id:
                        is_linked = True
                        break
                except: pass

        env_source = '[[ -f "$PX_ENV_FILE" ]] && source "$PX_ENV_FILE";'
        params_source = f"source {self.params_file};"
        
        if is_linked:
            raw_cmd = f"{env_source} {params_source} zsh {action_path} # {time.time()}"
            with open(self.signal_file, 'w') as f: f.write(f"LABEL:Action|CMD:{raw_cmd}\n")
            return f"change-header( ⚡ SENT TO LINKED SHELL )+reload(px-engine --context $(cat {self.return_ctx_file}))"
        else:
            full_cmd = f"{env_source} {params_source} zsh {action_path}"
            cmd_safe = full_cmd.replace('"', '\\"')
            return f"change-header( ⚡ EXECUTING... )+execute-silent(tmux send-keys -t 0 \"{cmd_safe}\" Enter)+reload(px-engine --context $(cat {self.return_ctx_file}))"

    def _get_params(self, file_path):
        """Parses @param tags from the script. Returns list of dicts."""
        params = []
        if not os.path.exists(file_path): return params
        try:
            with open(file_path, 'r') as f:
                for line in f.readlines()[:50]:
                    if "@param" in line:
                        line = line.strip().split("@param", 1)[1].strip()
                        if ":" in line:
                            var_part, desc_part = line.split(":", 1)
                            var_name = var_part.strip()
                            desc = desc_part.strip()
                            default = ""
                            dynamic_cmd = None
                            options = []
                            
                            # Extract Dynamic Cmd $(...)
                            if "$(" in desc:
                                start_idx = desc.find("$(")
                                balance = 0
                                for i in range(start_idx + 2, len(desc)):
                                    if desc[i] == '(': balance += 1
                                    elif desc[i] == ')':
                                        if balance == 0:
                                            dynamic_cmd = desc[start_idx+2:i]
                                            desc = desc[:start_idx] + desc[i+1:]
                                            break
                                        else: balance -= 1
                            
                            # Extract Fixed Options [...]
                            if "[" in desc and "]" in desc:
                                try:
                                    opts_match = re.search(r'\[([^\]]+)\]', desc)
                                    if opts_match:
                                        raw_opts = opts_match.group(1)
                                        options = [o.strip() for o in raw_opts.split(",")]
                                        desc = desc.replace(f"[{raw_opts}]", "").strip()
                                except: pass

                            # Extract Default (...)
                            if not dynamic_cmd and not options:
                                match = re.search(r'\(([^)]+)\)', desc)
                                if match:
                                    default = match.group(1)
                                    desc = desc.replace(f"({default})", "").strip()
                            
                            params.append({
                                "var": var_name, 
                                "desc": desc.strip(), 
                                "default": default, 
                                "dynamic_cmd": dynamic_cmd,
                                "options": options
                            })
        except: pass
        return params
