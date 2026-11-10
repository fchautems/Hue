"""Resolve Hue accessory dimming actions from the bridge's own configuration."""
from collections import defaultdict

GROUP_TYPES = ("room", "zone", "bridge_home")


def _targets(ref, groups, light_ids, by_device, visited=frozenset()):
    if not isinstance(ref, dict):
        return set()
    kind, uid = ref.get("rtype"), ref.get("rid")
    if not isinstance(uid, str) or uid in visited:
        return set()
    if kind == "light":
        return {uid} & light_ids
    if kind == "device":
        return by_device.get(uid, set())
    if kind not in (*GROUP_TYPES, "grouped_light"):
        return set()
    return set().union(*(
        _targets(child, groups, light_ids, by_device, visited | {uid})
        for child in groups.get(uid, ())
    ))


def group_light_resolver(groups, lights):
    """Resolve Hue device, light and group references to light IDs."""
    by_device = defaultdict(set)
    for light in lights:
        by_device[light.get("owner", {}).get("rid")].add(light["id"])
    light_ids = {light["id"] for light in lights}
    children = {group["id"]: group.get("children", []) for group in groups}
    for group in groups:
        for service in group.get("services", []):
            if service.get("rtype") == "grouped_light":
                children[service["rid"]] = children[group["id"]]
    return lambda ref: _targets(ref, children, light_ids, by_device)


def dimmer_bindings(instances, groups, lights):
    """Map (service type, id, event) to the lights controlled by that action."""
    resolve = group_light_resolver(groups, lights)
    bindings = defaultdict(set)
    for instance in instances:
        if instance.get("enabled") is not True:
            continue
        config = instance.get("configuration")
        if not isinstance(config, dict):
            continue
        for field, kind in (("buttons", "button"), ("rotaries", "relative_rotary")):
            controls = config.get(field)
            if not isinstance(controls, dict):
                continue
            for uid, control in controls.items():
                if not isinstance(control, dict):
                    continue
                actions = {
                    key.removeprefix("on_"): value for key, value in control.items()
                    if key.startswith("on_") and isinstance(value, dict)
                }
                if kind == "relative_rotary":
                    event_actions = {"start": actions.get("start", {}),
                                     "repeat": actions.get("repeat", {})}
                else:
                    event_actions = {key: value for key, value in actions.items()
                                     if value.get("action") in ("dim_up", "dim_down")}
                    if "repeat" in event_actions and not {"initial_press", "short_release"} & actions.keys():
                        event_actions["initial_press"] = event_actions["repeat"]
                for event, action in event_actions.items():
                    where = action.get("where", control.get("where", []))
                    if not isinstance(where, list):
                        continue
                    for target in where:
                        if not isinstance(target, dict):
                            continue
                        refs = target.get("items") or [target.get("group", target)]
                        if not isinstance(refs, list):
                            continue
                        for ref in refs:
                            bindings[(kind, uid, event)].update(resolve(ref))
    return dict(bindings)


def dimmer_events(containers):
    """Read real input reports and OFF events from CLIP v2 SSE updates."""
    if not isinstance(containers, list):
        return
    for container in containers:
        if not isinstance(container, dict):
            continue
        change = container.get("type")
        if change not in ("update", "add", "delete"):
            continue
        for item in container.get("data") or []:
            if not isinstance(item, dict) or not isinstance(item.get("id"), str):
                continue
            kind, uid = item.get("type"), item["id"]
            if kind in (*GROUP_TYPES, "behavior_instance", "device"):
                yield "config", uid, kind
            elif change != "update":
                continue
            elif kind == "light" and item.get("on", {}).get("on") is False:
                yield kind, uid, "off"
            elif kind == "button":
                data = item.get("button") or {}
                report = data.get("button_report") or {}
                event = report.get("event") or data.get("last_event")
                if isinstance(event, str):
                    yield kind, uid, event
            elif kind == "relative_rotary":
                data = item.get("relative_rotary") or {}
                report = data.get("rotary_report") or data.get("last_event") or {}
                steps = (report.get("rotation") or {}).get("steps")
                if report.get("action") in ("start", "repeat") and type(steps) is int and steps > 0:
                    yield kind, uid, report["action"]
