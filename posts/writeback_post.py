"""Write a built post's result back to the Supabase posts row (called by build_post.yml).

Reads out/rendered.html + out/meta.json on success; marks the row failed otherwise. Uses the
service key (RLS-bypassing) so it can update any post. Always leaves the row in a terminal state.
"""
import datetime
import json
import os
import urllib.request

URL = os.environ["SUPABASE_URL"].rstrip("/")
KEY = os.environ["SUPABASE_SERVICE_KEY"]
PID = os.environ["POST_ID"]
OK = os.environ.get("BUILD_OK") == "success"
now = datetime.datetime.now(datetime.timezone.utc).isoformat()


def patch(fields: dict) -> None:
    req = urllib.request.Request(
        f"{URL}/rest/v1/posts?id=eq.{PID}", data=json.dumps(fields).encode(), method="PATCH",
        headers={"apikey": KEY, "Authorization": f"Bearer {KEY}",
                 "Content-Type": "application/json", "Prefer": "return=minimal"})
    urllib.request.urlopen(req).read()


if OK and os.path.exists("out/rendered.html") and os.path.exists("out/meta.json"):
    meta = json.load(open("out/meta.json"))
    html = open("out/rendered.html").read()
    patch({
        "status": "published",
        "rendered_html": html,
        "title": meta.get("title") or "Untitled post",
        "summary": meta.get("summary"),
        "tags": meta.get("tags") or [],
        "has_strategy": bool(meta.get("has_strategy")),
        "build_log": None,
        "published_at": now,
        "updated_at": now,
    })
    print(f"published {PID}")
else:
    patch({"status": "failed",
           "build_log": "Build or render failed — see the workflow run logs.",
           "updated_at": now})
    print(f"marked failed {PID}")
