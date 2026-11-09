"""Compatibility entry point for bsa.tee_losses."""
if __name__=="__main__":
    import runpy
    runpy.run_module("bsa.tee_losses",run_name="__main__")
else:
    from bsa.tee_losses import *
