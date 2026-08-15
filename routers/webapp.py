from fastapi import APIRouter, HTTPException, status, Depends
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from database import get_db
from core.deps import get_current_user
from crud.webapp import get_webapps, create_webapp, get_webapp_slug, delete_webapp
from models import Users
from schemas.webapp import WebappCreateSchema
from validation import is_subdomain, validate_url

router = APIRouter(tags=["webapps"])


@router.get("/webapps")
def get_webapps_router(db: Session = Depends(get_db), user: Users = Depends(get_current_user)):
    webapps = get_webapps(user_id=user.id, db=db)
    return webapps


@router.post("/webapp", status_code=status.HTTP_201_CREATED)
def create_webapp_router(
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
        create_webapp(
            domain=data.domain,
            user_id=user.id,
            title=data.title,
            is_subdomain=subdomain_check,
            db=db
        )
        return {"message": f"{data.title} saqlandi!"}

    except IntegrityError:
        db.rollback()  # Xatolikdan keyin seansni tozalaymiz
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Ushbu domain allaqachon ro'yxatdan o'tkazilgan!"
        )
    except Exception as e:
        db.rollback()
        print(f"Xatolik: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail="Nimadir xato ketdi, qaytadan urinib ko'ring!"
        )

    
@router.get("/webapp/{slug}")
def get_webapp_router(slug: str, db: Session = Depends(get_db)):
    webapp = get_webapp_slug(slug=slug, db=db)
    if webapp:
        return webapp
    else:
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Web loyihangiz topilmadi!")


@router.delete("/webapp/{slug}")
def delete_webapp_router(slug: str, db: Session = Depends(get_db)):
    webapp = get_webapp_slug(slug=slug, db=db)
    if webapp:
        delete_webapp(webapp, db=db)
        return {"message":"O'chirildi", "status":status.HTTP_204_NO_CONTENT}
    return {"message":"Web loyiha topilmadi", "status":status.HTTP_404_NOT_FOUND}