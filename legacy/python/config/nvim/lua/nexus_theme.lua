-- Nexus Theme Loader
-- Loads the appropriate colorscheme based on active theme

local nexus_state = os.getenv("NEXUS_STATE") or "/tmp/nexus_" .. (os.getenv("USER") or "unknown")
local theme_file = nexus_state .. "/theme.json"

local function get_active_theme()
    local f = io.open(theme_file, "r")
    if not f then
        return "nexus-cyber"
    end
    
    local content = f:read("*a")
    f:close()
    
    -- Simple JSON parsing for "name" field
    local name = content:match('"name"%s*:%s*"([^"]+)"')
    return name or "nexus-cyber"
end

local function apply_theme()
    local theme = get_active_theme()
    
    -- Map theme names to colorschemes
    local theme_map = {
        ["nexus-cyber"] = "nexus-cyber",
        ["ghost-noir"] = "habamax",
        ["axiom-amber"] = "desert",
        ["dracula"] = "habamax",
        ["nord"] = "slate",
        ["solarized"] = "slate",
        ["the-void"] = "default",
    }
    
    local colorscheme = theme_map[theme] or "nexus-cyber"
    
    -- Try to load the colorscheme
    local ok, _ = pcall(vim.cmd, "colorscheme " .. colorscheme)
    if not ok then
        -- Fallback to default if custom scheme not found
        vim.cmd("colorscheme default")
    end
end

-- Apply on startup
apply_theme()

-- Re-apply when gaining focus (in case theme changed)
vim.api.nvim_create_autocmd("FocusGained", {
    callback = apply_theme
})
