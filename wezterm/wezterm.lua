local wezterm = require("wezterm")
local C = require("colors")
local T = require("tools")
local act = wezterm.action

local config = {
	font = wezterm.font_with_fallback({
		{ family = "Maple Mono NF CN", weight = "Bold" },
		{ family = "Maple Mono", weight = "Bold" },
	}),
	font_size = 18,
	color_scheme = "GruvboxLight",

	-- tabs
	-- enable_tab_bar = false,
	use_fancy_tab_bar = false,
	show_new_tab_button_in_tab_bar = false,
	hide_tab_bar_if_only_one_tab = true,
	-- tab_bar_at_bottom = true,
	text_background_opacity = 1,
	show_tab_index_in_tab_bar = false,
	tab_max_width = 32,
	-- 非 native fullscreen 时, 切回来时会展示 dock
	native_macos_fullscreen_mode = true,
	-- disable_default_key_bindings = true,
}

config.font_rules = {
	{
		intensity = "Half",
		italic = false,
		font = config.font,
	},
}

config.colors = {
	-- text
	-- foreground = C.GruvboxLightColors.green1,
	tab_bar = {
		background = C.GruvboxLightColors.blue,
		active_tab = {
			bg_color = C.GruvboxLightColors.orange,
			fg_color = C.GruvboxLightColors.bg1,
		},
		inactive_tab = {
			bg_color = C.GruvboxLightColors.green,
			fg_color = C.GruvboxLightColors.fg0,
			italic = true,
		},
	},
}

-- affect when using fancy tab bar
config.window_padding = {
	left = 0,
	right = 0,
	top = 0,
	bottom = 0,
}

local SOLID_LEFT_ARROW = wezterm.nerdfonts.pl_right_hard_divider
local SOLID_RIGHT_ARROW = wezterm.nerdfonts.pl_left_hard_divider
wezterm.on("format-tab-title", function(tab, tabs, panes, cfg, hover, max_width)
	local edge_background = C.GruvboxLightColors.blue
	local background = C.GruvboxLightColors.green
	local foreground = C.GruvboxLightColors.fg0

	if tab.is_active then
		background = C.GruvboxLightColors.orange
		foreground = C.GruvboxLightColors.bg1
	elseif hover then
		background = C.GruvboxLightColors.green1
		foreground = C.GruvboxLightColors.fg0
	end

	local edge_foreground = background
	local title = T.TabTitle(tab)
	title = wezterm.truncate_right(title, max_width - 2)

	return {
		{ Background = { Color = edge_background } },
		{ Foreground = { Color = edge_foreground } },
		{ Text = SOLID_LEFT_ARROW },
		{ Background = { Color = background } },
		{ Foreground = { Color = foreground } },
		{ Text = title },
		{ Background = { Color = edge_background } },
		{ Foreground = { Color = edge_foreground } },
		{ Text = SOLID_RIGHT_ARROW },
	}
end)

wezterm.on("update-right-status", function(window, pane)
	local date = wezterm.strftime("%H:%M:%S")
	local hostname = wezterm.hostname()
	local username = os.getenv("USER") or os.getenv("LOGNAME") or os.getenv("USERNAME")
	-- https://wezterm.org/config/lua/wezterm.url/Url.html
	-- local pwd = T.GetPwdFromPane(pane, 16)

	window:set_right_status(wezterm.format({
		{ Foreground = { Color = C.GruvboxLightColors.bg1 } },
		-- { Text = " " .. pwd .. " " },
		{ Text = " " .. username .. "@" },
		{ Text = hostname .. " " },
		{ Text = "󱑂 " .. date .. " " },
	}))
end)

config.inactive_pane_hsb = {
	saturation = 0.95,
	brightness = 0.95,
}

-- keys
config.leader = { key = "a", mods = "CTRL" }

config.keys = {
	{ key = "c", mods = "LEADER", action = wezterm.action.ActivateCommandPalette },
	-- scroll
	{ key = "[", mods = "LEADER", action = act.ScrollByPage(-0.5) },
	{ key = "]", mods = "LEADER", action = act.ScrollByPage(0.5) },
	-- copy mode
	-- press ctrl+v again to select rectangle area
	{ key = "v", mods = "LEADER", action = wezterm.action.ActivateCopyMode },
	-- panes
	{
		key = "\\",
		mods = "LEADER",
		action = wezterm.action.SplitHorizontal({ domain = "CurrentPaneDomain" }),
	},
	{
		key = "-",
		mods = "LEADER",
		action = wezterm.action.SplitVertical({ domain = "CurrentPaneDomain" }),
	},
	{
		key = "r",
		mods = "LEADER",
		action = act.ActivateKeyTable({
			name = "resize",
			one_shot = false,
		}),
	},
	{
		key = "p",
		mods = "LEADER",
		action = act.ActivateKeyTable({
			name = "pane",
			timeout_milliseconds = 1000,
		}),
	},
	{ key = "h", mods = "LEADER", action = act.ActivatePaneDirection("Left") },
	{ key = "l", mods = "LEADER", action = act.ActivatePaneDirection("Right") },
	{ key = "k", mods = "LEADER", action = act.ActivatePaneDirection("Up") },
	{ key = "j", mods = "LEADER", action = act.ActivatePaneDirection("Down") },
}
config.key_tables = {
	resize = {
		{ key = "LeftArrow", action = act.AdjustPaneSize({ "Left", 1 }) },
		{ key = "h", action = act.AdjustPaneSize({ "Left", 1 }) },

		{ key = "RightArrow", action = act.AdjustPaneSize({ "Right", 1 }) },
		{ key = "l", action = act.AdjustPaneSize({ "Right", 1 }) },

		{ key = "UpArrow", action = act.AdjustPaneSize({ "Up", 1 }) },
		{ key = "k", action = act.AdjustPaneSize({ "Up", 1 }) },

		{ key = "DownArrow", action = act.AdjustPaneSize({ "Down", 1 }) },
		{ key = "j", action = act.AdjustPaneSize({ "Down", 1 }) },

		-- Cancel the mode by pressing escape
		{ key = "Escape", action = "PopKeyTable" },
	},

	pane = {
		{ key = "LeftArrow", action = act.ActivatePaneDirection("Left") },
		{ key = "h", action = act.ActivatePaneDirection("Left") },

		{ key = "RightArrow", action = act.ActivatePaneDirection("Right") },
		{ key = "l", action = act.ActivatePaneDirection("Right") },

		{ key = "UpArrow", action = act.ActivatePaneDirection("Up") },
		{ key = "k", action = act.ActivatePaneDirection("Up") },

		{ key = "DownArrow", action = act.ActivatePaneDirection("Down") },
		{ key = "j", action = act.ActivatePaneDirection("Down") },
	},
}

return config
