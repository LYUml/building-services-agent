"""Compatibility entry point for bsa.tee_geometry."""
if __name__=="__main__":
    import runpy
    runpy.run_module("bsa.tee_geometry",run_name="__main__")
else:
    from bsa.tee_geometry import *
