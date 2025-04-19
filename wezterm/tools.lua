local M = {}

M.TruncateString = function(s, max_length)
	if #s > max_length then
		return "..." .. string.sub(s, #s - max_length, #s)
	else
		return s
	end
end

M.TabTitle = function(tab_info)
	local title = tab_info.tab_title
	if title and #title > 0 then
		return title
	else
		return tab_info.active_pane.title
	end
end

M.GetPwdFromPane = function(pane, max_length)
	local pwd = ""
	if pane then
		local c = pane:get_current_working_dir()
		if c then
			pwd = c.file_path
		end
	end
	return M.TruncateString(pwd, max_length)
end

return M
