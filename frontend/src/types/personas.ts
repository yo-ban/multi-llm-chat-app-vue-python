export interface Persona {
    id: string;
    name: string;
    image: string;
    systemMessage: string;
}

export interface UserDefinedPersona extends Persona {
    custom: true;
}