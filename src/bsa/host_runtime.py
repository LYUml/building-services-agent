"""Host-only runtime option names, independent of optional engineering engines."""
OPTIONS=frozenset({'energyplus','autocad','radiance_bin','ifcmcp_python','three_phase_python','graphviz','pdf2plot_python','honeybee_python','module_providers','module_runtime','disabled_module_providers'})

# Shared host-only path flags. Installing a path is not execution acceptance.
PATH_ARGUMENTS={
    'autocad':'file','pdftoppm':'file','energyplus':'file',
    'ifcmcp-python':'file','three-phase-python':'file','graphviz':'file',
    'pdf2plot-python':'file','honeybee-python':'file','report-font':'file',
    'fds-release':'file',
    'radiance-bin':'directory','moosas-upstream':'directory','moosas-deps':'directory',
}
