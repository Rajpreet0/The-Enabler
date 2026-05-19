

export interface EntityMeta {
    label: string;
    color: string;
    anonymizeLabel: string;
} 

/**
 * Definition of Entities used for identifiying PII and anonymising it
 */
export const ENTITY_CONFIG: Record<string, EntityMeta> = {
  PERSON:        { 
    label: "Person",  
    color: "bg-red-100 text-red-700 border-red-200",
    anonymizeLabel: "[PERSON]"
 },
  EMAIL_ADDRESS: { 
    label: "E-Mail",  
    color: "bg-blue-100 text-blue-700 border-blue-200",
    anonymizeLabel: "[EMAIL]"
 },
  PHONE_NUMBER:  { 
    label: "Telefon", 
    color: "bg-yellow-100 text-yellow-700 border-yellow-200",
    anonymizeLabel: "[TELEFON]"
 },
  LOCATION:      { 
    label: "Ort",     
    color: "bg-green-100 text-green-700 border-green-200",
    anonymizeLabel: "[ORT]"
 },
  IBAN_CODE:     { 
    label: "IBAN",    
    color: "bg-purple-100 text-purple-700 border-purple-200",
    anonymizeLabel: "[IBAN]"
 },
  ORGANIZATION:  { 
    label: "Firma",   
    color: "bg-orange-100 text-orange-700 border-orange-200",
    anonymizeLabel: "[FIRMA]"
 },
  ADDRESS:       { 
    label: "Adresse", 
    color: "bg-amber-100 text-amber-700 border-amber-200",
    anonymizeLabel: "[ADRESSE]"
 },
};

export const getEntitiyMeta = (type: string): EntityMeta => {
    return (
        ENTITY_CONFIG[type] ?? {
            label: type,
            color: "bg-muted text-foreground border-border",
            anonymizeLabel: `[${type}]`,
        }
    )
}