local wezterm = require("wezterm")
local act = wezterm.action

local config = {
	font = wezterm.font("Maple Mono", { weight = "Bold" }),
	font_size = 18,
	color_scheme = "GruvboxLight",

	-- tabs
	use_fancy_tab_bar = false,
	-- hide_tab_bar_if_only_one_tab = true,
	-- tab_bar_at_bottom = true,

	text_background_opacity = 0.3,
}

-- affect when using fancy tab bar
config.window_frame = {
	font = wezterm.font("Maple Mono", { italic = true }),
	font_size = 15,
}

wezterm.on("update-right-status", function(window, pane)
	local date = wezterm.strftime("%H:%M:%S")
	local hostname = wezterm.hostname()
	-- local table = window:active_key_table()
	-- if table then
	-- 	table = "T[" .. table .. "]"
	-- end

	window:set_right_status(wezterm.format({
		{ Foreground = { Color = "#ffffff" } },
		-- { Background = { Color = "#005f5f" } },
		{ Text = date },
		{ Text = " | " },
		{ Text = hostname },
		{ Text = " " },
	}))
end)

config.leader = { key = "n", mods = "CTRL" }
config.keys = {
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
