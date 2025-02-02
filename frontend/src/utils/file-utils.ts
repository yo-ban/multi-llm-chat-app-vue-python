import { API_BASE_URL, API_EXTRACT_ENDPOINT } from '@/constants/api';

export const extractTextFromFile = async (file: File): Promise<string> => {

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

};
