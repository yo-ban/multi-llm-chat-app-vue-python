import { defineStore } from 'pinia';
import { getUserDefinedPersonas, saveUserDefinedPersonas } from '@/services/indexeddb';
import type { UserDefinedPersona } from '@/types/personas';
import { saveAs } from 'file-saver';

export const usePersonaStore = defineStore('persona', {
  state: () => ({
    showPersonasManagement: false,
    userDefinedPersonas: [] as UserDefinedPersona[],
  }),
  actions: {
    async loadUserDefinedPersonas() {
      if (this.userDefinedPersonas.length === 0) {
        this.userDefinedPersonas = await getUserDefinedPersonas();
      }
    },

    async addPersona(persona: UserDefinedPersona) {
      this.userDefinedPersonas.push(persona);
      await this.savePersonas();
    },

    async updatePersona(personaId: string, updatedPersona: Partial<UserDefinedPersona>) {
      const index = this.userDefinedPersonas.findIndex(p => p.id === personaId);
      if (index !== -1) {
        this.userDefinedPersonas[index] = { ...this.userDefinedPersonas[index], ...updatedPersona };
        await this.savePersonas();
      }
    },

    async deletePersona(personaId: string) {
      this.userDefinedPersonas = this.userDefinedPersonas.filter(p => p.id !== personaId);
      await this.savePersonas();
    },

    async savePersonas() {
      await saveUserDefinedPersonas(this.userDefinedPersonas);
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
            this.addPersona(importedPersona);
          };
          reader.readAsText(file);
        }
      };
      input.click();
    },

    togglePersonasManagement() {
      this.showPersonasManagement = !this.showPersonasManagement;
    },
    
    setShowPersonasManagement(value: boolean) {
      this.showPersonasManagement = value;
    },
  },
});
