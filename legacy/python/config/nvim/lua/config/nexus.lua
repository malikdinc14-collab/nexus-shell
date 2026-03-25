-- Nexus Integration Core

-- === Load Nexus Modules ===
local nexus_home = os.getenv("NEXUS_HOME") or (os.getenv("HOME") .. "/.config/nexus-shell")
package.path = package.path .. ";" .. nexus_home .. "/config/nvim/lua/?.lua"

-- === State Sync ===
-- Broadcast current file to Nexus state for render daemon
local nexus_state = os.getenv("NEXUS_STATE") or "/tmp/nexus_" .. (os.getenv("USER") or "unknown")

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
-- Used by dispatch.sh to check for unsaved changes
function _G.is_dirty()
    for _, buf in ipairs(vim.api.nvim_list_bufs()) do
        if vim.api.nvim_buf_is_loaded(buf) and vim.bo[buf].modified then
            return "true"
        end
    end
    return "false"
end

-- === Diagnostics Configuration (from nexus_diag.lua) ===
vim.diagnostic.config({
    virtual_text = {
        prefix = '●',
        spacing = 2,
    },
    signs = true,
    underline = true,
    update_in_insert = false,
    severity_sort = true,
    float = {
        border = "rounded",
        source = "always",
    },
})

local signs = {
    Error = "✖",
    Warn = "▲",
    Hint = "●",
    Info = "ℹ",
}

for type, icon in pairs(signs) do
    local hl = "DiagnosticSign" .. type
    vim.fn.sign_define(hl, { text = icon, texthl = hl, numhl = "" })
end

-- Initial sync
sync_file_path()
