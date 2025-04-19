local wezterm = require("wezterm")
local act = wezterm.action

local gruvbox_light_colors = {
	bg = "#F9F5D7",
	bg0 = "#FBF1C7",
	bg1 = "#EBDBB2",
	bg2 = "#D5C4A1",
	bg3 = "#BDAE93",
	bg4 = "#A89984",
	gray = "#928374",
	fg = "#3C3836",
	fg0 = "#282828",
	fg1 = "#3C3836",
	fg2 = "#504945",
	fg3 = "#665C54",
	fg4 = "#7C6F64",
	red = "#9D0006",
	red1 = "#CC241D",
	green = "#79740E",
	green1 = "#98971A",
	yellow = "#B57614",
	yellow1 = "#D79921",
	blue = "#076678",
	blue1 = "#458588",
	purple = "#8F3F71",
	purple1 = "#B16286",
	aqua = "#427B58",
	aqua1 = "#689D6A",
	orange = "#AF3A03",
	orange1 = "#D65D0E",
}

local config = {
	font = wezterm.font_with_fallback({
		{ family = "Maple Mono NF CN", weight = "Bold" },
		{ family = "Maple Mono", weight = "Bold" },
	}),
	font_size = 18,
	color_scheme = "GruvboxLight",

	-- tabs
	use_fancy_tab_bar = false,
	show_new_tab_button_in_tab_bar = false,
	hide_tab_bar_if_only_one_tab = true,
	tab_bar_at_bottom = true,
	text_background_opacity = 1,
	show_tab_index_in_tab_bar = false,
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
	foreground = gruvbox_light_colors.green1,
	tab_bar = {
		background = gruvbox_light_colors.blue,
		active_tab = {
			bg_color = gruvbox_light_colors.orange,
			fg_color = gruvbox_light_colors.bg1,
		},
		inactive_tab = {
			bg_color = gruvbox_light_colors.green,
			fg_color = gruvbox_light_colors.fg0,
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

local function tab_title(tab_info)
	local title = tab_info.tab_title
	if title and #title > 0 then
		return title
	else
		return tab_info.active_pane.title
	end
end
local SOLID_LEFT_ARROW = wezterm.nerdfonts.pl_right_hard_divider
local SOLID_RIGHT_ARROW = wezterm.nerdfonts.pl_left_hard_divider
wezterm.on("format-tab-title", function(tab, tabs, panes, config, hover, max_width)
	local edge_background = gruvbox_light_colors.blue
	local background = gruvbox_light_colors.green
	local foreground = gruvbox_light_colors.fg0

	if tab.is_active then
		background = gruvbox_light_colors.orange
		foreground = gruvbox_light_colors.bg1
	elseif hover then
		background = gruvbox_light_colors.green1
		foreground = gruvbox_light_colors.fg0
	end

	local edge_foreground = background

	local title = tab_title(tab)

	-- ensure that the titles fit in the available space,
	-- and that we have room for the edges.
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

	window:set_right_status(wezterm.format({
		{ Text = " " },
		{ Text = date },
		{ Text = " " },
		{ Text = hostname },
		{ Text = " " },
	}))
end)

config.inactive_pane_hsb = {
	saturation = 0.95,
	brightness = 0.95,
}

-- keys
config.leader = { key = "i", mods = "CTRL" }

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
