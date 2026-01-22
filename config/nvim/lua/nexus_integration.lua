-- Nexus-Shell Integration for Neovim
-- Add to your init.lua: require("nexus_integration")
-- Or source from: ~/.config/nexus-shell/config/nvim/lua/nexus_integration.lua

local M = {}

-- Only activate when inside a Nexus session
if not os.getenv("NEXUS_PROJECT") then
    return M
end

local nexus_state = os.getenv("NEXUS_STATE") or "/tmp/nexus_" .. (os.getenv("USER") or "unknown")
local nexus_config = os.getenv("NEXUS_CONFIG") or (os.getenv("HOME") .. "/.config/nexus-shell")

-- === State Sync ===
-- Broadcast current file to Nexus state for render daemon and cross-pane awareness
local function sync_file_path()
    local filepath = vim.fn.expand("%:p")
    if filepath ~= "" then
        local f = io.open(nexus_state .. "/last_path", "w")
        if f then
            f:write(filepath)
            f:close()
        end
    end
end

vim.api.nvim_create_autocmd({"BufEnter", "BufWritePost"}, {
    callback = sync_file_path
})

-- === Dirty State Helper ===
-- Used by dispatch.sh to check for unsaved changes before switching modes
function _G.nexus_is_dirty()
    for _, buf in ipairs(vim.api.nvim_list_bufs()) do
        if vim.api.nvim_buf_is_loaded(buf) and vim.bo[buf].modified then
            return "true"
        end
    end
    return "false"
end

-- === Keybindings ===
-- Toggle render/preview mode (Ctrl+Space is handled by tmux, this is backup)
vim.keymap.set("n", "<leader>nv", function()
    vim.cmd("confirm w")
    os.execute(nexus_config .. "/scripts/swap.sh 2>/dev/null")
end, { desc = "Nexus: Toggle Render Mode" })

-- Open file in tree pane
vim.keymap.set("n", "<leader>nt", function()
    local dir = vim.fn.expand("%:p:h")
    os.execute(string.format("tmux send-keys -t '{left-of}' 'cd %s && yazi' Enter 2>/dev/null", dir))
end, { desc = "Nexus: Focus Tree" })

-- === Status indicator ===
-- Optional: Add to your statusline
M.status = function()
    return "[NXS:" .. (os.getenv("NEXUS_PROJECT") or "?") .. "]"
end

-- Initial sync
sync_file_path()

vim.notify("Nexus-Shell integration loaded", vim.log.levels.INFO)

return M
