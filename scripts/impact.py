#!/usr/bin/env python3
"""
Change Impact Analysis Tool for CoE-RagPipeline

Builds an internal import graph across key packages and computes
transitive dependents for changed files. Also extracts FastAPI routes
from routers/* to list affected endpoints.

Usage examples:
  python scripts/impact.py --since origin/main
  python scripts/impact.py --files services/vector.py routers/search.py

Outputs a console summary and writes JSON/DOT to output/results/.
"""
from __future__ import annotations

import argparse
import ast
import json
import subprocess
from collections import defaultdict, deque
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Set, Tuple


ROOT = Path(__file__).resolve().parents[1]
INCLUDE_TOP_LEVEL = {
    "analyzers",
    "core",
    "routers",
    "services",
    "models",
    "utils",
    "config",
}
PY_EXT = {".py"}
RESULTS_DIR = ROOT / "output" / "results"


def iter_python_files() -> Iterable[Path]:
    for top in INCLUDE_TOP_LEVEL:
        base = ROOT / top
        if not base.exists():
            continue
        for p in base.rglob("*.py"):
            # skip cache or generated
            if "__pycache__" in p.parts:
                continue
            yield p


def module_name_from_path(p: Path) -> str:
    rel = p.relative_to(ROOT)
    parts = list(rel.parts)
    if parts[-1] == "__init__.py":
        parts = parts[:-1]
    else:
        parts[-1] = parts[-1].replace(".py", "")
    return ".".join(parts)


def is_internal_module(mod: str) -> bool:
    return any(mod == top or mod.startswith(top + ".") for top in INCLUDE_TOP_LEVEL)


def parse_imports(p: Path) -> Set[str]:
    try:
        src = p.read_text(encoding="utf-8")
        tree = ast.parse(src)
    except Exception:
        return set()

    deps: Set[str] = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for n in node.names:
                name = (n.name or "").split(".")[0]
                # keep full top.package chain for internal modules
                full = n.name
                if full and is_internal_module(full):
                    deps.add(full)
                elif is_internal_module(name):
                    deps.add(name)
        elif isinstance(node, ast.ImportFrom):
            mod = node.module or ""
            if mod and is_internal_module(mod):
                deps.add(mod)
    return deps


def build_graph(files: Iterable[Path]) -> Tuple[Dict[str, Set[str]], Dict[str, Path]]:
    module_to_file: Dict[str, Path] = {}
    graph: Dict[str, Set[str]] = defaultdict(set)  # module -> imports

    for p in files:
        mod = module_name_from_path(p)
        module_to_file[mod] = p
    for mod, p in module_to_file.items():
        deps = parse_imports(p)
        # only keep internal modules present in our map (filter 3rd-party)
        deps = {d for d in deps if any(d == m or d.startswith(m + ".") for m in module_to_file.keys())}
        graph[mod] |= deps
    return graph, module_to_file


def reverse_graph(graph: Dict[str, Set[str]]) -> Dict[str, Set[str]]:
    rev: Dict[str, Set[str]] = defaultdict(set)
    for a, outs in graph.items():
        for b in outs:
            rev[b].add(a)
    return rev


def git_changed_files(since: str) -> List[Path]:
    try:
        out = subprocess.check_output([
            "git", "diff", "--name-only", f"{since}...HEAD"
        ], cwd=str(ROOT), text=True)
        paths = [ROOT / line.strip() for line in out.splitlines() if line.strip()]
        return [p for p in paths if p.suffix in PY_EXT and p.exists()]
    except Exception:
        return []


def impacted_modules(changed: Iterable[str], rev: Dict[str, Set[str]]) -> Set[str]:
    impacted: Set[str] = set(changed)
    q = deque(changed)
    while q:
        cur = q.popleft()
        for dep in rev.get(cur, ()):  # who depends on cur
            if dep not in impacted:
                impacted.add(dep)
                q.append(dep)
    return impacted


@dataclass
class Route:
    method: str
    path: str
    module: str


