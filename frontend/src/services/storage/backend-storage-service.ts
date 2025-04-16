import type { GlobalSettings } from '@/types/settings';
import type { StorageService } from './indexeddb-service'; // Import the interface

// Base URL for the backend API (adjust if necessary)
const API_BASE_URL = '/api'; 

/**
 * Implementation of StorageService that interacts with the backend API
 * for global settings. Other methods are not implemented as they still
 * rely on IndexedDB (for now).
 */
class BackendStorageService implements Partial<StorageService> {

  async getGlobalSettings(): Promise<GlobalSettings | null> {
    try {
      const response = await fetch(`${API_BASE_URL}/settings`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
          // Add authentication headers here if/when implemented
          // 'Authorization': `Bearer ${getToken()}` 
        },
      });

      if (!response.ok) {
        // Handle non-successful responses (e.g., 404 Not Found)
        if (response.status === 404) {
          console.warn('No settings found on backend, returning null.');
          return null; // Or return default settings if preferred
        }
        console.error(`Error fetching settings: ${response.status} ${response.statusText}`);
        // Consider throwing an error or returning null based on desired behavior
        // throw new Error(`Failed to fetch settings: ${response.status}`);
        return null; 
      }

      const settings: GlobalSettings = await response.json();
      // Ensure openrouterModels is always an array
      if (!settings.openrouterModels) {
        settings.openrouterModels = [];
      }
      return settings;
    } catch (error) { 
      console.error('Network or other error fetching global settings:', error);
      // Depending on requirements, might re-throw, return null, or defaults
      return null; 
    }
  }

  async saveGlobalSettings(settings: GlobalSettings): Promise<void> {
    try {
      console.log('Saving settings to backend:', JSON.stringify(settings));
      const response = await fetch(`${API_BASE_URL}/settings`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          // Add authentication headers here if/when implemented
          // 'Authorization': `Bearer ${getToken()}`
        },
        body: JSON.stringify(settings),
      });

      if (!response.ok) {
        console.error(`Error saving settings: ${response.status} ${response.statusText}`);
        const errorBody = await response.text(); // Try to get more details
        console.error('Error details:', errorBody);
        // Consider throwing an error to signal failure to the caller
        throw new Error(`Failed to save settings: ${response.status}`);
      }

      // Get the saved settings from response 
      const savedSettings = await response.json(); 
      console.log('Settings saved successfully. Response:', JSON.stringify(savedSettings));

    } catch (error) {
      console.error('Network or other error saving global settings:', error);
      // Re-throw the error so the calling code (e.g., Pinia store) knows about it
      throw error; 
    }
  }

  // --- Methods still using IndexedDB (or not implemented for backend yet) ---
  // Add stubs or references to indexedDbService for other methods if this 
  // service needs to fully implement StorageService later.
  // For now, we only implement the settings-related methods.

  // Example for unimplemented methods (if needed):
  // async getAllPersonas(): Promise<UserDefinedPersona[]> { throw new Error('Method not implemented.'); }
  // async savePersona(persona: UserDefinedPersona): Promise<void> { throw new Error('Method not implemented.'); }
  // ... and so on for personas, folders, conversations etc. 
}

// Singleton instance export
export const backendStorageService = new BackendStorageService(); 