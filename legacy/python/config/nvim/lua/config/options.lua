-- Nexus-Shell Neovim Options

vim.g.mapleader = " "
vim.g.maplocalleader = " "

local opt = vim.opt

opt.termguicolors = true
opt.background = "dark"
opt.number = true
opt.relativenumber = false
opt.signcolumn = "yes"
opt.cursorline = true
opt.scrolloff = 8
opt.tabstop = 4
opt.shiftwidth = 4
opt.expandtab = true
opt.smartindent = true
opt.wrap = false
opt.swapfile = false
opt.backup = false
opt.undofile = true
opt.hlsearch = false
opt.incsearch = true
opt.ignorecase = true
opt.smartcase = true
opt.updatetime = 50
opt.colorcolumn = "100"

-- Disable netrw (we use neo-tree or yazi)
vim.g.loaded_netrw = 1
vim.g.loaded_netrwPlugin = 1
