from fastapi import Request, HTTPException, status
from jose import jwt, JWTError
import httpx

async def oidc_auth(request: Request):
    # Instead of an Authorization header, retrieve the session_id from cookies.
    session_id = request.cookies.get("session_id")
    if not session_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session cookie missing"
        )

    session = request.app.state.session_store.get(session_id)
    # Set in order to reset the TTL on use, creating an inactivity timeout
    request.app.state.session_store.set(session_id, session)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session"
        )

    # Retrieve the long token from the session.
    token = session.get("id_token")
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session does not contain token"
        )

    try:
        if request.app.state.jwkts_store.get("jwks"):
            jwks = request.app.state.jwkts_store.get("jwks")
        else:
            jwks_url = "https://auth-test.berkeley.edu/cas/oidc/jwks"
            async with httpx.AsyncClient() as client:
                jwks_response = await client.get(jwks_url)
                jwks_response.raise_for_status()
                jwks = jwks_response.json()

        issuer = "https://auth-test.berkeley.edu/cas/oidc"
        audience = "anthropology_folklore_archive"

        decoded = jwt.decode(
            token,
            jwks,
            algorithms=["RS256"],
            audience=audience,
            issuer=issuer,
            subject=session.get("uid"),
            access_token=session.get("access_token"),
        )
        request.state.user = decoded
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Token validation error: {str(e)}"
        )
    except httpx.HTTPError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"JWKS fetch error: {str(e)}"
        )