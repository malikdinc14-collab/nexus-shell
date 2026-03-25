-- nexus-sidebar.yazi/main.lua
-- Sovereign Anchor: Bridging the Isolation Gap.

-- The Sync Bridge: Reaches out to the UI thread to get the TRUE state.
local get_cwd = ya.sync(function(state)
	return tostring(cx.active.current.cwd)
end)

local function split(s, delimiter)
    local result = {}
    for match in (s..delimiter):gmatch("(.-)"..delimiter) do
        table.insert(result, match)
    end
    return result
end

return {
	entry = function(_, job)
		local action = job.args[1]
		if not action then return end

		local physical_root = os.getenv("PROJECT_ROOT")
		local virtual_root = os.getenv("VIRTUAL_ROOT")
		local workspace_roots_raw = os.getenv("NEXUS_WORKSPACE_ROOTS")
		
		if physical_root then physical_root = physical_root:gsub("/$", "") end
		if virtual_root then virtual_root = virtual_root:gsub("/$", "") end
		
		-- Use the Sync Bridge to get the CWD from the UI thread
		local current = get_cwd():gsub("/$", "")

		if action == "leave" then
			local is_at_root = false
			
			-- 1. Check physical roots (Workspace aware)
			if workspace_roots_raw then
				-- FIX: Split by | to handle paths with spaces correctly
				local roots = split(workspace_roots_raw, "|")
				for _, r in ipairs(roots) do
					if current == r:gsub("/$", "") then
						is_at_root = true
						break
					end
				end
			elseif physical_root and current == physical_root then
				is_at_root = true
			end
			
			-- 2. Check virtual container
			if not is_at_root and virtual_root and current == virtual_root then
				is_at_root = true
			end

			if is_at_root then
				ya.notify({
					title = "Sovereign Anchor",
					content = "Locked: Project Boundary Reached",
					timeout = 1,
					level = "info"
				})
			else
				ya.manager_emit("leave", {})
			end
		elseif action == "enter" then
			ya.manager_emit("enter", {})
		end
	end
}
