import type { Message } from '@/types/messages';
import { API_BASE_URL, API_MESSAGES_ENDPOINT } from '@/constants/api';
import { useSettingsStore } from '@/store/settings';
import type { APISettings } from '@/types/api';
import type { ToolCall } from '@/types/tools';
import { REASONING_PREFIX_OPENAI } from '@/constants/personas';

/**
 * LLMサービスのインターフェース
 * APIとの通信を担当し、メッセージの送信と応答の処理を行う
 */
export interface LLMService {
  /**
   * メッセージをAPIに送信し、SSEレスポンスを処理する
   * @param messages 送信するメッセージリスト
   * @param system システムメッセージ
   * @param settings API設定
   * @param onUpdate レスポンス更新時のコールバック
   * @param signal 中断シグナル
   * @returns 完全なレスポンステキスト
   */
  sendMessageToAPI(
    messages: Message[], 
    system: string, 
    settings: APISettings, 
    onUpdate: (text: string, toolCall?: ToolCall, isIndicator?: boolean, image?: string) => void,
    signal?: AbortSignal
  ): Promise<string>;
  
  /**
   * 会話のタイトルを生成する
   * @param messages メッセージリスト
   * @returns 生成されたタイトル
   */
  generateChatTitle(messages: Message[]): Promise<string>;
}

/**
 * LLMサービスの実装クラス
 */
class LLMServiceImpl implements LLMService {
  /**
   * SSEレスポンスを処理する共通関数
   * @param response SSEレスポンス
   * @param onUpdate 更新コールバック
   * @returns 完全なレスポンステキスト
   */
  private async processSSEResponse(
    response: Response,
    onUpdate?: (text: string, toolCall?: ToolCall, isIndicator?: boolean, image?: string) => void
  ): Promise<string> {
    const reader = response.body?.getReader();
    if (!reader) {
      throw new Error('Response body is null or undefined');
    }

    const decoder = new TextDecoder('utf-8');
    let result = '';
    let stopReason = '';
    
    // For handling chunked image data
    let isCollectingImage = false;
    let imageChunks: string[] = [];
    let imageMimeType = '';
    
    let done = false;
    let buffer = '';

    // Helper function to process a single SSE line (starting with 'data:')
    async function processDataLine(line: string): Promise<boolean> {
      const dataString = line.slice(5).trim(); // Get content after 'data:' and trim whitespace
        
      // Handle empty data lines gracefully
      if (!dataString) {
          console.warn("Received empty SSE data line:", line);
          return false; // Skip processing this line
      }

      const data = JSON.parse(dataString); // Parse the JSON content

      // Handle the [DONE] marker which is not JSON
      if (data.text === '[DONE]') {
        if (onUpdate) {
          await new Promise(resolve => { onUpdate(result); setTimeout(resolve, 0); });
        }
        return true; // Signal completion
      }

      // Existing logic for processing parsed data...
      if (data.error) {
        throw new Error(data.error);
      }
      if (data.type === 'tool_call_start' && onUpdate) {
        onUpdate(result, { type: data.tool, status: 'start' }, true);
      } else if (data.type === 'tool_execution' && onUpdate) {
        // Store the input dictionary when it arrives during execution
        const toolCall: ToolCall = { type: data.tool, status: 'start', input: data.input }; 
        onUpdate(result, toolCall, true);
      } else if (data.type === 'tool_call_end' && onUpdate) {
        onUpdate(result, { type: data.tool, status: 'end' }, true);
      } else if (data.stop_reason) {
        stopReason = data.stop_reason;
        console.log("stopReason", stopReason);
      } else if (data.type === 'image_start') {
        isCollectingImage = true;
        imageChunks = [];
        imageMimeType = data.mime_type;
      } else if (data.type === 'image_chunk' && isCollectingImage) {
        imageChunks.push(data.chunk);
      } else if (data.type === 'image_end' && isCollectingImage) {
        const completeBase64 = imageChunks.join('');
        const dataUrl = `data:${imageMimeType};base64,${completeBase64}`;
        if (onUpdate) { onUpdate(result, undefined, undefined, dataUrl); }
        isCollectingImage = false;
        imageChunks = [];
      } else if (data.text) {
        result += data.text;
        if (onUpdate) { onUpdate(result); }
      } else if (data.usage) {
        console.log("usage", data.usage);
      }
      return false;
    }

    // Main loop to process SSE stream
    while (!done) {
      const { value, done: readerDone } = await reader.read();
      done = readerDone;
      if (value) {
        buffer += decoder.decode(value, { stream: true });
      }
      const lines = buffer.split('\n');
      // Keep the last partial line in the buffer
      buffer = lines.pop() || '';
      for (const line of lines) {
        if (line.startsWith('data:')) {
          if (await processDataLine(line)) {
            return result;
          }
        }
      }
    }

    // Process any remaining buffered text after the stream ends
    if (buffer.trim() !== '') {
      const remainingLines = buffer.split('\n');
      for (const line of remainingLines) {
        if (line.startsWith('data:')) {
          if (await processDataLine(line)) {
            return result;
          }
        }
      }
    }

    return result;
  }

