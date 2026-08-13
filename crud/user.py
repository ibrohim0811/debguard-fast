from sqlalchemy.orm import Session

from models import Users

def get_user_by_email(email: str, db: Session):
    """Email bo'yicha foydalanuvchini qaytaradi (yoki None)."""
    return db.query(Users).filter(Users.email == email).first()


def get_user_by_phone_number(phone_number: str, db: Session):
    """Email bo'yicha foydalanuvchini qaytaradi (yoki None)."""
    return db.query(Users).filter(Users.phone_number == phone_number).first()


def create_user(full_name: str, phone_number: str, email: str, password: str, db: Session):
    new_user = Users(
        full_name=full_name,
        phone_number=phone_number,
        email=email,
        password=password
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user