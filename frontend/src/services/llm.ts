import type { Message } from '@/types/messages';
import { API_BASE_URL, API_MESSAGES_ENDPOINT } from '@/constants/api';
import { useSettingsStore } from '@/store/settings';
import type { APISettings } from '@/types/api';
import { WEB_SEARCH_TOOL_SUFFIX } from '@/constants/personas';
// import { MODELS } from '@/constants/models';
// import { getLastModelOfVendor } from '@/utils/model-utils';

// SSEレスポンスを処理する共通関数
async function processSSEResponse(
  response: Response,
  onUpdate?: (text: string, toolCall?: { type: string; status: 'start' | 'end' }, isIndicator?: boolean) => void
): Promise<string> {
  const reader = response.body?.getReader();
  if (!reader) {
    throw new Error('Response body is null or undefined');
  }

  const decoder = new TextDecoder('utf-8');
  let result = '';
  let stopReason = '';
  
  let done = false;
  while (!done) {
    const { value, done: readerDone } = await reader.read();
    done = readerDone;
    if (done) break;

    const chunk = decoder.decode(value);
    const lines = chunk.split('\n');

    for (const line of lines) {
      if (line.startsWith('data:')) {
        const data = JSON.parse(line.slice(5));
        if (data.error) {
          throw new Error(data.error);
        }
        if (data.text === '[DONE]') {
          // Ensure the final update is reflected
          if (onUpdate) {
            await new Promise(resolve => {
              onUpdate(result);
              setTimeout(resolve, 0);
            });
          }
          return result;
        }
        if (data.type === 'tool_call_start' && onUpdate) {
          onUpdate(result, { type: data.tool, status: 'start' }, true);
        } else if (data.stop_reason) {
          stopReason = data.stop_reason;
        } else if (data.text) {
          result += data.text;
          if (onUpdate) {
            onUpdate(result);
          }
        }
      }
    }
  }
  return result;
}

export async function sendMessageToAPI(
  messages: Message[], 
  system: string, 
  settings: APISettings, 
  onUpdate: (text: string, toolCall?: { type: string; status: 'start' | 'end' }, isIndicator?: boolean) => void,
  signal?: AbortSignal
) {

  try {
    const apiMessages = messages.map(({ role, text, images }) => ({
      role,
      text,
      images,
    }));
    console.log(API_BASE_URL);
    console.log(API_MESSAGES_ENDPOINT);

    const systemMessage = settings.websearch ? `${system}${WEB_SEARCH_TOOL_SUFFIX}` : system;

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
        multimodal: settings.multimodal
      }),
      signal
    });

    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(`HTTP error! status: ${response.status}, message: ${errorData.error}`);
    }

    return await processSSEResponse(response, onUpdate);
  } catch (error) {
    console.error('Error in sendMessage:', error);
    throw error;
  }
}


export async function generateChatTitle(messages: Message[]) {
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

    const result = await processSSEResponse(response);
    return result.trim();

  } catch (error) {
    console.error('Error in generateChatTitle:', error);
    throw error;
  }
}