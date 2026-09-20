"""A0 adapter for the Loreley runtime.

One executable, one runtime.  ``adapter_contract.md`` §3 specifies a single CLI
covering all four runtimes; this package implements the Loreley arm and refuses
the other runtimes with exit code 2 rather than pretending to serve them.

Subcommands: ``run``, ``conformance``, ``closure-probe``, ``a02``, ``traps``,
``eidr``, ``plan``.
"""

__all__ = ["__version__"]

__version__ = "1.0.0"
