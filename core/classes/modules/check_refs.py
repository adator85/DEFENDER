import asyncio
import gc
import os
import sys
import types
import weakref
from datetime import datetime
from typing import Optional


# Attributs de uplink dont on veut vérifier qu'aucune ancienne instance ne survit.
TRACKED_ATTRS = {
    'protocol': lambda u: u.Irc.Protocol,
    'commands': lambda u: u.Commands,
    'base': lambda u: u.Base,
    'rpc': lambda u: u.RpcServer,
    'user': lambda u: u.User,
    'admin': lambda u: u.Admin,
    'channel': lambda u: u.Channel,
    'reputation': lambda u: u.Reputation,
    'sasl': lambda u: u.Sasl,
    'module_utils': lambda u: u.ModuleUtils,
    'core_utils': lambda u: u.Utils,
}

LAST_REFS: dict[str, weakref.ref] = {}
LAST_REPORT: Optional[dict] = None


def snapshot_refs(uplink) -> dict[str, weakref.ref]:
    """Capture weakrefs on actuals objects without keeping them alive."""
    refs = {}
    for name, getter in TRACKED_ATTRS.items():
        try:
            refs[name] = weakref.ref(getter(uplink))
        except (AttributeError, TypeError) as exc:
            # Attribut absent ou type non supporté par weakref (ex. dict, list).
            print(f"[SNAPSHOT] {name} ignoré : {exc}")
    return refs


def check_leaks(refs: dict[str, weakref.ref], verbose: bool = True) -> dict[str, int]:
    """
    Vérifie que les anciens objets ont bien été libérés.
    Retourne {nom: nombre_de_référents} pour chaque objet encore vivant.
    """
    gc.collect()
    leaks = {}
    for name, ref in refs.items():
        obj = ref()
        if obj is None:
            if verbose:
                print(f"[OK] {name} libéré")
            continue

        referrers = gc.get_referrers(obj)
        # Exclut la liste temporaire créée par get_referrers et la référence locale `obj`.
        leaks[name] = len(referrers)
        if verbose:
            print(f"[FUITE] {name} encore vivant : {len(referrers)} référents")
            for r in referrers:
                if isinstance(r, dict):
                    print("        <- dict (contenu non affiché)")
                else:
                    print(f"        <- {type(r).__name__}")
        del referrers
        del obj
    return leaks


def _describe(r) -> str:
    if asyncio.iscoroutine(r):
        frame = getattr(r, 'cr_frame', None)
        where = '?'
        if frame is not None:
            where = frame.f_code.co_name
            self_obj = frame.f_locals.get('self')
            if self_obj is not None:
                where += f" (self={type(self_obj).__name__})"
        return f"coroutine {where}"

    if type(r).__name__ == 'CoroutineWrapper':
        return f"coroutine wrapper {r.cr_code.co_name}"

    if isinstance(r, types.MethodType):
        owner = type(r.__self__).__name__
        return f"method {r.__qualname__} on {owner}"

    if isinstance(r, types.CellType):
        try:
            c = r.cell_contents
        except ValueError:
            return "cell (empty)"
        owners = []
        for r2 in gc.get_referrers(r):
            if isinstance(r2, types.FunctionType):
                owners.append(f"{r2.__module__}.{r2.__qualname__}")
            elif isinstance(r2, types.MethodType):
                owners.append(f"bound {r2.__qualname__}")
            else:
                owners.append(type(r2).__name__)
        return f"cell holding {type(c).__name__} owned by {owners}"

    if isinstance(r, dict):
        name = r.get('__name__')
        if name:
            return f"module dict {name}"
        keys = list(r.keys())[:8]
        return f"dict keys={keys}"

    if isinstance(r, types.FunctionType):
        return f"function {r.__module__}.{r.__qualname__}"

    if isinstance(r, asyncio.Task):
        return f"Task {r.get_name()} done={r.done()}"

    if isinstance(r, (tuple, list)):
        return f"{type(r).__name__} len={len(r)}"

    return type(r).__name__


def check_leaks_v2(refs: dict[str, weakref.ref], verbose: bool = True) -> dict[str, list[str]]:
    """
    Vérifie que les anciens objets ont bien été libérés.
    Retourne {nom: [descriptions des référents]} pour chaque objet encore vivant.
    """
    gc.collect()
    leaks = {}

    for name, ref in refs.items():
        obj = ref()
        if obj is None:
            if verbose:
                print(f"[OK] {name} libéré")
            continue

        raw = gc.get_referrers(obj)
        referrers = [r for r in raw if r is not obj]
        del raw

        descriptions = [_describe(r) for r in referrers]
        leaks[name] = descriptions
        if verbose:
            print(f"[FUITE] {name} encore vivant : {len(descriptions)} référents")
            for desc in descriptions:
                print(f"        <- {desc}")

        del referrers
        del obj

    return leaks


def _is_current_class(cls: type) -> bool:
    """True si la classe est toujours celle exposée par son module dans sys.modules."""
    mod_name = getattr(cls, '__module__', None)
    if not isinstance(mod_name, str):
        return False

    mod = sys.modules.get(mod_name)
    if mod is None:
        # Module retiré de sys.modules (ex: module service déchargé).
        return False

    qualname = getattr(cls, '__qualname__', None)
    if not isinstance(qualname, str) or '<locals>' in qualname:
        # Chemin non résolvable : on ne peut pas trancher, éviter les faux positifs.
        return True

    obj = mod
    for part in qualname.split('.'):
        obj = getattr(obj, part, None)
        if obj is None:
            return False
    return obj is cls


