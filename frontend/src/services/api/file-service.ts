import { API_BASE_URL, API_EXTRACT_ENDPOINT } from '@/constants/api';

/**
 * ファイル処理に関するAPIサービスのインターフェース
 */
export interface FileService {
  /**
   * ファイルからテキストを抽出するAPIを呼び出す
   * @param file 抽出するファイル
   * @returns 抽出されたテキスト
   */
  extractTextFromFile(file: File): Promise<string>;
  // 将来的に追加される可能性のあるメソッド
}

/**
 * FileServiceの実装クラス
 */
class FileServiceImpl implements FileService {
  /**
   * ファイルからテキストを抽出するAPIを呼び出す
   * @param file 抽出するファイル
   * @returns 抽出されたテキスト
   */
  async extractTextFromFile(file: File): Promise<string> {
    const formData = new FormData();
    formData.append('file', file);
    
    const response = await fetch(`${API_BASE_URL}${API_EXTRACT_ENDPOINT}`, {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(`API error: ${response.status}, message: ${errorData.error}`);
    }

    const data = await response.json();

    if (data.error) {
      throw new Error(`API error: ${data.error}`);
    }

    return data.text;
  }
}

// シングルトンインスタンスをエクスポート
export const fileService = new FileServiceImpl(); 