"""
設定サービス

設定ドメインのビジネスロジックを実装する
"""
from sqlalchemy.orm import Session
from typing import Dict, Optional

from app.domain.settings.repository import SettingsRepository
from app.domain.settings.schemas import SettingsCreate, SettingsResponse
from app.domain.settings.models import UserSettings # Type hinting用
from app.domain.settings.constants import KNOWN_VENDORS # Import known vendors


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
        
        # APIキーを復号化
        decrypted_api_keys = self.settings_repo.decrypt_api_keys(db_settings)

        # レスポンスデータを準備 (KNOWN_VENDORS を使って status を生成)
        response_data = self._prepare_response_data(db_settings, decrypted_api_keys)

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
        
        # APIキーを復号化
        decrypted_api_keys = self.settings_repo.decrypt_api_keys(db_settings)
        
        # レスポンスデータを準備 (KNOWN_VENDORS を使って status を生成)
        response_data = self._prepare_response_data(db_settings, decrypted_api_keys)
        
        return SettingsResponse.model_validate(response_data)

    def get_decrypted_api_key(self, user_id: int, vendor: str) -> Optional[str]:
        """
        指定されたユーザーとベンダーの復号化されたAPIキーを取得する。

        引数:
            user_id: ユーザーID
            vendor: APIキーを取得するベンダー名

        戻り値:
            復号化されたAPIキー文字列、または見つからない場合はNone
        """
        db_settings = self.settings_repo.get_by_user_id(user_id)
        if not db_settings:
            return None
        
        decrypted_api_keys = self.settings_repo.decrypt_api_keys(db_settings)
        return decrypted_api_keys.get(vendor)

    def _prepare_response_data(self, db_settings: UserSettings, decrypted_api_keys: Dict[str, str]) -> Dict:
        """
        データベースモデルと復号化されたAPIキーからレスポンス用辞書を作成するヘルパー
        
        引数:
            db_settings: UserSettingsモデルインスタンス
            decrypted_api_keys: 復号化されたAPIキーの辞書
        
        戻り値:
            レスポンススキーマに渡すための辞書
        """
        # UserSettingsモデルからSettingsResponseに必要な基本データを取得
        response_data = SettingsResponse.model_validate(db_settings).model_dump(by_alias=True)

        # KNOWN_VENDORS に基づいて APIキーの状態 (boolean) を生成
        api_keys_status = { 
            vendor: bool(decrypted_api_keys.get(vendor)) 
            for vendor in KNOWN_VENDORS
        }
        
        response_data['apiKeys'] = api_keys_status # 生成した boolean の辞書を設定
        
        # openrouterModels が None の場合に空リストを設定 (安全のため)
        if response_data.get('openrouterModels') is None:
            response_data['openrouterModels'] = []
        
        return response_data