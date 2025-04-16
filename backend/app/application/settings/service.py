"""
設定サービス

設定ドメインのビジネスロジックを実装する
"""
from sqlalchemy.orm import Session
from typing import Dict

from app.domain.settings.repository import SettingsRepository
from app.domain.settings.schemas import SettingsCreate, SettingsResponse
from app.domain.settings.models import UserSettings # Type hinting用


class SettingsService:
    """
    設定関連のビジネスロジックを提供するサービスクラス
    """
    
    def __init__(self, db: Session):
        """
        引数:
            db: SQLAlchemyセッション
        """
        self.settings_repo = SettingsRepository(db)
    
    def get_settings_for_user(self, user_id: int) -> SettingsResponse:
        """
        ユーザーの設定を取得する。
        存在しない場合はデフォルト設定を作成して返す。
        
        引数:
            user_id: ユーザーID
            
        戻り値:
            設定のレスポンスモデル (SettingsResponse)
        """
        db_settings = self.settings_repo.get_by_user_id(user_id)
        
        if db_settings is None:
            # 設定が存在しない場合はデフォルト値で作成
            default_settings_data = SettingsCreate()
            db_settings = self.settings_repo.create_or_update(
                user_id=user_id,
                **default_settings_data.model_dump(by_alias=False) # DB列名で渡す
            )
        
        # APIキーを復号化してレスポンスモデルを作成
        api_keys = self.settings_repo.decrypt_api_keys(db_settings)
        response_data = self._prepare_response_data(db_settings, api_keys)
        return SettingsResponse.model_validate(response_data)
        
    def update_settings_for_user(self, user_id: int, settings_data: SettingsCreate) -> SettingsResponse:
        """
        ユーザーの設定を更新する。
        
        引数:
            user_id: ユーザーID
            settings_data: 更新する設定データ (SettingsCreate)
            
        戻り値:
            更新された設定のレスポンスモデル (SettingsResponse)
        """
        # リポジトリを使用して設定を作成または更新
        db_settings = self.settings_repo.create_or_update(
            user_id=user_id,
            **settings_data.model_dump(by_alias=False) # DB列名で渡す
        )
        
        # APIキーを復号化してレスポンスモデルを作成
        api_keys = self.settings_repo.decrypt_api_keys(db_settings)
        response_data = self._prepare_response_data(db_settings, api_keys)
        return SettingsResponse.model_validate(response_data)

    def _prepare_response_data(self, db_settings: UserSettings, api_keys: Dict[str, str]) -> Dict:
        """
        データベースモデルと復号化されたAPIキーからレスポンス用辞書を作成するヘルパー
        
        引数:
            db_settings: UserSettingsモデルインスタンス
            api_keys: 復号化されたAPIキーの辞書
        
        戻り値:
            レスポンススキーマに渡すための辞書
        """
        response_data = SettingsResponse.model_validate(db_settings).model_dump(by_alias=True)
        response_data['apiKeys'] = api_keys
        if response_data.get('openrouterModels') is None:
            response_data['openrouterModels'] = []
        return response_data 