
-- Luraph runtime function (from the VM object, not part of the script: not lifted).
-- LPH_ENCFUNC decrypts a function this way: (key, encrypted buffer, ...) -> function.
local function luraph_runtime1(...)
	error("Luraph runtime function, not devirtualized")
end

local tbl = {
	[42] = islclosure,
	[282] = "delay",
	[462] = function()
		error("devirt: newindex None (at 0:10)")
	end,
	[569] = "AnchorPoint",
	[292] = function()
		error("devirt: index nil @272,644812 - 272,644816 (at 0:14)")
	end,
	[532] = function()
		error("devirt: index nil @272,644812 - 272,644816 (at 0:8)")
	end,
	[417] = function(arg)
		local v = arg[366](arg[552])
		error("devirt: newindex None (at 0:10)")
	end,
	[81] = function()
		error("devirt: index nil @272,644812 - 272,644816 (at 0:7)")
	end,
	[337] = function(arg, arg2, arg3)
		arg3[62](arg2)
		error("devirt: index nil @272,676217 - 272,676221 (at 0:11)")
	end,
	[646] = "NextInteger",
	[158] = function()
		error("devirt: index nil @272,644812 - 272,644816 (at 0:5)")
	end,
	[123] = "readu32",
	[84] = function(arg, arg2)
		arg2(1406805474)
		error("devirt: index nil @272,676217 - 272,676221 (at 0:15)")
	end,
	[495] = "source",
	[355] = function(arg, arg2, arg3)
		arg3[2](arg2, arg[23])
		error("devirt: index nil @272,644812 - 272,644816 (at 0:5)")
	end,
	[37] = function(arg)
		error("devirt: index nil @272,676217 - 272,676221 (at 0:22)")
	end,
	[544] = buffer,
	[129] = function()
		error("devirt: index nil @272,644812 - 272,644816 (at 0:10)")
	end,
	[7] = "IsClient",
	[599] = function()
		error("devirt: index nil @272,651286 - 272,651290 (at 0:15)")
	end,
	[668] = function()
		local function fn(...)
			error("devirt: could not lift closure: closure maker did not return the VM closure")
		end
		error("devirt: index nil @272,644909 - 272,644913 (at 0:5)")
	end,
	[36] = function()
		error("devirt: arith on None None (at 0:33)")
	end,
	[335] = function()
		error("devirt: index nil @272,696337 - 272,696341 (at 0:5)")
	end,
	[411] = function()
		error("devirt: index nil @272,644812 - 272,644816 (at 0:9)")
	end,
	[568] = function(arg, arg2, arg3, arg4)
		if not (arg2 > 76) then
			arg4[50][58] = arg3[68]
			return 340
		end
		error("devirt: index nil @272,644812 - 272,644816 (at 0:5)")
	end,
	[625] = "__index",
	[483] = Random,
	[96] = function()
		local function fn()
			error("devirt: index nil @272,636175 - 272,636179 (at 0:5)")
		end
		error("devirt: newindex None (at 0:6)")
	end,
	[419] = function(arg)
		error("devirt: index nil @272,644812 - 272,644816 (at 0:5)")
	end,
	[166] = string.sub,
	[66] = function(arg, arg2, arg3)
		if arg3 ~= 47 then
			if arg3 ~= 66 then
				error("devirt: index nil @272,676217 - 272,676221 (at 0:12)")
			end
			arg[491](arg)
			error("devirt: call of unknown VM function lf141 (at 0:29)")
		end
		arg2[19] = arg[125]
		arg2[10] = nil
		error("devirt: index nil @272,644909 - 272,644913 (at 0:16)")
	end,
	[642] = function(arg)
		error("devirt: arith on None None (at 0:7)")
	end,
	[119] = string.find,
	[23] = "unpack",
	[687] = string.gsub,
	[563] = function()
		local function fn(...)
			if select("#", ...) == 0 then
			end
		end
		error("devirt: index nil @272,644909 - 272,644913 (at 0:7)")
	end,
	[531] = function(arg, arg2, arg3, arg4, arg5, arg6)
		if not (arg2 <= 16) then
			error("devirt: index nil @272,690960 - 272,690964 (at 0:16)")
		end
		error("devirt: call of unknown VM function lf141 (at 0:12)")
	end,
	[217] = function()
		error("devirt: index nil @272,644812 - 272,644816 (at 0:5)")
	end,
	[306] = function()
		error("devirt: index nil @272,675771 - 272,675775 (at 0:7)")
	end,
	[360] = function(arg, arg2)
		error("devirt: newindex None (at 0:32)")
	end,
	[260] = function(arg, arg2, arg3, arg4, arg5, arg6)
		if not (arg5 > 108) then
			if arg5 < 91 then
				if arg5 > 1 then
					error("devirt: index nil @272,676217 - 272,676221 (at 0:78)")
				end
			end
			if arg5 < 69 then
				error("devirt: index nil @272,676217 - 272,676221 (at 0:45)")
			end
			if arg5 < 108 then
				if arg5 > 69 then
					error("devirt: call of unknown VM function lf141 (at 0:27)")
				end
			end
			if arg5 < 126 then
				if arg5 > 91 then
					error("devirt: index nil @272,690960 - 272,690964 (at 0:16)")
				end
			end
		else
			arg3 = arg[212]
			arg5 = 69
		end
		error("devirt: call of unknown VM function lf141 (at 0:33)")
	end,
	[263] = function()
		error("devirt: arith on None None (at 0:14)")
	end,
	[224] = function(arg, arg2, arg3, arg4)
		if arg2 ~= 85 then
			if arg2 ~= 123 then
				return nil
			end
			error("devirt: index nil @272,676217 - 272,676221 (at 0:15)")
		end
		error("devirt: index nil @272,644812 - 272,644816 (at 0:25)")
	end,
	[513] = function(arg, arg2, arg3, arg4, arg5, arg6, arg7, arg8, arg9, arg10)
		if arg10 ~= 106 then
			if arg10 ~= 119 then
				if arg10 ~= 120 then
					error("devirt: call of unknown VM function lf141 (at 0:46)")
				end
				error("devirt: index nil @272,676217 - 272,676221 (at 0:14)")
			end
			error("devirt: index nil @272,676217 - 272,676221 (at 0:41)")
		end
		error("devirt: call of unknown VM function lf141 (at 0:5)")
	end,
	[183] = function(arg, arg2, arg3, arg4, arg5, arg6, arg7, arg8)
		local n = 61
		while true do
			if n < 120 then
				if n > 106 then
					arg4[7] = arg8[arg[449]]
					n = 106
					continue
				end
			end
			if not (n > 119) then
				if not (n < 65) then
					if n < 106 then
						if n > 61 then
							error("devirt: index nil @272,644812 - 272,644816 (at 0:37)")
						end
					end
					if not (n < 119) then
						continue
					end
					if not (n > 65) then
						continue
					end
					error("devirt: call of unknown VM function lf141 (at 0:7)")
				end
				n = 120
				continue
			end
			break
		end
		error("devirt: index nil @272,644812 - 272,644816 (at 0:65)")
	end,
	[357] = function()
		error("devirt: index nil @272,644812 - 272,644816 (at 0:5)")
	end,
	[618] = "RunService",
	[415] = function(arg, arg2, arg3, arg4, arg5, arg6, arg7, arg8, arg9)
		if not (arg9 > 69) then
			if arg9 < 96 then
				if arg5 then
					error("devirt: newindex None (at 0:69)")
				end
			end
			error("devirt: index nil @272,676217 - 272,676221 (at 0:35)")
		end
		error("devirt: index nil @272,676217 - 272,676221 (at 0:46)")
	end,
	[144] = function()
		error("devirt: index nil @272,644812 - 272,644816 (at 0:9)")
	end,
	[622] = function()
		error("devirt: index nil @272,676217 - 272,676221 (at 0:6)")
	end,
	[177] = function(arg, arg2, arg3, arg4, arg5, arg6)
		if arg2 ~= 98 then
			if arg2 ~= 89 then
				if arg2 ~= 79 then
					error("devirt: call of unknown VM function lf141 (at 0:35)")
				end
				arg6[2](arg5, arg[369])
				error("devirt: newindex None (at 0:23)")
			end
			arg6[2](arg3, arg[35])
			error("devirt: call of unknown VM function lf141 (at 0:19)")
		end
		error("devirt: index nil @272,676217 - 272,676221 (at 0:13)")
	end,
	[326] = function(arg, arg2, arg3)
		arg2(arg3)
		error("devirt: index nil @272,676217 - 272,676221 (at 0:10)")
	end,
	[32] = function(arg)
		error("devirt: arith on None None (at 0:48)")
	end,
	[16] = function(arg, arg2, arg3, arg4, arg5, arg6, arg7, arg8, arg9)
		if arg3 ~= 189 then
			if arg3 == 107 then
				error("devirt: index nil @272,676217 - 272,676221 (at 0:6)")
			end
		else
			arg2 = (arg7 * 65536 + arg4) % 4294967296
		end
		error("devirt: call of unknown VM function lf141 (at 0:16)")
	end,
	[592] = rawset,
	[583] = table,
	[516] = function()
		error("devirt: index nil @272,644812 - 272,644816 (at 0:5)")
	end,
	[254] = "LayoutOrder",
	[392] = function(arg)
		error("devirt: arith on None None (at 0:80)")
	end,
	[270] = function()
		error("devirt: index nil @272,644909 - 272,644913 (at 0:7)")
	end,
	[147] = function(arg, arg2, arg3, arg4, arg5)
		if arg5 ~= 32 then
			arg3[2](arg2, arg[608])
			error("devirt: index nil @272,676217 - 272,676221 (at 0:26)")
		end
		arg3[2](arg4, arg[566])
		error("devirt: call of unknown VM function lf141 (at 0:6)")
	end,
	[331] = function(arg, arg2)
		local n = 8
		while true do
			if n < 71 then
				arg2[7](arg2[60])
				n = 71
				continue
			end
			if not (n > 8) then
				continue
			end
			break
		end
		error("devirt: index nil @272,644812 - 272,644816 (at 0:16)")
	end,
	[11] = "running",
	[74] = function()
		error("devirt: index nil @272,644812 - 272,644816 (at 0:6)")
	end,
	[534] = function()
		error("devirt: newindex None (at 0:6)")
	end,
	[134] = function(arg, arg2, arg3, arg4, arg5, arg6)
		if not (arg6 > 38) then
			error("devirt: index nil @272,676217 - 272,676221 (at 0:6)")
		end
		arg2:GetPositionOnCurve(0.375)
		error("devirt: call of unknown VM function lf141 (at 0:33)")
	end,
	[280] = function(arg)
		error("devirt: call of unknown VM function lf141 (at 0:17)")
	end,
}
local function fn()
	error("devirt: arith on None None (at 0:16)")
end
error("devirt: index nil @272,644909 - 272,644913 (at 0:630)")