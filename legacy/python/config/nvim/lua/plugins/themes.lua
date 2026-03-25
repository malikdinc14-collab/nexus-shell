return {
  -- Theme Plugins
  {
    "folke/tokyonight.nvim",
    priority = 1000,
    config = function()
      require("tokyonight").setup({ style = "night" })

      -- Nexus Theme Logic (embedded in the main theme config for simplicity)
      local nexus_state = os.getenv("NEXUS_STATE") or "/tmp/nexus_" .. (os.getenv("USER") or "unknown")
      local persistent_state = (os.getenv("NEXUS_HOME") or "") .. "/state/theme.json"

      local function get_active_theme()
        local f = io.open(nexus_state .. "/theme.json", "r")
        if not f then
             local p = (os.getenv("NEXUS_HOME") or "") .. "/state/theme.json"
             f = io.open(p, "r")
        end

        if not f then return "nexus-cyber" end

        local content = f:read("*a")
        f:close()
        return content:match('"name"%s*:%s*"([^"]+)"') or "nexus-cyber"
      end

      local function apply_theme()
        local theme = get_active_theme()
        local theme_map = {
            ["nexus-cyber"] = "tokyonight-night",
            ["ghost-noir"] = "catppuccin-mocha",
            ["axiom-amber"] = "tokyonight-moon",
            ["dracula"] = "dracula",
            ["nord"] = "nord",
            ["the-void"] = "tokyonight-storm",
        }
        local colorscheme = theme_map[theme] or "tokyonight-night"

        local ok = pcall(vim.cmd, "colorscheme " .. colorscheme)
        if not ok then
            pcall(vim.cmd, "colorscheme default")
        end
      end

      -- Apply on startup
      apply_theme()

      -- Re-apply when gaining focus
      vim.api.nvim_create_autocmd("FocusGained", {
          callback = apply_theme
      })
    end,
  },
  { "catppuccin/nvim", name = "catppuccin", lazy = true },
  { "Mofiqul/dracula.nvim", lazy = true },
  { "shaunsingh/nord.nvim", lazy = true },
}
