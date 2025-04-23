import uuid
import httpx
from fastapi import APIRouter, Request, HTTPException, status
from fastapi.responses import RedirectResponse

router = APIRouter()

@router.get("/login")
async def login(request: Request):
    authorization_url = (
        f"{request.app.auth.authority_url}/oidcAuthorize?response_type=code&client_id={request.app.auth.client_id}"
        f"&redirect_uri={request.app.auth.redirect_url}%2Fauth%2Fcallback&scope=openid%20profile%20berkeley_edu_default"
    )
    return RedirectResponse(authorization_url)

# OIDC Callback Route
@router.get("/callback")
async def callback(request: Request, code: str):
    # Exchange the authorization code for tokens.
    async with httpx.AsyncClient() as client:
        token_response = await client.post(
            f"{request.app.auth.authority_url}/oidcAccessToken",
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": request.app.auth.redirect_url,
                "client_id": request.app.auth.client_id,
                "client_secret": request.app.auth.client_secret,
            },
        )
    token_data = token_response.json()
    if token_response.status_code != 200:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid token request"
        )

    access_token = token_data.get("access_token")
    id_token = token_data.get("id_token")

    # Retrieve user info from the OIDC provider.
    async with httpx.AsyncClient() as client:
        user_response = await client.get(
            f"{request.app.auth.authority_url}/oidcProfile",
            headers={"Authorization": f"Bearer {access_token}"}
        )
    user_info = user_response.json()

    # Prepare the payload (this could include additional data).
    payload = {"user_info": user_info, "id_token": id_token, "access_token": access_token}

    # Generate a short session ID and store the payload.
    session_id = str(uuid.uuid4())
    request.app.state.session_store.set(session_id, payload)

    # Redirect to the frontend.
    frontend_url = request.app.auth.frontend_url
    response = RedirectResponse(url=f"{frontend_url}/callback")

    # Set a cookie with the session id.
    response.set_cookie(
        key="session_id",
        value=session_id,
        httponly=True,  # Prevents JavaScript access (more secure)
        secure=True,
        samesite="lax",
        max_age=1800  # 30 mins
    )
    return response

@router.get("/current-user")
async def current_user(request: Request):
    session_id = request.cookies.get("session_id")
    if not session_id or session_id not in request.app.state.session_store:
        raise HTTPException(status_code=401, detail="Unauthenticated")
    return request.app.state.session_store.get(session_id)
@router.get("/logout")
async def logout(request: Request):
    # Remove the session from the store
    session_id = request.cookies.get("session_id")

    if session_id and session_id in request.app.state.session_store:
        request.app.state.session_store.delete(session_id)
        id_token = request.app.state.session_store.get(session_id).get("id_token")
        logout_url = (
            f"{request.app.auth.authority_url}/oidcLogout?id_token_hint={id_token}"
            f"&post_logout_redirect_uri={request.app.auth.frontend_url}"
        )
    else:
        logout_url = (
            f"{request.app.auth.authority_url}/oidcLogout"
        )

    return RedirectResponse(logout_url)