import argparse
import sys
import app.main
from sqlalchemy import select,func

from app.database import SessionLocal
from app.models.user import User
from app.models.contract import Contract
from app.models.certificate import Certificate
from app.models.identity_document import IdentityDocument
from app.models.user_identity import UserIdentity
from app.services.account_deletion import delete_user

def find_user(
        db,
        email
):
    email=email.strip().lower()
    query=select(User).where(User.email==email)
    user=db.scalar(query)
    if user is None:
        print("No account with that email")
        sys.exit(1)
    return user
def cmd_users(db):
    all_users=db.scalars(select(User).order_by(User.id.desc())).all()
    print(f"There are {len(all_users)} accounts")
    for user in all_users:
        
        print(f"id:{user.id}")
        print(f"email:{user.email}")
        print(f"created_at:{user.created_at}")
        print(f"has_password:{'yes' if user.hashed_password is not None else 'no'}")

def cmd_show(db,email):
    user=find_user(db,email)
    contracts=db.scalar(select(func.count()).select_from(Contract).where(Contract.user_id==user.id))
    certificates=db.scalar(select(func.count()).select_from(Certificate).where(Certificate.user_id==user.id))
    documents=db.scalar(select(func.count()).select_from(IdentityDocument).where(IdentityDocument.user_id==user.id))
    providers=db.scalars(select(UserIdentity.provider).where(UserIdentity.user_id==user.id)).all()

    print(f"#{user.id}  {user.email}")
    print(f" created: {user.created_at:%Y-%m-%d}")
    print(f" password:{'yes' if user.hashed_password is not None else 'no'}")
    print(f" sign-in-with: {', '.join(providers) or '-'}")
    print(f" contracts:{contracts} certificates {certificates} documents:{documents}")
    return user

def cmd_delete(db,email):
    user=cmd_show(db,email)
    typed=input("Type the email again to delete this account :")
    deleted_email=user.email
    if typed.strip().lower() != user.email:
        print("Not deleted")
        sys.exit(1)
    delete_user(db,user,by="admin")
    print(f"{deleted_email} account has been deleted.")

def main():
    parser=argparse.ArgumentParser(description="Sefername Admin")
    sub=parser.add_subparsers(dest="command",required=True)
    sub.add_parser("users")
    show=sub.add_parser("show")
    show.add_argument("email")
    delete=sub.add_parser("delete")
    delete.add_argument("email")

    args=parser.parse_args()
    db=SessionLocal()
    try:
        if args.command=="users":
            cmd_users(db)
        elif args.command == "show":
            cmd_show(db,args.email)
        elif args.command == "delete":
            cmd_delete(db,args.email)
    finally:
        db.close()
if __name__ == "__main__":
    main()


