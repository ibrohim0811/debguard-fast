import logging
import requests
from fastapi import APIRouter, HTTPException, status, Depends
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from bs4 import BeautifulSoup
import httpx


from database import get_db, AsyncSession
from core.deps import get_current_user
from crud.webapp import get_webapps, create_webapp, get_webapp_slug, delete_webapp
from models import Users
from schemas.webapp import WebappCreateSchema
from validation import is_subdomain, validate_url, validate_safe_url_or_domain

router = APIRouter(tags=["webapps"])
logger = logging.getLogger(__name__)


@router.get("/webapps")
async def get_webapps_router(db: Session = Depends(get_db), user: Users = Depends(get_current_user)):
    webapps = await get_webapps(user_id=user.id, db=db)
    return webapps


@router.post("/webapp", status_code=status.HTTP_201_CREATED)
async def create_webapp_router(
    data: WebappCreateSchema, 
    db: Session = Depends(get_db), 
    user: Users = Depends(get_current_user)
):
    validation_result = validate_url(data.domain)
    
    if not validation_result if isinstance(validation_result, bool) else not validation_result.get("is_valid"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Berilgan domain xato formatda!"
        )

    subdomain_check = is_subdomain(data.domain)

    try:
        await create_webapp(
            domain=data.domain,
            user_id=user.id,
            title=data.title,
            is_subdomain=subdomain_check,
            db=db
        )
        return {"message": f"{data.title} saqlandi!"}

    except IntegrityError:
        await db.rollback()  # Xatolikdan keyin seansni tozalaymiz
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Ushbu domain allaqachon ro'yxatdan o'tkazilgan!"
        )
    except Exception as e:
        await db.rollback()
        print(f"Xatolik: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail="Nimadir xato ketdi, qaytadan urinib ko'ring!"
        )

    
@router.get("/webapp/{slug}")
async def get_webapp_router(slug: str, db: Session = Depends(get_db), user: Session = Depends(get_current_user)):
    webapp = await get_webapp_slug(slug=slug.strip(), user_id=user.id, db=db)
    if webapp:
        return webapp
    else:
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Web loyihangiz topilmadi!")


@router.delete("/webapp/{slug}")
async def delete_webapp_router(slug: str, db: Session = Depends(get_db), user: Session = Depends(get_current_user)):
    webapp = await get_webapp_slug(slug=slug, user_id=user.id, db=db)
    if webapp:
        await delete_webapp(webapp, db=db)
        return {"message":"O'chirildi", "status":status.HTTP_204_NO_CONTENT}
    return {"message":"Web loyiha topilmadi", "status":status.HTTP_404_NOT_FOUND}


@router.get("/webapp/check/{slug}")
async def check_webtoken(
    slug: str, 
    db: AsyncSession = Depends(get_db), 
    user = Depends(get_current_user) # AsyncSession emas, User modeli bo'ladi
):
    # 1. Bazadan asinxron olish (get_webapp_slug ham async bo'lishi va await ishlatilishi kerak)
    webapp = await get_webapp_slug(slug=slug, user_id=user.id, db=db)
    if not webapp:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Web sahifa topilmadi")

    if webapp.is_verified:
        return {"message": "Websahifangiz allaqachon tasdiqlangan"}

    is_safe, safe_msg_or_host = validate_safe_url_or_domain(webapp.domain)
    if not is_safe:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Domen tekshirib bo'linmadi yoki rad etildi: {safe_msg_or_host}"
        )

    target_domain = webapp.domain
    if not target_domain.startswith(('http://', 'https://')):
        target_domain = f"https://{target_domain}"

    token = webapp.verification_token
    headers = {'User-Agent': 'DevGuard-Scanner/1.0'}

    # 2. httpx.AsyncClient orqali asinxron so'rov yuborish
    async with httpx.AsyncClient(timeout=7.0, follow_redirects=True) as client:
        # A) Meta tag tekshiruvi
        try:
            html_response = await client.get(target_domain, headers=headers)
            if html_response.status_code == 200:
                soup = BeautifulSoup(html_response.text, 'html.parser')
                meta_tag = soup.find('meta', attrs={'name': 'devguard'})

                if meta_tag and meta_tag.get('content') == token:
                    webapp.is_verified = True
                    await db.commit() # Asinxron saqlash
                    return {"message": "Veb-saytingiz HTML Meta-tag orqali tasdiqlandi 🎉"}
        except httpx.RequestError as e:
            logger.warning(f"Meta tag tekshirishda ulanish xatoligi ({target_domain}): {e}")

        # B) API Endpoint tekshiruvi
        api_url = f"{target_domain.rstrip('/')}/devguard/"
        try:
            api_response = await client.get(api_url, headers=headers)
            if api_response.status_code == 200:
                try:
                    data = api_response.json()
                    if data.get("devguard") == token:
                        webapp.is_verified = True
                        await db.commit() # Asinxron saqlash
                        return {"message": "Veb-saytingiz /devguard API endpointi orqali tasdiqlandi 🎉"}
                except Exception:
                    pass
        except httpx.RequestError as e:
            logger.warning(f"API Endpoint tekshirishda ulanish xatoligi ({api_url}): {e}")

    # Ikkalasi ham o'xshamasa xatolik qaytarish
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=(
            "Tasdiqlash amalga oshmadi ⛔. "
            "Sayt HTML qismiga <meta name=\"devguard\" content=\"YOUR_TOKEN\"> tegi qo'shilganini "
            "yoki /devguard endpointi {'devguard': 'YOUR_TOKEN'} shaklida JSON qaytarayotganini tekshiring!"
        )
    )