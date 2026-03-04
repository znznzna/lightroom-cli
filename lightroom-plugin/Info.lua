return {

	LrSdkVersion = 5.0,
	LrSdkMinimumVersion = 5.0,

	LrToolkitIdentifier = 'com.example.lightroom.pythonbridge',

	LrPluginName = "Lightroom Python Bridge",

	LrInitPlugin = "PluginInit.lua",
	LrForceInitPlugin = true,
	LrShutdownPlugin = "PluginShutdown.lua",
	LrShutdownApp = "AppShutdown.lua",

	LrExportMenuItems = {
		{
			title = "Start Python Bridge",
			file = "MenuActions.lua",
		},
		{
			title = "Stop Python Bridge",
			file = "StopMenuAction.lua",
		},
	},

	-- LrLibraryMenuItems = {
	-- 	{
	-- 		title = "Python Bridge Settings",
	-- 		file = "SettingsDialog.lua",
	-- 	}
	-- },

	VERSION = { major=1, minor=0, revision=0, build=1 },

}