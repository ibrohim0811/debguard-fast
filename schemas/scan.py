import sys
from pydantic import BaseModel
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


from models import ScanType

class ScanSchema(BaseModel):
    webapp_id: int



class ScanCreateSchema(BaseModel):
    slug: str