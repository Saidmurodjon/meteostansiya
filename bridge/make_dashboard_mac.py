import json
import uuid
import urllib.request
import os


def _load_env(path=os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")):
    # Secrets live in a gitignored bridge/.env (see .env.example), not in the repo.
    if os.path.exists(path):
        for line in open(path):
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())


_load_env()


TB_BASE = "http://localhost:9090"
USERNAME = os.environ["TB_USERNAME"]
PASSWORD = os.environ["TB_PASSWORD"]
DEVICE_ID = "e595c5f0-b70a-11f1-8df9-f17783d629e6"  # Meteostansiya-1 (local Mac TB)

METRICS = [
    {"name": "temperature", "label": "Harorat", "units": "°C", "color": "#EF5350", "icon": "thermostat", "iconColor": "#EF5350"},
    {"name": "humidity", "label": "Namlik", "units": "%", "color": "#42A5F5", "icon": "water_drop", "iconColor": "#42A5F5"},
    {"name": "light", "label": "Yorug'lik", "units": "Lux", "color": "#FFA726", "icon": "wb_sunny", "iconColor": "#FFA726"},
    {"name": "wind_speed", "label": "Shamol tezligi", "units": "m/s", "color": "#26A69A", "icon": "air", "iconColor": "#26A69A"},
    {"name": "wind_direction", "label": "Shamol yo'nalishi", "units": "°", "color": "#AB47BC", "icon": "explore", "iconColor": "#AB47BC"},
    {"name": "rainfall", "label": "Yog'ingarchilik", "units": "mm", "color": "#5C6BC0", "icon": "water", "iconColor": "#5C6BC0"},
    {"name": "battery_voltage", "label": "Batareya kuchlanishi", "units": "V", "color": "#66BB6A", "icon": "battery_charging_full", "iconColor": "#66BB6A"},
]


def http_json(method, url, token=None, body=None):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["X-Authorization"] = f"Bearer {token}"
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=15) as resp:
        raw = resp.read()
        return json.loads(raw) if raw else None


def build_widget(metric, row, col):
    widget_id = str(uuid.uuid4())
    alarm_key = f"{metric['name']}AlarmThreshold"
    config = {
        "datasources": [
            {
                "type": "entity",
                "name": "",
                "entityAliasId": "meteostansiya-alias",
                "dataKeys": [
                    {
                        "name": metric["name"],
                        "type": "timeseries",
                        "label": metric["label"],
                        "color": metric["color"],
                        "settings": {
                            "yAxisId": "default",
                            "showInLegend": True,
                            "dataHiddenByDefault": False,
                            "type": "line",
                            "lineSettings": {
                                "showLine": True,
                                "step": False,
                                "stepType": "start",
                                "smooth": True,
                                "lineType": "solid",
                                "lineWidth": 2.5,
                                "showPoints": False,
                                "showPointLabel": False,
                                "pointLabelPosition": "top",
                                "pointShape": "circle",
                                "pointSize": 14,
                                "fillAreaSettings": {
                                    "type": "gradient",
                                    "opacity": 0.4,
                                    "gradient": {"start": 60, "end": 10},
                                },
                            },
                            "barSettings": {
                                "showBorder": False,
                                "borderWidth": 2,
                                "borderRadius": 0,
                                "showLabel": False,
                                "labelPosition": "top",
                                "backgroundSettings": {
                                    "type": "none",
                                    "opacity": 0.4,
                                    "gradient": {"start": 100, "end": 0},
                                },
                            },
                        },
                        "units": metric["units"],
                        "decimals": 1,
                    }
                ],
                "alarmFilterConfig": {"statusList": ["ACTIVE"]},
            }
        ],
        "timewindow": {
            "hideAggregation": False,
            "hideAggInterval": False,
            "hideTimezone": False,
            "selectedTab": 0,
            "realtime": {
                "realtimeType": 0,
                "timewindowMs": 3600000,
                "quickInterval": "CURRENT_DAY",
                "interval": 30000,
            },
            "aggregation": {"type": "AVG", "limit": 25000},
            "timezone": None,
        },
        "showTitle": True,
        "backgroundColor": "rgba(0, 0, 0, 0)",
        "color": "rgba(0, 0, 0, 0.87)",
        "padding": "0px",
        "settings": {
            "showLegend": True,
            "legendConfig": {
                "direction": "column",
                "position": "bottom",
                "sortDataKeys": False,
                "showMin": True,
                "showMax": True,
                "showAvg": True,
                "showTotal": False,
                "showLatest": True,
            },
            "thresholds": [],
            "dataZoom": True,
            "stack": False,
            "yAxis": {"show": True, "label": "", "position": "left", "showTickLabels": True, "showTicks": True, "showLine": True, "showSplitLines": True},
            "xAxis": {"show": True, "label": "", "position": "bottom", "showTickLabels": True, "showTicks": True, "showLine": True, "showSplitLines": True},
            "showTooltip": True,
            "tooltipTrigger": "axis",
            "tooltipShowDate": True,
            "yAxes": {
                "default": {
                    "units": metric["units"],
                    "decimals": 1,
                    "show": True,
                    "label": "",
                    "position": "left",
                    "showTickLabels": True,
                    "showTicks": True,
                    "showLine": True,
                    "showSplitLines": True,
                    "id": "default",
                    "order": 0,
                }
            },
            "animation": {"animation": True, "animationThreshold": 2000, "animationDuration": 500},
            "padding": "12px",
        },
        "title": metric["label"],
        "dropShadow": True,
        "enableFullscreen": True,
        "configMode": "basic",
        "actions": {},
        "showTitleIcon": True,
        "titleIcon": metric["icon"],
        "iconColor": metric["iconColor"],
        "useDashboardTimewindow": True,
        "displayTimewindow": True,
        "widgetStyle": {},
        "widgetCss": "",
        "pageSize": 1024,
        "units": metric["units"],
        "decimals": 1,
        "noDataDisplayMessage": "",
    }
    widget = {
        "typeFullFqn": "system.time_series_chart",
        "type": "timeseries",
        "sizeX": 12,
        "sizeY": 6,
        "config": config,
        "row": row,
        "col": col,
        "id": widget_id,
    }
    return widget_id, widget


