"""
ユーザーリポジトリ

ユーザー関連のデータアクセスロジックを提供
"""
from typing import Optional
from sqlalchemy.orm import Session
from app.domain.user.models import User


class UserRepository:
    """
    ユーザーリポジトリ
    
    ユーザーエンティティのCRUD操作を提供します
    """
    
    def __init__(self, db: Session):
        """
        引数:
            db: SQLAlchemyセッション
        """
        self.db = db
    
    def get_by_id(self, user_id: int) -> Optional[User]:
        """
        IDによってユーザーを取得
        
        引数:
            user_id: ユーザーID
            
        戻り値:
            ユーザーが見つかればUserオブジェクト、なければNone
        """
        return self.db.query(User).filter(User.id == user_id).first()
    
    def create(self, user_id: int = 1) -> User:
        """
        ユーザーを作成
        
        引数:
            user_id: ユーザーID (デフォルト: 1)
            
        戻り値:
            作成されたUserオブジェクト
        """
        user = User(id=user_id)
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user 