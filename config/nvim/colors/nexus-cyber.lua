-- Nexus-Cyber Colorscheme for Neovim
-- Cyan on dark - the default Nexus theme

vim.cmd("hi clear")
if vim.fn.exists("syntax_on") then
    vim.cmd("syntax reset")
end

vim.g.colors_name = "nexus-cyber"

local colors = {
    bg = "#0a0e14",
    bg_light = "#141820",
    bg_lighter = "#1a1f2c",
    fg = "#c0c0c0",
    fg_dim = "#707080",
    cyan = "#00ffff",
    magenta = "#ff00ff",
    green = "#50fa7b",
    yellow = "#ffb86c",
    red = "#ff5555",
    blue = "#6272a4",
    purple = "#bd93f9",
    orange = "#ffb86c",
    comment = "#4a5568",
    selection = "#2d3748",
}

local hi = function(group, opts)
    vim.api.nvim_set_hl(0, group, opts)
end

-- Editor
hi("Normal", { fg = colors.fg, bg = colors.bg })
hi("NormalFloat", { fg = colors.fg, bg = colors.bg_light })
hi("Cursor", { fg = colors.bg, bg = colors.cyan })
hi("CursorLine", { bg = colors.bg_light })
hi("CursorColumn", { bg = colors.bg_light })
hi("ColorColumn", { bg = colors.bg_lighter })
hi("LineNr", { fg = colors.fg_dim })
hi("CursorLineNr", { fg = colors.cyan, bold = true })
hi("SignColumn", { bg = colors.bg })
hi("VertSplit", { fg = colors.cyan, bg = colors.bg })
hi("WinSeparator", { fg = colors.cyan, bg = colors.bg })
hi("Folded", { fg = colors.comment, bg = colors.bg_light })
hi("FoldColumn", { fg = colors.comment, bg = colors.bg })
hi("NonText", { fg = colors.fg_dim })
hi("SpecialKey", { fg = colors.fg_dim })
hi("EndOfBuffer", { fg = colors.bg })

-- Selections & Search
hi("Visual", { bg = colors.selection })
hi("VisualNOS", { bg = colors.selection })
hi("Search", { fg = colors.bg, bg = colors.yellow })
hi("IncSearch", { fg = colors.bg, bg = colors.cyan })
hi("MatchParen", { fg = colors.cyan, bold = true, underline = true })

-- Status & Tab line
hi("StatusLine", { fg = colors.cyan, bg = colors.bg_lighter })
hi("StatusLineNC", { fg = colors.fg_dim, bg = colors.bg_light })
hi("TabLine", { fg = colors.fg_dim, bg = colors.bg_light })
hi("TabLineSel", { fg = colors.cyan, bg = colors.bg_lighter })
hi("TabLineFill", { bg = colors.bg })

-- Popup Menu
hi("Pmenu", { fg = colors.fg, bg = colors.bg_light })
hi("PmenuSel", { fg = colors.bg, bg = colors.cyan })
hi("PmenuSbar", { bg = colors.bg_lighter })
hi("PmenuThumb", { bg = colors.cyan })

-- Messages
hi("ModeMsg", { fg = colors.cyan })
hi("MoreMsg", { fg = colors.cyan })
hi("Question", { fg = colors.cyan })
hi("WarningMsg", { fg = colors.yellow })
hi("ErrorMsg", { fg = colors.red })

-- Diff
hi("DiffAdd", { fg = colors.green, bg = "#1a2f1a" })
hi("DiffChange", { fg = colors.yellow, bg = "#2f2f1a" })
hi("DiffDelete", { fg = colors.red, bg = "#2f1a1a" })
hi("DiffText", { fg = colors.cyan, bg = "#1a2f2f" })

-- Syntax
hi("Comment", { fg = colors.comment, italic = true })
hi("Constant", { fg = colors.purple })
hi("String", { fg = colors.green })
hi("Character", { fg = colors.green })
hi("Number", { fg = colors.purple })
hi("Boolean", { fg = colors.purple })
hi("Float", { fg = colors.purple })

hi("Identifier", { fg = colors.fg })
hi("Function", { fg = colors.cyan })

hi("Statement", { fg = colors.magenta })
hi("Conditional", { fg = colors.magenta })
hi("Repeat", { fg = colors.magenta })
hi("Label", { fg = colors.magenta })
hi("Operator", { fg = colors.cyan })
hi("Keyword", { fg = colors.magenta })
hi("Exception", { fg = colors.magenta })

hi("PreProc", { fg = colors.cyan })
hi("Include", { fg = colors.magenta })
hi("Define", { fg = colors.magenta })
hi("Macro", { fg = colors.cyan })
hi("PreCondit", { fg = colors.cyan })

hi("Type", { fg = colors.cyan })
hi("StorageClass", { fg = colors.magenta })
hi("Structure", { fg = colors.cyan })
hi("Typedef", { fg = colors.cyan })

hi("Special", { fg = colors.orange })
hi("SpecialChar", { fg = colors.orange })
hi("Tag", { fg = colors.cyan })
hi("Delimiter", { fg = colors.fg })
hi("SpecialComment", { fg = colors.cyan })
hi("Debug", { fg = colors.red })

hi("Underlined", { fg = colors.cyan, underline = true })
hi("Ignore", { fg = colors.fg_dim })
hi("Error", { fg = colors.red })
hi("Todo", { fg = colors.bg, bg = colors.yellow, bold = true })

-- Treesitter (if available)
hi("@variable", { fg = colors.fg })
hi("@function", { fg = colors.cyan })
hi("@function.builtin", { fg = colors.cyan })
hi("@keyword", { fg = colors.magenta })
hi("@keyword.function", { fg = colors.magenta })
hi("@string", { fg = colors.green })
hi("@comment", { fg = colors.comment, italic = true })
hi("@type", { fg = colors.cyan })
hi("@type.builtin", { fg = colors.cyan })
hi("@constant", { fg = colors.purple })
hi("@constant.builtin", { fg = colors.purple })
hi("@property", { fg = colors.fg })
hi("@punctuation", { fg = colors.fg })
hi("@punctuation.bracket", { fg = colors.fg })
hi("@operator", { fg = colors.cyan })

-- Diagnostics
hi("DiagnosticError", { fg = colors.red })
hi("DiagnosticWarn", { fg = colors.yellow })
hi("DiagnosticInfo", { fg = colors.cyan })
hi("DiagnosticHint", { fg = colors.green })
hi("DiagnosticUnderlineError", { sp = colors.red, undercurl = true })
hi("DiagnosticUnderlineWarn", { sp = colors.yellow, undercurl = true })
hi("DiagnosticUnderlineInfo", { sp = colors.cyan, undercurl = true })
hi("DiagnosticUnderlineHint", { sp = colors.green, undercurl = true })

-- Git Signs (if using gitsigns.nvim)
hi("GitSignsAdd", { fg = colors.green })
hi("GitSignsChange", { fg = colors.yellow })
hi("GitSignsDelete", { fg = colors.red })

-- Telescope (if using)
hi("TelescopeBorder", { fg = colors.cyan })
hi("TelescopePromptBorder", { fg = colors.cyan })
hi("TelescopeResultsBorder", { fg = colors.cyan })
hi("TelescopePreviewBorder", { fg = colors.cyan })
hi("TelescopeSelection", { bg = colors.selection })
hi("TelescopeMatching", { fg = colors.cyan, bold = true })
