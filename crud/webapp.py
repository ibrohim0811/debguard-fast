from typing import List, Optional
from sqlalchemy.orm import Session
from models import WebApplications


def create_webapp(domain: str, user_id: int, title: str, is_subdomain: Optional[bool], db: Session) -> WebApplications:
    webapp = WebApplications(
        domain=domain,
        user_id=user_id,
        title=title,
        is_subdomain=is_subdomain | False
    )
    db.add(webapp)
    db.commit()
    db.refresh(webapp)  
    return webapp


def get_webapps(user_id: int, db: Session) -> List[WebApplications]:
    return db.query(WebApplications).filter(WebApplications.user_id == user_id).all()


def get_webapp_slug(slug: str, db: Session) -> Optional[WebApplications]:
    return db.query(WebApplications).filter(WebApplications.slug == slug).first()


def delete_webapp(slug: str, db: Session) -> bool:
    webapp = db.query(WebApplications).filter(WebApplications.slug == slug).first()
    if webapp:
        db.delete(webapp)
        db.commit()
        return True
    return False