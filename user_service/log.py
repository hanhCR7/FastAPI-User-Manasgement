from databases import db_dependency
from models import Log
from fastapi.encoders import jsonable_encoder
def log_user_action(db: db_dependency, user_id: int, action: str):
    new_log =  Log(user_id=user_id, action=action)
    db.add(new_log)
    db.commit()
    db.refresh(new_log)
    return {
        "detail": "User action logged successfully",
        "log": jsonable_encoder(new_log) 
    }
def get_log_user(db: db_dependency, user_id: int):
    logs = db.query(Log).filter(Log.user_id == user_id).order_by(Log.timestamp.desc()).all()
    return {
        "detail": "User logs retrieved successfully",
        "logs": jsonable_encoder(logs)
    }