def find_stale_classes() -> list[dict]:
    """
    Détecte les classes de core./mods. qui ne sont plus celles liées dans
    sys.modules (anciennes versions après rehash / modules déchargés) ainsi
    que le nombre d'instances encore vivantes de chacune.

    Retourne une liste de dicts: {module, name, instances}.
    """
    gc.collect()

    candidates: dict[int, type] = {}
    for obj in gc.get_objects():
        if not isinstance(obj, type):
            continue
        mod_name = getattr(obj, '__module__', None)
        if not isinstance(mod_name, str):
            continue
        if mod_name != 'core' and not mod_name.startswith('core.') \
                and mod_name != 'mods' and not mod_name.startswith('mods.'):
            continue
        if not _is_current_class(obj):
            candidates[id(obj)] = obj

    if not candidates:
        return []

    stale_set = set(candidates.values())
    instances: dict[type, int] = {}
    for obj in gc.get_objects():
        t = type(obj)
        if t in stale_set:
            instances[t] = instances.get(t, 0) + 1

    result = [
        {
            'module': cls.__module__,
            'name': getattr(cls, '__qualname__', cls.__name__),
            'instances': instances.get(cls, 0),
        }
        for cls in candidates.values()
    ]
    result.sort(key=lambda item: (-item['instances'], item['module'], item['name']))
    return result


def get_rss_kb() -> int:
    """Current resident set size in KiB (Linux /proc); 0 if unavailable."""
    try:
        with open('/proc/self/status') as f:
            for line in f:
                if line.startswith('VmRSS:'):
                    return int(line.split()[1])
    except (OSError, ValueError, IndexError):
        return 0
    return 0


def find_stale_modules() -> list[dict]:
    """
    Détecte les modules core./mods. encore vivants dans le gc alors qu'ils ne
    sont plus ceux de sys.modules (anciens modules après rehash). Un ancien
    module retient toutes ses fonctions/constantes et sa dict de globals, ce
    que find_stale_classes ne voit pas (pas de classes dedans, ex: core.utils).

    Retourne une liste de dicts: {name, referrer_count, referrers}.
    """
    gc.collect()
    result: list[dict] = []
    for obj in gc.get_objects():
        if not isinstance(obj, types.ModuleType):
            continue
        name = getattr(obj, '__name__', '') or ''
        if name not in ('core', 'mods') \
                and not name.startswith(('core.', 'mods.')):
            continue
        if sys.modules.get(name) is obj:
            continue
        raw = gc.get_referrers(obj)
        referrers = [_describe(r) for r in raw if r is not obj]
        del raw
        result.append({
            'name': name,
            'referrer_count': len(referrers),
            'referrers': referrers[:8],
        })
    result.sort(key=lambda item: item['name'])
    return result


def store_report(nickname: str, refs: dict[str, weakref.ref],
                 leaks: dict[str, list[str]], stale: list[dict],
                 collected: int = 0, stale_modules: Optional[list[dict]] = None,
                 rss_kb: int = 0) -> dict:
    """Conserve le dernier rapport de rehash pour !show_leaks / le journal."""
    global LAST_REFS, LAST_REPORT

    LAST_REFS = dict(refs)
    LAST_REPORT = {
        'ts': datetime.now(),
        'by': nickname,
        'refs': LAST_REFS,
        'refs_total': len(refs),
        'refs_alive': {name: len(descs) for name, descs in leaks.items()},
        'refs_detail': leaks,
        'stale': stale,
        'stale_modules': stale_modules or [],
        'collected': collected,
        'rss_kb': rss_kb,
    }
    return LAST_REPORT


def get_report() -> Optional[dict]:
    return LAST_REPORT


def write_report_to_log(path: str = os.path.join('logs', 'leaks.log')) -> None:
    """Append the last rehash report to a log file for history/diffing."""
    if LAST_REPORT is None:
        return

    try:
        directory = os.path.dirname(path)
        if directory:
            os.makedirs(directory, exist_ok=True)

        report = LAST_REPORT
        alive = report['refs_alive']
        released = report['refs_total'] - len(alive)
        with open(path, 'a') as f:
            f.write(f"{report['ts']} | rehash by {report['by']} | "
                    f"refs released {released}/{report['refs_total']} | "
                    f"stale classes {len(report['stale'])} | "
                    f"stale modules {len(report.get('stale_modules', []))} | "
                    f"rss {report.get('rss_kb', 0) / 1024:.1f}MiB | "
                    f"gc collected {report['collected']}\n")
            for name, descs in report['refs_detail'].items():
                f.write(f"  [LEAK] {name}: {len(descs)} referrer(s)\n")
                for desc in descs:
                    f.write(f"      <- {desc}\n")
            for item in report['stale']:
                f.write(f"  [STALE] {item['module']}.{item['name']} "
                        f"x {item['instances']} instance(s)\n")
            for item in report.get('stale_modules', []):
                f.write(f"  [STALE-MOD] {item['name']} "
                        f"({item['referrer_count']} referrer(s))\n")
                for desc in item['referrers']:
                    f.write(f"      <- {desc}\n")
            if not report['refs_detail'] and not report['stale'] \
                    and not report.get('stale_modules'):
                f.write("  [OK] no stale references detected\n")
    except OSError as exc:
        print(f"[LEAKS LOG] Impossible d'écrire le rapport : {exc}")
