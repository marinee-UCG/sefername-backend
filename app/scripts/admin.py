import argparse
import sys
import app.main
from sqlalchemy import select,func,
from sqlalchemy.orm import Session
from app.database import SessionLocal,get_db,
from app.core.deps import get_current_user
from app.models.user import User
from app.models.contract import Contract
from app.models.certificate import Certificate
from app.models.identity_document import IdentityDocument
from app.models.vessel import Vessel
from app.models.user_identity import UserIdentity
from app.services.account_deletion import delete_user

def find_user(
        db:Session,
        
):
