return {

	LrSdkVersion = 5.0,
	LrSdkMinimumVersion = 5.0,

	LrToolkitIdentifier = 'com.znznzna.lightroom.cli-bridge',

	LrPluginName = "Lightroom CLI Bridge",

	LrInitPlugin = "PluginInit.lua",
	LrForceInitPlugin = true,
	LrShutdownPlugin = "PluginShutdown.lua",
	LrShutdownApp = "AppShutdown.lua",

	LrExportMenuItems = {
		{
			title = "Start CLI Bridge",
			file = "MenuActions.lua",
		},
		{
			title = "Stop CLI Bridge",
			file = "StopMenuAction.lua",
		},
	},

	-- LrLibraryMenuItems = {
	-- 	{
	-- 		title = "CLI Bridge Settings",
	-- 		file = "SettingsDialog.lua",
	-- 	}
	-- },

	VERSION = { major=1, minor=2, revision=0, build=1 },

}