def main():
    login = http_json("POST", f"{TB_BASE}/api/auth/login", body={"username": USERNAME, "password": PASSWORD})
    token = login["token"]

    entity_alias_id = "meteostansiya-alias"
    entity_aliases = {
        entity_alias_id: {
            "id": entity_alias_id,
            "alias": "Meteostansiya-1",
            "filter": {
                "type": "singleEntity",
                "singleEntity": {"id": DEVICE_ID, "entityType": "DEVICE"},
            },
        }
    }

    widgets = {}
    layout_widgets = {}
    row = 0
    col = 0
    for i, metric in enumerate(METRICS):
        wid, w = build_widget(metric, row, col)
        widgets[wid] = w
        layout_widgets[wid] = {
            "sizeX": 12,
            "sizeY": 6,
            "row": row,
            "col": col,
        }
        col += 12
        if col >= 24:
            col = 0
            row += 6

    dashboard_config = {
        "widgets": widgets,
        "states": {
            "default": {
                "name": "Meteostansiya-1",
                "root": True,
                "layouts": {
                    "main": {
                        "widgets": layout_widgets,
                        "gridSettings": {
                            "backgroundColor": "#eeeeee",
                            "color": "rgba(0,0,0,0.870588)",
                            "columns": 24,
                            "backgroundSizeMode": "100%",
                            "autoFillHeight": True,
                            "mobileAutoFillHeight": False,
                            "mobileRowHeight": 70,
                            "margin": 10,
                            "outerMargin": True,
                            "layoutType": "default",
                        },
                    }
                },
            }
        },
        "entityAliases": entity_aliases,
        "timewindow": {
            "displayValue": "",
            "selectedTab": 0,
            "realtime": {"realtimeType": 0, "timewindowMs": 3600000, "quickInterval": "CURRENT_DAY", "interval": 30000},
            "aggregation": {"type": "AVG", "limit": 25000},
        },
        "settings": {
            "stateControllerId": "entity",
            "showTitle": False,
            "showDashboardsSelect": True,
            "showEntitiesSelect": True,
            "showDashboardTimewindow": True,
            "showDashboardExport": True,
            "toolbarAlwaysOpen": True,
        },
        "filters": {},
    }

    dashboard = {
        "title": "Meteostansiya-1",
        "configuration": dashboard_config,
    }

    # Update the existing dashboard in place instead of creating a duplicate.
    found = http_json("GET", f"{TB_BASE}/api/tenant/dashboards?pageSize=100&page=0&textSearch=Meteostansiya-1", token=token)
    for d in found.get("data", []):
        if d["title"] == dashboard["title"]:
            existing = http_json("GET", f"{TB_BASE}/api/dashboard/{d['id']['id']}", token=token)
            dashboard["id"] = existing["id"]
            dashboard["version"] = existing.get("version")
            break

    result = http_json("POST", f"{TB_BASE}/api/dashboard", token=token, body=dashboard)
    print("DASHBOARD_ID:", result["id"]["id"])
    print("TITLE:", result["title"])


if __name__ == "__main__":
    main()
