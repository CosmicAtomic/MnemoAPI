import schemathesis
import requests
import uuid

# ==============================================================================
# SCHEMATHESIS RUN INSTRUCTION
# ==============================================================================
# export SCHEMATHESIS_HOOKS="performance/schemathesis_hook.py"

# schemathesis run http://localhost:8000/openapi.json \
#   --checks=not_a_server_error,response_schema_conformance
# ==============================================================================

TEST_EMAIL = f"schemathesis_{uuid.uuid4().hex[:8]}@example.com"
TEST_PASSWORD = "Password123!"
AUTH_DATA = {}  
BASE = "http://localhost:8000"
PUBLIC_PATHS = {"/auth/signup", "/auth/login"}

def get_cached_auth():
    global AUTH_DATA
    if not AUTH_DATA:
        requests.post(f"{BASE}/auth/signup",
                      json={"email": TEST_EMAIL, "password": TEST_PASSWORD})
        resp = requests.post(f"{BASE}/auth/login",
                             json={"email": TEST_EMAIL, "password": TEST_PASSWORD})
        assert resp.status_code == 200, resp.text   # fail loudly, not as a wall of 401s
        AUTH_DATA = {"jwt": f"Bearer {resp.json()['access_token']}"}
    return AUTH_DATA

@schemathesis.hook
def before_call(ctx, case, kwargs):
    if case.path in PUBLIC_PATHS:
        return
    if case.headers is None:
        case.headers = {}
    case.headers["Authorization"] = get_cached_auth()["jwt"]