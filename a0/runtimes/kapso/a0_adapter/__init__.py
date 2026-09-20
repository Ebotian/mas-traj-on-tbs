"""A0 runtime adapter for KAPSO — evaluator integration conformance (A0.1) and
the score -> search selection contract (A0.2).

The package is named ``a0_adapter`` because ``a0/contract/adapter_contract.md``
§3 fixes the invocation as ``python -m a0_adapter <subcommand>`` for all four
runtimes.  Every artifact it writes names the runtime it belongs to.
"""

__all__ = ["__main__"]
