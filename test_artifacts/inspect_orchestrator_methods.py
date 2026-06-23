import inspect
from docsynthfab.orchestrator import RunOrchestrator, RunRequest

orch = RunOrchestrator()

print("=== RunRequest ===")
print(RunRequest)
print(inspect.signature(RunRequest))

print("\n=== RunOrchestrator public methods ===")
for name in dir(orch):
    if name.startswith("_"):
        continue
    obj = getattr(orch, name)
    if callable(obj):
        try:
            print(f"{name}{inspect.signature(obj)}")
        except Exception:
            print(name)
