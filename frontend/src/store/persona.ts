import { defineStore } from 'pinia';
import { storageService } from '@/services/storage/indexeddb-service';
import type { UserDefinedPersona } from '@/types/personas';
import { saveAs } from 'file-saver';
import { v4 as uuidv4 } from 'uuid';

export const usePersonaStore = defineStore('persona', {
  state: () => ({
    showPersonasManagement: false,
    userDefinedPersonas: [] as UserDefinedPersona[],
  }),
  actions: {
    async loadUserDefinedPersonas() {
      // Load all personas from storage service
      this.userDefinedPersonas = await storageService.getAllPersonas();
    },

    async addPersona(persona: UserDefinedPersona) {
      // Assume persona object is complete and valid
      // Add to local state first for UI responsiveness
      this.userDefinedPersonas.push(persona);
      // Save the individual persona to storage
      await storageService.savePersona(persona);
    },

    async updatePersona(personaId: string, updatedFields: Partial<UserDefinedPersona>) {
      const index = this.userDefinedPersonas.findIndex(p => p.id === personaId);
      if (index !== -1) {
        // Update local state
        this.userDefinedPersonas[index] = { 
          ...this.userDefinedPersonas[index], 
          ...updatedFields 
        };
        // Save the updated individual persona to storage
        await storageService.savePersona(this.userDefinedPersonas[index]);
      }
    },

    async deletePersona(personaId: string) {
      // Remove from local state
      this.userDefinedPersonas = this.userDefinedPersonas.filter(p => p.id !== personaId);
      // Delete the individual persona from storage
      await storageService.deletePersona(personaId);
    },

    async exportPersona(persona: UserDefinedPersona) {
      const jsonString = JSON.stringify(persona, null, 2);
      const blob = new Blob([jsonString], { type: 'application/json;charset=utf-8' });
      saveAs(blob, `${persona.name}.json`);
    },

    async importPersona() {
      const input = document.createElement('input');
      input.type = 'file';
      input.accept = '.json';
      input.onchange = async (event: Event) => {
        const file = (event.target as HTMLInputElement).files?.[0];
        if (file) {
          const reader = new FileReader();
          reader.onload = async (e) => {
            const importedPersona = JSON.parse(e.target?.result as string) as UserDefinedPersona;
            const personaWithNewId = {
              ...importedPersona,
              id: `persona-${uuidv4()}`
            };
            this.addPersona(personaWithNewId);
          };
          reader.readAsText(file);
        }
      };
      input.click();
    },

    async duplicatePersona(personaId: string) {
      try {
        // 複製するペルソナを検索
        const personaToDuplicate = this.userDefinedPersonas.find(
          p => p.id === personaId
        );
        
        if (!personaToDuplicate) {
          throw new Error(`Persona with ID ${personaId} not found`);
        }
        
        // 新しいペルソナIDを生成
        const newPersonaId = `persona-${uuidv4()}`;
        
        // ペルソナのディープコピーを作成
        const duplicatedPersona: UserDefinedPersona = {
          ...JSON.parse(JSON.stringify(personaToDuplicate)), // ディープコピー
          id: newPersonaId,
          name: `Copy ${personaToDuplicate.name}`
        };
        
        // Add the duplicated persona to local state and save it individually
        await this.addPersona(duplicatedPersona);
        
        return newPersonaId;
      } catch (error) {
        console.error('Error duplicating persona:', error);
        throw error;
      }
    },

    togglePersonasManagement() {
      this.showPersonasManagement = !this.showPersonasManagement;
    },
    
    setShowPersonasManagement(value: boolean) {
      this.showPersonasManagement = value;
    },
  },
});
