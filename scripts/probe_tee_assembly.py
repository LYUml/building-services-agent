"""Compatibility entry point for bsa.tee_assembly."""
if __name__=="__main__":
    import runpy
    runpy.run_module("bsa.tee_assembly",run_name="__main__")
else:
    from bsa.tee_assembly import *
