-- Nexus Diagnostics Configuration
-- Minimal diagnostic display settings

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

-- Diagnostic signs
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
