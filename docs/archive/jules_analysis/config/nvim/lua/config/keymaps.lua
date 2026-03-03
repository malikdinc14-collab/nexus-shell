-- Nexus-Shell Keymaps

local map = vim.keymap.set
local nexus_home = os.getenv("NEXUS_HOME") or (os.getenv("HOME") .. "/.config/nexus-shell")

-- === General ===

-- Quick save
map("n", "<leader>w", ":w<CR>", { desc = "Save" })

-- Better paste (don't overwrite register)
map("x", "<leader>p", '"_dP')

-- Copy to system clipboard
map({"n", "v"}, "<leader>y", '"+y')

-- Delete without yanking
map({"n", "v"}, "<leader>d", '"_d')

-- Quick escape
map("i", "jk", "<Esc>")

-- Move lines
map("v", "J", ":m '>+1<CR>gv=gv")
map("v", "K", ":m '<-2<CR>gv=gv")

-- Center cursor on navigation
map("n", "<C-d>", "<C-d>zz")
map("n", "<C-u>", "<C-u>zz")
map("n", "n", "nzzzv")
map("n", "N", "Nzzzv")

-- === Nexus Integration ===

-- Toggle render mode (Ctrl+Space is handled by tmux, this is backup)
map("n", "<leader>v", function()
    vim.cmd("confirm w")
    local nexus_scripts = nexus_home .. "/scripts"
    os.execute(nexus_scripts .. "/swap.sh")
end, { desc = "Toggle Render Mode" })