  /**
   * メッセージをAPIに送信し、SSEレスポンスを処理する
   * @param messages 送信するメッセージリスト
   * @param system システムメッセージ
   * @param settings API設定
   * @param onUpdate レスポンス更新時のコールバック
   * @param signal 中断シグナル
   * @returns 完全なレスポンステキスト
   */
  async sendMessageToAPI(
    messages: Message[], 
    system: string, 
    settings: APISettings, 
    onUpdate: (text: string, toolCall?: ToolCall, isIndicator?: boolean, image?: string) => void,
    signal?: AbortSignal
  ): Promise<string> {
    try {
      const apiMessages = messages.map(({ role, text, images }) => ({
        role,
        text,
        images,
      }));
      console.log(API_BASE_URL);
      console.log(API_MESSAGES_ENDPOINT);
      console.log("API Settings:", settings);

      let systemMessage = system;
      // if (settings.websearch) {
      //   systemMessage = `${system}${WEB_SEARCH_TOOL_SUFFIX}`;
      // }

      if (settings.isReasoningSupported && settings.vendor === "openai") {
        systemMessage = `${REASONING_PREFIX_OPENAI}\n\n${systemMessage}`;
      }

      const response = await fetch(`${API_BASE_URL}${API_MESSAGES_ENDPOINT}`, {
        method: "POST",
        headers: {
          'Content-Type': 'application/json',
          'X-API-Key': useSettingsStore().apiKeys[settings.vendor]
        },
        body: JSON.stringify({
          system: systemMessage,
          messages: apiMessages,
          model: settings.model,
          maxTokens: settings.maxTokens,
          temperature: settings.temperature,
          stream: true,
          websearch: settings.websearch,
          reasoningEffort: settings.reasoningEffort,
          isReasoningSupported: settings.isReasoningSupported,
          multimodal: settings.multimodal,
          imageGeneration: settings.imageGeneration
        }),
        signal
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(`HTTP error! status: ${response.status}, message: ${errorData.error}`);
      }

      return await this.processSSEResponse(response, onUpdate);
    } catch (error) {
      console.error('Error in sendMessage:', error);
      throw error;
    }
  }

  /**
   * 会話のタイトルを生成する
   * @param messages メッセージリスト
   * @returns 生成されたタイトル
   */
  async generateChatTitle(messages: Message[]): Promise<string> {
    const settingsStore = useSettingsStore();

    try {
      const apiMessages = messages.map(({ role, text, images }) => ({
        role,
        text,
        images,
      }));

      const temperature = 0.7;
      const maxTokens = 512;
      const vendor = settingsStore.titleGenerationVendor;
      const model = settingsStore.titleGenerationModel;
      const system = "You are the AI of generating conversation titles.";
      apiMessages.push(
        { 
          role:"user", 
          text: "Based on your conversation history, create a short title, no more than 10 words, that is appropriate for this conversation. Titles should be created in the language used by the user. Do not output anything other than the title of the conversation. Avoid including unnecessary characters such as brackets or 'Title:'.",
          images: []
        }
      );
      
      const response = await fetch(`${API_BASE_URL}${API_MESSAGES_ENDPOINT}`, {
        method: "POST",
        headers: {
          'Content-Type': 'application/json',
          'X-API-Key': settingsStore.apiKeys[vendor]
        },
        body: JSON.stringify({
          system: system,
          messages: apiMessages,
          maxTokens: maxTokens,
          model: model,
          temperature: temperature,
          stream: false
        })
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(`HTTP error! status: ${response.status}, message: ${errorData.error}`);
      }

      const result = await this.processSSEResponse(response);
      return result.trim();

    } catch (error) {
      console.error('Error in generateChatTitle:', error);
      throw error;
    }
  }
}

// シングルトンインスタンスをエクスポート
export const llmService = new LLMServiceImpl(); 