from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

security_scheme = HTTPBearer(auto_error=False)

class Principal:
    def __init__(self, principal_id: str, tenant_id: str | None = None, app_id: str | None = None, roles: list[str] | None = None):
        self.principal_id = principal_id
        self.tenant_id = tenant_id
        self.app_id = app_id
        self.roles = roles or []

async def get_current_principal(
    credentials: HTTPAuthorizationCredentials | None = Depends(security_scheme),
) -> Principal:
    # NOTE: Placeholder – hier später echte JWT-Validierung einbauen.
    if credentials is None:
        # Für lokale Entwicklung erlauben wir anonyme Requests
        return Principal(principal_id="anonymous")
    token = credentials.credentials
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    # TODO: Token parsen
    return Principal(principal_id="token-user")
