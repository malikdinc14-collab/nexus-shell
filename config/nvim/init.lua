-- Nexus-Shell Neovim Configuration

-- === Basic Settings ===
vim.opt.termguicolors = true
vim.opt.background = "dark"
vim.opt.number = true
vim.opt.relativenumber = false
vim.opt.signcolumn = "yes"
vim.opt.cursorline = true
vim.opt.scrolloff = 8
vim.opt.tabstop = 4
vim.opt.shiftwidth = 4
vim.opt.expandtab = true
vim.opt.smartindent = true
vim.opt.wrap = false
vim.opt.swapfile = false
vim.opt.backup = false
vim.opt.undofile = true
vim.opt.hlsearch = false
vim.opt.incsearch = true
vim.opt.ignorecase = true
vim.opt.smartcase = true
vim.opt.updatetime = 50
vim.opt.colorcolumn = "100"

-- === Leader Key ===
vim.g.mapleader = " "

-- === Syntax ===
vim.cmd("syntax on")

-- === Load Nexus Modules ===
local nexus_home = os.getenv("NEXUS_HOME") or (os.getenv("HOME") .. "/.config/nexus-shell")
package.path = package.path .. ";" .. nexus_home .. "/config/nvim/lua/?.lua"

-- Theme
require("nexus_theme")

-- Diagnostics display
pcall(require, "nexus_diag")

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

-- === Keybindings ===
-- Quick save
vim.keymap.set("n", "<leader>w", ":w<CR>", { desc = "Save" })

-- Toggle render mode (Ctrl+Space is handled by tmux, this is backup)
vim.keymap.set("n", "<leader>v", function()
    vim.cmd("confirm w")
    local nexus_scripts = nexus_home .. "/scripts"
    os.execute(nexus_scripts .. "/swap.sh")
end, { desc = "Toggle Render Mode" })

-- Quick navigation
vim.keymap.set("n", "<C-d>", "<C-d>zz")
vim.keymap.set("n", "<C-u>", "<C-u>zz")
vim.keymap.set("n", "n", "nzzzv")
vim.keymap.set("n", "N", "Nzzzv")

-- Better paste (don't overwrite register)
vim.keymap.set("x", "<leader>p", '"_dP')

-- Copy to system clipboard
vim.keymap.set("n", "<leader>y", '"+y')
vim.keymap.set("v", "<leader>y", '"+y')

-- Delete without yanking
vim.keymap.set("n", "<leader>d", '"_d')
vim.keymap.set("v", "<leader>d", '"_d')

-- Quick escape
vim.keymap.set("i", "jk", "<Esc>")

-- Move lines
vim.keymap.set("v", "J", ":m '>+1<CR>gv=gv")
vim.keymap.set("v", "K", ":m '<-2<CR>gv=gv")