def extract_routes(p: Path) -> List[Route]:
    try:
        src = p.read_text(encoding="utf-8")
        tree = ast.parse(src)
    except Exception:
        return []

    router_names: Set[str] = set()
    prefixes: Dict[str, str] = {}
    routes: List[Route] = []

    # find router vars and optional prefix
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Call):
            # router = APIRouter(prefix="/x")
            func = node.value.func
            if isinstance(func, ast.Name) and func.id == "APIRouter":
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        router_names.add(target.id)
                        # extract prefix kw
                        pfx = ""
                        for kw in node.value.keywords:
                            if kw.arg == "prefix" and isinstance(kw.value, ast.Constant) and isinstance(kw.value.value, str):
                                pfx = kw.value.value
                        prefixes[target.id] = pfx

    # find decorator usages e.g. @router.get("/foo")
    def lit_str(arg) -> str:
        return arg.value if isinstance(arg, ast.Constant) and isinstance(arg.value, str) else ""

    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            for dec in node.decorator_list:
                if isinstance(dec, ast.Call) and isinstance(dec.func, ast.Attribute):
                    if isinstance(dec.func.value, ast.Name) and dec.func.value.id in router_names:
                        method = dec.func.attr.upper()
                        path = lit_str(dec.args[0]) if dec.args else ""
                        pfx = prefixes.get(dec.func.value.id, "")
                        full = (pfx or "") + (path or "")
                        routes.append(Route(method=method, path=full or "/", module=module_name_from_path(p)))
    return routes


def write_dot(graph: Dict[str, Set[str]], out: Path) -> None:
    lines = ["digraph deps {"]
    for a, outs in graph.items():
        for b in outs:
            lines.append(f'  "{a}" -> "{b}";')
    lines.append("}")
    out.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser(description="Change impact analysis")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--since", help="Git ref to diff against, e.g., origin/main")
    g.add_argument("--files", nargs="+", help="Explicit changed files (paths)")
    ap.add_argument("--write", action="store_true", help="Write JSON and DOT outputs to output/results/")
    args = ap.parse_args()

    files = list(iter_python_files())
    graph, module_to_file = build_graph(files)
    rev = reverse_graph(graph)

    changed_paths: List[Path] = []
    if args.since:
        changed_paths = git_changed_files(args.since)
    else:
        changed_paths = [Path(p).resolve() for p in args.files]

    changed_modules: Set[str] = set()
    for p in changed_paths:
        try:
            # map to closest module (handle package __init__ gracefully)
            mod = module_name_from_path(p)
            if mod in module_to_file:
                changed_modules.add(mod)
            else:
                # try parent packages
                parts = mod.split(".")
                while parts and ".".join(parts) not in module_to_file:
                    parts.pop()
                if parts:
                    changed_modules.add(".".join(parts))
        except Exception:
            continue

    impacted = impacted_modules(changed_modules, rev)

    # route extraction
    all_routes: List[Route] = []
    routers_dir = ROOT / "routers"
    if routers_dir.exists():
        for rp in routers_dir.rglob("*.py"):
            all_routes.extend(extract_routes(rp))
    impacted_routes = [r for r in all_routes if r.module in impacted]

    # summary
    print("Changed files:")
    for p in changed_paths:
        print(f"  - {p.relative_to(ROOT)}")
    print("")
    print("Impacted modules (transitive dependents):")
    for m in sorted(impacted):
        print(f"  - {m}")
    print("")
    print("Impacted API routes:")
    if impacted_routes:
        for r in impacted_routes:
            print(f"  - {r.method:6s} {r.path:30s} ({r.module})")
    else:
        print("  - (none detected)")

    if args.write:
        RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        # JSON report
        rep = {
            "changed_files": [str(p.relative_to(ROOT)) for p in changed_paths],
            "impacted_modules": sorted(impacted),
            "impacted_routes": [
                {"method": r.method, "path": r.path, "module": r.module} for r in impacted_routes
            ],
        }
        (RESULTS_DIR / "impact_report.json").write_text(json.dumps(rep, indent=2), encoding="utf-8")
        # DOT graph
        write_dot(graph, RESULTS_DIR / "dependency_graph.dot")


if __name__ == "__main__":
    main()

